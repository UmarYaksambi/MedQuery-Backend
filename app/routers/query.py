import os
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from openai import OpenAI

from .. import models, dependencies
from ..auth_utils import role_required, get_current_user # Import security helpers

# Initialize Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter(prefix="/query", tags=["Query"])

# --- Enhanced Prompts ---

SQL_GENERATION_PROMPT = """
You are a Clinical Data Scientist and SQL Expert for the MedQuery platform. 
Your goal is to translate natural language questions from clinicians into valid, read-only MySQL queries for the MIMIC-IV demo(version2.2) database.

### FULL DATABASE SCHEMA & RELATIONSHIPS:

1. CORE MODULE:
   - `patients`: {subject_id (PK), gender, anchor_age, anchor_year, anchor_year_group, dod (date of death)}.
   - `admissions`: {hadm_id (PK), subject_id (FK -> patients), admittime, dischtime, deathtime, admission_type, admission_location, discharge_location, insurance, language, marital_status, race, hospital_expire_flag (1=died)}.
   - `transfers`: {transfer_id (PK), subject_id (FK -> patients), hadm_id (FK -> admissions), eventtype, careunit, intime, outtime}.

2. HOSP MODULE:
   - `diagnoses_icd`: {subject_id (FK -> patients), hadm_id (FK -> admissions), seq_num, icd_code, icd_version (9 or 10)}.
   - `procedures_icd`: {subject_id (FK -> patients), hadm_id (FK -> admissions), seq_num, chartdate, icd_code, icd_version}.
   - `prescriptions`: {subject_id (FK -> patients), hadm_id (FK -> admissions), drug, drug_type, starttime, stoptime, dose_val_rx, dose_unit_rx, route}.
   - `labevents`: {labevent_id (PK), subject_id (FK -> patients), hadm_id (FK -> admissions), itemid (FK -> d_labitems), charttime, value, valuenum, valueuom, flag}.
   - `d_labitems`: {itemid (PK), label, fluid, category}.

3. ICU MODULE:
   - `icustays`: {stay_id (PK), subject_id (FK -> patients), hadm_id (FK -> admissions), first_careunit, last_careunit, intime, outtime, los (length of stay)}.
   - `chartevents`: {subject_id (FK -> patients), hadm_id (FK -> admissions), stay_id (FK -> icustays), charttime, itemid, value, valuenum, valueuom}.

### CLINICAL LOGIC RULES:
- To find a specific lab (e.g., "glucose"), you MUST join 'labevents' with 'd_labitems' and filter by 'd_labitems.label'.
- "Mortality" or "Died" refers to 'hospital_expire_flag = 1' in the 'admissions' table.
- "Abnormal" results are identified by 'flag = "abnormal"' in the 'labevents' table.
- Date differences for "Length of Stay" should use the 'los' column in 'icustays' or 'TIMESTAMPDIFF' on 'admittime' and 'dischtime'.

### CRITICAL SQL RULES:
- **Join Path for Labs:** JOIN `labevents` with `d_labitems` ON `itemid` to filter by test labels (e.g., 'Glucose').
- **Joins:** Use INNER JOINs by default. Use `subject_id` for patient history and `hadm_id` for specific hospital encounters.
- **Filters:** For "abnormal" results, filter `labevents` where `flag = 'abnormal'`.
- **Gender:** Always use 'M' for male and 'F' for female.
- **Precision:** Use `ROUND(valuenum, 2)` for numeric clinical values.
- **Safety:** Always include `LIMIT 100`.
- **Output:** Return ONLY the raw SQL code. No markdown, no commentary.
"""

DATA_EXPLAINER_PROMPT = """
You are a Senior Clinical Research Assistant. Your goal is to provide a structured, professional, and well-defined interpretation of clinical data retrieved from the MIMIC-IV v2.2 demo database.

### USER CONTEXT:
Question: "{question}"
Raw Data: {records}

### OUTPUT REQUIREMENTS:
1. **Executive Summary:** Start with a brief (2-3 sentence) clinical summary of the findings.
2. **Data Presentation:** - If the data is a list of records, ALWAYS use a **Markdown Table** with clear headers.
   - If the data is a single count or metric, use **Bold Text** or a **Highlight** block.
3. **Clinical Context:** Explain the relevance of the found data (e.g., why a specific lab value or diagnosis is significant in this context).
4. **Data Origin:** Explicitly state: "Data retrieved from MIMIC-IV v2.2 clinical records."
5. **No Hallucinations:** If no records are found, explain why and suggest what the user might search for instead.

Use professional Markdown to make the report easy for a doctor to read.
"""

# --- Schemas ---

class QueryRequest(BaseModel):
    question: str
    model: str = "gpt-4o"
    sql_only: bool = False
    edited_sql: Optional[str] = None

class QueryResponse(BaseModel):
    id: str
    question: str
    answer: Optional[str] = None
    sql: str
    timestamp: datetime
    status: str
    executionTime: int = 0
    rowCount: int = 0
    records: List[Dict[str, Any]] = []

# --- Endpoints ---

# Apply role_required dependency to protect clinical data access
@router.post("/", 
             response_model=QueryResponse, 
             dependencies=[Depends(role_required(["doctor", "admin"]))])
async def process_query(
    request: QueryRequest, 
    db: Session = Depends(dependencies.get_db),
    current_user: dict = Depends(get_current_user) # Capture which user is querying
):
    try:
        # 1. SQL Generation
        if not request.edited_sql:
            response = client.chat.completions.create(
                model=request.model,
                messages=[
                    {"role": "system", "content": SQL_GENERATION_PROMPT}, 
                    {"role": "user", "content": request.question}
                ],
                temperature=0
            )
            sql_query = response.choices[0].message.content.strip().replace("```sql", "").replace("```", "")
        else:
            sql_query = request.edited_sql

        # 2. Review Mode Handling
        if request.sql_only and not request.edited_sql:
            return QueryResponse(
                id=f"pending-{datetime.now().timestamp()}",
                question=request.question,
                sql=sql_query,
                timestamp=datetime.now(),
                status="pending_review"
            )

        # 3. Execution & Safety Check
        start_time = datetime.now()
        allowed_starts = ("select", "with", "show", "describe", "desc", "explain")
        if not sql_query.strip().lower().startswith(allowed_starts):
             raise HTTPException(
                 status_code=status.HTTP_400_BAD_REQUEST, 
                 detail="Security violation: Only read-only clinical queries are allowed."
             )

        result_proxy = db.execute(text(sql_query))
        columns = result_proxy.keys()
        records = [dict(zip(columns, row)) for row in result_proxy.fetchall()]
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

        # 4. Enhanced Interpretation Pass
        explanation_res = client.chat.completions.create(
            model=request.model,
            messages=[
                {"role": "user", "content": DATA_EXPLAINER_PROMPT.format(
                    question=request.question, 
                    records=json.dumps(records[:10], default=str)
                )}
            ]
        )
        answer = explanation_res.choices[0].message.content

        # 5. Save to History (Using current_user for the audit trail)
        history = models.QueryHistory(
            user_id=current_user.get("username", "Unknown"), # Map to the logged-in user
            question=request.question, 
            generated_sql=sql_query,
            answer_text=answer, 
            execution_time_ms=execution_time, 
            row_count=len(records)
        )
        db.add(history)
        db.commit()
        db.refresh(history)

        return QueryResponse(
            id=str(history.id), 
            question=request.question, 
            answer=answer,
            sql=sql_query, 
            timestamp=datetime.now(),
            executionTime=execution_time, 
            rowCount=len(records), 
            records=records, 
            status="success"
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Internal Query Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Clinical Query Engine Error: {str(e)}"
        )
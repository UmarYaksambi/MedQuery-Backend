from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from .. import schemas, models, dependencies
from openai import OpenAI
from datetime import datetime
import os
import json

router = APIRouter(prefix="/query", tags=["Query"])
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 1. ADVANCED SQL GENERATION PROMPT
SQL_GENERATION_PROMPT = """
You are a Clinical Data Scientist and SQL Expert for the MedQuery platform. 
Your goal is to translate natural language questions from clinicians into valid, read-only MySQL queries for the MIMIC-IV demo(version2.2) database.

### DATABASE SCHEMA OVERVIEW:

1. CORE MODULE:
   - patients: Demographic info. subject_id (PK), gender, anchor_age, anchor_year, anchor_year_group, dod (date of death).
   - admissions: Hospital stays. hadm_id (PK), subject_id (FK), admittime, dischtime, deathtime, admission_type, admission_location, discharge_location, insurance, language, marital_status, race, hospital_expire_flag (1=died).
   - transfers: Patient movement. transfer_id (PK), subject_id (FK), hadm_id (FK), eventtype, careunit, intime, outtime.

2. HOSP MODULE:
   - diagnoses_icd: Diagnosis codes. subject_id, hadm_id, seq_num, icd_code, icd_version (9 or 10).
   - procedures_icd: Procedures performed. subject_id, hadm_id, seq_num, chartdate, icd_code, icd_version.
   - prescriptions: Medications. subject_id, hadm_id, drug, drug_type, starttime, stoptime, dose_val_rx, dose_unit_rx, route.
   - labevents: Laboratory results. labevent_id (PK), subject_id, hadm_id, itemid (FK), charttime, value, valuenum, valueuom, flag (e.g., 'abnormal').
   - d_labitems: Lab test definitions. itemid (PK), label, fluid, category.

3. ICU MODULE:
   - icustays: ICU stays. stay_id (PK), subject_id, hadm_id, first_careunit, last_careunit, intime, outtime, los (length of stay).
   - chartevents: ICU vitals/observations. subject_id, hadm_id, stay_id (FK), charttime, itemid, value, valuenum, valueuom.

### CRITICAL RULES:
- Use only read-only SELECT statements.
- Join tables using 'subject_id' for patient-level joins or 'hadm_id' for admission-level joins.
- For "female" patients, use 'F'; for "male", use 'M'.
- When querying diagnoses, join 'diagnoses_icd' on 'admissions'.
- Always include a LIMIT 100 clause unless the user asks for a specific count.
- Return ONLY the raw SQL code. No markdown backticks, no explanation.
"""

# 2. IMPROVED DATA EXPLAINER PROMPT
DATA_EXPLAINER_PROMPT = """You are a Clinical Research Assistant. 
Your task is to interpret data retrieved from the MIMIC-IV v2.2 demo database for a medical professional.

User's Question: "{question}"
Data Records (MIMIC-IV v2.2): {records}

### GUIDELINES:
- Provide a professional, concise summary of the findings in a clinical context.
- Explicitly mention that this data is sourced from the MIMIC-IV v2.2 demo database.
- If the data is a count, report it clearly. If it's a list, summarize the primary trends.
- If no records are found, explain that no matches exist in the MIMIC-IV v2.2 demo dataset.
- Do not make specific references to individual doctors unless mentioned in the question.
- Do not invent or hallucinate data points.
"""

@router.post("/", response_model=schemas.QueryResponse)
async def process_query(request: schemas.QueryRequest, db: Session = Depends(dependencies.get_db)):
    try:
        # SQL Generation or Editing Pass
        if not request.edited_sql:
            response = client.chat.completions.create(
                model=request.model,
                messages=[{"role": "system", "content": SQL_GENERATION_PROMPT}, {"role": "user", "content": request.question}],
                temperature=0
            )
            sql_query = response.choices[0].message.content.strip().replace("```sql", "").replace("```", "")
        else:
            sql_query = request.edited_sql

        # Review Mode Handling
        if request.sql_only and not request.edited_sql:
            return schemas.QueryResponse(
                id=f"pending-{datetime.now().timestamp()}",
                question=request.question,
                sql=sql_query,
                timestamp=datetime.now(),
                status="pending_review",
                executionTime=0,
                rowCount=0
            )

        # Execution
        start_time = datetime.now()
        result_proxy = db.execute(text(sql_query))
        columns = result_proxy.keys()
        records = [dict(zip(columns, row)) for row in result_proxy.fetchall()]
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

        # Interpretation Pass
        explanation_res = client.chat.completions.create(
            model=request.model,
            messages=[{"role": "user", "content": DATA_EXPLAINER_PROMPT.format(question=request.question, records=json.dumps(records[:5], default=str))}]
        )
        answer = explanation_res.choices[0].message.content

        # Save to History
        history = models.QueryHistory(
            question=request.question, generated_sql=sql_query,
            answer_text=answer, execution_time_ms=execution_time, row_count=len(records)
        )
        db.add(history); db.commit(); db.refresh(history)

        return schemas.QueryResponse(
            id=str(history.id), question=request.question, answer=answer,
            sql=sql_query, timestamp=history.timestamp,
            executionTime=execution_time, rowCount=len(records), records=records, status="success"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database or LLM Error: {str(e)}")
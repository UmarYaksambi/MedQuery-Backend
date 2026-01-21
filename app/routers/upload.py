from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
import io
import json
from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel
from .. import models, dependencies, database

router = APIRouter(prefix="/upload", tags=["Upload"])

# --- Configuration ---

TABLE_MAPPING = {
    "patients": models.Patient,
    "admissions": models.Admission,
    "transfers": models.Transfer,
    "diagnoses_icd": models.DiagnosisICD,
    "procedures_icd": models.ProcedureICD,
    "prescriptions": models.Prescription,
    "labevents": models.LabEvent,
    "d_labitems": models.DLabItem,
    "icustays": models.ICUStay,
    "chartevents": models.ChartEvent,
}

DATE_COLS = ['admittime', 'dischtime', 'dob', 'dod', 'intime', 'outtime', 'charttime', 'starttime', 'stoptime']

# --- Pydantic Models ---

class SingleRecordRequest(BaseModel):
    table_name: str
    data: Dict[str, Any]

# --- Helper Functions (The "Engine" of the script) ---

def validate_columns(columns: list, model):
    model_columns = [c.name for c in model.__table__.columns]
    unknown_columns = set(columns) - set(model_columns)
    if unknown_columns:
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown columns: {', '.join(unknown_columns)}"
        )
    return True

async def process_file_to_df(file: UploadFile):
    """Consolidated file reading and date processing logic"""
    try:
        contents = await file.read()
        buffer = io.BytesIO(contents)
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(buffer)
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(buffer)
        elif file.filename.endswith('.json'):
            df = pd.read_json(buffer)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
            
        # Date conversion
        for col in df.columns:
            if col.lower() in DATE_COLS:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Handle NaNs (Pandas NaN -> SQL NULL)
        df = df.where(pd.notnull(df), None)
        return df
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

def parse_clinical_date(value: str):
    """Original flexible date parsing logic preserved"""
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return value

# --- ADMIN ENDPOINTS (Direct Integration) ---

@router.post("/direct")
async def admin_bulk_upload(
    file: UploadFile = File(...),
    table_name: str = Form(...),
    db: Session = Depends(dependencies.get_db),
    current_user = Depends(dependencies.role_required(["admin"]))
):
    if table_name not in TABLE_MAPPING:
        raise HTTPException(status_code=400, detail="Invalid table name")
    
    model = TABLE_MAPPING[table_name]
    df = await process_file_to_df(file)
    validate_columns(df.columns.tolist(), model)

    try:
        df.to_sql(table_name, con=database.engine, if_exists='append', index=False, method='multi')
        return {"status": "success", "rows_processed": len(df), "table": table_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Insertion Error: {str(e)}")

@router.post("/single/direct")
async def admin_single_upload(
    request: SingleRecordRequest,
    db: Session = Depends(dependencies.get_db),
    current_user = Depends(dependencies.role_required(["admin"]))
):
    model_class = TABLE_MAPPING.get(request.table_name)
    processed_data = {k: (parse_clinical_date(v) if k.lower() in DATE_COLS else v) for k, v in request.data.items()}
    
    try:
        new_record = model_class(**processed_data)
        db.add(new_record)
        db.commit()
        return {"status": "success", "message": "Record integrated directly by Admin"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

# --- DOCTOR ENDPOINTS (Quarantine/Request) ---

@router.post("/request")
async def doctor_bulk_request(
    file: UploadFile = File(...),
    table_name: str = Form(...),
    db: Session = Depends(dependencies.get_db),
    current_user = Depends(dependencies.role_required(["doctor", "admin"]))
):
    # Metadata entry in the requests table
    new_request = models.UploadRequest(
        username=current_user.get("sub"),
        filename=file.filename,
        table_name=table_name,
        status="pending"
    )
    db.add(new_request)
    db.commit()
    return {"status": "request_sent", "message": "Bulk upload request sent for Admin review"}

@router.post("/single/request")
async def doctor_single_request(
    request: SingleRecordRequest,
    db: Session = Depends(dependencies.get_db),
    current_user = Depends(dependencies.role_required(["doctor", "admin"]))
):
    new_request = models.UploadRequest(
        username=current_user.get("sub"),
        filename="Manual Entry",
        table_name=request.table_name,
        payload=json.dumps(request.data), # Save the JSON data
        status="pending"
    )
    db.add(new_request)
    db.commit()
    return {"status": "request_sent", "message": "Clinical record queued for Admin approval"}
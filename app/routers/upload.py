from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
import io
from typing import Dict, Any
from datetime import datetime
from pydantic import BaseModel
from .. import models, dependencies, database

router = APIRouter(prefix="/upload", tags=["Upload"])

# --- Configuration ---

# Map table names to SQLAlchemy Models
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

# Date columns for automatic conversion
DATE_COLS = ['admittime', 'dischtime', 'dob', 'dod', 'intime', 'outtime', 'charttime', 'starttime', 'stoptime']

# --- Pydantic Models ---

class SingleRecordRequest(BaseModel):
    table_name: str
    data: Dict[str, Any]

# --- Helper Functions ---

def validate_columns(columns: list, model):
    """
    Checks if the provided columns match the model's columns.
    """
    model_columns = [c.name for c in model.__table__.columns]
    
    # Check for unknown columns (case-insensitive logic could be added here if needed)
    unknown_columns = set(columns) - set(model_columns)
    if unknown_columns:
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown columns: {', '.join(unknown_columns)}"
        )
    return True

# --- Endpoints ---

@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    table_name: str = Form(...),
    db: Session = Depends(dependencies.get_db)
):
    """
    Bulk upload via CSV/Excel/JSON file.
    """
    if table_name not in TABLE_MAPPING:
        raise HTTPException(status_code=400, detail=f"Invalid table name: {table_name}")
    
    model = TABLE_MAPPING[table_name]
    
    # 1. Read File
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
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    # 2. Date conversion
    for col in df.columns:
        if col.lower() in DATE_COLS:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # 3. Handle NaNs (Pandas NaN -> SQL NULL)
    df = df.where(pd.notnull(df), None)

    # 4. Validate
    validate_columns(df.columns.tolist(), model)

    # 5. Insert
    try:
        df.to_sql(
            table_name, 
            con=database.engine, 
            if_exists='append', 
            index=False, 
            chunksize=1000,
            method='multi'
        )
        return {
            "status": "success",
            "filename": file.filename,
            "rows_processed": len(df),
            "table": table_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Insertion Error: {str(e)}")


@router.post("/single")
async def create_single_record(
    request: SingleRecordRequest,
    db: Session = Depends(dependencies.get_db)
):
    """
    Inserts a single record. Expects JSON: { "table_name": "...", "data": { ... } }
    """
    table_name = request.table_name
    data = request.data

    if table_name not in TABLE_MAPPING:
        raise HTTPException(status_code=400, detail=f"Invalid table name: {table_name}")
    
    model_class = TABLE_MAPPING[table_name]
    
    # 1. Validate Columns
    # We use list(data.keys()) because we only care about the fields sent
    model_columns = [c.name for c in model_class.__table__.columns]
    unknown_columns = set(data.keys()) - set(model_columns)
    if unknown_columns:
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown columns: {', '.join(unknown_columns)}"
        )

    # 2. Process Data (Dates & Empty Strings)
    processed_data = {}
    for key, value in data.items():
        if value == "" or value is None:
            processed_data[key] = None
        elif key.lower() in DATE_COLS and isinstance(value, str):
            # Attempt flexible date parsing
            try:
                processed_data[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                try:
                    processed_data[key] = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                except:
                    try:
                        processed_data[key] = datetime.strptime(value, "%Y-%m-%d")
                    except:
                        processed_data[key] = value # Fallback
        else:
            processed_data[key] = value

    # 3. Insert using ORM
    try:
        new_record = model_class(**processed_data)
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        
        # safely get the ID/Primary Key for the response
        pk = getattr(new_record, 'id', getattr(new_record, 'subject_id', getattr(new_record, 'stay_id', 'new_record')))
        
        return {
            "status": "success",
            "message": "Record inserted successfully",
            "id": pk,
            "table": table_name
        }
    except SQLAlchemyError as e:
        db.rollback()
        # Extract underlying error message if possible
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        raise HTTPException(status_code=500, detail=f"Database Error: {error_msg}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")
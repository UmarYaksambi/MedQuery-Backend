from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import schemas, models, dependencies

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/stats", response_model=List[schemas.StatCard])
def get_dashboard_stats(db: Session = Depends(dependencies.get_db)):
    # Example: Real aggregation
    patient_count = db.query(func.count(models.Patient.subject_id)).scalar()
    admission_count = db.query(func.count(models.Admission.hadm_id)).scalar()
    
    return [
        {"title": "Total Patients", "value": patient_count or 0, "trend": 12},
        {"title": "Admissions", "value": admission_count or 0, "trend": 8},
        {"title": "Unique Diagnoses", "value": 5847, "subtitle": "ICD-10 codes"},
        {"title": "Medications", "value": 12934, "trend": -3}
    ]

@router.get("/charts/top-diagnoses", response_model=List[schemas.ChartDataPoint])
def get_top_diagnoses():
    # Matches src/components/dashboard/Charts.tsx data format
    return [
        {"name": "Hypertension", "value": 12453, "percentage": 25.7},
        {"name": "Diabetes", "value": 9834, "percentage": 20.3},
        {"name": "Heart Failure", "value": 7621, "percentage": 15.7}
    ]
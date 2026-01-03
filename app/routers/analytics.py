from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, extract
from typing import List
from .. import schemas, models, dependencies

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/dashboard", response_model=schemas.AnalyticsResponse)
def get_analytics_dashboard(db: Session = Depends(dependencies.get_db)):
    """
    Fetches all aggregated data for the Analytics Dashboard in one go.
    """
    try:
        # --- 1. KPI STATS ---
        
        # Total Patients
        total_patients = db.query(func.count(models.Patient.subject_id)).scalar() or 0
        
        # Total Admissions
        total_admissions = db.query(func.count(models.Admission.hadm_id)).scalar() or 0
        
        # Avg ICU Length of Stay (LOS)
        avg_los = db.query(func.avg(models.ICUStay.los)).scalar()
        avg_los_val = round(avg_los, 1) if avg_los else 0
        
        # Hospital Mortality Rate (hospital_expire_flag = 1)
        deaths = db.query(func.count(models.Admission.hadm_id))\
                   .filter(models.Admission.hospital_expire_flag == 1).scalar() or 0
        mortality_rate = (deaths / total_admissions * 100) if total_admissions > 0 else 0

        stats = [
            {"title": "Total Patients", "value": f"{total_patients:,}", "subtitle": "Unique subjects"},
            {"title": "Total Admissions", "value": f"{total_admissions:,}", "subtitle": "Hospital encounters"},
            {"title": "Avg. ICU Stay", "value": f"{avg_los_val} days", "subtitle": "Across all units"},
            {"title": "Mortality Rate", "value": f"{mortality_rate:.1f}%", "subtitle": "In-hospital expiration"},
        ]

        # --- 2. TOP DIAGNOSES (Pie/Bar Chart) ---
        # Aggregating by ICD Code from diagnoses_icd
        top_diag_query = db.query(
            models.DiagnosisICD.icd_code,
            func.count(models.DiagnosisICD.icd_code).label('count')
        ).group_by(models.DiagnosisICD.icd_code)\
         .order_by(desc('count'))\
         .limit(5).all()

        top_diagnoses = [
            {"name": row.icd_code, "value": row.count} for row in top_diag_query
        ]

        # --- 3. ADMISSIONS BY MONTH (Line/Bar Chart) ---
        # Grouping by Year-Month from admittime (Taking top 12 chronologically)
        # Note: MIMIC years are shifted. We sort by date.
        
        # MySQL/Postgres specific extraction might vary. 
        # Using a generic approach: Group by Year and Month.
        admissions_query = db.query(
            func.extract('year', models.Admission.admittime).label('year'),
            func.extract('month', models.Admission.admittime).label('month'),
            func.count(models.Admission.hadm_id).label('count')
        ).group_by('year', 'month')\
         .order_by(desc('year'), desc('month'))\
         .limit(12).all()
        
        # Reverse to show chronological order left-to-right
        admissions_by_month = [
            {"name": f"{int(row.month)}/{int(row.year)}", "value": row.count} 
            for row in reversed(admissions_query)
        ]

        # --- 4. DEMOGRAPHICS BY RACE (Pie Chart) ---
        # Aggregating distinct races
        race_query = db.query(
            models.Admission.race,
            func.count(models.Admission.hadm_id).label('count')
        ).group_by(models.Admission.race)\
         .order_by(desc('count'))\
         .limit(6).all()

        demographics_race = [
            {"name": (row.race or "UNKNOWN").title(), "value": row.count} 
            for row in race_query
        ]

        # --- 5. ICU UTILIZATION (Bar Chart) ---
        # Admissions per Care Unit
        icu_query = db.query(
            models.ICUStay.first_careunit,
            func.count(models.ICUStay.stay_id).label('count')
        ).group_by(models.ICUStay.first_careunit)\
         .order_by(desc('count')).all()

        icu_utilization = [
            {"name": row.first_careunit or "Unknown", "value": row.count} 
            for row in icu_query
        ]

        return {
            "stats": stats,
            "top_diagnoses": top_diagnoses,
            "admissions_by_month": admissions_by_month,
            "demographics_race": demographics_race,
            "icu_utilization": icu_utilization
        }

    except Exception as e:
        print(f"Analytics Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
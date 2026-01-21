from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Any
import json
from .. import models, dependencies
from ..auth_utils import role_required

router = APIRouter(prefix="/audit", tags=["Audit"])

# --- 1. Audit Summary (Existing) ---
@router.get("/summary", dependencies=[Depends(role_required(["admin"]))])
async def get_audit_summary(db: Session = Depends(dependencies.get_db)):
    try:
        total_queries = db.query(models.QueryHistory).count()
        avg_latency = db.query(func.avg(models.QueryHistory.execution_time_ms)).scalar() or 0
        total_records = db.query(func.sum(models.QueryHistory.row_count)).scalar() or 0

        top_questions = db.query(
            models.QueryHistory.question, 
            func.count(models.QueryHistory.id).label('count')
        ).group_by(models.QueryHistory.question).order_by(desc('count')).limit(5).all()

        return {
            "total_queries": total_queries,
            "avg_latency_ms": round(float(avg_latency), 2),
            "total_records_retrieved": int(total_records),
            "top_questions": [{"question": q, "count": c} for q, c in top_questions]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit Analytics Error: {str(e)}")

# --- 2. Audit Logs (Existing) ---
@router.get("/logs", dependencies=[Depends(role_required(["admin"]))])
async def get_audit_logs(db: Session = Depends(dependencies.get_db), limit: int = 50):
    try:
        return db.query(models.QueryHistory).order_by(models.QueryHistory.timestamp.desc()).limit(limit).all()
    except Exception:
        raise HTTPException(status_code=500, detail="Could not retrieve audit logs.")

# --- 3. NEW: List Pending Uploads ---
@router.get("/pending-uploads", dependencies=[Depends(role_required(["admin"]))])
async def get_pending_uploads(db: Session = Depends(dependencies.get_db)):
    """Fetches doctor requests that need admin approval"""
    try:
        return db.query(models.UploadRequest).filter(models.UploadRequest.status == "pending").all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch requests: {str(e)}")

# --- 4. NEW: Approve & Integrate Request ---
@router.post("/upload/{request_id}/approve", dependencies=[Depends(role_required(["admin"]))])
async def approve_upload(request_id: int, db: Session = Depends(dependencies.get_db)):
    request = db.query(models.UploadRequest).filter(models.UploadRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    try:
        # If it's a Manual Entry, the payload contains JSON clinical data
        if request.payload:
            data = json.loads(request.payload)
            
            # Local mapping to avoid circular imports with upload.py
            MAPPING = {
                "patients": models.Patient,
                "admissions": models.Admission,
                "transfers": models.Transfer,
                "diagnoses_icd": models.DiagnosisICD,
                "prescriptions": models.Prescription,
                "labevents": models.LabEvent
            }
            
            model_class = MAPPING.get(request.table_name)
            if not model_class:
                raise HTTPException(status_code=400, detail="Unsupported table name")

            new_record = model_class(**data)
            db.add(new_record)

        # Update the request status
        request.status = "approved"
        db.commit()
        return {"status": "success", "message": f"Integrated into {request.table_name}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Integration Error: {str(e)}")

# --- 5. NEW: Reject Request ---
@router.post("/upload/{request_id}/reject", dependencies=[Depends(role_required(["admin"]))])
async def reject_upload(request_id: int, db: Session = Depends(dependencies.get_db)):
    request = db.query(models.UploadRequest).filter(models.UploadRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request.status = "rejected"
    db.commit()
    return {"status": "success", "message": "Request archived as rejected"}
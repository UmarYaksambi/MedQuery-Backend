from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, models, dependencies

router = APIRouter(prefix="/api/history", tags=["History"])

@router.get("/", response_model=List[schemas.QueryResponse])
def get_history(db: Session = Depends(dependencies.get_db)):
    history = db.query(models.QueryHistory).order_by(models.QueryHistory.timestamp.desc()).limit(50).all()
    
    return [
        schemas.QueryResponse(
            id=str(h.id),
            question=h.question,
            answer=h.answer_text,
            sql=h.generated_sql,
            timestamp=h.timestamp,
            executionTime=h.execution_time_ms,
            rowCount=h.row_count
        ) for h in history
    ]
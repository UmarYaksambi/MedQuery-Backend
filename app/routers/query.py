from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import schemas, models, dependencies
import uuid
from datetime import datetime
import random

router = APIRouter(prefix="/query", tags=["Query"])

@router.post("/", response_model=schemas.QueryResponse)
async def process_query(request: schemas.QueryRequest, db: Session = Depends(dependencies.get_db)):
    # 1. TODO: Call LLM here to get SQL from request.question
    mock_sql = "SELECT count(*) FROM patients WHERE gender = 'F';"
    mock_answer = "Based on the database, there are 2,847 female patients matching criteria."
    
    # 2. Save history
    history_entry = models.QueryHistory(
        question=request.question,
        generated_sql=mock_sql,
        answer_text=mock_answer,
        execution_time_ms=120,
        row_count=2847
    )
    db.add(history_entry)
    db.commit()
    db.refresh(history_entry)

    return schemas.QueryResponse(
        id=str(history_entry.id),
        question=request.question,
        answer=mock_answer,
        sql=mock_sql,
        timestamp=history_entry.timestamp,
        executionTime=history_entry.execution_time_ms,
        rowCount=history_entry.row_count
    )
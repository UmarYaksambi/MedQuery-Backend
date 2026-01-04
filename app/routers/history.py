from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models, dependencies, schemas

router = APIRouter(prefix="/history", tags=["History"])

@router.get("/", response_model=list[schemas.QueryHistoryItem])
def get_recent_history(limit: int = 10, db: Session = Depends(dependencies.get_db)):
    """
    Fetch the most recent queries executed by the user.
    """
    return db.query(models.QueryHistory)\
             .order_by(models.QueryHistory.timestamp.desc())\
             .limit(limit)\
             .all()
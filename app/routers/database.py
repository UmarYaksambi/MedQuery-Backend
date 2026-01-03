from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from .. import schemas, dependencies

router = APIRouter(prefix="/api/database", tags=["Database"])

@router.get("/tables", response_model=List[str])
def list_tables():
    return ["patients", "admissions", "transfers", "diagnoses_icd", "labevents"]

@router.get("/tables/{table_name}", response_model=schemas.TableData)
def get_table_data(table_name: str, page: int = 1, limit: int = 10, db: Session = Depends(dependencies.get_db)):
    # Validate table name to prevent injection
    allowed_tables = ["patients", "admissions", "labevents", "diagnoses_icd"]
    if table_name not in allowed_tables:
        raise HTTPException(status_code=400, detail="Invalid table name")

    offset = (page - 1) * limit
    
    # Using raw SQL for generic table fetching, or map to models dynamically
    try:
        sql = text(f"SELECT * FROM {table_name} LIMIT :limit OFFSET :offset")
        result = db.execute(sql, {"limit": limit, "offset": offset})
        rows = [dict(row._mapping) for row in result]
        keys = list(rows[0].keys()) if rows else []
        
        # Get total count
        count_sql = text(f"SELECT COUNT(*) FROM {table_name}")
        total = db.execute(count_sql).scalar()

        return {
            "data": rows,
            "total_rows": total,
            "page": page,
            "columns": keys
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
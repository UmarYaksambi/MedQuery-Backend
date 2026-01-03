from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from .. import schemas, dependencies

# UPDATED: Removed /api prefix
router = APIRouter(prefix="/database", tags=["Database"])

# Full list of tables available in your schema
ALL_TABLES = [
    "patients", 
    "admissions", 
    "transfers", 
    "diagnoses_icd", 
    "procedures_icd", 
    "prescriptions", 
    "labevents", 
    "d_labitems", 
    "icustays", 
    "chartevents"
]

@router.get("/tables", response_model=List[str])
def list_tables():
    """
    Returns a list of all queryable tables.
    """
    return ALL_TABLES

@router.get("/tables/{table_name}", response_model=schemas.TableData)
def get_table_data(
    table_name: str, 
    page: int = 1, 
    limit: int = 10, 
    db: Session = Depends(dependencies.get_db)
):
    """
    Fetches raw data for a specific table with pagination.
    """
    if table_name not in ALL_TABLES:
        raise HTTPException(status_code=400, detail=f"Invalid table name: {table_name}")

    offset = (page - 1) * limit
    
    try:
        # Fetch Data
        sql = text(f"SELECT * FROM {table_name} LIMIT :limit OFFSET :offset")
        result = db.execute(sql, {"limit": limit, "offset": offset})
        
        # Convert SQLAlchemy rows to dictionaries
        rows = [dict(row._mapping) for row in result]
        
        # Determine Columns
        if rows:
            columns = list(rows[0].keys())
        else:
            # If table is empty, inspect columns
            inspector = inspect(db.bind)
            columns = [col['name'] for col in inspector.get_columns(table_name)]

        # Get Total Row Count
        count_sql = text(f"SELECT COUNT(*) FROM {table_name}")
        total = db.execute(count_sql).scalar()

        return {
            "data": rows,
            "total_rows": total,
            "page": page,
            "columns": columns
        }
        
    except Exception as e:
        print(f"Database Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch table data")
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime


# --- Query Interface ---class QueryRequest(BaseModel):
class QueryRequest(BaseModel):
    question: str
    model: Optional[str] = "gpt-4o"
    sql_only: bool = False # Flag for review mode
    edited_sql: Optional[str] = None # For when user edits SQL

class QueryResponse(BaseModel):
    id: Optional[str] = None
    question: str
    answer: Optional[str] = None
    sql: str
    timestamp: datetime
    executionTime: Optional[int] = 0
    rowCount: Optional[int] = 0
    records: Optional[List[Dict[str, Any]]] = None # The actual data
    status: str = "success" # "pending_review" or "success"

# --- Database Explorer ---
class TableData(BaseModel):
    data: List[Dict[str, Any]]
    total_rows: int
    page: int
    columns: List[str]

# --- Schema Viewer ---
class ColumnDef(BaseModel):
    name: str
    type: str
    description: Optional[str]

class TableDef(BaseModel):
    name: str
    columns: List[ColumnDef]

class ModuleDef(BaseModel):
    name: str
    description: str
    tables: List[TableDef]

# --- Analytics Response Models ---
class StatCard(BaseModel):
    title: str
    value: str | int | float
    subtitle: Optional[str] = None
    trend: Optional[int] = None
    trendDir: Optional[str] = None # 'up' or 'down'

class ChartDataPoint(BaseModel):
    name: str
    value: float | int
    # Optional extra fields for specific charts
    percentage: Optional[float] = None 
    fill: Optional[str] = None

class AnalyticsResponse(BaseModel):
    stats: List[StatCard]
    top_diagnoses: List[ChartDataPoint]
    admissions_by_month: List[ChartDataPoint]
    demographics_race: List[ChartDataPoint]
    icu_utilization: List[ChartDataPoint]

# --- History Models ---
class QueryHistoryItem(BaseModel):
    id: int
    question: str
    generated_sql: Optional[str] = None
    answer_text: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True
        
# --- NoSQL schema ---
class ClinicalNoteCreate(BaseModel):
    subject_id: int
    hadm_id: Optional[int] = None
    note_type: str = "General"
    content: str

class ClinicalNote(ClinicalNoteCreate):
    id: str
    timestamp: datetime

    class Config:
        from_attributes = True
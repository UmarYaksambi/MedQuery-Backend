from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime

# --- General ---
class ChartDataPoint(BaseModel):
    name: str
    value: float | int
    percentage: Optional[float] = None
    fill: Optional[str] = None

class StatCard(BaseModel):
    title: str
    value: int | str
    subtitle: Optional[str] = None
    trend: Optional[int] = None

# --- Query Interface ---
class QueryRequest(BaseModel):
    question: str
    model: Optional[str] = "gpt-4"

class QueryResponse(BaseModel):
    id: str
    question: str
    answer: str
    sql: Optional[str]
    timestamp: datetime
    executionTime: int
    rowCount: int

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
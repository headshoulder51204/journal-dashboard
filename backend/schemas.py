from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any
from datetime import datetime

class LogEntryBase(BaseModel):
    timestamp: str
    source: str
    status: str
    message: str
    stack_trace: Optional[str] = None
    metadata_info: Optional[dict] = None

class LogEntryCreate(LogEntryBase):
    pass

class LogEntry(LogEntryBase):
    id: int
    report_id: int
    model_config = ConfigDict(from_attributes=True)

class ReportBase(BaseModel):
    trace_id: Optional[str] = None
    title: Optional[str] = None
    host: Optional[str] = None
    log_file: Optional[str] = None
    since: Optional[str] = None
    until: Optional[str] = None
    unit: Optional[str] = None
    
    status: Optional[str] = "SUCCESS"
    llm_model: Optional[str] = None
    severity: Optional[str] = "Info"
    
    # Stats
    tokens_used: Optional[int] = 0
    chunks_analyzed: Optional[int] = 0
    total_lines: Optional[int] = 0
    match_count: Optional[int] = 0
    log_hash: Optional[str] = None
    
    root_cause: Optional[str] = None
    recommendations: Optional[List[str]] = None
    anomaly_context: Optional[str] = None
    
    # Legacy/Additional Stats
    total_events: Optional[int] = 0
    duration: Optional[str] = None
    affected_nodes: Optional[int] = 0
    error_distribution: Optional[dict] = None
    result: Optional[str] = None  # Detailed AI Analysis in Markdown

class ReportCreate(ReportBase):
    model: Optional[str] = None  # Mapping from incoming JSON
    analysis: Optional[str] = None # Mapping from incoming JSON
    created_at: Optional[str] = None # Mapping from incoming JSON
    log_entries: Optional[List[LogEntryCreate]] = []

class SimpleResultInput(BaseModel):
    result: Any  # Can be a string or a dict/JSON object

class Report(ReportBase):
    id: int
    date_generated: datetime
    log_entries: List[LogEntry] = []
    model_config = ConfigDict(from_attributes=True)

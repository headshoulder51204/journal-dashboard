from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
try:
    from .database import Base
except ImportError:
    from database import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String, unique=True, index=True)
    title = Column(String)
    host = Column(String)
    log_file = Column(String)
    since = Column(String)
    until = Column(String)
    unit = Column(String)
    
    status = Column(String)  # SUCCESS, FAILED, PROCESSING
    llm_model = Column(String)
    severity = Column(String)  # Critical, Medium, Low
    date_generated = Column(DateTime, default=datetime.utcnow)
    
    # Stats
    tokens_used = Column(Integer)
    chunks_analyzed = Column(Integer)
    total_lines = Column(Integer)
    match_count = Column(Integer)
    log_hash = Column(String)
    
    # AI Analysis
    root_cause = Column(Text)
    recommendations = Column(JSON)  # List of recommended actions
    anomaly_context = Column(Text)
    
    # Legacy/Additional Stats
    total_events = Column(Integer)
    duration = Column(String)
    affected_nodes = Column(Integer)
    error_distribution = Column(JSON)  # { "Timeout Errors": 64, "Auth Failure": 22, ... }
    error_count = Column(Integer, default=0)
    result = Column(Text)  # Detailed AI Analysis in Markdown
    
    log_entries = relationship("LogEntry", back_populates="report", cascade="all, delete-orphan")

class LogEntry(Base):
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"))
    timestamp = Column(String)
    source = Column(String)
    status = Column(String)
    message = Column(String)
    
    # Detailed Trace info
    stack_trace = Column(Text)
    metadata_info = Column(JSON)  # { "Node ID": "...", "Client IP": "...", "Protocol": "...", "Latency": "..." }

    report = relationship("Report", back_populates="log_entries")

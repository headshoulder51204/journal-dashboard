from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import os

try:
    from . import models, schemas, database
except ImportError:
    import models, schemas, database
try:
    from .database import SessionLocal, engine
except ImportError:
    from database import SessionLocal, engine

# Create the database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Analytica LOG INTELLIGENCE API")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def delete_old_reports(db: Session):
    """Deletes reports older than 90 days."""
    ninety_days_ago = datetime.utcnow() - timedelta(days=90)
    old_reports = db.query(models.Report).filter(models.Report.date_generated < ninety_days_ago).all()
    for report in old_reports:
        db.delete(report)
    db.commit()

@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    delete_old_reports(db)
    db.close()

import json

@app.post("/api/webhook/analysis", response_model=schemas.Report)
def receive_analysis(payload: schemas.ReportCreate, db: Session = Depends(get_db)):
    """Receives analysis data according to the structured payload and saves/updates it."""
    # Convert payload to dict and handle mappings
    data = payload.dict(exclude={"log_entries", "model", "analysis", "created_at"})
    
    # Mapping for new JSON structure
    if payload.model and not data.get("llm_model"):
        data["llm_model"] = payload.model
    if payload.analysis and not data.get("result"):
        data["result"] = payload.analysis
    if payload.title and not data.get("trace_id"):
        data["trace_id"] = payload.title
        
    # Handle date_generated from created_at
    if payload.created_at:
        try:
            data["date_generated"] = datetime.strptime(payload.created_at, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass # Fallback to default
            
    # Check for existing report
    trace_id = data.get("trace_id")
    if not trace_id:
        import uuid
        trace_id = f"auto-{uuid.uuid4().hex[:8]}"
        data["trace_id"] = trace_id

    db_report = db.query(models.Report).filter(models.Report.trace_id == trace_id).first()
    
    if db_report:
        for key, value in data.items():
            if hasattr(db_report, key):
                setattr(db_report, key, value)
        # Refresh log entries by deleting and re-adding if provided
        db.query(models.LogEntry).filter(models.LogEntry.report_id == db_report.id).delete()
    else:
        db_report = models.Report(**data)
        db.add(db_report)
        db.commit()
        db.refresh(db_report)

    # Add log entries if present
    if payload.log_entries:
        for entry in payload.log_entries:
            db_entry = models.LogEntry(
                report_id=db_report.id,
                **entry.dict()
            )
            db.add(db_entry)
    
    db.commit()
    db.refresh(db_report)
    return db_report

@app.get("/api/reports", response_model=List[schemas.Report])
def list_reports(db: Session = Depends(get_db)):
    return db.query(models.Report).all()

@app.get("/api/reports/{trace_id}", response_model=schemas.Report)
def get_report(trace_id: str, db: Session = Depends(get_db)):
    report = db.query(models.Report).filter(models.Report.trace_id == trace_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

# Serve static files for frontend
from fastapi.staticfiles import StaticFiles
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_dir = os.path.join(base_dir, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")

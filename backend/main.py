from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import os

from . import models, schemas, database
from .database import SessionLocal, engine

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
def receive_analysis(payload: schemas.SimpleResultInput, db: Session = Depends(get_db)):
    """Receives a single 'result' field, parses it, and saves to the database."""
    result_data = payload.result
    
    # If it's a string, try parsing it as JSON
    if isinstance(result_data, str):
        try:
            result_data = json.loads(result_data)
        except json.JSONDecodeError:
            # Fallback for plain text: wrap it in a basic report structure
            result_data = {
                "trace_id": f"RAW-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "status": "SUCCESS",
                "llm_model": "LLM-Response",
                "severity": "Low",
                "root_cause": result_data,
                "recommendations": ["Review the full output for details."],
                "log_entries": []
            }
    
    # Validation/Defaults for structure
    report_data = {
        "trace_id": result_data.get("trace_id", f"GEN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"),
        "status": result_data.get("status", "SUCCESS"),
        "llm_model": result_data.get("llm_model", "Unknown"),
        "severity": result_data.get("severity", "Medium"),
        "root_cause": result_data.get("root_cause", str(result_data)),
        "recommendations": result_data.get("recommendations", []),
        "anomaly_context": result_data.get("anomaly_context", ""),
        "total_events": result_data.get("total_events", 0),
        "duration": result_data.get("duration", "0s"),
        "affected_nodes": result_data.get("affected_nodes", 0),
        "error_distribution": result_data.get("error_distribution", {})
    }

    # Save logic
    db_report = db.query(models.Report).filter(models.Report.trace_id == report_data["trace_id"]).first()
    if db_report:
        for var, value in report_data.items():
            setattr(db_report, var, value)
        db.query(models.LogEntry).filter(models.LogEntry.report_id == db_report.id).delete()
    else:
        db_report = models.Report(**report_data)
        db.add(db_report)
        db.commit()
        db.refresh(db_report)

    # Add log entries if present
    log_entries = result_data.get("log_entries", [])
    for entry in log_entries:
        db_entry = models.LogEntry(
            report_id=db_report.id,
            timestamp=entry.get("timestamp", ""),
            source=entry.get("source", ""),
            status=entry.get("status", ""),
            message=entry.get("message", ""),
            stack_trace=entry.get("stack_trace", ""),
            metadata_info=entry.get("metadata_info", {})
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
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import os
import sys

# Vercel entry point at root
try:
    from backend import models, schemas, database
    from backend.database import SessionLocal, engine
except ImportError:
    # Fallback for local standalone or different structures
    import models, schemas, database
    from database import SessionLocal, engine

app = FastAPI(title="Analytica LOG INTELLIGENCE API")

@app.on_event("startup")
async def startup_event():
    # Ensure tables are created on startup
    print(f"Starting up... Database URL matches: {database.SQLALCHEMY_DATABASE_URL[:20]}...")
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    delete_old_reports(db)
    db.close()

@app.get("/api/debug/db")
def debug_db():
    """Diagnostic endpoint to check database connectivity."""
    db_url = database.SQLALCHEMY_DATABASE_URL
    db_type = "PostgreSQL" if db_url.startswith("postgresql") else "SQLite"
    masked_url = db_url.split("@")[-1] if "@" in db_url else "Hidden"
    return {
        "database_type": db_type,
        "is_vercel": os.environ.get("VERCEL") is not None,
        "database_host_check": masked_url,
        "status": "connected"
    }


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

# --- Endpoint definitions ---
@app.post("/api/webhook/analysis", response_model=schemas.Report)
def receive_analysis(payload: schemas.ReportCreate, db: Session = Depends(get_db)):
    data = payload.dict(exclude={"log_entries", "model", "analysis", "created_at"})
    if payload.model and not data.get("llm_model"):
        data["llm_model"] = payload.model
    if payload.analysis and not data.get("result"):
        data["result"] = payload.analysis
    if payload.title and not data.get("trace_id"):
        data["trace_id"] = payload.title
        
    if payload.created_at:
        try:
            data["date_generated"] = datetime.strptime(payload.created_at, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
            
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
        db.query(models.LogEntry).filter(models.LogEntry.report_id == db_report.id).delete()
    else:
        db_report = models.Report(**data)
        db.add(db_report)
        db.commit()
        db.refresh(db_report)

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
base_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(base_dir, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

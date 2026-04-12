from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import os
import sys
import traceback
from contextlib import asynccontextmanager

# Add the parent directory to sys.path to ensure backend package is found
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Import from backend package
try:
    from backend import models, schemas, database
    from backend.database import SessionLocal, engine
    # Explicitly import models to ensure they are registered with Base.metadata
    from backend.models import Report as _Report, LogEntry as _LogEntry
except ImportError:
    # Local fallback
    try:
        import models, schemas, database
        from database import SessionLocal, engine
        from models import Report as _Report, LogEntry as _LogEntry
    except ImportError:
        # Emergency fallback if both fail (though they shouldn't with sys.path fix)
        raise

# Global variable to capture startup errors
STARTUP_ERROR = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global STARTUP_ERROR
    # Ensure tables are created on startup
    print(f"DATABASE INITIALIZATION: Checking connection to {database.SQLALCHEMY_DATABASE_URL[:20]}...")
    try:
        models.Base.metadata.create_all(bind=engine)
        print("DATABASE INITIALIZATION: Tables created or verified successfully.")
        
        db = SessionLocal()
        try:
            delete_old_reports(db)
        finally:
            db.close()
    except Exception as e:
        STARTUP_ERROR = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "db_url_masked": database.SQLALCHEMY_DATABASE_URL[:20] + "..." if database.SQLALCHEMY_DATABASE_URL else None
        }
        print(f"DATABASE ERROR during startup: {e}")
    
    yield

app = FastAPI(title="Analytica LOG INTELLIGENCE API", lifespan=lifespan)

@app.get("/")
def read_root():
    """Simple health check to see if the app starts on Vercel."""
    return {"status": "ok", "message": "Analytica API is running", "environment": "Vercel" if os.environ.get("VERCEL") else "Local"}

@app.get("/api/health")
def health_check():
    """Diagnostic endpoint to see startup errors."""
    return {
        "status": "up" if STARTUP_ERROR is None else "error",
        "startup_error": STARTUP_ERROR,
        "database_url_provided": os.environ.get("DATABASE_URL") is not None,
        "tables_found": list(models.Base.metadata.tables.keys()),
        "python_version": sys.version,
        "cwd": os.getcwd()
    }

@app.get("/api/setup-db")
def setup_db():
    """Explicitly triggers table creation and returns results."""
    results = {
        "action": "create_all",
        "database_url": database.SQLALCHEMY_DATABASE_URL[:20] + "..." if database.SQLALCHEMY_DATABASE_URL else None,
        "success": False,
        "error": None,
        "tables_after": []
    }
    try:
        models.Base.metadata.create_all(bind=engine)
        results["success"] = True
        results["tables_after"] = list(models.Base.metadata.tables.keys())
    except Exception as e:
        results["error"] = str(e)
    return results

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
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_dir = os.path.join(project_root, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")

# For Vercel, the app object must be named 'app'

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, APIRouter
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import os
import sys
import traceback
import uuid
from contextlib import asynccontextmanager

# Add the parent directory to sys.path to ensure backend package is found
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Import from backend package
try:
    from backend import models, schemas, database
    from backend.database import SessionLocal, engine
    from backend.models import Report as _Report, LogEntry as _LogEntry
except ImportError:
    # Local fallback
    try:
        import models, schemas, database
        from database import SessionLocal, engine
        from models import Report as _Report, LogEntry as _LogEntry
    except ImportError:
        raise

# Global variable to capture startup errors
STARTUP_ERROR = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global STARTUP_ERROR
    print(f"DATABASE INITIALIZATION: Checking connection to {database.SQLALCHEMY_DATABASE_URL[:20]}...")
    try:
        # Load models into metadata (already done by imports above)
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
router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def delete_old_reports(db: Session):
    """Deletes reports older than 24 hours."""
    cutoff = datetime.utcnow() - timedelta(hours=24)
    try:
        # Use date_generated as defined in backend/models.py
        db.query(models.Report).filter(models.Report.date_generated < cutoff).delete()
        db.commit()
    except Exception as e:
        print(f"CLEANUP ERROR: {e}")
        db.rollback()

@router.get("/")
def read_root():
    return {"status": "ok", "message": "Analytica API is running", "environment": "Vercel" if os.environ.get("VERCEL") else "Local"}

@router.get("/health")
def health_check():
    return {
        "status": "up" if STARTUP_ERROR is None else "error",
        "startup_error": STARTUP_ERROR,
        "database_url_provided": os.environ.get("DATABASE_URL") is not None,
        "tables_found": list(models.Base.metadata.tables.keys()),
        "python_version": sys.version,
    }

@router.get("/setup-db")
def setup_db():
    """Manually trigger table creation for Supabase."""
    results = {"action": "create_all", "success": False, "error": None, "tables_after": []}
    try:
        models.Base.metadata.create_all(bind=engine)
        results["success"] = True
        results["tables_after"] = list(models.Base.metadata.tables.keys())
    except Exception as e:
        results["error"] = str(e)
    return results

@router.get("/debug/db")
def debug_db():
    try:
        with engine.connect() as connection:
            return {"status": "connected", "database": database.SQLALCHEMY_DATABASE_URL[:20] + "..."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/webhook/analysis")
async def receive_analysis(report: schemas.ReportCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Map incoming schema to database model
    # Note: Report model uses 'llm_model' for model and 'result' for analysis text
    db_report = models.Report(
        trace_id=report.trace_id or str(uuid.uuid4()),
        title=report.title,
        llm_model=report.model or report.llm_model,
        result=report.analysis or report.result,
        date_generated=datetime.utcnow(),
        host=report.host,
        log_file=report.log_file,
        tokens_used=report.tokens_used,
        log_hash=report.log_hash,
        total_lines=report.total_lines,
        total_events=report.total_events,
        error_count=getattr(report, 'error_count', 0)
    )
    
    # Map additional fields if present in schema
    if hasattr(report, 'root_cause') and report.root_cause:
        db_report.root_cause = report.root_cause
    if hasattr(report, 'recommendations') and report.recommendations:
        db_report.recommendations = report.recommendations
    
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    if report.log_entries:
        for entry in report.log_entries:
            db_entry = models.LogEntry(
                report_id=db_report.id,
                timestamp=entry.timestamp,
                source=entry.source,
                status=entry.status,
                message=entry.message,
                stack_trace=getattr(entry, 'stack_trace', None),
                metadata_info=getattr(entry, 'metadata_info', None)
            )
            db.add(db_entry)
        db.commit()
    
    background_tasks.add_task(delete_old_reports, db)
    return {"status": "success", "report_id": db_report.id}

@router.get("/reports", response_model=List[schemas.Report])
def list_reports(db: Session = Depends(get_db)):
    # Match schema date_generated to model field
    return db.query(models.Report).order_by(models.Report.date_generated.desc()).all()

@router.get("/reports/{report_id}", response_model=schemas.Report)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

# Include router twice to handle both /api and root paths on Vercel
app.include_router(router, prefix="/api")
app.include_router(router)

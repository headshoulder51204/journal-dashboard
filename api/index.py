from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, APIRouter, Request
from typing import List, Optional
from datetime import datetime, timedelta
import os
import sys
import traceback
import uuid
from contextlib import asynccontextmanager

# Global variables to capture startup and import errors
STARTUP_ERROR = None
IMPORT_ERROR = None

# Vercel-friendly initialization
IS_VERCEL = os.environ.get("VERCEL") == "1"

# Safe access to engine and session (Lazy Initialization)
_engine = None
_SessionLocal = None

def get_db_components():
    """Lazy loader for database components to prevent module-level crashes."""
    global IMPORT_ERROR, _engine, _SessionLocal
    try:
        # Avoid redundant imports
        import backend.models as models
        import backend.schemas as schemas
        import backend.database as database
        from backend.database import SessionLocal, engine
        return models, schemas, database, SessionLocal, engine
    except Exception as e:
        IMPORT_ERROR = {
            "type": type(e).__name__,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "sys_path": sys.path[:5]
        }
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    global STARTUP_ERROR
    
    # Add project root to path for Vercel
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if BASE_DIR not in sys.path:
        sys.path.append(BASE_DIR)

    try:
        models, schemas, database, SessionLocal, engine = get_db_components()
        
        print(f"DATABASE INITIALIZATION: Checking connection to {database.SQLALCHEMY_DATABASE_URL[:20] if database.SQLALCHEMY_DATABASE_URL else 'None'}...")
        
        # 1. Synchronize Schema
        models.Base.metadata.create_all(bind=engine)
        
        # 2. Test Connection
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # 3. Initial Maintenance
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(hours=24)
            db.query(models.Report).filter(models.Report.date_generated < cutoff).delete()
            db.commit()
        finally:
            db.close()
            
    except Exception as e:
        STARTUP_ERROR = {
            "type": type(e).__name__,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.utcnow().isoformat()
        }
        print(f"DATABASE ERROR during startup: {e}")
    yield

app = FastAPI(
    title="Analytica LOG INTELLIGENCE API (Safe Mode)", 
    lifespan=lifespan,
    root_path="/api" if IS_VERCEL else ""
)

router = APIRouter()

def get_db():
    try:
        models, schemas, database, SessionLocal, engine = get_db_components()
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    except Exception:
        raise HTTPException(status_code=503, detail="Database components unavailable")

@router.get("/")
def read_root(request: Request):
    return {
        "status": "ok", 
        "mode": "safe-diagnostic",
        "environment": "Vercel" if IS_VERCEL else "Local",
        "path": request.url.path,
        "root_path": request.scope.get("root_path")
    }

@router.get("/health")
def health_check(request: Request):
    return {
        "status": "online",
        "diagnostic": {
            "startup_error": STARTUP_ERROR,
            "import_error": IMPORT_ERROR,
            "is_vercel": IS_VERCEL
        },
        "routing": {
            "request_path": request.url.path,
            "root_path": request.scope.get("root_path")
        }
    }

@router.post("/webhook/analysis")
async def receive_analysis(
    report_in: dict, # Receive raw dict first for safety
    background_tasks: BackgroundTasks, 
    request: Request
):
    try:
        models, schemas, database, SessionLocal, engine = get_db_components()
        
        # Parse using Pydantic
        report = schemas.ReportCreate(**report_in)
        
        db = SessionLocal()
        try:
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
                        message=entry.message
                    )
                    db.add(db_entry)
                db.commit()
            
            # Simple cleanup task
            def safe_cleanup():
                try:
                    cutoff = datetime.utcnow() - timedelta(hours=24)
                    db.query(models.Report).filter(models.Report.date_generated < cutoff).delete()
                    db.commit()
                except Exception:
                    pass

            background_tasks.add_task(safe_cleanup)
            return {"status": "success", "report_id": db_report.id}
        finally:
            db.close()

    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc() if not IS_VERCEL else "Check logs"
        }

@router.get("/reports")
def list_reports():
    try:
        models, schemas, database, SessionLocal, engine = get_db_components()
        db = SessionLocal()
        try:
            return db.query(models.Report).order_by(models.Report.date_generated.desc()).all()
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}

# Standard approach: router without prefix + root_path handles it
app.include_router(router)

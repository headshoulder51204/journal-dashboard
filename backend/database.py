import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Priority 1: Cloud Database (Supabase PostgreSQL via Environment Variable)
# Priority 2: Vercel Ephemeral SQLite (for initial testing/fallback)
# Priority 3: Local SQLite
SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL")

if SQLALCHEMY_DATABASE_URL:
    # Fix for Supabase/Heroku style URLs (postgres:// -> postgresql://)
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
else:
    # Fallback logic for SQLite
    if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
        SQLALCHEMY_DATABASE_URL = "sqlite:////tmp/sql_app.db"
    else:
        SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
    
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

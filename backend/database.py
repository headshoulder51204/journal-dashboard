from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os

# Use /tmp for SQLite on Vercel to avoid read-only filesystem errors
# Note: /tmp is ephemeral and data will not persist between cold starts.
# For persistent storage, use an external database like Supabase or Neon.
if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
    SQLALCHEMY_DATABASE_URL = "sqlite:////tmp/sql_app.db"
else:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

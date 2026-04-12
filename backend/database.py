import os
import re
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

def sanitize_db_url(url: str) -> str:
    """Sanitizes the database URL to handle common Supabase/Vercel issues."""
    if not url:
        return url
    
    # Fix for Supabase/Heroku style URLs (postgres:// -> postgresql://)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    
    # Robust password encoding for special characters (!, @, #, etc.)
    if "@" in url and "://" in url:
        try:
            # Separation of credentials and host at the last '@'
            creds_part, host_part = url.rsplit("@", 1)
            protocol_split = creds_part.split("://", 1)
            
            if len(protocol_split) == 2:
                protocol, user_pass = protocol_split
                if ":" in user_pass:
                    user, password = user_pass.split(":", 1)
                    # Quote the password to handle special characters
                    quoted_password = urllib.parse.quote(password)
                    url = f"{protocol}://{user}:{quoted_password}@{host_part}"
        except Exception:
            # Fallback to original if parsing fails
            pass
            
    return url

# Priority 1: Cloud Database (Supabase PostgreSQL via Environment Variable)
# Priority 2: Vercel Ephemeral SQLite (for initial testing/fallback)
# Priority 3: Local SQLite
raw_db_url = os.environ.get("DATABASE_URL")
SQLALCHEMY_DATABASE_URL = sanitize_db_url(raw_db_url)

if SQLALCHEMY_DATABASE_URL:
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

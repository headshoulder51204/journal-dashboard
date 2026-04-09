import os
import re
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
    
    # Handle unencoded '#' characters in the password
    # Database URLs follow: protocol://user:password@host:port/dbname
    # If a '#' exists before the last '@', it's likely an unencoded password character
    if "#" in url and "@" in url:
        parts = url.rsplit("@", 1)
        if len(parts) == 2:
            creds, rest = parts
            # Only replace '#' if it's in the credentials part and not part of the protocol
            protocol_split = creds.split("://", 1)
            if len(protocol_split) == 2:
                protocol, user_pass = protocol_split
                if "#" in user_pass:
                    sanitized_user_pass = user_pass.replace("#", "%23")
                    url = f"{protocol}://{sanitized_user_pass}@{rest}"
    
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

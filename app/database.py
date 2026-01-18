"""Database connection and initialization."""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from app.config import DATABASE_URL, DATABASE_DIR
from app.models import Base


# Ensure database directory exists
def ensure_database_dir():
    """Create database directory if it doesn't exist."""
    Path(DATABASE_DIR).mkdir(parents=True, exist_ok=True)


# Create engine
ensure_database_dir()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database and create all tables."""
    ensure_database_dir()
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for database sessions (for non-FastAPI use)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

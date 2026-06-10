"""
Database initialization and session management.
Uses SQLite via SQLAlchemy for local-first storage.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from models import Base

# Resolve the path to the SQLite file (next to this script)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "deals.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Single engine shared across the app
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # required for SQLite in FastAPI
    echo=False,                                  # set True to see SQL statements
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables if they don't exist yet."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print(f"[DB] Initialized at {DB_PATH}")


@contextmanager
def get_db_session() -> Session:
    """
    Context manager for database sessions.
    Automatically handles commit/rollback/close.
    
    Usage:
        with get_db_session() as db:
            db.add(some_object)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db():
    """
    FastAPI dependency for database sessions.
    Yields a session, then closes it after the request.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

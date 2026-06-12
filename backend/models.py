"""
SQLAlchemy ORM models for the AI Deals Tracker.
Defines the database schema for snapshots and changes.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Snapshot(Base):
    """
    Stores a pricing snapshot for a given tool at a point in time.
    Each run saves a new snapshot; we compare against the previous one.
    """
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tool_name = Column(String(100), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False)   # SHA-256 of cleaned text
    raw_content = Column(Text, nullable=False)           # cleaned text content
    structured_json = Column(Text, nullable=True)        # JSON from scraper
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Snapshot tool={self.tool_name} hash={self.content_hash[:8]} at={self.created_at}>"


class Change(Base):
    """
    Records a detected pricing/content change between two snapshots.
    One row per detected change event.
    """
    __tablename__ = "changes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tool_name = Column(String(100), nullable=False, index=True)
    old_content = Column(Text, nullable=True)   # previous snapshot text
    new_content = Column(Text, nullable=True)   # new snapshot text
    summary = Column(Text, nullable=True)        # human-readable summary of what changed
    structured_change_json = Column(Text, nullable=True)  # structured changes details in JSON
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Change tool={self.tool_name} at={self.detected_at}>"

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from app.db import Base


class LongformMemory(Base):
    __tablename__ = "longform_memories"
    __table_args__ = (
        UniqueConstraint("project_id", "memory_type", "scope_key", name="uq_longform_memories_scope"),
        Index("ix_longform_memories_project_type", "project_id", "memory_type"),
        Index("ix_longform_memories_project_range", "project_id", "start_chapter_index", "end_chapter_index"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    memory_type = Column(String, nullable=False)
    scope_key = Column(String, nullable=False)
    start_chapter_index = Column(Integer, nullable=True)
    end_chapter_index = Column(Integer, nullable=True)
    title = Column(String, default="")
    summary = Column(Text, default="")
    status = Column(String, default="current")
    memory_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

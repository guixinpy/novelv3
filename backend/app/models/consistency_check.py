import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.db import Base


class ConsistencyCheck(Base):
    __tablename__ = "consistency_checks"
    __table_args__ = (
        Index("ix_consistency_checks_project_chapter", "project_id", "chapter_index"),
        Index("ix_consistency_checks_project_status", "project_id", "status"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    chapter_index = Column(Integer, nullable=False)
    checker_name = Column(String, nullable=False)
    severity = Column(String, default="warn")
    subject = Column(String, default="")
    description = Column(Text, default="")
    evidence = Column(Text, default="")
    suggested_fix = Column(Text, default="")
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

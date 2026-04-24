import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String

from app.db import Base


class Outline(Base):
    __tablename__ = "outlines"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    total_chapters = Column(Integer, default=0)
    chapters = Column(JSON, default=list)
    plotlines = Column(JSON, default=list)
    foreshadowing = Column(JSON, default=list)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

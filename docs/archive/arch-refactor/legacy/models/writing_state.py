from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.db import Base


class WritingState(Base):
    __tablename__ = "writing_states"

    project_id = Column(String, ForeignKey("projects.id"), primary_key=True)
    current_chapter = Column(Integer, default=1, nullable=False)
    status = Column(String, default="idle", nullable=False)
    last_error = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text

from app.db import Base


class BackgroundTask(Base):
    __tablename__ = "background_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    task_type = Column(String, nullable=False)
    payload = Column(JSON, default=dict)
    status = Column(String, default="pending")
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

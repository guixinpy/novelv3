import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String

from app.db import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String, default="")
    genre = Column(String, default="")
    target_word_count = Column(Integer, default=0)
    current_word_count = Column(Integer, default=0)
    status = Column(String, default="draft")
    current_phase = Column(String, default="setup")
    ai_model = Column(String, default="deepseek-chat")
    language = Column(String, default="zh-CN")
    style = Column(String, default="")
    complexity = Column(Integer, default=3)
    style_config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

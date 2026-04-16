import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, Float, DateTime, ForeignKey
from app.db import Base


class ChapterContent(Base):
    __tablename__ = "chapter_contents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    chapter_index = Column(Integer, nullable=False)
    title = Column(String, default="")
    content = Column(Text, default="")
    word_count = Column(Integer, default=0)
    status = Column(String, default="pending")
    model = Column(String, default="")
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    generation_time = Column(Integer, default=0)
    temperature = Column(Float, default=0.7)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

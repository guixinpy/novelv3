import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, ForeignKey
from app.db import Base


class ExtractedFact(Base):
    __tablename__ = "extracted_facts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    chapter_index = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    source = Column(String, default="l1_rule")
    confidence = Column(Float, default=1.0)
    data = Column(JSON, default=dict)
    evidence = Column(JSON, default=dict)
    validation = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

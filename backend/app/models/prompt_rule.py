import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from app.db import Base


class PromptRule(Base):
    __tablename__ = "prompt_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    rule_type = Column(String, nullable=False)
    condition = Column(String, default="")
    action = Column(String, default="")
    priority = Column(Integer, default=0)
    hit_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

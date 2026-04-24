import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String

from app.db import Base


class Setup(Base):
    __tablename__ = "setups"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    world_building = Column(JSON, default=dict)
    characters = Column(JSON, default=list)
    core_concept = Column(JSON, default=dict)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

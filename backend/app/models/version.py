import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from app.db import Base


class Version(Base):
    __tablename__ = "versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    node_type = Column(String, nullable=False)
    node_id = Column(String, nullable=False)
    version_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    description = Column(String, default="")
    author = Column(String, default="ai_system")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

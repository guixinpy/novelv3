import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.db import Base


class Version(Base):
    __tablename__ = "versions"
    __table_args__ = (
        Index("ix_versions_project_node_created", "project_id", "node_type", "node_id", "created_at", "id"),
        Index("ix_versions_project_node_version", "project_id", "node_type", "node_id", "version_number"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    node_type = Column(String, nullable=False)
    node_id = Column(String, nullable=False)
    version_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    description = Column(String, default="")
    author = Column(String, default="ai_system")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

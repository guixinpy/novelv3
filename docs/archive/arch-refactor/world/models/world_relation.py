import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.db import Base


class WorldRelation(Base):
    __tablename__ = "world_relations"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "profile_version",
            "relation_id",
            name="uq_world_relations_project_profile_relation_id",
        ),
        ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        Index("ix_world_relations_project_profile_version", "project_id", "profile_version"),
        Index("ix_world_relations_relation_id", "relation_id"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    profile_version = Column(Integer, nullable=False)
    relation_id = Column(String, nullable=False)
    source_entity_ref = Column(String, nullable=False)
    target_entity_ref = Column(String, nullable=False)
    relation_type = Column(String, nullable=False)
    directionality = Column(String, nullable=False)
    status = Column(String, nullable=False)
    visibility_layer = Column(String, nullable=False)
    strength_or_weight = Column(String, default="")
    start_anchor_id = Column(String, nullable=True)
    end_anchor_id = Column(String, nullable=True)
    evidence_refs = Column(JSON, default=list)
    notes = Column(Text, default="")
    contract_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

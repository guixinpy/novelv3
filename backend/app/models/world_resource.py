import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, String, Text, UniqueConstraint

from app.db import Base


class WorldResource(Base):
    __tablename__ = "world_resources"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "profile_version",
            "resource_id",
            name="uq_world_resources_project_profile_resource_id",
        ),
        UniqueConstraint(
            "project_id",
            "profile_version",
            "canonical_id",
            name="uq_world_resources_project_profile_canonical",
        ),
        ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        Index("ix_world_resources_project_profile_version", "project_id", "profile_version"),
        Index("ix_world_resources_canonical_id", "canonical_id"),
        Index("ix_world_resources_primary_alias", "primary_alias"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    profile_version = Column(Integer, nullable=False)
    resource_id = Column(String, nullable=False)
    canonical_id = Column(String, nullable=False)
    primary_alias = Column(String, default="")
    name = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    unit_or_scale = Column(String, default="")
    holder_type = Column(String, default="")
    acquisition_paths = Column(JSON, default=list)
    consumption_paths = Column(JSON, default=list)
    scarcity_level = Column(String, default="")
    renewal_model = Column(String, default="")
    transferability = Column(String, default="")
    visibility = Column(String, default="")
    critical_threshold_effect = Column(Text, default="")
    notes = Column(Text, default="")
    contract_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

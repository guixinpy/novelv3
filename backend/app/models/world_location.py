import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, String, Text, UniqueConstraint

from app.db import Base


class WorldLocation(Base):
    __tablename__ = "world_locations"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "profile_version",
            "location_id",
            name="uq_world_locations_project_profile_location_id",
        ),
        UniqueConstraint(
            "project_id",
            "profile_version",
            "canonical_id",
            name="uq_world_locations_project_profile_canonical",
        ),
        ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        Index("ix_world_locations_project_profile_version", "project_id", "profile_version"),
        Index("ix_world_locations_canonical_id", "canonical_id"),
        Index("ix_world_locations_primary_alias", "primary_alias"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    profile_version = Column(Integer, nullable=False)
    location_id = Column(String, nullable=False)
    canonical_id = Column(String, nullable=False)
    primary_alias = Column(String, default="")
    name = Column(String, nullable=False)
    aliases = Column(JSON, default=list)
    location_type = Column(String, nullable=False)
    parent_location_id = Column(String, nullable=True)
    spatial_scope = Column(Text, default="")
    access_constraints = Column(JSON, default=list)
    functional_tags = Column(JSON, default=list)
    hazards = Column(JSON, default=list)
    resource_tags = Column(JSON, default=list)
    surveillance_or_visibility_level = Column(String, default="")
    notes = Column(Text, default="")
    contract_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

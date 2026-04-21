import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, String, Text, UniqueConstraint

from app.db import Base


class WorldArtifact(Base):
    __tablename__ = "world_artifacts"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "profile_version",
            "artifact_id",
            name="uq_world_artifacts_project_profile_artifact_id",
        ),
        UniqueConstraint(
            "project_id",
            "profile_version",
            "canonical_id",
            name="uq_world_artifacts_project_profile_canonical",
        ),
        ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        Index("ix_world_artifacts_project_profile_version", "project_id", "profile_version"),
        Index("ix_world_artifacts_canonical_id", "canonical_id"),
        Index("ix_world_artifacts_primary_alias", "primary_alias"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    profile_version = Column(Integer, nullable=False)
    artifact_id = Column(String, nullable=False)
    canonical_id = Column(String, nullable=False)
    primary_alias = Column(String, default="")
    name = Column(String, nullable=False)
    aliases = Column(JSON, default=list)
    artifact_type = Column(String, nullable=False)
    origin = Column(Text, default="")
    function_summary = Column(Text, default="")
    activation_conditions = Column(JSON, default=list)
    usage_constraints = Column(JSON, default=list)
    risk_or_side_effects = Column(JSON, default=list)
    identity_or_auth_requirements = Column(JSON, default=list)
    uniqueness = Column(String, default="")
    traceability = Column(String, default="")
    notes = Column(Text, default="")
    contract_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

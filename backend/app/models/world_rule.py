import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, String, Text, UniqueConstraint

from app.db import Base


class WorldRule(Base):
    __tablename__ = "world_rules"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "profile_version",
            "rule_id",
            name="uq_world_rules_project_profile_rule_id",
        ),
        UniqueConstraint(
            "project_id",
            "profile_version",
            "canonical_id",
            name="uq_world_rules_project_profile_canonical",
        ),
        ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        Index("ix_world_rules_project_profile_version", "project_id", "profile_version"),
        Index("ix_world_rules_canonical_id", "canonical_id"),
        Index("ix_world_rules_primary_alias", "primary_alias"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    profile_version = Column(Integer, nullable=False)
    rule_id = Column(String, nullable=False)
    canonical_id = Column(String, nullable=False)
    primary_alias = Column(String, default="")
    name = Column(String, nullable=False)
    rule_type = Column(String, nullable=False)
    scope = Column(Text, default="")
    statement = Column(Text, nullable=False)
    preconditions = Column(JSON, default=list)
    effects = Column(JSON, default=list)
    constraints = Column(JSON, default=list)
    exceptions = Column(JSON, default=list)
    violation_cost = Column(Text, default="")
    enforcement_agent = Column(String, default="")
    repair_or_override_path = Column(Text, default="")
    notes = Column(Text, default="")
    contract_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

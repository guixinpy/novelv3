import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, String, Text, UniqueConstraint

from app.db import Base


class WorldFaction(Base):
    __tablename__ = "world_factions"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "profile_version",
            "faction_id",
            name="uq_world_factions_project_profile_faction_id",
        ),
        UniqueConstraint(
            "project_id",
            "profile_version",
            "canonical_id",
            name="uq_world_factions_project_profile_canonical",
        ),
        ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        Index("ix_world_factions_project_profile_version", "project_id", "profile_version"),
        Index("ix_world_factions_canonical_id", "canonical_id"),
        Index("ix_world_factions_primary_alias", "primary_alias"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    profile_version = Column(Integer, nullable=False)
    faction_id = Column(String, nullable=False)
    canonical_id = Column(String, nullable=False)
    primary_alias = Column(String, default="")
    name = Column(String, nullable=False)
    aliases = Column(JSON, default=list)
    faction_type = Column(String, nullable=False)
    mission_or_doctrine = Column(Text, default="")
    structure_model = Column(String, default="")
    authority_rules = Column(JSON, default=list)
    membership_rules = Column(JSON, default=list)
    taboos = Column(JSON, default=list)
    resource_domains = Column(JSON, default=list)
    territorial_scope = Column(Text, default="")
    public_image = Column(Text, default="")
    hidden_agenda = Column(Text, default="")
    notes = Column(Text, default="")
    contract_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

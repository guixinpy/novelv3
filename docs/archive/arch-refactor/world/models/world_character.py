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


class WorldCharacter(Base):
    __tablename__ = "world_characters"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "profile_version",
            "character_id",
            name="uq_world_characters_project_profile_character_id",
        ),
        UniqueConstraint(
            "project_id",
            "profile_version",
            "canonical_id",
            name="uq_world_characters_project_profile_canonical",
        ),
        ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        Index("ix_world_characters_project_profile_version", "project_id", "profile_version"),
        Index("ix_world_characters_canonical_id", "canonical_id"),
        Index("ix_world_characters_primary_alias", "primary_alias"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    profile_version = Column(Integer, nullable=False)
    character_id = Column(String, nullable=False)
    canonical_id = Column(String, nullable=False)
    primary_alias = Column(String, default="")
    name = Column(String, nullable=False)
    aliases = Column(JSON, default=list)
    role_type = Column(String, nullable=False)
    identity_anchor = Column(String, nullable=False)
    origin_background = Column(Text, default="")
    core_traits = Column(JSON, default=list)
    core_drives = Column(JSON, default=list)
    core_fears = Column(JSON, default=list)
    taboos_or_bottom_lines = Column(JSON, default=list)
    base_capabilities = Column(JSON, default=list)
    capability_ceiling_or_constraints = Column(JSON, default=list)
    default_affiliations = Column(JSON, default=list)
    public_persona = Column(Text, default="")
    hidden_truths = Column(JSON, default=list)
    notes = Column(Text, default="")
    contract_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

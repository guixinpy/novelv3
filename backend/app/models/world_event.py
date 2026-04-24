import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
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
from app.models.world_constraints import attach_profile_binding_consistency_triggers


class WorldEvent(Base):
    __tablename__ = "world_events"
    __table_args__ = (
        CheckConstraint(
            "profile_version IS NOT NULL OR project_profile_version_id IS NOT NULL",
            name="ck_world_events_has_profile_version_binding",
        ),
        ForeignKeyConstraint(
            ["project_id", "project_profile_version_id"],
            ["project_profile_versions.project_id", "project_profile_versions.id"],
        ),
        ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        UniqueConstraint("project_id", "event_id", name="uq_world_events_project_event_id"),
        UniqueConstraint("project_id", "idempotency_key", name="uq_world_events_project_idempotency_key"),
        ForeignKeyConstraint(
            ["project_id", "supersedes_event_ref"],
            ["world_events.project_id", "world_events.event_id"],
        ),
        Index("ix_world_events_project_profile_version", "project_id", "profile_version"),
        Index("ix_world_events_chapter_seq", "chapter_index", "intra_chapter_seq"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    project_profile_version_id = Column(
        String,
        ForeignKey("project_profile_versions.id"),
        nullable=True,
    )
    profile_version = Column(Integer, nullable=True)
    event_id = Column(String, nullable=False)
    idempotency_key = Column(String, nullable=True)
    timeline_anchor_id = Column(String, nullable=False)
    chapter_index = Column(Integer, nullable=False)
    intra_chapter_seq = Column(Integer, nullable=False)
    event_type = Column(String, nullable=False)
    participant_refs = Column(JSON, default=list)
    location_refs = Column(JSON, default=list)
    precondition_event_refs = Column(JSON, default=list)
    caused_event_refs = Column(JSON, default=list)
    primitive_payload = Column(JSON, default=dict)
    state_diffs = Column(JSON, default=list)
    truth_layer = Column(String, nullable=False)
    disclosure_layer = Column(String, nullable=False)
    evidence_refs = Column(JSON, default=list)
    contract_version_refs = Column(JSON, default=list)
    supersedes_event_ref = Column(String, nullable=True)
    notes = Column(Text, default="")
    contract_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


attach_profile_binding_consistency_triggers(WorldEvent.__table__, WorldEvent.__tablename__)

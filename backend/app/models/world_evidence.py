import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, String, Text, UniqueConstraint

from app.db import Base
from app.models.world_constraints import attach_profile_binding_consistency_triggers


class WorldEvidence(Base):
    __tablename__ = "world_evidence"
    __table_args__ = (
        CheckConstraint(
            "profile_version IS NOT NULL OR project_profile_version_id IS NOT NULL",
            name="ck_world_evidence_has_profile_version_binding",
        ),
        ForeignKeyConstraint(
            ["project_id", "project_profile_version_id"],
            ["project_profile_versions.project_id", "project_profile_versions.id"],
        ),
        ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        UniqueConstraint("project_id", "evidence_id", name="uq_world_evidence_project_evidence_id"),
        Index("ix_world_evidence_project_profile_version", "project_id", "profile_version"),
        Index("ix_world_evidence_chapter_seq", "chapter_index", "intra_chapter_seq"),
        Index("ix_world_evidence_evidence_id", "evidence_id"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    project_profile_version_id = Column(
        String,
        ForeignKey("project_profile_versions.id"),
        nullable=True,
    )
    profile_version = Column(Integer, nullable=True)
    evidence_id = Column(String, nullable=False)
    chapter_index = Column(Integer, nullable=True)
    intra_chapter_seq = Column(Integer, default=0)
    evidence_type = Column(String, nullable=False)
    source_scope = Column(String, nullable=False)
    content_excerpt_or_summary = Column(Text, default="")
    holder_ref = Column(String, default="")
    authenticity_status = Column(String, default="")
    reliability_level = Column(String, default="")
    disclosure_layer = Column(String, nullable=False)
    related_claim_refs = Column(JSON, default=list)
    related_event_refs = Column(JSON, default=list)
    timeline_anchor_id = Column(String, nullable=True)
    notes = Column(Text, default="")
    contract_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


attach_profile_binding_consistency_triggers(WorldEvidence.__table__, WorldEvidence.__tablename__)

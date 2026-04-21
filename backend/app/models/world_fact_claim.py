import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, String, Text, UniqueConstraint

from app.db import Base
from app.core.world_contracts import AUTHORITY_TYPES
from app.models.world_constraints import attach_profile_binding_consistency_triggers


_authority_types_sql = ", ".join(f"'{value}'" for value in AUTHORITY_TYPES)


class WorldFactClaim(Base):
    __tablename__ = "world_fact_claims"
    __table_args__ = (
        CheckConstraint(
            "profile_version IS NOT NULL OR project_profile_version_id IS NOT NULL",
            name="ck_world_fact_claims_has_profile_version_binding",
        ),
        CheckConstraint(
            f"authority_type IN ({_authority_types_sql})",
            name="ck_world_fact_claims_authority_type",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_world_fact_claims_confidence_range",
        ),
        ForeignKeyConstraint(
            ["project_id", "project_profile_version_id"],
            ["project_profile_versions.project_id", "project_profile_versions.id"],
        ),
        ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        UniqueConstraint("project_id", "claim_id", name="uq_world_fact_claims_project_claim_id"),
        Index("ix_world_fact_claims_project_profile_version", "project_id", "profile_version"),
        Index("ix_world_fact_claims_chapter_seq", "chapter_index", "intra_chapter_seq"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    project_profile_version_id = Column(
        String,
        ForeignKey("project_profile_versions.id"),
        nullable=True,
    )
    profile_version = Column(Integer, nullable=True)
    claim_id = Column(String, nullable=False)
    chapter_index = Column(Integer, nullable=True)
    intra_chapter_seq = Column(Integer, default=0)
    subject_ref = Column(String, nullable=False)
    predicate = Column(String, nullable=False)
    object_ref_or_value = Column(JSON, nullable=False)
    claim_layer = Column(String, nullable=False)
    claim_status = Column(String, nullable=False)
    valid_from_anchor_id = Column(String, nullable=True)
    valid_to_anchor_id = Column(String, nullable=True)
    source_event_ref = Column(String, nullable=True)
    evidence_refs = Column(JSON, default=list)
    authority_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    notes = Column(Text, default="")
    contract_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


attach_profile_binding_consistency_triggers(WorldFactClaim.__table__, WorldFactClaim.__tablename__)

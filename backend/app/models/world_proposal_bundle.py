import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.db import Base
from app.models.world_constraints import (
    attach_parent_item_lineage_consistency_triggers,
    attach_profile_binding_consistency_triggers,
)


class WorldProposalBundle(Base):
    __tablename__ = "world_proposal_bundles"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "project_profile_version_id"],
            ["project_profile_versions.project_id", "project_profile_versions.id"],
        ),
        ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        ForeignKeyConstraint(
            ["parent_bundle_id", "project_id", "project_profile_version_id", "profile_version"],
            [
                "world_proposal_bundles.id",
                "world_proposal_bundles.project_id",
                "world_proposal_bundles.project_profile_version_id",
                "world_proposal_bundles.profile_version",
            ],
        ),
        UniqueConstraint(
            "id",
            "project_id",
            "project_profile_version_id",
            "profile_version",
            name="uq_world_proposal_bundles_binding",
        ),
        Index("ix_world_proposal_bundles_project_profile_version", "project_id", "profile_version"),
        Index("ix_world_proposal_bundles_parent_bundle_id", "parent_bundle_id"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    project_profile_version_id = Column(String, ForeignKey("project_profile_versions.id"), nullable=False)
    profile_version = Column(Integer, nullable=False)
    parent_bundle_id = Column(String, ForeignKey("world_proposal_bundles.id"), nullable=True)
    bundle_status = Column(String, nullable=False, default="pending")
    title = Column(String, nullable=False)
    summary = Column(Text, default="")
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class WorldProposalItem(Base):
    __tablename__ = "world_proposal_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "project_profile_version_id"],
            ["project_profile_versions.project_id", "project_profile_versions.id"],
        ),
        ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        ForeignKeyConstraint(
            ["bundle_id", "project_id", "project_profile_version_id", "profile_version"],
            [
                "world_proposal_bundles.id",
                "world_proposal_bundles.project_id",
                "world_proposal_bundles.project_profile_version_id",
                "world_proposal_bundles.profile_version",
            ],
        ),
        UniqueConstraint(
            "id",
            "bundle_id",
            "project_id",
            "project_profile_version_id",
            "profile_version",
            name="uq_world_proposal_items_binding",
        ),
        Index("ix_world_proposal_items_bundle_id", "bundle_id"),
        Index("ix_world_proposal_items_parent_item_id", "parent_item_id"),
        Index("ix_world_proposal_items_project_profile_version", "project_id", "profile_version"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    project_profile_version_id = Column(String, ForeignKey("project_profile_versions.id"), nullable=False)
    profile_version = Column(Integer, nullable=False)
    bundle_id = Column(String, ForeignKey("world_proposal_bundles.id"), nullable=False)
    parent_item_id = Column(String, ForeignKey("world_proposal_items.id"), nullable=True)
    item_status = Column(String, nullable=False, default="pending")
    claim_id = Column(String, nullable=False)
    chapter_index = Column(Integer, nullable=True)
    intra_chapter_seq = Column(Integer, nullable=False, default=0)
    subject_ref = Column(String, nullable=False)
    predicate = Column(String, nullable=False)
    object_ref_or_value = Column(JSON, nullable=False)
    claim_layer = Column(String, nullable=False)
    valid_from_anchor_id = Column(String, nullable=True)
    valid_to_anchor_id = Column(String, nullable=True)
    source_event_ref = Column(String, nullable=True)
    evidence_refs = Column(JSON, default=list)
    authority_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    notes = Column(Text, default="")
    contract_version = Column(String, nullable=False)
    created_by = Column(String, nullable=False)
    approved_claim_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class WorldProposalReview(Base):
    __tablename__ = "world_proposal_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "project_profile_version_id"],
            ["project_profile_versions.project_id", "project_profile_versions.id"],
        ),
        ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        ForeignKeyConstraint(
            ["bundle_id", "project_id", "project_profile_version_id", "profile_version"],
            [
                "world_proposal_bundles.id",
                "world_proposal_bundles.project_id",
                "world_proposal_bundles.project_profile_version_id",
                "world_proposal_bundles.profile_version",
            ],
        ),
        ForeignKeyConstraint(
            ["proposal_item_id", "bundle_id", "project_id", "project_profile_version_id", "profile_version"],
            [
                "world_proposal_items.id",
                "world_proposal_items.bundle_id",
                "world_proposal_items.project_id",
                "world_proposal_items.project_profile_version_id",
                "world_proposal_items.profile_version",
            ],
        ),
        ForeignKeyConstraint(
            ["rollback_to_review_id", "bundle_id", "project_id", "project_profile_version_id", "profile_version"],
            [
                "world_proposal_reviews.id",
                "world_proposal_reviews.bundle_id",
                "world_proposal_reviews.project_id",
                "world_proposal_reviews.project_profile_version_id",
                "world_proposal_reviews.profile_version",
            ],
        ),
        UniqueConstraint(
            "id",
            "bundle_id",
            "project_id",
            "project_profile_version_id",
            "profile_version",
            name="uq_world_proposal_reviews_binding",
        ),
        UniqueConstraint("rollback_to_review_id", name="uq_world_proposal_reviews_rollback_to_review_id"),
        Index("ix_world_proposal_reviews_bundle_id", "bundle_id"),
        Index("ix_world_proposal_reviews_item_id", "proposal_item_id"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    project_profile_version_id = Column(String, ForeignKey("project_profile_versions.id"), nullable=False)
    profile_version = Column(Integer, nullable=False)
    bundle_id = Column(String, ForeignKey("world_proposal_bundles.id"), nullable=False)
    proposal_item_id = Column(String, ForeignKey("world_proposal_items.id"), nullable=True)
    review_action = Column(String, nullable=False)
    reviewer_ref = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    evidence_refs = Column(JSON, default=list)
    edited_fields = Column(JSON, default=dict)
    created_truth_claim_id = Column(String, nullable=True)
    rollback_to_review_id = Column(String, ForeignKey("world_proposal_reviews.id"), nullable=True)
    metadata_snapshot = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class WorldProposalImpactScopeSnapshot(Base):
    __tablename__ = "world_proposal_impact_scope_snapshots"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "project_profile_version_id"],
            ["project_profile_versions.project_id", "project_profile_versions.id"],
        ),
        ForeignKeyConstraint(
            ["project_id", "profile_version"],
            ["project_profile_versions.project_id", "project_profile_versions.version"],
        ),
        Index("ix_world_proposal_impact_scope_bundle_id", "bundle_id"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    project_profile_version_id = Column(String, ForeignKey("project_profile_versions.id"), nullable=False)
    profile_version = Column(Integer, nullable=False)
    bundle_id = Column(String, ForeignKey("world_proposal_bundles.id"), nullable=False)
    affected_subject_refs = Column(JSON, default=list)
    affected_predicates = Column(JSON, default=list)
    affected_truth_claim_ids = Column(JSON, default=list)
    candidate_item_ids = Column(JSON, default=list)
    summary = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


attach_profile_binding_consistency_triggers(WorldProposalBundle.__table__, WorldProposalBundle.__tablename__)
attach_profile_binding_consistency_triggers(WorldProposalItem.__table__, WorldProposalItem.__tablename__)
attach_profile_binding_consistency_triggers(WorldProposalReview.__table__, WorldProposalReview.__tablename__)
attach_profile_binding_consistency_triggers(
    WorldProposalImpactScopeSnapshot.__table__,
    WorldProposalImpactScopeSnapshot.__tablename__,
)
attach_parent_item_lineage_consistency_triggers(
    WorldProposalItem.__table__,
    WorldProposalItem.__tablename__,
    bundle_table_name=WorldProposalBundle.__tablename__,
)

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.world_contracts import AUTHORITY_TYPES


class _VersionBoundModel(BaseModel):
    project_id: str
    project_profile_version_id: str | None = None
    profile_version: int | None = Field(default=None, ge=1)
    contract_version: str

    @model_validator(mode="after")
    def validate_version_binding(self):
        if self.project_profile_version_id is None and self.profile_version is None:
            raise ValueError("either profile_version or project_profile_version_id is required")
        return self

    model_config = ConfigDict(extra="forbid")


class ProposalBundleCreate(_VersionBoundModel):
    title: str
    summary: str = ""
    created_by: str
    parent_bundle_id: str | None = None


class ProposalCandidateFactCreate(_VersionBoundModel):
    claim_id: str
    chapter_index: int | None = Field(default=None, ge=0)
    intra_chapter_seq: int = Field(default=0, ge=0)
    subject_ref: str
    predicate: str
    object_ref_or_value: Any
    claim_layer: str
    valid_from_anchor_id: str | None = None
    valid_to_anchor_id: str | None = None
    source_event_ref: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    authority_type: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    notes: str = ""

    @field_validator("authority_type")
    @classmethod
    def validate_authority_type(cls, value: str) -> str:
        if value not in AUTHORITY_TYPES:
            raise ValueError("authority_type is invalid")
        return value


class ProposalReviewCreate(BaseModel):
    reviewer_ref: str
    action: str
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    edited_fields: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class ProposalClaimEditPatch(BaseModel):
    chapter_index: int | None = Field(default=None, ge=0)
    intra_chapter_seq: int | None = Field(default=None, ge=0)
    valid_from_anchor_id: str | None = None
    valid_to_anchor_id: str | None = None
    source_event_ref: str | None = None
    evidence_refs: list[str] | None = None
    notes: str | None = None

    model_config = ConfigDict(extra="forbid", strict=True)


class ProposalBundleOut(BaseModel):
    id: str
    project_id: str
    project_profile_version_id: str
    profile_version: int
    parent_bundle_id: str | None
    bundle_status: str
    title: str
    summary: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProposalItemOut(BaseModel):
    id: str
    bundle_id: str
    parent_item_id: str | None
    item_status: str
    claim_id: str
    subject_ref: str
    predicate: str
    object_ref_or_value: Any
    claim_layer: str
    evidence_refs: list[str]
    authority_type: str
    confidence: float
    contract_version: str
    approved_claim_id: str | None
    created_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProposalReviewOut(BaseModel):
    id: str
    bundle_id: str
    proposal_item_id: str | None
    review_action: str
    reviewer_ref: str
    reason: str
    evidence_refs: list[str]
    edited_fields: dict[str, Any]
    created_truth_claim_id: str | None
    rollback_to_review_id: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProposalImpactScopeSnapshotOut(BaseModel):
    id: str
    bundle_id: str
    affected_subject_refs: list[str]
    affected_predicates: list[str]
    affected_truth_claim_ids: list[str]
    candidate_item_ids: list[str]
    summary: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProposalBundleSplitCreate(BaseModel):
    reviewer_ref: str
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    item_ids: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ProposalReviewRollbackCreate(BaseModel):
    reviewer_ref: str
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ProposalItemConflictOut(BaseModel):
    item_id: str
    conflict_type: str  # "truth_conflict" | "high_impact"
    detail: str
    existing_claim_id: str | None = None

    model_config = ConfigDict(extra="forbid")


class PaginatedProposalBundlesOut(BaseModel):
    items: list[ProposalBundleOut] = Field(default_factory=list)
    total: int = 0
    offset: int = 0
    limit: int = 20

    model_config = ConfigDict(extra="forbid")


class ProposalBundleDetailOut(BaseModel):
    bundle: ProposalBundleOut
    items: list[ProposalItemOut] = Field(default_factory=list)
    reviews: list[ProposalReviewOut] = Field(default_factory=list)
    impact_snapshots: list[ProposalImpactScopeSnapshotOut] = Field(default_factory=list)
    conflicts: list[ProposalItemConflictOut] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

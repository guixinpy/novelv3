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


class WorldEventCreate(_VersionBoundModel):
    event_id: str
    idempotency_key: str | None = None
    event_type: str
    timeline_anchor_id: str
    chapter_index: int = Field(ge=0)
    intra_chapter_seq: int = Field(ge=0)
    participant_refs: list[str] = Field(default_factory=list)
    location_refs: list[str] = Field(default_factory=list)
    precondition_event_refs: list[str] = Field(default_factory=list)
    caused_event_refs: list[str] = Field(default_factory=list)
    primitive_payload: dict[str, Any] = Field(default_factory=dict)
    state_diffs: list[dict[str, Any]] = Field(default_factory=list)
    truth_layer: str
    disclosure_layer: str
    evidence_refs: list[str] = Field(default_factory=list)
    contract_version_refs: list[str] = Field(default_factory=list)
    supersedes_event_ref: str | None = None
    notes: str = ""


class WorldEventOut(WorldEventCreate):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorldFactClaimCreate(_VersionBoundModel):
    claim_id: str
    chapter_index: int | None = Field(default=None, ge=0)
    intra_chapter_seq: int = Field(default=0, ge=0)
    subject_ref: str
    predicate: str
    object_ref_or_value: Any
    claim_layer: str
    claim_status: str
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


class WorldFactClaimOut(WorldFactClaimCreate):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorldEvidenceCreate(_VersionBoundModel):
    evidence_id: str
    chapter_index: int | None = Field(default=None, ge=0)
    intra_chapter_seq: int = Field(default=0, ge=0)
    evidence_type: str
    source_scope: str
    content_excerpt_or_summary: str = ""
    holder_ref: str = ""
    authenticity_status: str = ""
    reliability_level: str = ""
    disclosure_layer: str
    related_claim_refs: list[str] = Field(default_factory=list)
    related_event_refs: list[str] = Field(default_factory=list)
    timeline_anchor_id: str | None = None
    notes: str = ""


class WorldEvidenceOut(WorldEvidenceCreate):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

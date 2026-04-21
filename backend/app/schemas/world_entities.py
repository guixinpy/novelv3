from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class _WorldEntityCommon(BaseModel):
    project_id: str
    profile_version: int = Field(ge=1)
    canonical_id: str
    primary_alias: str = ""
    name: str
    contract_version: str

    model_config = ConfigDict(extra="forbid")


class WorldCharacterOut(_WorldEntityCommon):
    id: str
    character_id: str
    aliases: list[str]
    role_type: str
    identity_anchor: str
    origin_background: str
    core_traits: list[str]
    core_drives: list[str]
    core_fears: list[str]
    taboos_or_bottom_lines: list[str]
    base_capabilities: list[str]
    capability_ceiling_or_constraints: list[str]
    default_affiliations: list[str]
    public_persona: str
    hidden_truths: list[str]
    notes: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorldLocationOut(_WorldEntityCommon):
    id: str
    location_id: str
    aliases: list[str]
    location_type: str
    parent_location_id: str | None
    spatial_scope: str
    access_constraints: list[str]
    functional_tags: list[str]
    hazards: list[str]
    resource_tags: list[str]
    surveillance_or_visibility_level: str
    notes: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorldFactionOut(_WorldEntityCommon):
    id: str
    faction_id: str
    aliases: list[str]
    faction_type: str
    mission_or_doctrine: str
    structure_model: str
    authority_rules: list[str]
    membership_rules: list[str]
    taboos: list[str]
    resource_domains: list[str]
    territorial_scope: str
    public_image: str
    hidden_agenda: str
    notes: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorldArtifactOut(_WorldEntityCommon):
    id: str
    artifact_id: str
    aliases: list[str]
    artifact_type: str
    origin: str
    function_summary: str
    activation_conditions: list[str]
    usage_constraints: list[str]
    risk_or_side_effects: list[str]
    identity_or_auth_requirements: list[str]
    uniqueness: str
    traceability: str
    notes: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorldRuleOut(_WorldEntityCommon):
    id: str
    rule_id: str
    rule_type: str
    scope: str
    statement: str
    preconditions: list[str]
    effects: list[str]
    constraints: list[str]
    exceptions: list[str]
    violation_cost: str
    enforcement_agent: str
    repair_or_override_path: str
    notes: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorldResourceOut(_WorldEntityCommon):
    id: str
    resource_id: str
    resource_type: str
    unit_or_scale: str
    holder_type: str
    acquisition_paths: list[str]
    consumption_paths: list[str]
    scarcity_level: str
    renewal_model: str
    transferability: str
    visibility: str
    critical_threshold_effect: str
    notes: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorldRelationOut(BaseModel):
    id: str
    project_id: str
    profile_version: int
    relation_id: str
    source_entity_ref: str
    target_entity_ref: str
    relation_type: str
    directionality: str
    status: str
    visibility_layer: str
    strength_or_weight: str
    start_anchor_id: str | None
    end_anchor_id: str | None
    evidence_refs: list[str]
    notes: str
    contract_version: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorldTimelineAnchorOut(BaseModel):
    id: str
    project_id: str
    profile_version: int
    anchor_id: str
    chapter_index: int | None
    intra_chapter_seq: int
    world_time_label: str
    normalized_tick_or_range: str
    precision: str
    relative_to_anchor_ref: str | None
    ordering_key: str
    notes: str
    contract_version: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Index, JSON, String, UniqueConstraint

from app.db import Base


class GenreProfile(Base):
    __tablename__ = "genre_profiles"
    __table_args__ = (
        UniqueConstraint("canonical_id", name="uq_genre_profiles_canonical_id"),
        Index("ix_genre_profiles_canonical_id", "canonical_id"),
        Index("ix_genre_profiles_primary_alias", "primary_alias"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    canonical_id = Column(String, nullable=False)
    primary_alias = Column(String, default="")
    display_name = Column(String, nullable=False)
    contract_version = Column(String, nullable=False)
    field_authority = Column(JSON, default=dict)
    schema_payload = Column(JSON, default=dict)
    module_payload = Column(JSON, default=dict)
    event_types = Column(JSON, default=list)
    checker_config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


CORE_WORLD_EVENT_TYPES = (
    "entity_introduced",
    "attribute_mutated",
    "relation_mutated",
    "presence_shifted",
    "event_occurred",
    "event_linked",
    "retcon_applied",
    "fact_reviewed",
)


def _checker_layers(*profile_rules: str) -> dict[str, list[str]]:
    return {
        "L0 Schema Gate": ["schema_gate"],
        "L1 Event Ledger Gate": ["event_ledger_gate"],
        "L2 Deterministic Replay": ["deterministic_replay"],
        "L3 Cross-Entity Rules": [
            "entity_uniqueness",
            "timeline_consistency",
            "location_continuity",
            "ownership_chain",
            "relationship_mutex",
        ],
        "L4 Profile Rules": ["profile_event_type_guard", *profile_rules],
        "L5 Semantic Checks": ["semantic_placeholder"],
        "L6 Governance": ["governance_placeholder"],
    }


def _checker_config(*profile_rules: str) -> dict[str, Any]:
    return {
        "pack_version": "world.contract.v1",
        "layers": _checker_layers(*profile_rules),
    }


def _core_event_schemas() -> dict[str, dict[str, list[str]]]:
    return {
        "entity_introduced": {"required_payload_fields": ["entity_ref", "entity_type", "attributes"]},
        "attribute_mutated": {"required_payload_fields": ["entity_ref", "attribute", "value"]},
        "relation_mutated": {
            "required_payload_fields": [
                "relation_id",
                "source_entity_ref",
                "target_entity_ref",
                "relation_type",
                "status",
            ]
        },
        "presence_shifted": {"required_payload_fields": ["entity_ref", "location_ref", "presence_status"]},
        "event_occurred": {"required_payload_fields": ["event_ref"]},
        "event_linked": {"required_payload_fields": ["source_event_ref", "target_event_ref", "link_type"]},
        "retcon_applied": {"required_payload_fields": ["replacement_event_type"]},
        "fact_reviewed": {"required_payload_fields": ["claim_id", "review_status"]},
    }


@dataclass(frozen=True)
class OfficialGenreProfileDefinition:
    canonical_id: str
    display_name: str
    contract_version: str
    primary_alias: str = ""
    field_authority: dict[str, Any] = field(default_factory=dict)
    schema_payload: dict[str, Any] = field(default_factory=dict)
    module_payload: dict[str, Any] = field(default_factory=dict)
    event_types: tuple[str, ...] = field(default_factory=tuple)
    checker_config: dict[str, Any] = field(default_factory=dict)

    def to_model_kwargs(self) -> dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "display_name": self.display_name,
            "contract_version": self.contract_version,
            "primary_alias": self.primary_alias,
            "field_authority": deepcopy(self.field_authority),
            "schema_payload": deepcopy(self.schema_payload),
            "module_payload": deepcopy(self.module_payload),
            "event_types": list(self.event_types),
            "checker_config": deepcopy(self.checker_config),
        }


_GENERIC_SCHEMA = {
    "field_groups": [
        {
            "group_id": "core_entities",
            "label": "核心实体",
            "fields": [
                "world_character",
                "world_location",
                "world_faction",
                "world_artifact",
                "world_rule",
                "world_resource",
            ],
        },
        {
            "group_id": "continuity",
            "label": "连续性",
            "fields": ["timeline_anchor_id", "participant_refs", "location_refs", "evidence_refs"],
        },
    ],
    "event_schemas": _core_event_schemas(),
}

_SCI_FI_SCHEMA = deepcopy(_GENERIC_SCHEMA)
_SCI_FI_SCHEMA["field_groups"].append(
    {
        "group_id": "technology_and_logistics",
        "label": "技术与补给",
        "fields": ["technology_domain", "supply_source_ref", "distance_au", "declared_delay_hours"],
    }
)
_SCI_FI_SCHEMA["event_schemas"].update(
    {
        "technology_activated": {
            "required_payload_fields": ["technology_domain", "technology_ref", "activation_result"]
        },
        "resource_consumed": {"required_payload_fields": ["resource_ref", "amount"]},
        "communication_sent": {
            "required_payload_fields": [
                "sender_ref",
                "receiver_ref",
                "distance_au",
                "channel_speed_au_per_hour",
                "declared_delay_hours",
            ]
        },
        "access_attempted": {"required_payload_fields": ["subject_ref", "security_level"]},
    }
)

_MYSTERY_SCHEMA = deepcopy(_GENERIC_SCHEMA)
_MYSTERY_SCHEMA["field_groups"].append(
    {
        "group_id": "mystery_investigation",
        "label": "证据与叙述",
        "fields": ["evidence_id", "holder_ref", "related_claim_refs", "window_start", "window_end"],
    }
)
_MYSTERY_SCHEMA["event_schemas"].update(
    {
        "evidence_discovered": {"required_payload_fields": ["evidence_id", "discoverer_ref"]},
        "alibi_declared": {"required_payload_fields": ["subject_ref", "window_start", "window_end"]},
        "clue_interpreted": {"required_payload_fields": ["evidence_id", "claim_ref"]},
        "narration_reported": {"required_payload_fields": ["narrator_ref", "reliability_level"]},
    }
)


OFFICIAL_GENRE_PROFILES = (
    OfficialGenreProfileDefinition(
        canonical_id="generic",
        display_name="通用",
        primary_alias="基础题材",
        contract_version="world.contract.v1",
        field_authority={"field_groups": "authoritative_structured"},
        schema_payload=_GENERIC_SCHEMA,
        module_payload={
            "subgenre_modules": ["adventure", "drama", "ensemble"],
            "entity_expansion_policy": "cannot_add_new_core_entity_classes",
        },
        event_types=CORE_WORLD_EVENT_TYPES,
        checker_config=_checker_config(),
    ),
    OfficialGenreProfileDefinition(
        canonical_id="sci_fi",
        display_name="科幻",
        primary_alias="科学幻想",
        contract_version="world.contract.v1",
        field_authority={"field_groups": "authoritative_structured"},
        schema_payload=_SCI_FI_SCHEMA,
        module_payload={
            "subgenre_modules": ["hard_sf", "space_opera", "cyberpunk"],
            "technology_domains": ["propulsion", "communication", "identity", "energy"],
            "entity_expansion_policy": "cannot_add_new_core_entity_classes",
        },
        event_types=CORE_WORLD_EVENT_TYPES
        + (
            "technology_activated",
            "resource_consumed",
            "communication_sent",
            "access_attempted",
        ),
        checker_config=_checker_config(
            "technology_boundary",
            "energy_supply_closure",
            "communication_delay",
            "auth_bypassability",
        ),
    ),
    OfficialGenreProfileDefinition(
        canonical_id="mystery",
        display_name="悬疑",
        primary_alias="推理悬疑",
        contract_version="world.contract.v1",
        field_authority={"field_groups": "authoritative_structured"},
        schema_payload=_MYSTERY_SCHEMA,
        module_payload={
            "subgenre_modules": ["whodunit", "noir", "closed_circle"],
            "evidence_layers": ["physical", "testimonial", "narration"],
            "entity_expansion_policy": "cannot_add_new_core_entity_classes",
        },
        event_types=CORE_WORLD_EVENT_TYPES
        + (
            "evidence_discovered",
            "alibi_declared",
            "clue_interpreted",
            "narration_reported",
        ),
        checker_config=_checker_config(
            "evidence_chain_closure",
            "mystery_time_window",
            "knowledge_layer_conflict",
            "narration_reliability",
        ),
    ),
)

OFFICIAL_GENRE_PROFILE_BY_ID = {
    profile.canonical_id: profile for profile in OFFICIAL_GENRE_PROFILES
}


def iter_official_genre_profile_definitions() -> tuple[OfficialGenreProfileDefinition, ...]:
    return OFFICIAL_GENRE_PROFILES


def get_official_genre_profile_definition(canonical_id: str) -> OfficialGenreProfileDefinition:
    try:
        return OFFICIAL_GENRE_PROFILE_BY_ID[canonical_id]
    except KeyError as exc:
        raise KeyError(f"unknown official genre profile: {canonical_id}") from exc

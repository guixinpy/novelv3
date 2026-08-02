from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import Any

from sqlalchemy.orm import Session

from app.core.world_projection import FactRecord
from app.core.world_replay import (
    BrokenSupersedesChainError,
    DuplicateEventError,
    LedgerEvent,
    ReplayState,
    WorldReplayError,
    replay_events,
)
from app.models import GenreProfile, ProjectProfileVersion
from app.models.genre_profile import (
    CORE_WORLD_EVENT_TYPES,
    OfficialGenreProfileDefinition,
    get_official_genre_profile_definition,
    iter_official_genre_profile_definitions,
)

LAYER_ORDER = (
    "L0 Schema Gate",
    "L1 Event Ledger Gate",
    "L2 Deterministic Replay",
    "L3 Cross-Entity Rules",
    "L4 Profile Rules",
    "L5 Semantic Checks",
    "L6 Governance",
)

REQUIRED_CHECKER_LAYERS = (
    "L0 Schema Gate",
    "L1 Event Ledger Gate",
    "L2 Deterministic Replay",
    "L3 Cross-Entity Rules",
    "L4 Profile Rules",
)


@dataclass(frozen=True)
class GenreProfileSpec:
    canonical_id: str
    display_name: str
    contract_version: str
    primary_alias: str = ""
    field_authority: dict[str, Any] = field(default_factory=dict)
    schema_payload: dict[str, Any] = field(default_factory=dict)
    module_payload: dict[str, Any] = field(default_factory=dict)
    event_types: tuple[str, ...] = field(default_factory=tuple)
    checker_config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    evidence_type: str
    source_scope: str
    authenticity_status: str = ""
    reliability_level: str = ""
    holder_ref: str = ""
    disclosure_layer: str = ""
    related_claim_refs: tuple[str, ...] = field(default_factory=tuple)
    related_event_refs: tuple[str, ...] = field(default_factory=tuple)
    timeline_anchor_id: str | None = None
    content_excerpt_or_summary: str = ""


@dataclass(frozen=True)
class NormalizedWorldEvent:
    ledger_event: LedgerEvent
    precondition_event_refs: tuple[str, ...] = field(default_factory=tuple)
    participant_refs: tuple[str, ...] = field(default_factory=tuple)
    location_refs: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CheckerIssue:
    layer: str
    checker_name: str
    code: str
    message: str
    severity: str = "error"
    refs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CheckerPack:
    profile: GenreProfileSpec
    layer_map: dict[str, tuple[str, ...]]
    checker_config_fingerprint: str


@dataclass
class CheckerRunResult:
    profile: GenreProfileSpec
    layer_trace: list[str] = field(default_factory=list)
    checker_trace: list[str] = field(default_factory=list)
    issues: list[CheckerIssue] = field(default_factory=list)


@dataclass
class CheckerContext:
    profile: GenreProfileSpec
    events: list[NormalizedWorldEvent]
    facts: list[FactRecord]
    evidence: list[EvidenceRecord]
    replay_state: ReplayState | None = None


class CheckerPackConfigurationError(ValueError):
    pass


class CheckerPackContractMismatchError(ValueError):
    pass


def get_official_genre_profile(canonical_id: str) -> GenreProfileSpec:
    return _profile_spec_from_definition(get_official_genre_profile_definition(canonical_id))


def load_official_genre_profiles(db: Session) -> list[GenreProfile]:
    definitions = iter_official_genre_profile_definitions()
    existing = {
        profile.canonical_id: profile
        for profile in db.query(GenreProfile)
        .filter(GenreProfile.canonical_id.in_([definition.canonical_id for definition in definitions]))
        .all()
    }
    loaded: list[GenreProfile] = []
    has_changes = False

    for definition in definitions:
        payload = definition.to_model_kwargs()
        profile = existing.get(definition.canonical_id)
        if profile is None:
            profile = GenreProfile(**payload)
            db.add(profile)
            existing[definition.canonical_id] = profile
            has_changes = True
        else:
            for field_name, value in payload.items():
                if getattr(profile, field_name) != value:
                    setattr(profile, field_name, value)
                    has_changes = True
        loaded.append(profile)

    if has_changes:
        db.commit()
    else:
        db.flush()

    for profile in loaded:
        db.refresh(profile)
    return loaded


def get_checker_pack_for_genre_profile(profile: GenreProfile | GenreProfileSpec | OfficialGenreProfileDefinition) -> CheckerPack:
    return WorldCheckerRegistry().build_pack(profile)


def get_checker_pack_for_project_profile(
    *,
    db: Session,
    project_profile_version_id: str | None = None,
    project_id: str | None = None,
    profile_version: int | None = None,
) -> CheckerPack:
    project_profile = _resolve_project_profile_version(
        db=db,
        project_profile_version_id=project_profile_version_id,
        project_id=project_id,
        profile_version=profile_version,
    )
    genre_profile = _get_genre_profile_or_error(
        db=db,
        genre_profile_id=project_profile.genre_profile_id,
        not_found_message=(
            f"project profile version {project_profile.id} references missing genre profile "
            f"{project_profile.genre_profile_id}"
        ),
    )
    pack = get_checker_pack_for_genre_profile(genre_profile)
    _validate_project_profile_pack_contract(
        project_profile=project_profile,
        profile=pack.profile,
        pack=pack,
    )
    return pack


def run_checks_for_project_profile(
    *,
    db: Session,
    project_profile_version_id: str | None = None,
    project_id: str | None = None,
    profile_version: int | None = None,
    events: Iterable[Any] = (),
    facts: Iterable[Any] = (),
    evidence: Iterable[Any] = (),
) -> CheckerRunResult:
    pack = get_checker_pack_for_project_profile(
        db=db,
        project_profile_version_id=project_profile_version_id,
        project_id=project_id,
        profile_version=profile_version,
    )
    return WorldCheckerRegistry().run(
        profile=pack.profile,
        events=events,
        facts=facts,
        evidence=evidence,
    )


class WorldCheckerRegistry:
    def __init__(self) -> None:
        self._handlers = {
            "schema_gate": self._schema_gate,
            "event_ledger_gate": self._event_ledger_gate,
            "deterministic_replay": self._deterministic_replay,
            "entity_uniqueness": self._entity_uniqueness,
            "timeline_consistency": self._timeline_consistency,
            "location_continuity": self._location_continuity,
            "ownership_chain": self._ownership_chain,
            "relationship_mutex": self._relationship_mutex,
            "profile_event_type_guard": self._profile_event_type_guard,
            "technology_boundary": self._technology_boundary,
            "energy_supply_closure": self._energy_supply_closure,
            "communication_delay": self._communication_delay,
            "auth_bypassability": self._auth_bypassability,
            "evidence_chain_closure": self._evidence_chain_closure,
            "mystery_time_window": self._mystery_time_window,
            "knowledge_layer_conflict": self._knowledge_layer_conflict,
            "narration_reliability": self._narration_reliability,
            "semantic_placeholder": self._semantic_placeholder,
            "governance_placeholder": self._governance_placeholder,
        }

    def build_pack(
        self,
        profile: GenreProfile | GenreProfileSpec | OfficialGenreProfileDefinition,
    ) -> CheckerPack:
        profile_spec = _normalize_profile(profile)
        checker_config = _validate_checker_config(profile_spec)
        profile_spec = replace(profile_spec, checker_config=checker_config)
        layers = checker_config.get("layers", {})
        unknown_layers = [layer_name for layer_name in layers if layer_name not in LAYER_ORDER]
        if unknown_layers:
            raise CheckerPackConfigurationError(
                f"unknown checker layer for {profile_spec.canonical_id}: {', '.join(sorted(unknown_layers))}"
            )
        layer_map: dict[str, tuple[str, ...]] = {}
        for layer_name in LAYER_ORDER:
            checker_names = _normalize_checker_name_sequence(
                layers.get(layer_name, ()),
                profile_id=profile_spec.canonical_id,
                layer_name=layer_name,
            )
            for checker_name in checker_names:
                if checker_name not in self._handlers:
                    raise CheckerPackConfigurationError(
                        f"unknown checker configured for {profile_spec.canonical_id}: {checker_name}"
                    )
            layer_map[layer_name] = checker_names
        missing_required_layers = [
            layer_name for layer_name in REQUIRED_CHECKER_LAYERS if not layer_map.get(layer_name)
        ]
        if missing_required_layers:
            raise CheckerPackConfigurationError(
                f"required checker layers for {profile_spec.canonical_id} must exist and be non-empty: "
                f"{', '.join(missing_required_layers)}"
            )
        return CheckerPack(
            profile=profile_spec,
            layer_map=layer_map,
            checker_config_fingerprint=_checker_config_fingerprint(checker_config),
        )

    def run(
        self,
        *,
        profile: GenreProfile | GenreProfileSpec | OfficialGenreProfileDefinition,
        events: Iterable[Any] = (),
        facts: Iterable[Any] = (),
        evidence: Iterable[Any] = (),
    ) -> CheckerRunResult:
        pack = self.build_pack(profile)
        context = CheckerContext(
            profile=pack.profile,
            events=[_normalize_event(item) for item in events],
            facts=[_normalize_fact(item) for item in facts],
            evidence=[_normalize_evidence(item) for item in evidence],
        )
        result = CheckerRunResult(profile=pack.profile)

        for layer_name in LAYER_ORDER:
            result.layer_trace.append(layer_name)
            layer_issue_count_before = len(result.issues)
            for checker_name in pack.layer_map[layer_name]:
                result.checker_trace.append(checker_name)
                result.issues.extend(self._handlers[checker_name](context))
            if layer_name in {
                "L0 Schema Gate",
                "L1 Event Ledger Gate",
                "L2 Deterministic Replay",
            } and len(result.issues) > layer_issue_count_before:
                break

        return result

    def _schema_gate(self, context: CheckerContext) -> list[CheckerIssue]:
        issues: list[CheckerIssue] = []
        event_schemas = context.profile.schema_payload.get("event_schemas", {})
        for event in _sorted_events(context.events):
            if not event.ledger_event.event_id:
                issues.append(
                    _issue(
                        layer="L0 Schema Gate",
                        checker_name="schema_gate",
                        code="missing_event_id",
                        message="事件缺少 event_id",
                    )
                )
            if not event.ledger_event.event_type:
                issues.append(
                    _issue(
                        layer="L0 Schema Gate",
                        checker_name="schema_gate",
                        code="missing_event_type",
                        message=f"事件 {event.ledger_event.event_id or '<missing>'} 缺少 event_type",
                    )
                )
                continue
            schema = event_schemas.get(event.ledger_event.event_type)
            if not schema:
                continue
            required_fields = schema.get("required_payload_fields", [])
            missing_fields = [
                field_name
                for field_name in required_fields
                if field_name not in event.ledger_event.payload
            ]
            if missing_fields:
                issues.append(
                    _issue(
                        layer="L0 Schema Gate",
                        checker_name="schema_gate",
                        code="missing_payload_fields",
                        message=(
                            f"事件 {event.ledger_event.event_id} 缺少字段: "
                            f"{', '.join(missing_fields)}"
                        ),
                        event_id=event.ledger_event.event_id,
                        event_type=event.ledger_event.event_type,
                    )
                )
        for fact in context.facts:
            if fact.claim_id:
                continue
            issues.append(
                _issue(
                    layer="L0 Schema Gate",
                    checker_name="schema_gate",
                    code="missing_claim_id",
                    message=f"事实 {fact.subject_ref or '<missing>'}.{fact.predicate or '<missing>'} 缺少 claim_id",
                    subject_ref=fact.subject_ref,
                    predicate=fact.predicate,
                )
            )
        return issues

    def _event_ledger_gate(self, context: CheckerContext) -> list[CheckerIssue]:
        issues: list[CheckerIssue] = []
        seen_event_ids: dict[str, str] = {}
        seen_idempotency_keys: dict[str, str] = {}

        for event in _sorted_events(context.events):
            event_id = event.ledger_event.event_id
            if event_id in seen_event_ids:
                issues.append(
                    _issue(
                        layer="L1 Event Ledger Gate",
                        checker_name="event_ledger_gate",
                        code="duplicate_event_id",
                        message=f"重复事件 ID: {event_id}",
                        event_id=event_id,
                    )
                )
            seen_event_ids[event_id] = event_id

            idempotency_key = event.ledger_event.idempotency_key
            if not idempotency_key:
                continue
            previous = seen_idempotency_keys.get(idempotency_key)
            if previous is not None:
                issues.append(
                    _issue(
                        layer="L1 Event Ledger Gate",
                        checker_name="event_ledger_gate",
                        code="duplicate_idempotency_key",
                        message=(
                            f"幂等键 {idempotency_key} 被事件 {previous} 和 "
                            f"{event_id} 重复使用"
                        ),
                        event_id=event_id,
                        idempotency_key=idempotency_key,
                    )
                )
            seen_idempotency_keys[idempotency_key] = event_id

        return issues

    def _deterministic_replay(self, context: CheckerContext) -> list[CheckerIssue]:
        replayable_events = [
            event.ledger_event
            for event in _sorted_events(context.events)
            if event.ledger_event.event_type in CORE_WORLD_EVENT_TYPES
        ]
        if not replayable_events:
            context.replay_state = ReplayState(ledger={}, active_event_ids=[], inactive_event_ids=[])
            return []
        try:
            context.replay_state = replay_events(replayable_events)
        except (BrokenSupersedesChainError, DuplicateEventError, WorldReplayError) as exc:
            return [
                _issue(
                    layer="L2 Deterministic Replay",
                    checker_name="deterministic_replay",
                    code="deterministic_replay_failure",
                    message=str(exc),
                )
            ]
        return []

    def _entity_uniqueness(self, context: CheckerContext) -> list[CheckerIssue]:
        issues: list[CheckerIssue] = []
        seen_entities: dict[str, str] = {}
        seen_canonical_ids: dict[str, str] = {}

        for event in _sorted_events(context.events):
            if event.ledger_event.event_type != "entity_introduced":
                continue
            payload = event.ledger_event.payload
            entity_ref = str(payload.get("entity_ref", "")).strip()
            canonical_id = str(
                payload.get("canonical_id")
                or payload.get("attributes", {}).get("canonical_id")
                or entity_ref
            ).strip()

            previous_entity_event = seen_entities.get(entity_ref)
            if previous_entity_event is not None:
                issues.append(
                    _issue(
                        layer="L3 Cross-Entity Rules",
                        checker_name="entity_uniqueness",
                        code="entity_uniqueness",
                        message=f"实体 {entity_ref} 被重复引入",
                        event_id=event.ledger_event.event_id,
                        previous_event_id=previous_entity_event,
                        entity_ref=entity_ref,
                    )
                )
            seen_entities[entity_ref] = event.ledger_event.event_id

            previous_canonical_event = seen_canonical_ids.get(canonical_id)
            if previous_canonical_event is not None and previous_canonical_event != event.ledger_event.event_id:
                issues.append(
                    _issue(
                        layer="L3 Cross-Entity Rules",
                        checker_name="entity_uniqueness",
                        code="entity_uniqueness",
                        message=f"canonical_id {canonical_id} 被多个实体重复声明",
                        event_id=event.ledger_event.event_id,
                        previous_event_id=previous_canonical_event,
                        canonical_id=canonical_id,
                    )
                )
            seen_canonical_ids[canonical_id] = event.ledger_event.event_id

        return issues

    def _timeline_consistency(self, context: CheckerContext) -> list[CheckerIssue]:
        issues: list[CheckerIssue] = []
        ordered_events = _sorted_events(context.events)
        order_index = {
            event.ledger_event.event_id: index for index, event in enumerate(ordered_events)
        }

        for event in ordered_events:
            for dependency in event.precondition_event_refs:
                if dependency not in order_index:
                    issues.append(
                        _issue(
                            layer="L3 Cross-Entity Rules",
                            checker_name="timeline_consistency",
                            code="timeline_consistency",
                            message=f"事件 {event.ledger_event.event_id} 依赖缺失事件 {dependency}",
                            event_id=event.ledger_event.event_id,
                            dependency_event_id=dependency,
                        )
                    )
                    continue
                if order_index[dependency] > order_index[event.ledger_event.event_id]:
                    issues.append(
                        _issue(
                            layer="L3 Cross-Entity Rules",
                            checker_name="timeline_consistency",
                            code="timeline_consistency",
                            message=(
                                f"事件 {event.ledger_event.event_id} 的前置事件 {dependency} "
                                "出现在更晚的位置"
                            ),
                            event_id=event.ledger_event.event_id,
                            dependency_event_id=dependency,
                        )
                    )

        return issues

    def _location_continuity(self, context: CheckerContext) -> list[CheckerIssue]:
        issues: list[CheckerIssue] = []
        last_location_by_entity: dict[str, str] = {}

        for event in _sorted_events(context.events):
            if event.ledger_event.event_type != "presence_shifted":
                continue
            payload = event.ledger_event.payload
            entity_ref = str(payload.get("entity_ref", "")).strip()
            location_ref = str(payload.get("location_ref", "")).strip()
            if not entity_ref or not location_ref:
                continue
            previous_location = last_location_by_entity.get(entity_ref)
            from_location_ref = str(payload.get("from_location_ref", "")).strip()
            if (
                previous_location
                and previous_location != location_ref
                and from_location_ref != previous_location
            ):
                issues.append(
                    _issue(
                        layer="L3 Cross-Entity Rules",
                        checker_name="location_continuity",
                        code="location_continuity",
                        message=(
                            f"实体 {entity_ref} 从 {previous_location} 切到 {location_ref} "
                            "时缺少连续位置链"
                        ),
                        event_id=event.ledger_event.event_id,
                        entity_ref=entity_ref,
                    )
                )
            last_location_by_entity[entity_ref] = location_ref

        return issues

    def _ownership_chain(self, context: CheckerContext) -> list[CheckerIssue]:
        issues: list[CheckerIssue] = []
        current_owner_by_subject: dict[str, str] = {}

        for event in _sorted_events(context.events):
            if event.ledger_event.event_type != "relation_mutated":
                continue
            payload = event.ledger_event.payload
            if payload.get("relation_type") != "owned_by" or payload.get("status") != "active":
                continue
            subject_ref = str(payload.get("source_entity_ref", "")).strip()
            owner_ref = str(payload.get("target_entity_ref", "")).strip()
            previous_owner = current_owner_by_subject.get(subject_ref)
            if previous_owner and payload.get("previous_owner_ref") != previous_owner:
                issues.append(
                    _issue(
                        layer="L3 Cross-Entity Rules",
                        checker_name="ownership_chain",
                        code="ownership_chain",
                        message=(
                            f"实体 {subject_ref} 的所有权从 {previous_owner} 变更到 "
                            f"{owner_ref} 时缺少正确前置 owner"
                        ),
                        event_id=event.ledger_event.event_id,
                        entity_ref=subject_ref,
                    )
                )
            if subject_ref and owner_ref:
                current_owner_by_subject[subject_ref] = owner_ref

        return issues

    def _relationship_mutex(self, context: CheckerContext) -> list[CheckerIssue]:
        issues: list[CheckerIssue] = []
        active_relation_ids_by_pair: dict[tuple[str, str], dict[str, set[str]]] = {}
        exclusive_types = {"ally", "enemy", "romantic"}
        inactive_statuses = {"inactive", "ended", "revoked", "removed"}

        for event in _sorted_events(context.events):
            if event.ledger_event.event_type != "relation_mutated":
                continue
            payload = event.ledger_event.payload
            relation_id = str(payload.get("relation_id", "")).strip()
            relation_type = str(payload.get("relation_type", "")).strip()
            pair = tuple(
                sorted(
                    [
                        str(payload.get("source_entity_ref", "")).strip(),
                        str(payload.get("target_entity_ref", "")).strip(),
                    ]
                )
            )
            status = str(payload.get("status", "")).strip().lower()
            if not pair[0] or not pair[1] or not relation_id:
                continue
            if relation_type in exclusive_types and status in inactive_statuses:
                active_types = active_relation_ids_by_pair.get(pair)
                if active_types is not None:
                    relation_ids = active_types.get(relation_type)
                    if relation_ids is not None:
                        relation_ids.discard(relation_id)
                        if not relation_ids:
                            active_types.pop(relation_type, None)
                    if not active_types:
                        active_relation_ids_by_pair.pop(pair, None)
                continue
            if relation_type not in exclusive_types or status != "active":
                continue
            active_types = active_relation_ids_by_pair.setdefault(pair, {})
            conflicting_types = sorted(
                type_name
                for type_name, relation_ids in active_types.items()
                if type_name != relation_type and relation_ids
            )
            if conflicting_types:
                issues.append(
                    _issue(
                        layer="L3 Cross-Entity Rules",
                        checker_name="relationship_mutex",
                        code="relationship_mutex",
                        message=f"关系对 {pair} 同时声明了 {conflicting_types[0]} 与 {relation_type}",
                        event_id=event.ledger_event.event_id,
                    )
                )
            active_types.setdefault(relation_type, set()).add(relation_id)

        return issues

    def _profile_event_type_guard(self, context: CheckerContext) -> list[CheckerIssue]:
        allowed_event_types = set(context.profile.event_types)
        return [
            _issue(
                layer="L4 Profile Rules",
                checker_name="profile_event_type_guard",
                code="unsupported_event_type",
                message=(
                    f"事件 {event.ledger_event.event_id} 的类型 "
                    f"{event.ledger_event.event_type} 不属于题材档案 {context.profile.canonical_id}"
                ),
                event_id=event.ledger_event.event_id,
                event_type=event.ledger_event.event_type,
                profile_id=context.profile.canonical_id,
            )
            for event in _sorted_events(context.events)
            if event.ledger_event.event_type not in allowed_event_types
        ]

    def _technology_boundary(self, context: CheckerContext) -> list[CheckerIssue]:
        allowed_domains = set(context.profile.module_payload.get("technology_domains", []))
        if not allowed_domains:
            return []
        issues: list[CheckerIssue] = []
        for event in _sorted_events(context.events):
            technology_domain = event.ledger_event.payload.get("technology_domain")
            if technology_domain and technology_domain not in allowed_domains:
                issues.append(
                    _issue(
                        layer="L4 Profile Rules",
                        checker_name="technology_boundary",
                        code="technology_boundary",
                        message=f"技术域 {technology_domain} 超出题材档案允许范围",
                        event_id=event.ledger_event.event_id,
                        technology_domain=technology_domain,
                    )
                )
        return issues

    def _energy_supply_closure(self, context: CheckerContext) -> list[CheckerIssue]:
        issues: list[CheckerIssue] = []
        for event in _sorted_events(context.events):
            if event.ledger_event.event_type != "resource_consumed":
                continue
            payload = event.ledger_event.payload
            if payload.get("amount", 0) and not payload.get("supply_source_ref") and not payload.get("loop_closed"):
                issues.append(
                    _issue(
                        layer="L4 Profile Rules",
                        checker_name="energy_supply_closure",
                        code="energy_supply_closure",
                        message=f"事件 {event.ledger_event.event_id} 缺少能源/补给闭环来源",
                        event_id=event.ledger_event.event_id,
                    )
                )
        return issues

    def _communication_delay(self, context: CheckerContext) -> list[CheckerIssue]:
        issues: list[CheckerIssue] = []
        for event in _sorted_events(context.events):
            if event.ledger_event.event_type != "communication_sent":
                continue
            payload = event.ledger_event.payload
            distance = _coerce_float(payload.get("distance_au"))
            speed = _coerce_float(payload.get("channel_speed_au_per_hour"))
            declared_delay = _coerce_float(payload.get("declared_delay_hours"))
            if distance is None or speed is None or declared_delay is None:
                issues.append(
                    _issue(
                        layer="L4 Profile Rules",
                        checker_name="communication_delay",
                        code="invalid_numeric_payload",
                        message=f"事件 {event.ledger_event.event_id} 的通信延迟字段不是有效数值",
                        event_id=event.ledger_event.event_id,
                    )
                )
                continue
            minimum_delay = distance / speed if speed > 0 else float("inf")
            if declared_delay + 1e-9 < minimum_delay:
                issues.append(
                    _issue(
                        layer="L4 Profile Rules",
                        checker_name="communication_delay",
                        code="communication_delay",
                        message=(
                            f"事件 {event.ledger_event.event_id} 声明通信延迟 {declared_delay}h，"
                            f"但按距离/信道速度至少需要 {minimum_delay:.2f}h"
                        ),
                        event_id=event.ledger_event.event_id,
                        declared_delay_hours=declared_delay,
                        minimum_delay_hours=round(minimum_delay, 4),
                    )
                )
        return issues

    def _auth_bypassability(self, context: CheckerContext) -> list[CheckerIssue]:
        issues: list[CheckerIssue] = []
        for event in _sorted_events(context.events):
            if event.ledger_event.event_type != "access_attempted":
                continue
            payload = event.ledger_event.payload
            security_level = str(payload.get("security_level", "")).lower()
            if security_level in {"high", "critical"} and payload.get("bypass_vector") and not payload.get("mitigations"):
                issues.append(
                    _issue(
                        layer="L4 Profile Rules",
                        checker_name="auth_bypassability",
                        code="auth_bypassability",
                        message=f"事件 {event.ledger_event.event_id} 暴露可绕过的高等级认证",
                        event_id=event.ledger_event.event_id,
                    )
                )
        return issues

    def _evidence_chain_closure(self, context: CheckerContext) -> list[CheckerIssue]:
        issues: list[CheckerIssue] = []
        for evidence in context.evidence:
            if evidence.authenticity_status != "verified":
                continue
            if evidence.holder_ref and (evidence.related_claim_refs or evidence.related_event_refs):
                continue
            issues.append(
                _issue(
                    layer="L4 Profile Rules",
                    checker_name="evidence_chain_closure",
                    code="evidence_chain_closure",
                    message=f"证据 {evidence.evidence_id} 缺少完整持有/关联链",
                    evidence_id=evidence.evidence_id,
                )
            )
        return issues

    def _mystery_time_window(self, context: CheckerContext) -> list[CheckerIssue]:
        issues: list[CheckerIssue] = []
        for event in _sorted_events(context.events):
            if event.ledger_event.event_type != "alibi_declared":
                continue
            payload = event.ledger_event.payload
            window_start = payload.get("window_start")
            window_end = payload.get("window_end")
            observed_at = payload.get("observed_at")
            if window_start is None or window_end is None:
                continue
            if any(not _is_strict_real_number(value) for value in [window_start, window_end] if value is not None):
                issues.append(
                    _issue(
                        layer="L4 Profile Rules",
                        checker_name="mystery_time_window",
                        code="invalid_time_window_type",
                        message=f"事件 {event.ledger_event.event_id} 的时间窗口字段类型非法",
                        event_id=event.ledger_event.event_id,
                    )
                )
                continue
            if observed_at is not None and not _is_strict_real_number(observed_at):
                issues.append(
                    _issue(
                        layer="L4 Profile Rules",
                        checker_name="mystery_time_window",
                        code="invalid_time_window_type",
                        message=f"事件 {event.ledger_event.event_id} 的 observed_at 类型非法",
                        event_id=event.ledger_event.event_id,
                    )
                )
                continue
            if window_start > window_end or (
                observed_at is not None and not (window_start <= observed_at <= window_end)
            ):
                issues.append(
                    _issue(
                        layer="L4 Profile Rules",
                        checker_name="mystery_time_window",
                        code="mystery_time_window",
                        message=f"事件 {event.ledger_event.event_id} 的时间窗口与观察结果冲突",
                        event_id=event.ledger_event.event_id,
                    )
                )
        return issues

    def _knowledge_layer_conflict(self, context: CheckerContext) -> list[CheckerIssue]:
        grouped: dict[tuple[str, str, str], set[str]] = {}
        for fact in context.facts:
            if fact.claim_status != "confirmed" or fact.claim_layer not in {"belief", "disclosure"}:
                continue
            if not fact.perspective_ref:
                continue
            key = (fact.perspective_ref, fact.subject_ref, fact.predicate)
            grouped.setdefault(key, set()).add(str(fact.object_ref_or_value))

        issues: list[CheckerIssue] = []
        for (perspective_ref, subject_ref, predicate), values in grouped.items():
            if len(values) <= 1:
                continue
            issues.append(
                _issue(
                    layer="L4 Profile Rules",
                    checker_name="knowledge_layer_conflict",
                    code="knowledge_layer_conflict",
                    message=(
                        f"{perspective_ref} 对 {subject_ref}.{predicate} 同时持有冲突认知: "
                        f"{', '.join(sorted(values))}"
                    ),
                    perspective_ref=perspective_ref,
                    subject_ref=subject_ref,
                    predicate=predicate,
                )
            )
        return issues

    def _narration_reliability(self, context: CheckerContext) -> list[CheckerIssue]:
        issues: list[CheckerIssue] = []
        for evidence in context.evidence:
            if evidence.evidence_type != "narration" and evidence.source_scope != "narration":
                continue
            if evidence.reliability_level not in {"low", "unreliable"}:
                continue
            issues.append(
                _issue(
                    layer="L4 Profile Rules",
                    checker_name="narration_reliability",
                    code="narration_reliability",
                    message=f"叙述证据 {evidence.evidence_id} 的可靠性不足",
                    evidence_id=evidence.evidence_id,
                )
            )
        return issues

    def _semantic_placeholder(self, context: CheckerContext) -> list[CheckerIssue]:
        return []

    def _governance_placeholder(self, context: CheckerContext) -> list[CheckerIssue]:
        return []


def _resolve_project_profile_version(
    *,
    db: Session,
    project_profile_version_id: str | None,
    project_id: str | None,
    profile_version: int | None,
) -> ProjectProfileVersion:
    if project_profile_version_id:
        project_profile = (
            db.query(ProjectProfileVersion)
            .filter(ProjectProfileVersion.id == project_profile_version_id)
            .one_or_none()
        )
        if project_profile is None:
            raise ValueError(f"project profile version {project_profile_version_id} does not exist")
        return project_profile
    if project_id and profile_version is not None:
        project_profile = (
            db.query(ProjectProfileVersion)
            .filter(
                ProjectProfileVersion.project_id == project_id,
                ProjectProfileVersion.version == profile_version,
            )
            .one_or_none()
        )
        if project_profile is None:
            raise ValueError(
                "project profile version does not exist for "
                f"project_id={project_id}, profile_version={profile_version}"
            )
        return project_profile
    raise ValueError("project_profile_version_id or project_id + profile_version is required")


def _get_genre_profile_or_error(
    *,
    db: Session,
    genre_profile_id: str,
    not_found_message: str | None = None,
) -> GenreProfile:
    genre_profile = db.query(GenreProfile).filter(GenreProfile.id == genre_profile_id).one_or_none()
    if genre_profile is None:
        raise ValueError(not_found_message or f"genre profile {genre_profile_id} does not exist")
    return genre_profile


def _profile_spec_from_definition(definition: OfficialGenreProfileDefinition) -> GenreProfileSpec:
    return GenreProfileSpec(
        canonical_id=definition.canonical_id,
        display_name=definition.display_name,
        contract_version=definition.contract_version,
        primary_alias=definition.primary_alias,
        field_authority=deepcopy(definition.field_authority),
        schema_payload=deepcopy(definition.schema_payload),
        module_payload=deepcopy(definition.module_payload),
        event_types=tuple(definition.event_types),
        checker_config=deepcopy(definition.checker_config),
    )


def _normalize_profile(
    profile: GenreProfile | GenreProfileSpec | OfficialGenreProfileDefinition,
) -> GenreProfileSpec:
    if isinstance(profile, GenreProfileSpec):
        return profile
    if isinstance(profile, OfficialGenreProfileDefinition):
        return _profile_spec_from_definition(profile)
    return GenreProfileSpec(
        canonical_id=profile.canonical_id,
        display_name=profile.display_name,
        contract_version=profile.contract_version,
        primary_alias=profile.primary_alias or "",
        field_authority=deepcopy(profile.field_authority or {}),
        schema_payload=deepcopy(profile.schema_payload or {}),
        module_payload=deepcopy(profile.module_payload or {}),
        event_types=tuple(profile.event_types or ()),
        checker_config=deepcopy(profile.checker_config) if profile.checker_config is not None else {},
    )


def _normalize_event(event: Any) -> NormalizedWorldEvent:
    if isinstance(event, NormalizedWorldEvent):
        return event
    if isinstance(event, LedgerEvent):
        return NormalizedWorldEvent(ledger_event=event)
    if isinstance(event, dict):
        payload = _normalize_mapping(event.get("payload") or event.get("primitive_payload"))
        return NormalizedWorldEvent(
            ledger_event=LedgerEvent(
                event_id=_coerce_identifier(event.get("event_id")),
                event_type=_coerce_identifier(event.get("event_type")),
                chapter_index=_coerce_int(event.get("chapter_index")),
                intra_chapter_seq=_coerce_int(event.get("intra_chapter_seq")),
                payload=payload,
                idempotency_key=_coerce_optional_identifier(event.get("idempotency_key")),
                supersedes_event_ref=_coerce_optional_identifier(event.get("supersedes_event_ref")),
                timeline_anchor_id=_coerce_optional_identifier(event.get("timeline_anchor_id")),
            ),
            precondition_event_refs=_normalize_name_sequence(event.get("precondition_event_refs", ())),
            participant_refs=_normalize_name_sequence(event.get("participant_refs", ())),
            location_refs=_normalize_name_sequence(event.get("location_refs", ())),
        )
    payload = _normalize_mapping(getattr(event, "primitive_payload", None) or getattr(event, "payload", None))
    return NormalizedWorldEvent(
        ledger_event=LedgerEvent(
            event_id=_coerce_identifier(getattr(event, "event_id", "")),
            event_type=_coerce_identifier(getattr(event, "event_type", "")),
            chapter_index=_coerce_int(getattr(event, "chapter_index", 0)),
            intra_chapter_seq=_coerce_int(getattr(event, "intra_chapter_seq", 0)),
            payload=payload,
            idempotency_key=_coerce_optional_identifier(getattr(event, "idempotency_key", None)),
            supersedes_event_ref=_coerce_optional_identifier(getattr(event, "supersedes_event_ref", None)),
            timeline_anchor_id=_coerce_optional_identifier(getattr(event, "timeline_anchor_id", None)),
        ),
        precondition_event_refs=_normalize_name_sequence(getattr(event, "precondition_event_refs", ()) or ()),
        participant_refs=_normalize_name_sequence(getattr(event, "participant_refs", ()) or ()),
        location_refs=_normalize_name_sequence(getattr(event, "location_refs", ()) or ()),
    )


def _normalize_fact(fact: Any) -> FactRecord:
    if isinstance(fact, FactRecord):
        return fact
    if isinstance(fact, dict):
        return FactRecord(
            claim_id=_coerce_identifier(fact.get("claim_id")),
            subject_ref=_coerce_identifier(fact.get("subject_ref")),
            predicate=_coerce_identifier(fact.get("predicate")),
            object_ref_or_value=fact.get("object_ref_or_value"),
            claim_layer=_coerce_identifier(fact.get("claim_layer")),
            claim_status=_coerce_identifier(fact.get("claim_status")),
            perspective_ref=_coerce_optional_identifier(fact.get("perspective_ref")),
            disclosed_to_refs=_normalize_name_sequence(fact.get("disclosed_to_refs", ())),
            chapter_index=_coerce_optional_int(fact.get("chapter_index")),
            intra_chapter_seq=_coerce_int(fact.get("intra_chapter_seq")),
            valid_from_anchor_id=_coerce_optional_identifier(fact.get("valid_from_anchor_id")),
            valid_to_anchor_id=_coerce_optional_identifier(fact.get("valid_to_anchor_id")),
        )
    return FactRecord(
        claim_id=_coerce_identifier(getattr(fact, "claim_id", "")),
        subject_ref=_coerce_identifier(getattr(fact, "subject_ref", "")),
        predicate=_coerce_identifier(getattr(fact, "predicate", "")),
        object_ref_or_value=getattr(fact, "object_ref_or_value", None),
        claim_layer=_coerce_identifier(getattr(fact, "claim_layer", "")),
        claim_status=_coerce_identifier(getattr(fact, "claim_status", "")),
        perspective_ref=_coerce_optional_identifier(getattr(fact, "perspective_ref", None)),
        disclosed_to_refs=_normalize_name_sequence(getattr(fact, "disclosed_to_refs", ()) or ()),
        chapter_index=_coerce_optional_int(getattr(fact, "chapter_index", None)),
        intra_chapter_seq=_coerce_int(getattr(fact, "intra_chapter_seq", 0)),
        valid_from_anchor_id=_coerce_optional_identifier(getattr(fact, "valid_from_anchor_id", None)),
        valid_to_anchor_id=_coerce_optional_identifier(getattr(fact, "valid_to_anchor_id", None)),
    )


def _normalize_evidence(evidence: Any) -> EvidenceRecord:
    if isinstance(evidence, EvidenceRecord):
        return evidence
    if isinstance(evidence, dict):
        return EvidenceRecord(
            evidence_id=_coerce_identifier(evidence.get("evidence_id")),
            evidence_type=_coerce_identifier(evidence.get("evidence_type")),
            source_scope=_coerce_identifier(evidence.get("source_scope")),
            authenticity_status=_coerce_identifier(evidence.get("authenticity_status")),
            reliability_level=_coerce_identifier(evidence.get("reliability_level")),
            holder_ref=_coerce_identifier(evidence.get("holder_ref")),
            disclosure_layer=_coerce_identifier(evidence.get("disclosure_layer")),
            related_claim_refs=_normalize_name_sequence(evidence.get("related_claim_refs", ())),
            related_event_refs=_normalize_name_sequence(evidence.get("related_event_refs", ())),
            timeline_anchor_id=_coerce_optional_identifier(evidence.get("timeline_anchor_id")),
            content_excerpt_or_summary=evidence.get("content_excerpt_or_summary", ""),
        )
    return EvidenceRecord(
        evidence_id=_coerce_identifier(getattr(evidence, "evidence_id", "")),
        evidence_type=_coerce_identifier(getattr(evidence, "evidence_type", "")),
        source_scope=_coerce_identifier(getattr(evidence, "source_scope", "")),
        authenticity_status=_coerce_identifier(getattr(evidence, "authenticity_status", "")),
        reliability_level=_coerce_identifier(getattr(evidence, "reliability_level", "")),
        holder_ref=_coerce_identifier(getattr(evidence, "holder_ref", "")),
        disclosure_layer=_coerce_identifier(getattr(evidence, "disclosure_layer", "")),
        related_claim_refs=_normalize_name_sequence(getattr(evidence, "related_claim_refs", ()) or ()),
        related_event_refs=_normalize_name_sequence(getattr(evidence, "related_event_refs", ()) or ()),
        timeline_anchor_id=_coerce_optional_identifier(getattr(evidence, "timeline_anchor_id", None)),
        content_excerpt_or_summary=getattr(evidence, "content_excerpt_or_summary", ""),
    )


def _sorted_events(events: Iterable[NormalizedWorldEvent]) -> list[NormalizedWorldEvent]:
    return sorted(events, key=lambda event: event.ledger_event.sort_key())


def _issue(
    *,
    layer: str,
    checker_name: str,
    code: str,
    message: str,
    severity: str = "error",
    **refs: Any,
) -> CheckerIssue:
    return CheckerIssue(
        layer=layer,
        checker_name=checker_name,
        code=code,
        message=message,
        severity=severity,
        refs=refs,
    )


def _validate_project_profile_pack_contract(
    *,
    project_profile: ProjectProfileVersion,
    profile: GenreProfileSpec,
    pack: CheckerPack,
) -> None:
    pack_version = _checker_pack_version(profile)
    version_refs = {
        "project_profile_version.contract_version": project_profile.contract_version,
        "genre_profile.contract_version": profile.contract_version,
        "checker_pack.version": pack_version,
    }
    errors: list[str] = []
    if len(set(version_refs.values())) != 1:
        errors.append(
            "contract_version mismatch: "
            + ", ".join(f"{key}={value}" for key, value in version_refs.items())
        )

    profile_fingerprint = _checker_config_fingerprint(profile.checker_config)
    if profile_fingerprint != pack.checker_config_fingerprint:
        errors.append(
            "checker_config fingerprint mismatch: "
            f"genre_profile={profile_fingerprint}, checker_pack={pack.checker_config_fingerprint}"
        )

    official_definition = _get_official_genre_profile_definition_or_none(profile.canonical_id)
    if official_definition is not None:
        official_profile = _profile_spec_from_definition(official_definition)
        official_fingerprint = _checker_config_fingerprint(official_profile.checker_config)
        if official_profile.contract_version != profile.contract_version:
            errors.append(
                "official contract drift: "
                f"official={official_profile.contract_version}, genre_profile={profile.contract_version}"
            )
        if official_fingerprint != profile_fingerprint:
            errors.append(
                "checker_config fingerprint mismatch: "
                f"official={official_fingerprint}, genre_profile={profile_fingerprint}"
            )

    if errors:
        raise CheckerPackContractMismatchError("; ".join(errors))


def _checker_pack_version(profile: GenreProfileSpec) -> str:
    pack_version = profile.checker_config.get("pack_version")
    if pack_version is None:
        return profile.contract_version
    if isinstance(pack_version, str) and pack_version.strip():
        return pack_version.strip()
    raise CheckerPackConfigurationError(
        f"checker_config.pack_version for {profile.canonical_id} must be a non-empty string"
    )


def _normalize_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _normalize_name_sequence(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        return ()
    if isinstance(value, (Sequence, set)):
        normalized: list[str] = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                normalized.append(text)
        return tuple(normalized)
    return ()


def _normalize_checker_name_sequence(
    value: Any,
    *,
    profile_id: str,
    layer_name: str,
) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, (Sequence, set)):
        raise CheckerPackConfigurationError(
            f"checker_config.layers[{layer_name!r}] for {profile_id} must be a sequence of checker names"
        )

    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise CheckerPackConfigurationError(
                f"checker_config.layers[{layer_name!r}] for {profile_id} contains invalid checker name at index {index}"
            )
        normalized.append(item.strip())
    return tuple(normalized)


def _validate_checker_config(profile: GenreProfileSpec) -> dict[str, Any]:
    checker_config = _canonicalize_checker_config_value(
        profile.checker_config,
        profile_id=profile.canonical_id,
        path="checker_config",
    )
    if not isinstance(checker_config, dict):
        raise CheckerPackConfigurationError(
            f"checker_config for {profile.canonical_id} must be a mapping"
        )
    layers = checker_config.get("layers", {})
    if not isinstance(layers, Mapping):
        raise CheckerPackConfigurationError(
            f"checker_config.layers for {profile.canonical_id} must be a mapping"
        )
    checker_config["layers"] = dict(layers)
    return checker_config


def _canonicalize_checker_config_value(
    value: Any,
    *,
    profile_id: str,
    path: str,
) -> Any:
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key.strip():
                raise CheckerPackConfigurationError(
                    f"{path} for {profile_id} contains invalid mapping key"
                )
            normalized[key] = _canonicalize_checker_config_value(
                item,
                profile_id=profile_id,
                path=f"{path}.{key}",
            )
        return normalized
    if isinstance(value, (list, tuple)):
        return [
            _canonicalize_checker_config_value(
                item,
                profile_id=profile_id,
                path=f"{path}[]",
            )
            for item in value
        ]
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CheckerPackConfigurationError(
                f"{path} for {profile_id} must not contain NaN or infinity"
            )
        return value
    if isinstance(value, str):
        return value
    raise CheckerPackConfigurationError(
        f"{path} for {profile_id} contains unsupported value type {type(value).__name__}"
    )


def _checker_config_fingerprint(checker_config: Mapping[str, Any]) -> str:
    canonical_payload = json.dumps(
        checker_config,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def _get_official_genre_profile_definition_or_none(
    canonical_id: str,
) -> OfficialGenreProfileDefinition | None:
    try:
        return get_official_genre_profile_definition(canonical_id)
    except KeyError:
        return None


def _coerce_identifier(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _coerce_optional_identifier(value: Any) -> str | None:
    text = _coerce_identifier(value)
    return text or None


def _coerce_int(value: Any) -> int:
    coerced = _coerce_optional_int(value)
    return coerced if coerced is not None else 0


def _coerce_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return 0.0 if value == "" else None
    if isinstance(value, bool):
        return None
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(coerced):
        return None
    return coerced


def _is_strict_real_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))

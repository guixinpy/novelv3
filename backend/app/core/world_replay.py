from collections import defaultdict
from dataclasses import dataclass, field, replace
from typing import Any, Iterable

from app.core.world_time_normalizer import StoryTimePoint, build_anchor_time_index, normalize_story_time


class WorldReplayError(ValueError):
    pass


class DuplicateEventError(WorldReplayError):
    pass


class BrokenSupersedesChainError(WorldReplayError):
    pass


@dataclass(frozen=True)
class LedgerEvent:
    event_id: str
    event_type: str
    chapter_index: int
    intra_chapter_seq: int = 0
    payload: dict[str, Any] = field(default_factory=dict)
    idempotency_key: str | None = None
    supersedes_event_ref: str | None = None
    timeline_anchor_id: str | None = None
    storage_id: str | None = None
    story_time: StoryTimePoint | None = None

    def resolved_story_time(self) -> StoryTimePoint:
        return self.story_time or normalize_story_time(
            chapter_index=self.chapter_index,
            intra_chapter_seq=self.intra_chapter_seq,
        )

    def sort_key(self) -> tuple[int, int, int, str, str]:
        return (*self.resolved_story_time().sort_key(), self.event_id, self.storage_id or "")


@dataclass
class ReplayState:
    ledger: dict[str, LedgerEvent]
    active_event_ids: list[str]
    inactive_event_ids: list[str]
    entities: dict[str, dict[str, Any]] = field(default_factory=dict)
    relations: dict[str, dict[str, Any]] = field(default_factory=dict)
    presence: dict[str, dict[str, Any]] = field(default_factory=dict)
    occurred_events: dict[str, dict[str, Any]] = field(default_factory=dict)
    event_links: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    fact_reviews: dict[str, dict[str, Any]] = field(default_factory=dict)


def replay_events(events: Iterable[LedgerEvent]) -> ReplayState:
    ordered_events = sorted(events, key=lambda event: event.sort_key())
    ledger: dict[str, LedgerEvent] = {}
    idempotency_index: dict[str, str] = {}
    inactive_ids: list[str] = []
    inactive_lookup: set[str] = set()

    for event in ordered_events:
        if event.event_id in ledger:
            raise DuplicateEventError(f"duplicate event_id: {event.event_id}")
        if event.idempotency_key:
            existing = idempotency_index.get(event.idempotency_key)
            if existing is not None:
                raise DuplicateEventError(
                    f"idempotency key {event.idempotency_key} already used by {existing}"
                )
            idempotency_index[event.idempotency_key] = event.event_id
        if event.supersedes_event_ref is not None:
            if event.event_type != "retcon_applied":
                raise BrokenSupersedesChainError(
                    "supersedes_event_ref is only valid for retcon_applied events"
                )
            superseded = ledger.get(event.supersedes_event_ref)
            if superseded is None or event.supersedes_event_ref in inactive_lookup:
                raise BrokenSupersedesChainError(
                    f"supersedes target is missing or inactive: {event.supersedes_event_ref}"
                )
            inactive_lookup.add(event.supersedes_event_ref)
            inactive_ids.append(event.supersedes_event_ref)
        ledger[event.event_id] = event

    active_event_ids = [
        event.event_id for event in ordered_events if event.event_id not in inactive_lookup
    ]
    state = ReplayState(
        ledger=ledger,
        active_event_ids=active_event_ids,
        inactive_event_ids=inactive_ids,
    )
    for event in ordered_events:
        if event.event_id in inactive_lookup:
            continue
        _apply_event(state, event)
    state.event_links = dict(state.event_links)
    return state


def ledger_events_from_world_events(events: Iterable[Any], anchors: Iterable[Any] = ()) -> list[LedgerEvent]:
    anchor_index = build_anchor_time_index(anchors) if anchors else {}
    return [ledger_event_from_world_event(event, anchor_index=anchor_index) for event in events]


def bind_event_story_times(
    *,
    events: Iterable[LedgerEvent],
    anchor_index: dict[str, StoryTimePoint],
) -> list[LedgerEvent]:
    return [_bind_event_story_time(event=event, anchor_index=anchor_index) for event in events]


def ledger_event_from_world_event(
    event: Any,
    *,
    anchor_index: dict[str, StoryTimePoint] | None = None,
) -> LedgerEvent:
    anchor_index = anchor_index or {}
    ledger_event = LedgerEvent(
        event_id=event.event_id,
        event_type=event.event_type,
        chapter_index=event.chapter_index,
        intra_chapter_seq=event.intra_chapter_seq,
        payload=dict(getattr(event, "primitive_payload", None) or {}),
        idempotency_key=getattr(event, "idempotency_key", None),
        supersedes_event_ref=getattr(event, "supersedes_event_ref", None),
        timeline_anchor_id=getattr(event, "timeline_anchor_id", None),
        storage_id=getattr(event, "id", None),
    )
    return _bind_event_story_time(event=ledger_event, anchor_index=anchor_index)


def _bind_event_story_time(
    *,
    event: LedgerEvent,
    anchor_index: dict[str, StoryTimePoint],
) -> LedgerEvent:
    if event.timeline_anchor_id is None:
        return event
    if event.timeline_anchor_id not in anchor_index:
        raise ValueError(f"missing anchor reference: {event.timeline_anchor_id}")
    return replace(event, story_time=anchor_index[event.timeline_anchor_id])


def _apply_event(state: ReplayState, event: LedgerEvent) -> None:
    payload = dict(event.payload)
    event_type = event.event_type

    if event_type == "retcon_applied":
        event_type = payload.pop("replacement_event_type", "")
        if not event_type:
            raise BrokenSupersedesChainError(
                f"retcon event {event.event_id} is missing replacement_event_type"
            )

    if event_type == "entity_introduced":
        entity_ref = payload["entity_ref"]
        state.entities[entity_ref] = {
            "entity_type": payload.get("entity_type", ""),
            "attributes": dict(payload.get("attributes", {})),
        }
        return
    if event_type == "attribute_mutated":
        entity_ref = payload["entity_ref"]
        entity_state = state.entities.setdefault(
            entity_ref,
            {"entity_type": "", "attributes": {}},
        )
        entity_state["attributes"][payload["attribute"]] = payload["value"]
        return
    if event_type == "relation_mutated":
        relation_id = payload["relation_id"]
        state.relations[relation_id] = dict(payload)
        return
    if event_type == "presence_shifted":
        state.presence[payload["entity_ref"]] = dict(payload)
        return
    if event_type == "event_occurred":
        state.occurred_events[payload["event_ref"]] = dict(payload)
        return
    if event_type == "event_linked":
        state.event_links[payload["source_event_ref"]].append(
            {
                "target_event_ref": payload["target_event_ref"],
                "link_type": payload["link_type"],
            }
        )
        return
    if event_type == "fact_reviewed":
        state.fact_reviews[payload["claim_id"]] = dict(payload)
        return

    raise WorldReplayError(f"unsupported event type: {event.event_type}")

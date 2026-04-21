from dataclasses import dataclass, field
from typing import Any, Iterable

from app.core.world_replay import LedgerEvent, bind_event_story_times, replay_events
from app.core.world_time_normalizer import StoryTimePoint, build_anchor_time_index, compare_story_time, normalize_story_time


@dataclass(frozen=True)
class FactRecord:
    claim_id: str
    subject_ref: str
    predicate: str
    object_ref_or_value: Any
    claim_layer: str
    claim_status: str
    perspective_ref: str | None = None
    disclosed_to_refs: tuple[str, ...] = field(default_factory=tuple)
    chapter_index: int | None = None
    intra_chapter_seq: int = 0
    valid_from_anchor_id: str | None = None
    valid_to_anchor_id: str | None = None
    story_time: StoryTimePoint | None = None


def project_world_truth(
    *,
    events: Iterable[LedgerEvent],
    facts: Iterable[FactRecord],
    anchors: Iterable[Any] = (),
) -> dict[str, Any]:
    event_list = list(events)
    fact_list = list(facts)
    anchor_index = build_anchor_time_index(anchors) if anchors else {}
    resolved_events = bind_event_story_times(events=event_list, anchor_index=anchor_index)
    replay_state = replay_events(resolved_events)
    truth_facts = _materialize_truth_facts(
        facts=fact_list,
        anchor_index=anchor_index,
        as_of_time=_resolve_current_time(events=resolved_events, facts=fact_list, anchor_index=anchor_index),
    )
    return {
        "entities": replay_state.entities,
        "relations": replay_state.relations,
        "presence": replay_state.presence,
        "occurred_events": replay_state.occurred_events,
        "event_links": replay_state.event_links,
        "facts": truth_facts,
    }


def project_subject_knowledge(
    *,
    subject_ref: str,
    events: Iterable[LedgerEvent],
    facts: Iterable[FactRecord],
    anchors: Iterable[Any] = (),
) -> dict[str, Any]:
    event_list = list(events)
    fact_list = list(facts)
    anchor_index = build_anchor_time_index(anchors) if anchors else {}
    resolved_all_events = bind_event_story_times(events=event_list, anchor_index=anchor_index)
    _validate_fact_anchors(facts=fact_list, anchor_index=anchor_index)
    visible_events = [
        event
        for event in resolved_all_events
        if _event_is_visible_to_subject(event=event, subject_ref=subject_ref)
    ]
    replay_events_for_subject = _expand_subject_event_dependencies(
        visible_events=visible_events,
        all_events=resolved_all_events,
    )
    replay_state = replay_events(replay_events_for_subject)
    visible_facts = [fact for fact in fact_list if _fact_is_visible_to_subject(fact=fact, subject_ref=subject_ref)]
    projected_facts = _materialize_subject_facts(
        facts=visible_facts,
        subject_ref=subject_ref,
        anchor_index=anchor_index,
        as_of_time=_resolve_current_time(events=replay_events_for_subject, facts=visible_facts, anchor_index=anchor_index),
    )
    return {
        "entities": replay_state.entities,
        "relations": replay_state.relations,
        "presence": replay_state.presence,
        "occurred_events": replay_state.occurred_events,
        "event_links": replay_state.event_links,
        "facts": projected_facts,
    }


def project_snapshot(
    *,
    events: Iterable[LedgerEvent],
    facts: Iterable[FactRecord],
    chapter_index: int,
    intra_chapter_seq: int | None = None,
    as_of_anchor_id: str | None = None,
    anchors: Iterable[Any] = (),
) -> dict[str, Any]:
    event_list = list(events)
    fact_list = list(facts)
    anchor_index = build_anchor_time_index(anchors) if anchors else {}
    snapshot_time = _resolve_snapshot_time(
        chapter_index=chapter_index,
        intra_chapter_seq=intra_chapter_seq,
        as_of_anchor_id=as_of_anchor_id,
        anchor_index=anchor_index,
    )
    resolved_events = bind_event_story_times(events=event_list, anchor_index=anchor_index)
    scoped_events = [
        event
        for event in resolved_events
        if compare_story_time(_event_time(event, anchor_index), snapshot_time) <= 0
    ]
    scoped_facts = [
        fact
        for fact in fact_list
        if _fact_is_started_by(fact=fact, as_of_time=snapshot_time, anchor_index=anchor_index)
    ]
    replay_state = replay_events(scoped_events)
    truth_facts = _materialize_truth_facts(
        facts=scoped_facts,
        anchor_index=anchor_index,
        as_of_time=snapshot_time,
    )
    return {
        "entities": replay_state.entities,
        "relations": replay_state.relations,
        "presence": replay_state.presence,
        "occurred_events": replay_state.occurred_events,
        "event_links": replay_state.event_links,
        "facts": truth_facts,
    }


def _materialize_truth_facts(
    *,
    facts: Iterable[FactRecord],
    anchor_index: dict[str, StoryTimePoint],
    as_of_time: StoryTimePoint,
) -> dict[str, dict[str, Any]]:
    candidates: dict[tuple[str, str], FactRecord] = {}
    for fact in facts:
        if fact.claim_status != "confirmed" or fact.claim_layer != "truth":
            continue
        if not _fact_is_active_at(fact=fact, as_of_time=as_of_time, anchor_index=anchor_index):
            continue
        key = (fact.subject_ref, fact.predicate)
        current = candidates.get(key)
        if current is None or _fact_precedence_key(fact, anchor_index, 0) > _fact_precedence_key(current, anchor_index, 0):
            candidates[key] = fact
    return _materialize_fact_map(candidates.values())


def _materialize_subject_facts(
    *,
    facts: Iterable[FactRecord],
    subject_ref: str,
    anchor_index: dict[str, StoryTimePoint],
    as_of_time: StoryTimePoint,
) -> dict[str, dict[str, Any]]:
    candidates: dict[tuple[str, str], tuple[int, FactRecord]] = {}
    for fact in facts:
        if fact.claim_status != "confirmed":
            continue
        if not _fact_is_active_at(fact=fact, as_of_time=as_of_time, anchor_index=anchor_index):
            continue
        layer_priority = 1 if fact.perspective_ref == subject_ref else 0
        key = (fact.subject_ref, fact.predicate)
        current = candidates.get(key)
        if current is None or _fact_precedence_key(fact, anchor_index, layer_priority) > _fact_precedence_key(current[1], anchor_index, current[0]):
            candidates[key] = (layer_priority, fact)
    return _materialize_fact_map(fact for _, fact in candidates.values())


def _materialize_fact_map(facts: Iterable[FactRecord]) -> dict[str, dict[str, Any]]:
    projected: dict[str, dict[str, Any]] = {}
    for fact in facts:
        projected.setdefault(fact.subject_ref, {})[fact.predicate] = fact.object_ref_or_value
    return projected


def _fact_is_visible_to_subject(*, fact: FactRecord, subject_ref: str) -> bool:
    if fact.perspective_ref == subject_ref:
        return True
    return fact.claim_layer == "truth" and subject_ref in fact.disclosed_to_refs


def _event_is_visible_to_subject(*, event: LedgerEvent, subject_ref: str) -> bool:
    known_by_refs = event.payload.get("known_by_refs")
    if known_by_refs is None:
        return True
    return subject_ref in known_by_refs


def _fact_is_started_by(
    *,
    fact: FactRecord,
    as_of_time: StoryTimePoint,
    anchor_index: dict[str, StoryTimePoint],
) -> bool:
    start_time = _fact_start_time(fact, anchor_index)
    if start_time is None:
        return False
    return compare_story_time(start_time, as_of_time) <= 0


def _fact_is_active_at(
    *,
    fact: FactRecord,
    as_of_time: StoryTimePoint,
    anchor_index: dict[str, StoryTimePoint],
) -> bool:
    start_time = _fact_start_time(fact, anchor_index)
    if start_time is not None and compare_story_time(start_time, as_of_time) > 0:
        return False
    end_time = _fact_end_time(fact, anchor_index)
    if end_time is not None and compare_story_time(end_time, as_of_time) <= 0:
        return False
    return True


def _fact_precedence_key(
    fact: FactRecord,
    anchor_index: dict[str, StoryTimePoint],
    layer_priority: int,
) -> tuple[int, int, int, int, int, int, int, str]:
    start_time = _fact_start_time(fact, anchor_index) or StoryTimePoint(-1, -1, -1)
    claim_time = _fact_claim_time(fact, anchor_index) or StoryTimePoint(-1, -1, -1)
    return (
        layer_priority,
        *start_time.sort_key(),
        *claim_time.sort_key(),
        fact.claim_id,
    )


def _fact_start_time(
    fact: FactRecord,
    anchor_index: dict[str, StoryTimePoint],
) -> StoryTimePoint | None:
    if fact.valid_from_anchor_id is not None:
        return _anchor_time_or_raise(anchor_id=fact.valid_from_anchor_id, anchor_index=anchor_index)
    return _fact_claim_time(fact, anchor_index)


def _fact_end_time(
    fact: FactRecord,
    anchor_index: dict[str, StoryTimePoint],
) -> StoryTimePoint | None:
    if fact.valid_to_anchor_id is not None:
        return _anchor_time_or_raise(anchor_id=fact.valid_to_anchor_id, anchor_index=anchor_index)
    return None


def _fact_claim_time(
    fact: FactRecord,
    anchor_index: dict[str, StoryTimePoint],
) -> StoryTimePoint | None:
    if fact.story_time is not None:
        return fact.story_time
    if fact.chapter_index is None:
        return None
    return normalize_story_time(
        chapter_index=fact.chapter_index,
        intra_chapter_seq=fact.intra_chapter_seq,
    )


def _event_time(event: LedgerEvent, anchor_index: dict[str, StoryTimePoint]) -> StoryTimePoint:
    if event.story_time is not None:
        return event.story_time
    if event.timeline_anchor_id is not None and event.timeline_anchor_id in anchor_index:
        return anchor_index[event.timeline_anchor_id]
    if event.timeline_anchor_id is not None:
        raise ValueError(f"missing anchor reference: {event.timeline_anchor_id}")
    return event.resolved_story_time()


def _resolve_snapshot_time(
    *,
    chapter_index: int,
    intra_chapter_seq: int | None,
    as_of_anchor_id: str | None,
    anchor_index: dict[str, StoryTimePoint],
) -> StoryTimePoint:
    if as_of_anchor_id is not None:
        return _anchor_time_or_raise(anchor_id=as_of_anchor_id, anchor_index=anchor_index)
    if intra_chapter_seq is None:
        return StoryTimePoint(chapter_index=chapter_index, intra_chapter_seq=999999, day_offset=999999)
    return normalize_story_time(chapter_index=chapter_index, intra_chapter_seq=intra_chapter_seq)


def _resolve_current_time(
    *,
    events: Iterable[LedgerEvent],
    facts: Iterable[FactRecord],
    anchor_index: dict[str, StoryTimePoint],
) -> StoryTimePoint:
    points = [_event_time(event, anchor_index) for event in events]
    for fact in facts:
        start_time = _fact_start_time(fact, anchor_index)
        end_time = _fact_end_time(fact, anchor_index)
        if start_time is not None:
            points.append(start_time)
        if end_time is not None:
            points.append(end_time)
    if not points:
        return StoryTimePoint(0, 0, 0)
    return max(points, key=lambda point: point.sort_key())


def _expand_subject_event_dependencies(
    *,
    visible_events: list[LedgerEvent],
    all_events: list[LedgerEvent],
) -> list[LedgerEvent]:
    event_index = {event.event_id: event for event in all_events}
    expanded: dict[str, LedgerEvent] = {event.event_id: event for event in visible_events}
    stack = [event for event in visible_events if event.supersedes_event_ref is not None]

    while stack:
        event = stack.pop()
        dependency_ref = event.supersedes_event_ref
        if dependency_ref is None or dependency_ref in expanded:
            continue
        dependency = event_index.get(dependency_ref)
        if dependency is None:
            raise ValueError(f"missing superseded event reference: {dependency_ref}")
        expanded[dependency_ref] = dependency
        if dependency.supersedes_event_ref is not None:
            stack.append(dependency)

    return list(expanded.values())


def _validate_fact_anchors(
    *,
    facts: Iterable[FactRecord],
    anchor_index: dict[str, StoryTimePoint],
) -> None:
    for fact in facts:
        _fact_start_time(fact, anchor_index)
        _fact_end_time(fact, anchor_index)


def _anchor_time_or_raise(
    *,
    anchor_id: str,
    anchor_index: dict[str, StoryTimePoint],
) -> StoryTimePoint:
    if anchor_id not in anchor_index:
        raise ValueError(f"missing anchor reference: {anchor_id}")
    return anchor_index[anchor_id]

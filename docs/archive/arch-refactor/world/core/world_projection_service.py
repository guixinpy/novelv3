from collections import OrderedDict
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import or_
from sqlalchemy.orm import Session, load_only

from app.core.world_projection import (
    FactRecord,
    project_snapshot,
    project_subject_knowledge,
    project_world_truth,
)
from app.core.world_replay import LedgerEvent, ledger_event_from_world_event
from app.core.world_time_normalizer import build_anchor_time_index
from app.models import (
    ProjectProfileVersion,
    WorldArtifact,
    WorldCharacter,
    WorldEvent,
    WorldFactClaim,
    WorldFaction,
    WorldLocation,
    WorldResource,
    WorldTimelineAnchor,
)
from app.schemas import ProjectWorldOverviewOut, WorldProjectionOut

WorldProjectionViewType = Literal["current_truth", "subject_knowledge", "chapter_snapshot"]
WorldProjectionCacheKey = tuple[str, str, int, WorldProjectionViewType, str | None, int | None]
WORLD_PROJECTION_CACHE_MAX_ENTRIES = 128
WORLD_PROJECTION_CACHE_MAX_ITEMS = 5000
_projection_cache: OrderedDict[WorldProjectionCacheKey, ProjectWorldOverviewOut] = OrderedDict()


@dataclass(frozen=True)
class WorldProjectionSource:
    anchors: list[WorldTimelineAnchor]
    events: list[LedgerEvent]
    facts: list[FactRecord]


def build_world_projection_overview(
    *,
    db: Session,
    project_id: str,
    profile: ProjectProfileVersion | None,
    view_type: WorldProjectionViewType,
    subject_ref: str | None = None,
    chapter_index: int | None = None,
) -> ProjectWorldOverviewOut:
    if profile is None:
        return ProjectWorldOverviewOut(project_profile=None, projection=None)

    cache_key = _projection_cache_key(
        project_id=project_id,
        profile=profile,
        view_type=view_type,
        subject_ref=subject_ref,
        chapter_index=chapter_index,
    )
    cached = _projection_cache.get(cache_key)
    if cached is not None:
        _projection_cache.move_to_end(cache_key)
        return cached

    source = load_world_projection_source(
        db=db,
        project_id=project_id,
        profile=profile,
        max_chapter_index=chapter_index if view_type == "chapter_snapshot" else None,
    )
    projection = build_world_projection(source=source, view_type=view_type, subject_ref=subject_ref, chapter_index=chapter_index)
    overview = ProjectWorldOverviewOut(
        project_profile=profile,
        projection=WorldProjectionOut(view_type=view_type, **projection),
    )
    if _projection_cache_item_count(overview) > WORLD_PROJECTION_CACHE_MAX_ITEMS:
        return overview
    _projection_cache[cache_key] = overview
    _projection_cache.move_to_end(cache_key)
    while len(_projection_cache) > WORLD_PROJECTION_CACHE_MAX_ENTRIES:
        _projection_cache.popitem(last=False)
    return overview


def invalidate_world_projection_cache(project_id: str | None = None) -> None:
    if project_id is None:
        _projection_cache.clear()
        return
    stale_keys = [key for key in _projection_cache if key[0] == project_id]
    for key in stale_keys:
        _projection_cache.pop(key, None)


def clear_world_projection_cache() -> None:
    invalidate_world_projection_cache()


def _projection_cache_item_count(overview: ProjectWorldOverviewOut) -> int:
    projection = overview.projection
    if projection is None:
        return 0
    return (
        len(projection.entities)
        + len(projection.relations)
        + len(projection.presence)
        + len(projection.occurred_events)
        + len(projection.event_links)
        + _fact_item_count(projection.facts)
    )


def _fact_item_count(facts: dict) -> int:
    count = 0
    for values in facts.values():
        count += len(values) if isinstance(values, dict) else 1
    return count


def _projection_cache_key(
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    view_type: WorldProjectionViewType,
    subject_ref: str | None,
    chapter_index: int | None,
) -> WorldProjectionCacheKey:
    return (project_id, profile.id, profile.version, view_type, subject_ref, chapter_index)


def load_world_projection_source(
    *,
    db: Session,
    project_id: str,
    profile: ProjectProfileVersion,
    max_chapter_index: int | None = None,
) -> WorldProjectionSource:
    anchors = (
        db.query(WorldTimelineAnchor)
        .options(
            load_only(
                WorldTimelineAnchor.id,
                WorldTimelineAnchor.anchor_id,
                WorldTimelineAnchor.chapter_index,
                WorldTimelineAnchor.intra_chapter_seq,
                WorldTimelineAnchor.world_time_label,
                WorldTimelineAnchor.relative_to_anchor_ref,
            )
        )
        .filter(
            WorldTimelineAnchor.project_id == project_id,
            WorldTimelineAnchor.profile_version == profile.version,
        )
        .order_by(
            WorldTimelineAnchor.chapter_index.asc(),
            WorldTimelineAnchor.intra_chapter_seq.asc(),
            WorldTimelineAnchor.anchor_id.asc(),
        )
        .all()
    )
    catalog_events = _catalog_entity_events(db=db, project_id=project_id, profile=profile)
    event_query = db.query(WorldEvent).filter(
        WorldEvent.project_id == project_id,
        WorldEvent.project_profile_version_id == profile.id,
        WorldEvent.profile_version == profile.version,
    )
    event_query = event_query.options(
        load_only(
            WorldEvent.id,
            WorldEvent.event_id,
            WorldEvent.event_type,
            WorldEvent.chapter_index,
            WorldEvent.intra_chapter_seq,
            WorldEvent.primitive_payload,
            WorldEvent.idempotency_key,
            WorldEvent.supersedes_event_ref,
            WorldEvent.timeline_anchor_id,
        )
    )
    fact_query = db.query(WorldFactClaim).filter(
        WorldFactClaim.project_id == project_id,
        WorldFactClaim.project_profile_version_id == profile.id,
        WorldFactClaim.profile_version == profile.version,
        WorldFactClaim.claim_status == "confirmed",
    )
    fact_query = fact_query.options(
        load_only(
            WorldFactClaim.id,
            WorldFactClaim.claim_id,
            WorldFactClaim.subject_ref,
            WorldFactClaim.predicate,
            WorldFactClaim.object_ref_or_value,
            WorldFactClaim.claim_layer,
            WorldFactClaim.claim_status,
            WorldFactClaim.perspective_ref,
            WorldFactClaim.disclosed_to_refs,
            WorldFactClaim.chapter_index,
            WorldFactClaim.intra_chapter_seq,
            WorldFactClaim.valid_from_anchor_id,
            WorldFactClaim.valid_to_anchor_id,
        )
    )
    if max_chapter_index is not None:
        event_query = event_query.filter(WorldEvent.chapter_index <= max_chapter_index)
        fact_query = fact_query.filter(
            or_(
                WorldFactClaim.chapter_index.is_(None),
                WorldFactClaim.chapter_index <= max_chapter_index,
            )
        )
    events = (
        event_query.order_by(
            WorldEvent.chapter_index.asc(),
            WorldEvent.intra_chapter_seq.asc(),
            WorldEvent.event_id.asc(),
        )
        .all()
    )
    facts = (
        fact_query.order_by(
            WorldFactClaim.chapter_index.asc(),
            WorldFactClaim.intra_chapter_seq.asc(),
            WorldFactClaim.claim_id.asc(),
        )
        .all()
    )
    anchor_index = build_anchor_time_index(anchors)
    return WorldProjectionSource(
        anchors=anchors,
        events=[
            *catalog_events,
            *[ledger_event_from_world_event(event, anchor_index=anchor_index) for event in events],
        ],
        facts=[fact_record_from_model(fact) for fact in facts],
    )


def build_world_projection(
    *,
    source: WorldProjectionSource,
    view_type: WorldProjectionViewType,
    subject_ref: str | None = None,
    chapter_index: int | None = None,
) -> dict:
    if view_type == "current_truth":
        return project_world_truth(
            events=source.events,
            facts=source.facts,
            anchors=source.anchors,
        )
    if view_type == "subject_knowledge":
        if not subject_ref:
            raise ValueError("subject_ref is required for subject_knowledge projection")
        return project_subject_knowledge(
            subject_ref=subject_ref,
            events=source.events,
            facts=source.facts,
            anchors=source.anchors,
        )
    if view_type == "chapter_snapshot":
        if chapter_index is None:
            raise ValueError("chapter_index is required for chapter_snapshot projection")
        return project_snapshot(
            events=source.events,
            facts=source.facts,
            chapter_index=chapter_index,
            anchors=source.anchors,
        )
    raise ValueError(f"Unsupported world projection view_type: {view_type}")


def fact_record_from_model(fact: WorldFactClaim) -> FactRecord:
    return FactRecord(
        claim_id=fact.claim_id,
        subject_ref=fact.subject_ref,
        predicate=fact.predicate,
        object_ref_or_value=fact.object_ref_or_value,
        claim_layer=fact.claim_layer,
        claim_status=fact.claim_status,
        perspective_ref=getattr(fact, "perspective_ref", None),
        disclosed_to_refs=tuple(getattr(fact, "disclosed_to_refs", ()) or ()),
        chapter_index=fact.chapter_index,
        intra_chapter_seq=fact.intra_chapter_seq,
        valid_from_anchor_id=fact.valid_from_anchor_id,
        valid_to_anchor_id=fact.valid_to_anchor_id,
    )


def _catalog_entity_events(
    *,
    db: Session,
    project_id: str,
    profile: ProjectProfileVersion,
) -> list[LedgerEvent]:
    events: list[LedgerEvent] = []
    for model, entity_type, fields in [
        (
            WorldCharacter,
            "character",
            [
                "name",
                "primary_alias",
                "aliases",
                "role_type",
                "identity_anchor",
                "origin_background",
                "core_traits",
                "core_drives",
                "public_persona",
                "notes",
            ],
        ),
        (
            WorldLocation,
            "location",
            [
                "name",
                "primary_alias",
                "aliases",
                "location_type",
                "parent_location_id",
                "spatial_scope",
                "functional_tags",
                "notes",
            ],
        ),
        (
            WorldFaction,
            "faction",
            [
                "name",
                "primary_alias",
                "aliases",
                "faction_type",
                "mission_or_doctrine",
                "territorial_scope",
                "public_image",
                "notes",
            ],
        ),
        (
            WorldArtifact,
            "artifact",
            [
                "name",
                "primary_alias",
                "aliases",
                "artifact_type",
                "origin",
                "function_summary",
                "uniqueness",
                "notes",
            ],
        ),
        (
            WorldResource,
            "resource",
            [
                "name",
                "primary_alias",
                "resource_type",
                "unit_or_scale",
                "holder_type",
                "scarcity_level",
                "visibility",
                "notes",
            ],
        ),
    ]:
        rows = (
            db.query(model)
            .options(load_only(model.id, model.canonical_id, *[getattr(model, field) for field in fields]))
            .filter(
                model.project_id == project_id,
                model.profile_version == profile.version,
            )
            .order_by(model.canonical_id.asc(), model.id.asc())
            .all()
        )
        for row in rows:
            attributes = {
                field: getattr(row, field)
                for field in fields
                if getattr(row, field, None) not in (None, "", [], {})
            }
            events.append(
                LedgerEvent(
                    event_id=f"__catalog_entity__.{row.canonical_id}",
                    event_type="entity_introduced",
                    chapter_index=0,
                    intra_chapter_seq=0,
                    payload={
                        "entity_ref": row.canonical_id,
                        "entity_type": entity_type,
                        "attributes": attributes,
                        "known_by_refs": [row.canonical_id],
                    },
                    storage_id=row.id,
                )
            )
    return events

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.core.world_projection import (
    FactRecord,
    project_snapshot,
    project_subject_knowledge,
    project_world_truth,
)
from app.core.world_replay import LedgerEvent, ledger_event_from_world_event
from app.core.world_time_normalizer import build_anchor_time_index
from app.models import ProjectProfileVersion, WorldEvent, WorldFactClaim, WorldTimelineAnchor
from app.schemas import ProjectWorldOverviewOut, WorldProjectionOut

WorldProjectionViewType = Literal["current_truth", "subject_knowledge", "chapter_snapshot"]


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

    source = load_world_projection_source(db=db, project_id=project_id, profile=profile)
    projection = build_world_projection(source=source, view_type=view_type, subject_ref=subject_ref, chapter_index=chapter_index)
    return ProjectWorldOverviewOut(
        project_profile=profile,
        projection=WorldProjectionOut(view_type=view_type, **projection),
    )


def load_world_projection_source(
    *,
    db: Session,
    project_id: str,
    profile: ProjectProfileVersion,
) -> WorldProjectionSource:
    anchors = (
        db.query(WorldTimelineAnchor)
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
    events = (
        db.query(WorldEvent)
        .filter(
            WorldEvent.project_id == project_id,
            WorldEvent.project_profile_version_id == profile.id,
            WorldEvent.profile_version == profile.version,
        )
        .order_by(
            WorldEvent.chapter_index.asc(),
            WorldEvent.intra_chapter_seq.asc(),
            WorldEvent.event_id.asc(),
        )
        .all()
    )
    facts = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.project_profile_version_id == profile.id,
            WorldFactClaim.profile_version == profile.version,
        )
        .order_by(
            WorldFactClaim.chapter_index.asc(),
            WorldFactClaim.intra_chapter_seq.asc(),
            WorldFactClaim.claim_id.asc(),
        )
        .all()
    )
    anchor_index = build_anchor_time_index(anchors)
    return WorldProjectionSource(
        anchors=anchors,
        events=[ledger_event_from_world_event(event, anchor_index=anchor_index) for event in events],
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

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.athena_shared import get_current_profile, require_project
from app.db import get_db
from app.models import WorldEvent, WorldTimelineAnchor

router = APIRouter()


@router.get("/state")
def get_state(project_id: str, db: Session = Depends(get_db)):
    from app.api.world_model import (
        DEFAULT_PROJECTION_ENTITY_LIMIT,
        DEFAULT_PROJECTION_EVENT_LIMIT,
        DEFAULT_PROJECTION_EVENT_LINK_LIMIT,
        DEFAULT_PROJECTION_FACT_SUBJECT_LIMIT,
        DEFAULT_PROJECTION_PRESENCE_LIMIT,
        DEFAULT_PROJECTION_RELATION_LIMIT,
        get_world_model_overview,
    )
    return get_world_model_overview(
        project_id,
        db,
        entity_offset=0,
        entity_limit=DEFAULT_PROJECTION_ENTITY_LIMIT,
        relation_offset=0,
        relation_limit=DEFAULT_PROJECTION_RELATION_LIMIT,
        presence_offset=0,
        presence_limit=DEFAULT_PROJECTION_PRESENCE_LIMIT,
        event_offset=0,
        event_limit=DEFAULT_PROJECTION_EVENT_LIMIT,
        event_link_offset=0,
        event_link_limit=DEFAULT_PROJECTION_EVENT_LINK_LIMIT,
        fact_subject_offset=0,
        fact_subject_limit=DEFAULT_PROJECTION_FACT_SUBJECT_LIMIT,
    )


@router.get("/state/subject-knowledge")
def get_state_subject_knowledge(project_id: str, subject_ref: str, db: Session = Depends(get_db)):
    from app.api.world_model import get_subject_knowledge
    return get_subject_knowledge(project_id, subject_ref, db)


@router.get("/state/snapshot")
def get_state_snapshot(project_id: str, chapter_index: int = Query(..., ge=1), db: Session = Depends(get_db)):
    from app.api.world_model import get_chapter_snapshot
    return get_chapter_snapshot(project_id, chapter_index, db)


@router.get("/state/timeline")
def get_state_timeline(
    project_id: str,
    latest: bool = Query(False),
    offset: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    require_project(db, project_id)
    profile = get_current_profile(db, project_id)
    if profile is None:
        return _timeline_response(
            anchors=[],
            events=[],
            anchors_total=0,
            events_total=0,
            offset=offset,
            limit=limit,
            latest=latest,
        )

    anchor_filters = [
        WorldTimelineAnchor.project_id == project_id,
        WorldTimelineAnchor.profile_version == profile.version,
    ]
    event_filters = [
        WorldEvent.project_id == project_id,
        WorldEvent.project_profile_version_id == profile.id,
        WorldEvent.profile_version == profile.version,
    ]
    anchor_query = db.query(
        WorldTimelineAnchor.id,
        WorldTimelineAnchor.anchor_id,
        WorldTimelineAnchor.chapter_index,
        WorldTimelineAnchor.intra_chapter_seq,
        WorldTimelineAnchor.world_time_label,
    ).filter(*anchor_filters)
    event_query = db.query(
        WorldEvent.id,
        WorldEvent.event_id,
        WorldEvent.chapter_index,
        WorldEvent.intra_chapter_seq,
        WorldEvent.event_type,
        WorldEvent.primitive_payload,
        WorldEvent.notes,
    ).filter(*event_filters)
    anchors_total = db.query(func.count(WorldTimelineAnchor.id)).filter(*anchor_filters).scalar() or 0
    events_total = db.query(func.count(WorldEvent.id)).filter(*event_filters).scalar() or 0
    if latest:
        anchors = list(reversed(
            anchor_query.order_by(
                WorldTimelineAnchor.chapter_index.desc(),
                WorldTimelineAnchor.intra_chapter_seq.desc(),
                WorldTimelineAnchor.anchor_id.desc(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        ))
        events = list(reversed(
            event_query.order_by(
                WorldEvent.chapter_index.desc(),
                WorldEvent.intra_chapter_seq.desc(),
                WorldEvent.event_id.desc(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        ))
    else:
        anchors = (
            anchor_query.order_by(
                WorldTimelineAnchor.chapter_index.asc(),
                WorldTimelineAnchor.intra_chapter_seq.asc(),
                WorldTimelineAnchor.anchor_id.asc(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        )
        events = (
            event_query.order_by(
                WorldEvent.chapter_index.asc(),
                WorldEvent.intra_chapter_seq.asc(),
                WorldEvent.event_id.asc(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        )
    return _timeline_response(
        anchors=anchors,
        events=events,
        anchors_total=anchors_total,
        events_total=events_total,
        offset=offset,
        limit=limit,
        latest=latest,
    )


def _timeline_response(
    *,
    anchors: list[WorldTimelineAnchor],
    events: list[WorldEvent],
    anchors_total: int,
    events_total: int,
    offset: int,
    limit: int,
    latest: bool,
):
    return {
        "anchors": [
            {
                "id": a.id,
                "anchor_id": a.anchor_id,
                "chapter_index": a.chapter_index,
                "intra_chapter_seq": a.intra_chapter_seq,
                "label": a.world_time_label or a.anchor_id,
            }
            for a in anchors
        ],
        "events": [
            {
                "id": e.id,
                "event_id": e.event_id,
                "chapter_index": e.chapter_index,
                "intra_chapter_seq": e.intra_chapter_seq,
                "event_type": e.event_type,
                "description": _event_description(e),
            }
            for e in events
        ],
        "anchors_total": anchors_total,
        "anchors_offset": offset,
        "anchors_limit": limit,
        "anchors_has_more": offset + len(anchors) < anchors_total,
        "events_total": events_total,
        "events_offset": offset,
        "events_limit": limit,
        "events_has_more": offset + len(events) < events_total,
        "latest": latest,
    }


def _event_description(event: WorldEvent) -> str:
    payload = event.primitive_payload or {}
    title = str(payload.get("title") or payload.get("event_ref") or "").strip()
    summary = str(payload.get("summary") or "").strip()
    if title and summary:
        return f"{title}：{summary}"
    if title:
        return title
    if summary:
        return summary
    return event.notes or event.event_type

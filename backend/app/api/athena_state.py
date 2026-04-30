from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.athena_shared import get_current_profile, require_project
from app.db import get_db
from app.models import WorldEvent, WorldTimelineAnchor

router = APIRouter()


@router.get("/state")
def get_state(project_id: str, db: Session = Depends(get_db)):
    from app.api.world_model import get_world_model_overview
    return get_world_model_overview(project_id, db)


@router.get("/state/subject-knowledge")
def get_state_subject_knowledge(project_id: str, subject_ref: str, db: Session = Depends(get_db)):
    from app.api.world_model import get_subject_knowledge
    return get_subject_knowledge(project_id, subject_ref, db)


@router.get("/state/snapshot")
def get_state_snapshot(project_id: str, chapter_index: int = Query(..., ge=1), db: Session = Depends(get_db)):
    from app.api.world_model import get_chapter_snapshot
    return get_chapter_snapshot(project_id, chapter_index, db)


@router.get("/state/timeline")
def get_state_timeline(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    profile = get_current_profile(db, project_id)
    if profile is None:
        return {"anchors": [], "events": []}

    anchors = (
        db.query(WorldTimelineAnchor)
        .filter(
            WorldTimelineAnchor.project_id == project_id,
            WorldTimelineAnchor.profile_version == profile.version,
        )
        .order_by(WorldTimelineAnchor.chapter_index.asc(), WorldTimelineAnchor.intra_chapter_seq.asc())
        .all()
    )
    events = (
        db.query(WorldEvent)
        .filter(
            WorldEvent.project_id == project_id,
            WorldEvent.project_profile_version_id == profile.id,
            WorldEvent.profile_version == profile.version,
        )
        .order_by(WorldEvent.chapter_index.asc(), WorldEvent.intra_chapter_seq.asc())
        .all()
    )
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

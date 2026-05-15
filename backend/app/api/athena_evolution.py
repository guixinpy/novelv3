import json
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api.athena_shared import require_project
from app.api.outlines import ChapterOutlineUpdate
from app.core.athena_longform import analyze_chapter_to_world_proposals, build_chapter_context_package
from app.db import get_db
from app.models import Outline, Storyline
from app.schemas import ProposalBundleSplitCreate, ProposalReviewCreate, ProposalReviewRollbackCreate
from app.schemas.world_proposals import ProposalReviewQueueOut

router = APIRouter()


@router.get("/evolution/plan")
def get_evolution_plan(
    project_id: str,
    mode: str = Query("window", pattern="^(full|window)$"),
    chapter_offset: int = Query(0, ge=0),
    chapter_limit: int = Query(100, ge=1, le=500),
    plotline_offset: int = Query(0, ge=0),
    plotline_limit: int = Query(100, ge=1, le=500),
    milestone_offset: int = Query(0, ge=0),
    milestone_limit: int = Query(80, ge=1, le=500),
    foreshadowing_offset: int = Query(0, ge=0),
    foreshadowing_limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    require_project(db, project_id)
    if mode == "window":
        return _get_evolution_plan_window(
            db=db,
            project_id=project_id,
            chapter_offset=chapter_offset,
            chapter_limit=chapter_limit,
            plotline_offset=plotline_offset,
            plotline_limit=plotline_limit,
            milestone_offset=milestone_offset,
            milestone_limit=milestone_limit,
            foreshadowing_offset=foreshadowing_offset,
            foreshadowing_limit=foreshadowing_limit,
        )
    outline = db.query(Outline).filter(Outline.project_id == project_id).order_by(Outline.updated_at.desc()).first()
    storyline = db.query(Storyline).filter(Storyline.project_id == project_id).order_by(Storyline.updated_at.desc()).first()
    return {
        "outline": {
            "id": outline.id,
            "status": outline.status,
            "total_chapters": outline.total_chapters,
            "chapters": outline.chapters,
            "plotlines": outline.plotlines,
        } if outline else None,
        "storyline": {
            "id": storyline.id,
            "status": storyline.status,
            "plotlines": storyline.plotlines,
            "foreshadowing": storyline.foreshadowing,
        } if storyline else None,
    }


def _get_evolution_plan_window(
    *,
    db: Session,
    project_id: str,
    chapter_offset: int,
    chapter_limit: int,
    plotline_offset: int,
    plotline_limit: int,
    milestone_offset: int,
    milestone_limit: int,
    foreshadowing_offset: int,
    foreshadowing_limit: int,
) -> dict:
    outline = (
        db.query(
            Outline.id,
            Outline.status,
            Outline.total_chapters,
            func.coalesce(func.json_array_length(Outline.chapters), 0).label("chapters_total"),
            func.coalesce(func.json_array_length(Outline.plotlines), 0).label("plotlines_total"),
        )
        .filter(Outline.project_id == project_id)
        .order_by(Outline.updated_at.desc())
        .first()
    )
    storyline = (
        db.query(
            Storyline.id,
            Storyline.status,
            func.coalesce(func.json_array_length(Storyline.plotlines), 0).label("plotlines_total"),
            func.coalesce(func.json_array_length(Storyline.foreshadowing), 0).label("foreshadowing_total"),
        )
        .filter(Storyline.project_id == project_id)
        .order_by(Storyline.updated_at.desc())
        .first()
    )
    return {
        "outline": _windowed_outline(
            db=db,
            outline=outline,
            chapter_offset=chapter_offset,
            chapter_limit=chapter_limit,
            plotline_offset=plotline_offset,
            plotline_limit=plotline_limit,
        ),
        "storyline": _windowed_storyline(
            db=db,
            storyline=storyline,
            plotline_offset=plotline_offset,
            plotline_limit=plotline_limit,
            milestone_offset=milestone_offset,
            milestone_limit=milestone_limit,
            foreshadowing_offset=foreshadowing_offset,
            foreshadowing_limit=foreshadowing_limit,
        ),
    }


def _windowed_outline(
    *,
    db: Session,
    outline,
    chapter_offset: int,
    chapter_limit: int,
    plotline_offset: int,
    plotline_limit: int,
) -> dict | None:
    if outline is None:
        return None
    chapters_total = int(outline.chapters_total or 0)
    plotlines_total = int(outline.plotlines_total or 0)
    chapters = _json_array_window(db, "outlines", "chapters", outline.id, chapter_offset, chapter_limit)
    plotlines = _json_array_window(db, "outlines", "plotlines", outline.id, plotline_offset, plotline_limit)
    return {
        "id": outline.id,
        "status": outline.status,
        "total_chapters": outline.total_chapters,
        "chapters": chapters,
        "plotlines": plotlines,
        "chapters_total": chapters_total,
        "chapters_offset": chapter_offset,
        "chapters_limit": chapter_limit,
        "chapters_has_more": chapter_offset + len(chapters) < chapters_total,
        "plotlines_total": plotlines_total,
        "plotlines_offset": plotline_offset,
        "plotlines_limit": plotline_limit,
        "plotlines_has_more": plotline_offset + len(plotlines) < plotlines_total,
    }


def _windowed_storyline(
    *,
    db: Session,
    storyline,
    plotline_offset: int,
    plotline_limit: int,
    milestone_offset: int,
    milestone_limit: int,
    foreshadowing_offset: int,
    foreshadowing_limit: int,
) -> dict | None:
    if storyline is None:
        return None
    plotlines_total = int(storyline.plotlines_total or 0)
    foreshadowing_total = int(storyline.foreshadowing_total or 0)
    plotlines = _json_array_window(db, "storylines", "plotlines", storyline.id, plotline_offset, plotline_limit)
    plotlines = _window_plotline_milestones(plotlines, milestone_offset, milestone_limit)
    foreshadowing = _json_array_window(
        db,
        "storylines",
        "foreshadowing",
        storyline.id,
        foreshadowing_offset,
        foreshadowing_limit,
    )
    return {
        "id": storyline.id,
        "status": storyline.status,
        "plotlines": plotlines,
        "foreshadowing": foreshadowing,
        "plotlines_total": plotlines_total,
        "plotlines_offset": plotline_offset,
        "plotlines_limit": plotline_limit,
        "plotlines_has_more": plotline_offset + len(plotlines) < plotlines_total,
        "foreshadowing_total": foreshadowing_total,
        "foreshadowing_offset": foreshadowing_offset,
        "foreshadowing_limit": foreshadowing_limit,
        "foreshadowing_has_more": foreshadowing_offset + len(foreshadowing) < foreshadowing_total,
    }


def _window_plotline_milestones(plotlines: list[Any], offset: int, limit: int) -> list[Any]:
    windowed: list[Any] = []
    for plotline in plotlines:
        if not isinstance(plotline, dict):
            windowed.append(plotline)
            continue
        milestones = plotline.get("milestones")
        if not isinstance(milestones, list):
            windowed.append(plotline)
            continue
        total = len(milestones)
        next_plotline = dict(plotline)
        next_plotline["milestones"] = milestones[offset:offset + limit]
        next_plotline["milestones_total"] = total
        next_plotline["milestones_offset"] = offset
        next_plotline["milestones_limit"] = limit
        next_plotline["milestones_has_more"] = offset + len(next_plotline["milestones"]) < total
        windowed.append(next_plotline)
    return windowed


def _json_array_window(
    db: Session,
    table_name: str,
    column_name: str,
    row_id: str,
    offset: int,
    limit: int,
) -> list[Any]:
    rows = (
        db.execute(
            text(
                f"""
                SELECT item.value AS value
                FROM {table_name}, json_each({table_name}.{column_name}) AS item
                WHERE {table_name}.id = :row_id
                ORDER BY CAST(item.key AS INTEGER)
                LIMIT :limit OFFSET :offset
                """
            ),
            {"row_id": row_id, "limit": limit, "offset": offset},
        )
        .mappings()
        .all()
    )
    return [_decode_json_value(row["value"]) for row in rows]


def _decode_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


@router.post("/evolution/plan/generate")
async def generate_evolution_plan(
    project_id: str,
    target: str = "outline",
    db: Session = Depends(get_db),
):
    if target == "storyline":
        from app.api.storylines import generate_storyline
        return await generate_storyline(project_id, db)
    from app.api.outlines import generate_outline
    return await generate_outline(project_id, db)


@router.get("/evolution/proposals")
def get_evolution_proposals(
    project_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    bundle_status: str | None = None,
    item_status: str | None = None,
    db: Session = Depends(get_db),
):
    from app.api.world_model import list_world_proposal_bundles
    return list_world_proposal_bundles(project_id, offset, limit, bundle_status, item_status, None, db)


@router.get("/evolution/proposal-review-queue", response_model=ProposalReviewQueueOut)
def get_evolution_proposal_review_queue(
    project_id: str,
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    from app.api.world_model import get_world_model_proposal_review_queue
    return get_world_model_proposal_review_queue(project_id, limit, db)


@router.get("/evolution/proposals/{bundle_id}")
def get_evolution_proposal_detail(
    project_id: str,
    bundle_id: str,
    item_offset: int = Query(0, ge=0),
    item_limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    from app.api.world_model import get_world_proposal_bundle
    return get_world_proposal_bundle(
        project_id=project_id,
        bundle_id=bundle_id,
        item_offset=item_offset,
        item_limit=item_limit,
        db=db,
    )


@router.post("/evolution/proposals/{proposal_item_id}/review")
def review_evolution_proposal(
    project_id: str,
    proposal_item_id: str,
    payload: ProposalReviewCreate,
    db: Session = Depends(get_db),
):
    from app.api.world_model import review_world_proposal_item
    return review_world_proposal_item(project_id, proposal_item_id, payload, db)


@router.post("/evolution/proposals/{bundle_id}/split")
def split_evolution_proposal(
    project_id: str,
    bundle_id: str,
    payload: ProposalBundleSplitCreate,
    db: Session = Depends(get_db),
):
    from app.api.world_model import split_world_proposal_bundle
    return split_world_proposal_bundle(project_id, bundle_id, payload, db)


@router.post("/evolution/reviews/{review_id}/rollback")
def rollback_evolution_review(
    project_id: str,
    review_id: str,
    payload: ProposalReviewRollbackCreate,
    db: Session = Depends(get_db),
):
    from app.api.world_model import rollback_world_proposal_review
    return rollback_world_proposal_review(project_id, review_id, payload, db)


@router.get("/evolution/consistency")
def get_evolution_consistency(project_id: str, db: Session = Depends(get_db)):
    from app.api.consistency import list_issues
    return list_issues(project_id, db)


@router.post("/evolution/consistency/chapters/{chapter_index}/check")
async def check_evolution_consistency(
    project_id: str,
    chapter_index: int,
    depth: str = "l1",
    db: Session = Depends(get_db),
):
    from app.api.consistency import run_check
    return await run_check(project_id, chapter_index, depth, db)


@router.post("/evolution/chapters/{chapter_index}/analyze")
def analyze_evolution_chapter(
    project_id: str,
    chapter_index: int,
    db: Session = Depends(get_db),
):
    return analyze_chapter_to_world_proposals(db=db, project_id=project_id, chapter_index=chapter_index)


@router.patch("/evolution/plan/outline/chapters/{chapter_index}")
def update_evolution_chapter_outline(
    project_id: str,
    chapter_index: int,
    payload: ChapterOutlineUpdate,
    db: Session = Depends(get_db),
):
    from app.api.outlines import update_chapter_outline
    return update_chapter_outline(project_id, chapter_index, payload, db)


@router.get("/context/chapter/{chapter_index}")
def get_chapter_context(project_id: str, chapter_index: int, db: Session = Depends(get_db)):
    return build_chapter_context_package(db=db, project_id=project_id, chapter_index=chapter_index)

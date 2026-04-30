from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.athena_shared import require_project
from app.api.outlines import ChapterOutlineUpdate
from app.core.athena_longform import analyze_chapter_to_world_proposals, build_chapter_context_package
from app.db import get_db
from app.models import Outline, Storyline
from app.schemas import ProposalBundleSplitCreate, ProposalReviewCreate, ProposalReviewRollbackCreate

router = APIRouter()


@router.get("/evolution/plan")
def get_evolution_plan(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    outline = db.query(Outline).filter(Outline.project_id == project_id).first()
    storyline = db.query(Storyline).filter(Storyline.project_id == project_id).first()
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


@router.get("/evolution/proposals/{bundle_id}")
def get_evolution_proposal_detail(project_id: str, bundle_id: str, db: Session = Depends(get_db)):
    from app.api.world_model import get_world_proposal_bundle
    return get_world_proposal_bundle(project_id, bundle_id, db)


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

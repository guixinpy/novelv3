from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.api.athena_shared import require_project
from app.api.outlines import ChapterOutlineUpdate
from app.core.athena_longform import analyze_chapter_to_world_proposals, build_chapter_context_package
from app.core.narrative_plan_window import get_evolution_plan_window
from app.db import get_db
from app.models import Outline, Storyline
from app.schemas import ProposalBundleSplitCreate, ProposalReviewCreate, ProposalReviewRollbackCreate
from app.schemas.world_proposals import ProposalReviewQueueOut
from app.services.writing_agent.api_control_plane import AgentApiToolRunResult, execute_agent_api_tool

router = APIRouter()
ATHENA_EVOLUTION_AGENT_CONTROL_PLANE_VERSION = "phase68.athena_evolution_agent.v1"
ATHENA_EVOLUTION_GENERATE_ENTRYPOINT = "athena_evolution_plan_generate"
LEGACY_GENERATION_400_ERRORS = {
    "API key not configured",
    "Setup not generated yet",
    "Storyline not generated yet",
}


@router.get("/evolution/plan")
def get_evolution_plan(
    project_id: str,
    mode: str = Query("window", pattern="^(full|window)$"),
    chapter_offset: int = Query(0, ge=0),
    chapter_limit: int = Query(100, ge=1, le=500),
    plotline_offset: int = Query(0, ge=0),
    plotline_limit: int = Query(20, ge=1, le=500),
    milestone_offset: int = Query(0, ge=0),
    milestone_limit: int = Query(80, ge=1, le=500),
    foreshadowing_offset: int = Query(0, ge=0),
    foreshadowing_limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    require_project(db, project_id)
    if mode == "window":
        return get_evolution_plan_window(
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


@router.post("/evolution/plan/generate")
async def generate_evolution_plan(
    project_id: str,
    target: str = "outline",
    response_mode: str = Query("window", pattern="^(full|window)$"),
    db: Session = Depends(get_db),
):
    require_project(db, project_id)
    if target == "storyline":
        result = await _execute_evolution_generate_tool(db, project_id, target="storyline")
        _raise_if_agent_generation_failed(result, fallback_error="Agent storyline generation failed")
        if response_mode == "full":
            generated = db.query(Storyline).filter(Storyline.project_id == project_id).order_by(Storyline.updated_at.desc()).first()
            return _with_agent_metadata(generated, result=result, target=target)
        return _with_agent_metadata(get_evolution_plan_window(db=db, project_id=project_id)["storyline"], result=result, target=target)
    result = await _execute_evolution_generate_tool(db, project_id, target="outline")
    _raise_if_agent_generation_failed(result, fallback_error="Agent outline generation failed")
    if response_mode == "full":
        generated = db.query(Outline).filter(Outline.project_id == project_id).order_by(Outline.updated_at.desc()).first()
        return _with_agent_metadata(generated, result=result, target=target)
    return _with_agent_metadata(get_evolution_plan_window(db=db, project_id=project_id)["outline"], result=result, target=target)


async def _execute_evolution_generate_tool(
    db: Session,
    project_id: str,
    *,
    target: str,
) -> AgentApiToolRunResult:
    if target == "storyline":
        return await execute_agent_api_tool(
            db,
            project_id=project_id,
            entrypoint=ATHENA_EVOLUTION_GENERATE_ENTRYPOINT,
            version=ATHENA_EVOLUTION_AGENT_CONTROL_PLANE_VERSION,
            source=ATHENA_EVOLUTION_GENERATE_ENTRYPOINT,
            action_type="generate_storyline",
            tool_name="generate_storyline",
            goal="通过 Athena 叙事脉络入口生成故事线",
            extra_control_plane={"target": "storyline"},
        )
    return await execute_agent_api_tool(
        db,
        project_id=project_id,
        entrypoint=ATHENA_EVOLUTION_GENERATE_ENTRYPOINT,
        version=ATHENA_EVOLUTION_AGENT_CONTROL_PLANE_VERSION,
        source=ATHENA_EVOLUTION_GENERATE_ENTRYPOINT,
        action_type="generate_outline",
        tool_name="generate_outline",
        goal="通过 Athena 叙事脉络入口生成章节大纲",
        extra_control_plane={"target": "outline"},
    )


def _raise_if_agent_generation_failed(result: AgentApiToolRunResult, *, fallback_error: str) -> None:
    if result.run.status == "success":
        return
    detail = result.run.error or fallback_error
    status_code = 400 if detail in LEGACY_GENERATION_400_ERRORS else 500
    raise HTTPException(status_code=status_code, detail=detail)


def _with_agent_metadata(payload, *, result: AgentApiToolRunResult, target: str) -> dict:
    body = jsonable_encoder(payload)
    if body is None:
        raise HTTPException(status_code=500, detail=f"Agent {target} generation completed without output")
    body["agent_run_id"] = result.run.id
    body["control_plane"] = result.control_plane
    return body


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
    offset: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    from app.api.world_model import get_world_model_proposal_review_queue
    return get_world_model_proposal_review_queue(project_id=project_id, offset=offset, limit=limit, db=db)


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
def get_evolution_consistency(
    project_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    from app.api.consistency import list_issues
    return list_issues(project_id=project_id, offset=offset, limit=limit, db=db, response=None)


@router.post("/evolution/consistency/chapters/{chapter_index}/check")
async def check_evolution_consistency(
    project_id: str,
    chapter_index: int = Path(..., ge=1),
    depth: str = "l1",
    db: Session = Depends(get_db),
):
    from app.api.consistency import run_check
    return await run_check(project_id, chapter_index, depth, db)


@router.post("/evolution/chapters/{chapter_index}/analyze")
def analyze_evolution_chapter(
    project_id: str,
    chapter_index: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return analyze_chapter_to_world_proposals(db=db, project_id=project_id, chapter_index=chapter_index)


@router.patch("/evolution/plan/outline/chapters/{chapter_index}")
def update_evolution_chapter_outline(
    project_id: str,
    payload: ChapterOutlineUpdate,
    chapter_index: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    from app.api.outlines import update_chapter_outline
    return update_chapter_outline(project_id, chapter_index, payload, db)


@router.get("/context/chapter/{chapter_index}")
def get_chapter_context(project_id: str, chapter_index: int = Path(..., ge=1), db: Session = Depends(get_db)):
    return build_chapter_context_package(db=db, project_id=project_id, chapter_index=chapter_index)

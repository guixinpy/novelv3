import time

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import String, func
from sqlalchemy.orm import Session

from app.api.deprecation import add_deprecation_header
from app.config import load_api_key
from app.core.ai_service import AIService
from app.core.model_call_trace import create_trace, mark_trace_failed, mark_trace_success, now_ms
from app.core.narrative_plan_window import get_evolution_plan_window
from app.db import get_db
from app.models import Project, Setup, Storyline
from app.prompting.assembler import build_generation_payload
from app.prompting.providers.storyline import (
    SETUP_CHARACTERS_CONTEXT_CHARS,
    SETUP_CORE_CONCEPT_CONTEXT_CHARS,
    SETUP_WORLD_CONTEXT_CHARS,
    SetupContextSnapshot,
    build_storyline_context_blocks,
    build_storyline_variables,
)
from app.schemas import StorylineOut

router = APIRouter(prefix="/api/v1/projects/{project_id}/storyline", tags=["storylines"])
ai_service = AIService()


def _get_storyline_setup_context(db: Session, project_id: str) -> SetupContextSnapshot | None:
    row = (
        db.query(
            Setup.id,
            func.substr(func.cast(Setup.world_building, String), 1, SETUP_WORLD_CONTEXT_CHARS + 1).label("world_building"),
            func.substr(func.cast(Setup.characters, String), 1, SETUP_CHARACTERS_CONTEXT_CHARS + 1).label("characters"),
            func.substr(func.cast(Setup.core_concept, String), 1, SETUP_CORE_CONCEPT_CONTEXT_CHARS + 1).label("core_concept"),
        )
        .filter(Setup.project_id == project_id)
        .first()
    )
    if not row:
        return None
    return SetupContextSnapshot(
        world_building=row.world_building or "{}",
        characters=row.characters or "[]",
        core_concept=row.core_concept or "{}",
    )


def _build_storyline_call_payload(
    project: Project,
    setup: Setup | SetupContextSnapshot,
    command_args: str | None = None,
) -> dict:
    variables = build_storyline_variables(project, setup)
    return build_generation_payload(
        "storyline.generate",
        variables,
        trace_context_blocks=lambda rendered_prompt: build_storyline_context_blocks(
            setup,
            rendered_prompt=rendered_prompt,
            command_args=command_args,
        ),
        command_args=command_args,
    )


@router.post("/generate", response_model=StorylineOut)
async def generate_storyline(project_id: str, db: Session = Depends(get_db), command_args: str | None = None, response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/plan/generate?target=storyline")
    if not load_api_key():
        raise HTTPException(status_code=400, detail="API key not configured")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    setup = _get_storyline_setup_context(db, project_id)
    if not setup:
        raise HTTPException(status_code=400, detail="Setup not generated yet")

    payload = _build_storyline_call_payload(project, setup, command_args=command_args)
    trace = create_trace(
        db,
        project_id=project.id,
        trace_type="storyline_generation",
        messages=payload["messages"],
        context_blocks=payload["context_blocks"],
        trace_metadata=payload["trace_metadata"],
        model=project.ai_model or "deepseek-chat",
        temperature=0.7,
        max_tokens=payload["max_tokens"],
    )
    db.commit()

    started_at = now_ms()
    start = time.time()
    try:
        result = await ai_service.complete(
            payload["messages"],
            temperature=0.7,
            max_tokens=payload["max_tokens"],
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        mark_trace_failed(db, trace, error_message=str(exc), latency_ms=now_ms() - started_at)
        db.commit()
        raise
    try:
        data = ai_service.parse_json(result.content)
    except Exception as exc:
        mark_trace_failed(db, trace, error_message=str(exc), latency_ms=now_ms() - started_at)
        db.commit()
        raise

    storyline = Storyline(
        project_id=project_id,
        plotlines=data.get("plotlines", []),
        foreshadowing=data.get("foreshadowing", []),
        status="generated",
    )

    existing = db.query(Storyline).filter(Storyline.project_id == project_id).first()
    if existing:
        db.delete(existing)

    db.add(storyline)
    project.status = "storyline_generated"
    project.current_phase = "storyline"
    mark_trace_success(
        db,
        trace,
        prompt_tokens=getattr(result, "prompt_tokens", 0),
        completion_tokens=getattr(result, "completion_tokens", 0),
        latency_ms=int((time.time() - start) * 1000),
    )

    try:
        db.commit()
        db.refresh(storyline)
    except Exception:
        db.rollback()
        raise

    return storyline


@router.get("", response_model=StorylineOut)
def get_storyline(
    project_id: str,
    mode: str = Query("window", pattern="^(full|window)$"),
    plotline_offset: int = Query(0, ge=0),
    plotline_limit: int = Query(20, ge=1, le=500),
    milestone_offset: int = Query(0, ge=0),
    milestone_limit: int = Query(80, ge=1, le=500),
    foreshadowing_offset: int = Query(0, ge=0),
    foreshadowing_limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    response: Response = None,
):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/plan")
    if mode == "window":
        storyline = get_evolution_plan_window(
            db=db,
            project_id=project_id,
            plotline_offset=plotline_offset,
            plotline_limit=plotline_limit,
            milestone_offset=milestone_offset,
            milestone_limit=milestone_limit,
            foreshadowing_offset=foreshadowing_offset,
            foreshadowing_limit=foreshadowing_limit,
        )["storyline"]
        if not storyline:
            raise HTTPException(status_code=404, detail="Storyline not found")
        return storyline
    storyline = db.query(Storyline).filter(Storyline.project_id == project_id).first()
    if not storyline:
        raise HTTPException(status_code=404, detail="Storyline not found")
    return storyline

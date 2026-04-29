import time

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deprecation import add_deprecation_header
from app.config import load_api_key
from app.core.ai_service import AIService
from app.core.model_call_trace import create_trace, mark_trace_failed, mark_trace_success, now_ms
from app.db import get_db
from app.models import Outline, Project, Setup, Storyline
from app.prompting.assembler import build_generation_payload
from app.prompting.providers.outline import build_outline_context_blocks, build_outline_variables, target_total_chapters
from app.schemas import OutlineOut

router = APIRouter(prefix="/api/v1/projects/{project_id}/outline", tags=["outlines"])
ai_service = AIService()


def _target_total_chapters(project: Project) -> int:
    return target_total_chapters(project)


def _build_outline_call_payload(project: Project, setup: Setup, storyline: Storyline, command_args: str | None = None) -> dict:
    variables = build_outline_variables(project, setup, storyline)
    return build_generation_payload(
        "outline.generate",
        variables,
        trace_context_blocks=lambda rendered_prompt: build_outline_context_blocks(
            project,
            setup,
            storyline,
            rendered_prompt=rendered_prompt,
            command_args=command_args,
        ),
        command_args=command_args,
    )


@router.post("/generate", response_model=OutlineOut)
async def generate_outline(project_id: str, db: Session = Depends(get_db), command_args: str | None = None, response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/plan/generate?target=outline")
    if not load_api_key():
        raise HTTPException(status_code=400, detail="API key not configured")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    storyline = db.query(Storyline).filter(Storyline.project_id == project_id).first()
    if not storyline:
        raise HTTPException(status_code=400, detail="Storyline not generated yet")
    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    if not setup:
        raise HTTPException(status_code=400, detail="Setup not generated yet")

    payload = _build_outline_call_payload(project, setup, storyline, command_args=command_args)
    trace = create_trace(
        db,
        project_id=project.id,
        trace_type="outline_generation",
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

    outline = Outline(
        project_id=project_id,
        total_chapters=data.get("total_chapters", 0),
        chapters=data.get("chapters", []),
        plotlines=data.get("plotlines", []),
        foreshadowing=data.get("foreshadowing", []),
        status="generated",
    )

    existing = db.query(Outline).filter(Outline.project_id == project_id).first()
    if existing:
        db.delete(existing)

    db.add(outline)
    project.status = "outline_generated"
    project.current_phase = "outline"
    mark_trace_success(
        db,
        trace,
        prompt_tokens=getattr(result, "prompt_tokens", 0),
        completion_tokens=getattr(result, "completion_tokens", 0),
        latency_ms=int((time.time() - start) * 1000),
    )

    try:
        db.commit()
        db.refresh(outline)
    except Exception:
        db.rollback()
        raise

    return outline


@router.get("", response_model=OutlineOut)
def get_outline(project_id: str, db: Session = Depends(get_db), response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/plan")
    outline = db.query(Outline).filter(Outline.project_id == project_id).first()
    if not outline:
        raise HTTPException(status_code=404, detail="Outline not found")
    return outline


from pydantic import BaseModel


class ChapterOutlineUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    scenes: list[str] | None = None
    characters: list[str] | None = None
    purpose: str | None = None


@router.patch("/chapters/{chapter_index}")
def update_chapter_outline(project_id: str, chapter_index: int, payload: ChapterOutlineUpdate, db: Session = Depends(get_db), response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/plan/outline/chapters/{chapter_index}")
    outline = db.query(Outline).filter(Outline.project_id == project_id).first()
    if not outline:
        raise HTTPException(status_code=404, detail="Outline not found")

    chapters = outline.chapters or []
    found = False
    for ch in chapters:
        if ch.get("chapter_index") == chapter_index:
            if payload.title is not None:
                ch["title"] = payload.title
            if payload.summary is not None:
                ch["summary"] = payload.summary
            if payload.scenes is not None:
                ch["scenes"] = payload.scenes
            if payload.characters is not None:
                ch["characters"] = payload.characters
            if payload.purpose is not None:
                ch["purpose"] = payload.purpose
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Chapter not found in outline")

    from sqlalchemy.orm.attributes import flag_modified
    outline.chapters = chapters
    flag_modified(outline, "chapters")
    db.commit()
    return {"updated": True, "chapter_index": chapter_index}

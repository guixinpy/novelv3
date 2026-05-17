import time

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deprecation import add_deprecation_header
from app.config import load_api_key
from app.core.ai_service import AIService
from app.core.model_call_trace import create_trace, mark_trace_failed, mark_trace_success, now_ms
from app.db import get_db
from app.models import Project, Setup
from app.prompting.assembler import build_generation_payload
from app.prompting.providers.setup import build_setup_context_blocks, build_setup_variables
from app.schemas import SetupOut

router = APIRouter(prefix="/api/v1/projects/{project_id}/setup", tags=["setups"])

ai_service = AIService()


def _build_setup_call_payload(project: Project, command_args: str | None = None) -> dict:
    variables = build_setup_variables(project)
    return build_generation_payload(
        "setup.generate",
        variables,
        trace_context_blocks=lambda rendered_prompt: build_setup_context_blocks(
            project,
            rendered_prompt=rendered_prompt,
            command_args=command_args,
        ),
        command_args=command_args,
    )


@router.post("/generate", response_model=SetupOut)
async def generate_setup(project_id: str, db: Session = Depends(get_db), command_args: str | None = None, response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/ontology/generate")
    if not load_api_key():
        raise HTTPException(status_code=400, detail="API key not configured")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    existing = db.query(Setup).filter(Setup.project_id == project_id).first()

    payload = _build_setup_call_payload(project, command_args=command_args)
    trace = create_trace(
        db,
        project_id=project.id,
        trace_type="setup_generation",
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
            model=project.ai_model or "deepseek-chat",
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

    setup = Setup(
        project_id=project_id,
        world_building=data.get("world_building", {}),
        characters=data.get("characters", []),
        core_concept=data.get("core_concept", {}),
        status="generated",
    )

    if existing:
        db.delete(existing)

    db.add(setup)
    project.status = "setup_approved"
    project.current_phase = "setup"
    mark_trace_success(
        db,
        trace,
        prompt_tokens=getattr(result, "prompt_tokens", 0),
        completion_tokens=getattr(result, "completion_tokens", 0),
        latency_ms=int((time.time() - start) * 1000),
    )

    try:
        db.commit()
        db.refresh(setup)
    except Exception:
        db.rollback()
        raise

    return setup


@router.get("", response_model=SetupOut)
def get_setup(project_id: str, db: Session = Depends(get_db), response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/ontology")
    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    if not setup:
        raise HTTPException(status_code=404, detail="Setup not found")
    return setup

import json
import time

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deprecation import add_deprecation_header
from app.config import load_api_key
from app.core.ai_service import AIService
from app.core.model_call_trace import build_context_block, create_trace, mark_trace_failed, mark_trace_success, now_ms
from app.core.prompt_manager import PromptManager
from app.db import get_db
from app.models import Project, Setup, Storyline
from app.schemas import StorylineOut

router = APIRouter(prefix="/api/v1/projects/{project_id}/storyline", tags=["storylines"])
ai_service = AIService()


def _build_storyline_call_payload(project: Project, setup: Setup, command_args: str | None = None) -> dict:
    world_building = json.dumps(setup.world_building, ensure_ascii=False)
    characters = json.dumps(setup.characters, ensure_ascii=False)
    core_concept = json.dumps(setup.core_concept, ensure_ascii=False)
    pm = PromptManager()
    prompt_template = pm.load(
        "generate_storyline",
        {
            "name": project.name,
            "genre": project.genre,
            "world_building": world_building,
            "characters": characters,
            "core_concept": core_concept,
        },
    )
    prompt = prompt_template
    context_blocks = [
        build_context_block(key="setup_world_building", kind="setup", title="世界观", content=world_building),
        build_context_block(key="setup_characters", kind="setup", title="角色", content=characters),
        build_context_block(key="setup_core_concept", kind="setup", title="核心概念", content=core_concept),
        build_context_block(
            key="generate_storyline_template",
            kind="prompt_template",
            title="故事线生成模板",
            content=prompt_template,
        ),
    ]
    if command_args and command_args.strip():
        extra = command_args.strip()
        prompt = f"{prompt}\n\n附加要求：{extra}"
        context_blocks.append(
            build_context_block(
                key="command_args",
                kind="user_feedback",
                title="用户附加要求",
                content=extra,
            )
        )
    return {
        "messages": [{"role": "user", "content": prompt}],
        "context_blocks": context_blocks,
        "max_tokens": 4000,
    }


@router.post("/generate", response_model=StorylineOut)
async def generate_storyline(project_id: str, db: Session = Depends(get_db), command_args: str | None = None, response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/plan/generate?target=storyline")
    if not load_api_key():
        raise HTTPException(status_code=400, detail="API key not configured")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    if not setup:
        raise HTTPException(status_code=400, detail="Setup not generated yet")

    payload = _build_storyline_call_payload(project, setup, command_args=command_args)
    trace = create_trace(
        db,
        project_id=project.id,
        trace_type="storyline_generation",
        messages=payload["messages"],
        context_blocks=payload["context_blocks"],
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
def get_storyline(project_id: str, db: Session = Depends(get_db), response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/plan")
    storyline = db.query(Storyline).filter(Storyline.project_id == project_id).first()
    if not storyline:
        raise HTTPException(status_code=404, detail="Storyline not found")
    return storyline

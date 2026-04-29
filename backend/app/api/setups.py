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
from app.models import Project, Setup
from app.schemas import SetupOut

router = APIRouter(prefix="/api/v1/projects/{project_id}/setup", tags=["setups"])

ai_service = AIService()


def _build_setup_call_payload(project: Project, command_args: str | None = None) -> dict:
    pm = PromptManager()
    prompt_template = pm.load(
        "generate_setup",
        {
            "name": project.name,
            "genre": project.genre,
            "description": project.description,
            "style": project.style,
            "complexity": project.complexity,
        },
    )
    prompt = prompt_template
    context_blocks = [
        build_context_block(
            key="project_profile",
            kind="project",
            title="项目基础信息",
            content=json.dumps(
                {
                    "name": project.name,
                    "genre": project.genre,
                    "description": project.description,
                    "style": project.style,
                    "complexity": project.complexity,
                    "target_chapter_count": project.target_chapter_count,
                    "target_word_count": project.target_word_count,
                    "language": project.language,
                },
                ensure_ascii=False,
            ),
        ),
        build_context_block(
            key="generate_setup_template",
            kind="prompt_template",
            title="设定生成模板",
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

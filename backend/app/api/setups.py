import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Project, Setup
from app.schemas import SetupOut
from app.config import load_api_key
from app.core.ai_service import AIService
from app.core.prompt_manager import PromptManager

router = APIRouter(prefix="/api/v1/projects/{project_id}/setup", tags=["setups"])

ai_service = AIService()


@router.post("/generate", response_model=SetupOut)
async def generate_setup(project_id: str, db: Session = Depends(get_db), command_args: str | None = None):
    if not load_api_key():
        raise HTTPException(status_code=400, detail="API key not configured")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    existing = db.query(Setup).filter(Setup.project_id == project_id).first()

    pm = PromptManager()
    prompt = pm.load(
        "generate_setup",
        {
            "name": project.name,
            "genre": project.genre,
            "description": project.description,
            "style": project.style,
            "complexity": project.complexity,
        },
    )
    if command_args and command_args.strip():
        prompt = f"{prompt}\n\n附加要求：{command_args.strip()}"

    result = await ai_service.complete(
        [{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4000,
        response_format={"type": "json_object"},
    )
    data = ai_service.parse_json(result.content)

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

    try:
        db.commit()
        db.refresh(setup)
    except Exception:
        db.rollback()
        raise

    return setup


@router.get("", response_model=SetupOut)
def get_setup(project_id: str, db: Session = Depends(get_db)):
    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    if not setup:
        raise HTTPException(status_code=404, detail="Setup not found")
    return setup

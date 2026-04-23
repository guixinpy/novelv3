import json

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deprecation import add_deprecation_header
from app.config import load_api_key
from app.core.ai_service import AIService
from app.core.prompt_manager import PromptManager
from app.db import get_db
from app.models import Project, Setup, Storyline
from app.schemas import StorylineOut

router = APIRouter(prefix="/api/v1/projects/{project_id}/storyline", tags=["storylines"])
ai_service = AIService()


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

    pm = PromptManager()
    prompt = pm.load(
        "generate_storyline",
        {
            "name": project.name,
            "genre": project.genre,
            "world_building": json.dumps(setup.world_building, ensure_ascii=False),
            "characters": json.dumps(setup.characters, ensure_ascii=False),
            "core_concept": json.dumps(setup.core_concept, ensure_ascii=False),
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

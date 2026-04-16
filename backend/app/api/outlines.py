import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Project, Storyline, Outline
from app.schemas import OutlineOut
from app.core.ai_service import AIService
from app.core.prompt_manager import PromptManager
from app.config import load_api_key

router = APIRouter(prefix="/api/v1/projects/{project_id}/outline", tags=["outlines"])
ai_service = AIService()


@router.post("/generate", response_model=OutlineOut)
async def generate_outline(project_id: str, db: Session = Depends(get_db)):
    if not load_api_key():
        raise HTTPException(status_code=400, detail="API key not configured")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    storyline = db.query(Storyline).filter(Storyline.project_id == project_id).first()
    if not storyline:
        raise HTTPException(status_code=400, detail="Storyline not generated yet")

    pm = PromptManager()
    prompt = pm.load(
        "generate_outline",
        {
            "name": project.name,
            "storyline": json.dumps({"plotlines": storyline.plotlines, "foreshadowing": storyline.foreshadowing}, ensure_ascii=False),
            "total_chapters": project.target_word_count // 3000 or 10,
        },
    )

    result = await ai_service.complete(
        [{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4000,
    )
    data = ai_service.parse_json(result.content)

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

    try:
        db.commit()
        db.refresh(outline)
    except Exception:
        db.rollback()
        raise

    return outline


@router.get("", response_model=OutlineOut)
def get_outline(project_id: str, db: Session = Depends(get_db)):
    outline = db.query(Outline).filter(Outline.project_id == project_id).first()
    if not outline:
        raise HTTPException(status_code=404, detail="Outline not found")
    return outline

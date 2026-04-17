from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db import get_db
from app.models import Project

router = APIRouter(prefix="/api/v1/projects/{project_id}/preferences", tags=["preferences"])

DEFAULT_CONFIG = {
    "description_density": 3,
    "dialogue_ratio": 3,
    "pacing_speed": 3,
    "tone_preferences": [],
}


class PreferenceUpdate(BaseModel):
    description_density: int = 3
    dialogue_ratio: int = 3
    pacing_speed: int = 3
    tone_preferences: list[str] = []


@router.get("")
def get_preferences(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    config = project.style_config or DEFAULT_CONFIG
    return {"config": config, "updated_at": project.updated_at.isoformat() if project.updated_at else None}


@router.put("")
def update_preferences(project_id: str, payload: PreferenceUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.style_config = payload.model_dump()
    db.commit()
    return {"config": project.style_config}


@router.post("/reset")
def reset_preferences(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.style_config = DEFAULT_CONFIG.copy()
    db.commit()
    return {"config": project.style_config}

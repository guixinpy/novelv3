import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Project, Setup, Storyline, Outline, ChapterContent, Dialog, DialogMessage, PendingAction
from app.schemas import ChatOut, ChatIn, ResolveActionIn, ProjectDiagnosisOut, PendingActionOut, ChatMessageOut
from app.core.ai_service import AIService
from app.core.prompt_manager import PromptManager
from app.config import load_api_key

router = APIRouter(tags=["dialogs"])
ai_service = AIService()


def _get_or_create_dialog(db: Session, project_id: str) -> Dialog:
    dialog = db.query(Dialog).filter(Dialog.project_id == project_id).first()
    if not dialog:
        dialog = Dialog(project_id=project_id)
        db.add(dialog)
        db.commit()
        db.refresh(dialog)
    return dialog


def _build_diagnosis(db: Session, project_id: str) -> ProjectDiagnosisOut:
    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    storyline = db.query(Storyline).filter(Storyline.project_id == project_id).first()
    outline = db.query(Outline).filter(Outline.project_id == project_id).first()
    chapters = db.query(ChapterContent).filter(ChapterContent.project_id == project_id).count()

    completed = []
    missing = []
    next_step = None

    if setup and setup.status == "generated":
        completed.append("setup")
    else:
        missing.append("setup")
        next_step = "preview_setup"

    if storyline and storyline.status == "generated":
        completed.append("storyline")
    else:
        missing.append("storyline")
        if not next_step:
            next_step = "preview_storyline"

    if outline and outline.status == "generated":
        completed.append("outline")
    else:
        missing.append("outline")
        if not next_step:
            next_step = "preview_outline"

    if chapters > 0:
        completed.append("content")
    else:
        missing.append("content")
        if not next_step:
            next_step = "preview_outline"

    return ProjectDiagnosisOut(
        missing_items=missing,
        completed_items=completed,
        suggested_next_step=next_step,
    )


@router.get("/api/v1/projects/{project_id}/state-diagnosis")
def state_diagnosis(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _build_diagnosis(db, project_id)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import delete, inspect
from app.db import get_db
from app.models import (
    BackgroundTask,
    ChapterContent,
    ConsistencyCheck,
    Dialog,
    DialogMessage,
    ExtractedFact,
    Outline,
    PendingAction,
    Project,
    PromptRule,
    Setup,
    Storyline,
    Topology,
    Version,
)
from app.schemas import ProjectCreate, ProjectUpdate, ProjectOut

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

PROJECT_SCOPED_MODELS = (
    Setup,
    Storyline,
    Outline,
    ChapterContent,
    Topology,
    ConsistencyCheck,
    ExtractedFact,
    BackgroundTask,
    Version,
    PromptRule,
)


@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    inspector = inspect(db.bind)
    existing_tables = set(inspector.get_table_names())

    dialog_ids = [
        dialog_id
        for (dialog_id,) in db.query(Dialog.id).filter(Dialog.project_id == project_id).all()
    ]

    if dialog_ids:
        if DialogMessage.__tablename__ in existing_tables:
            db.execute(delete(DialogMessage).where(DialogMessage.dialog_id.in_(dialog_ids)))
        if PendingAction.__tablename__ in existing_tables:
            db.execute(delete(PendingAction).where(PendingAction.dialog_id.in_(dialog_ids)))
        if Dialog.__tablename__ in existing_tables:
            db.execute(delete(Dialog).where(Dialog.id.in_(dialog_ids)))

    for model in PROJECT_SCOPED_MODELS:
        if model.__tablename__ not in existing_tables:
            continue
        db.execute(delete(model).where(model.project_id == project_id))

    db.delete(project)
    db.commit()
    return {"deleted": True}

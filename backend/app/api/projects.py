from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, inspect, text, update
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    AIModelCallTrace,
    BackgroundTask,
    ChapterContent,
    ChapterRevision,
    ConsistencyCheck,
    Dialog,
    DialogMessage,
    ExtractedFact,
    GenreProfile,
    Outline,
    PendingAction,
    Project,
    ProjectProfileVersion,
    PromptRule,
    RetrievalChunk,
    RetrievalDocument,
    RetrievalEmbedding,
    RevisionAnnotation,
    RevisionCorrection,
    Setup,
    Storyline,
    Topology,
    Version,
    WorldArtifact,
    WorldCharacter,
    WorldEvent,
    WorldEvidence,
    WorldFactClaim,
    WorldFaction,
    WorldLocation,
    WorldProposalBundle,
    WorldProposalImpactScopeSnapshot,
    WorldProposalItem,
    WorldProposalReview,
    WorldRelation,
    WorldResource,
    WorldRule,
    WorldTimelineAnchor,
)
from app.schemas import ProjectCreate, ProjectOut, ProjectUpdate, WorkspaceBootstrapOut
from app.services.workspace.bootstrap import WorkspaceBootstrapService

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

SETUP_IMPORT_PROFILE_PREFIX = "project-setup-import"
PROJECT_PROFILE_VERSION_DELETE_TRIGGER = "trg_project_profile_versions_append_only_delete"
PROJECT_PROFILE_VERSION_DELETE_TRIGGER_SQL = """
CREATE TRIGGER IF NOT EXISTS trg_project_profile_versions_append_only_delete
BEFORE DELETE ON project_profile_versions
BEGIN
    SELECT RAISE(ABORT, 'project_profile_versions is append-only');
END;
"""

PROJECT_SCOPED_MODELS = (
    RetrievalEmbedding,
    RetrievalChunk,
    RetrievalDocument,
    WorldProposalReview,
    WorldProposalImpactScopeSnapshot,
    WorldProposalItem,
    WorldProposalBundle,
    WorldFactClaim,
    WorldEvidence,
    WorldEvent,
    WorldTimelineAnchor,
    WorldRelation,
    WorldCharacter,
    WorldLocation,
    WorldFaction,
    WorldArtifact,
    WorldResource,
    WorldRule,
    ProjectProfileVersion,
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


@router.get("/{project_id}/workspace-bootstrap", response_model=WorkspaceBootstrapOut)
def workspace_bootstrap(project_id: str, db: Session = Depends(get_db)):
    payload = WorkspaceBootstrapService(db).build(project_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Project not found")
    return payload


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

    if AIModelCallTrace.__tablename__ in existing_tables:
        db.execute(delete(AIModelCallTrace).where(AIModelCallTrace.project_id == project_id))

    if dialog_ids:
        if DialogMessage.__tablename__ in existing_tables:
            db.execute(delete(DialogMessage).where(DialogMessage.dialog_id.in_(dialog_ids)))
        if PendingAction.__tablename__ in existing_tables:
            db.execute(delete(PendingAction).where(PendingAction.dialog_id.in_(dialog_ids)))
        if Dialog.__tablename__ in existing_tables:
            db.execute(delete(Dialog).where(Dialog.id.in_(dialog_ids)))

    revision_ids = [
        revision_id
        for (revision_id,) in db.query(ChapterRevision.id).filter(ChapterRevision.project_id == project_id).all()
    ] if ChapterRevision.__tablename__ in existing_tables else []
    if revision_ids:
        if RevisionAnnotation.__tablename__ in existing_tables:
            db.execute(delete(RevisionAnnotation).where(RevisionAnnotation.revision_id.in_(revision_ids)))
        if RevisionCorrection.__tablename__ in existing_tables:
            db.execute(delete(RevisionCorrection).where(RevisionCorrection.revision_id.in_(revision_ids)))
        db.execute(delete(ChapterRevision).where(ChapterRevision.id.in_(revision_ids)))

    profile_delete_guard_dropped = _drop_project_profile_version_delete_guard(db, existing_tables)
    try:
        _clear_world_model_self_references(db, project_id, existing_tables)
        for model in PROJECT_SCOPED_MODELS:
            if model.__tablename__ not in existing_tables:
                continue
            db.execute(delete(model).where(model.project_id == project_id))
        if GenreProfile.__tablename__ in existing_tables:
            db.execute(
                delete(GenreProfile).where(
                    GenreProfile.canonical_id == f"{SETUP_IMPORT_PROFILE_PREFIX}.{project_id}"
                )
            )
        db.delete(project)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        if profile_delete_guard_dropped:
            _restore_project_profile_version_delete_guard(db)
    return {"deleted": True}


def _clear_world_model_self_references(db: Session, project_id: str, existing_tables: set[str]) -> None:
    if WorldProposalReview.__tablename__ in existing_tables:
        db.execute(
            update(WorldProposalReview)
            .where(WorldProposalReview.project_id == project_id)
            .values(rollback_to_review_id=None)
        )
    if WorldProposalItem.__tablename__ in existing_tables:
        db.execute(
            update(WorldProposalItem)
            .where(WorldProposalItem.project_id == project_id)
            .values(parent_item_id=None)
        )
    if WorldProposalBundle.__tablename__ in existing_tables:
        db.execute(
            update(WorldProposalBundle)
            .where(WorldProposalBundle.project_id == project_id)
            .values(parent_bundle_id=None)
        )
    if WorldEvent.__tablename__ in existing_tables:
        db.execute(
            update(WorldEvent)
            .where(WorldEvent.project_id == project_id)
            .values(supersedes_event_ref=None)
        )


def _drop_project_profile_version_delete_guard(db: Session, existing_tables: set[str]) -> bool:
    if ProjectProfileVersion.__tablename__ not in existing_tables:
        return False
    if db.bind is None or db.bind.dialect.name != "sqlite":
        return False
    db.execute(text(f"DROP TRIGGER IF EXISTS {PROJECT_PROFILE_VERSION_DELETE_TRIGGER}"))
    return True


def _restore_project_profile_version_delete_guard(db: Session) -> None:
    try:
        db.execute(text(PROJECT_PROFILE_VERSION_DELETE_TRIGGER_SQL))
        db.commit()
    except Exception:
        db.rollback()
        raise

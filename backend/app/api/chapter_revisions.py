from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.chapters import create_or_replace_chapter
from app.core.revision_feedback import format_revision_feedback
from app.core.self_optimization import apply_revision_optimization
from app.db import get_db
from app.models import ChapterContent, ChapterRevision, Dialog, DialogMessage, Project, RevisionAnnotation, RevisionCorrection, Version
from app.schemas import ChapterOut
from app.schemas.chapter_revision import ChapterRevisionCreate, ChapterRevisionDraftUpdate, ChapterRevisionOut

router = APIRouter(prefix="/api/v1/projects/{project_id}/revisions", tags=["chapter-revisions"])


def _get_or_create_hermes_dialog(db: Session, project_id: str) -> Dialog:
    dialog = db.query(Dialog).filter(Dialog.project_id == project_id, Dialog.dialog_type == "hermes").first()
    if dialog:
        return dialog
    dialog = Dialog(project_id=project_id, dialog_type="hermes")
    db.add(dialog)
    db.flush()
    return dialog


def _persist_regeneration_messages(db: Session, project_id: str, revision: ChapterRevision, chapter: ChapterContent) -> None:
    dialog = _get_or_create_hermes_dialog(db, project_id)
    existing = db.query(DialogMessage).filter(
        DialogMessage.dialog_id == dialog.id,
        DialogMessage.meta["revision_id"].as_string() == revision.id,
    ).first()
    if existing:
        return
    db.add(
        DialogMessage(
            dialog_id=dialog.id,
            role="user",
            content=f"提交修订 {revision.id}，请根据批注和修正重新生成章节。",
            meta={"revision_id": revision.id, "chapter_index": revision.chapter_index},
        )
    )
    db.add(
        DialogMessage(
            dialog_id=dialog.id,
            role="assistant",
            content=f"已根据修订反馈重新生成第 {chapter.chapter_index} 章。",
            meta={"revision_id": revision.id, "chapter_id": chapter.id, "chapter_index": chapter.chapter_index},
            action_result={"type": "regenerate_revision", "status": "success"},
        )
    )


def _next_revision_index(db: Session, project_id: str, chapter_index: int) -> int:
    latest_revision_index = db.query(func.max(ChapterRevision.revision_index)).filter(
        ChapterRevision.project_id == project_id,
        ChapterRevision.chapter_index == chapter_index,
    ).scalar() or 0
    return latest_revision_index + 1


def _next_version_number(db: Session, project_id: str, node_type: str, node_id: str) -> int:
    max_num = db.query(func.max(Version.version_number)).filter(
        Version.project_id == project_id,
        Version.node_type == node_type,
        Version.node_id == node_id,
    ).scalar() or 0
    return max_num + 1


def _create_chapter_version(db: Session, chapter: ChapterContent, description: str, author: str) -> Version:
    version = Version(
        project_id=chapter.project_id,
        node_type="chapter",
        node_id=chapter.id,
        version_number=_next_version_number(db, chapter.project_id, "chapter", chapter.id),
        content=chapter.content,
        description=description,
        author=author,
    )
    db.add(version)
    db.flush()
    return version


def _get_open_revision(db: Session, project_id: str, chapter_index: int) -> ChapterRevision | None:
    return (
        db.query(ChapterRevision)
        .filter(
            ChapterRevision.project_id == project_id,
            ChapterRevision.chapter_index == chapter_index,
            ChapterRevision.status.in_(["draft", "submitted", "failed"]),
        )
        .order_by(ChapterRevision.revision_index.desc())
        .first()
    )


def _replace_revision_feedback(db: Session, revision: ChapterRevision, payload: ChapterRevisionDraftUpdate | ChapterRevisionCreate) -> None:
    db.query(RevisionAnnotation).filter(RevisionAnnotation.revision_id == revision.id).delete()
    db.query(RevisionCorrection).filter(RevisionCorrection.revision_id == revision.id).delete()
    for item in payload.annotations:
        db.add(RevisionAnnotation(revision_id=revision.id, **item.model_dump()))
    for item in payload.corrections:
        db.add(RevisionCorrection(revision_id=revision.id, **item.model_dump()))


def _ensure_base_version(db: Session, revision: ChapterRevision) -> None:
    if revision.base_version_id:
        return
    chapter = db.query(ChapterContent).filter(ChapterContent.id == revision.chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    version = _create_chapter_version(
        db,
        chapter,
        description=f"Revision {revision.revision_index} base before regeneration",
        author="user",
    )
    revision.base_version_id = version.id


def _revision_out(db: Session, revision: ChapterRevision) -> ChapterRevisionOut:
    annotations = db.query(RevisionAnnotation).filter(RevisionAnnotation.revision_id == revision.id).all()
    corrections = db.query(RevisionCorrection).filter(RevisionCorrection.revision_id == revision.id).all()
    return ChapterRevisionOut.model_validate(
        {
            "id": revision.id,
            "project_id": revision.project_id,
            "chapter_id": revision.chapter_id,
            "chapter_index": revision.chapter_index,
            "revision_index": revision.revision_index,
            "status": revision.status,
            "submitted_at": revision.submitted_at,
            "completed_at": revision.completed_at,
            "base_version_id": revision.base_version_id,
            "result_version_id": revision.result_version_id,
            "annotations": annotations,
            "corrections": corrections,
        }
    )


@router.post("", response_model=ChapterRevisionOut)
def submit_revision(project_id: str, payload: ChapterRevisionCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    chapter = db.query(ChapterContent).filter(
        ChapterContent.project_id == project_id,
        ChapterContent.chapter_index == payload.chapter_index,
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    latest_revision_index = db.query(func.max(ChapterRevision.revision_index)).filter(
        ChapterRevision.project_id == project_id,
        ChapterRevision.chapter_index == payload.chapter_index,
    ).scalar() or 0
    revision = ChapterRevision(
        project_id=project_id,
        chapter_id=chapter.id,
        chapter_index=payload.chapter_index,
        revision_index=latest_revision_index + 1,
        status="submitted",
        submitted_at=datetime.now(UTC),
    )
    db.add(revision)
    db.flush()

    _replace_revision_feedback(db, revision, payload)
    _ensure_base_version(db, revision)

    db.commit()
    db.refresh(revision)
    apply_revision_optimization(
        db,
        project,
        annotations=[item.model_dump() for item in payload.annotations],
        corrections=[item.model_dump() for item in payload.corrections],
    )
    return _revision_out(db, revision)


@router.get("/chapters/{chapter_index}/active", response_model=ChapterRevisionOut | None)
def get_active_revision(project_id: str, chapter_index: int, db: Session = Depends(get_db)):
    revision = _get_open_revision(db, project_id, chapter_index)
    if not revision:
        return None
    return _revision_out(db, revision)


@router.put("/chapters/{chapter_index}/draft", response_model=ChapterRevisionOut | None)
def save_revision_draft(project_id: str, chapter_index: int, payload: ChapterRevisionDraftUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    chapter = db.query(ChapterContent).filter(
        ChapterContent.project_id == project_id,
        ChapterContent.chapter_index == chapter_index,
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    revision = _get_open_revision(db, project_id, chapter_index)
    if not payload.annotations and not payload.corrections:
        if revision and revision.status in ["draft", "submitted", "failed"]:
            db.query(RevisionAnnotation).filter(RevisionAnnotation.revision_id == revision.id).delete()
            db.query(RevisionCorrection).filter(RevisionCorrection.revision_id == revision.id).delete()
            db.delete(revision)
            db.commit()
        return None

    if not revision:
        revision = ChapterRevision(
            project_id=project_id,
            chapter_id=chapter.id,
            chapter_index=chapter_index,
            revision_index=_next_revision_index(db, project_id, chapter_index),
            status="draft",
        )
        db.add(revision)
        db.flush()
    else:
        revision.chapter_id = chapter.id
        revision.status = "draft"
        revision.submitted_at = None
        revision.completed_at = None

    _replace_revision_feedback(db, revision, payload)
    db.commit()
    db.refresh(revision)
    return _revision_out(db, revision)


@router.post("/{revision_id}/submit", response_model=ChapterRevisionOut)
def submit_revision_draft(project_id: str, revision_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    revision = db.query(ChapterRevision).filter(
        ChapterRevision.project_id == project_id,
        ChapterRevision.id == revision_id,
    ).first()
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found")
    if revision.status == "completed":
        raise HTTPException(status_code=400, detail="Completed revision cannot be submitted again")
    annotations = db.query(RevisionAnnotation).filter(RevisionAnnotation.revision_id == revision.id).all()
    corrections = db.query(RevisionCorrection).filter(RevisionCorrection.revision_id == revision.id).all()
    if not annotations and not corrections:
        raise HTTPException(status_code=422, detail="revision feedback cannot be empty")
    annotation_payloads = [
        {
            "paragraph_index": item.paragraph_index,
            "start_offset": item.start_offset,
            "end_offset": item.end_offset,
            "selected_text": item.selected_text,
            "comment": item.comment,
        }
        for item in annotations
    ]
    correction_payloads = [
        {
            "paragraph_index": item.paragraph_index,
            "original_text": item.original_text,
            "corrected_text": item.corrected_text,
        }
        for item in corrections
    ]
    _ensure_base_version(db, revision)
    revision.status = "submitted"
    revision.submitted_at = datetime.now(UTC)
    revision.completed_at = None
    db.commit()
    db.refresh(revision)
    apply_revision_optimization(db, project, annotations=annotation_payloads, corrections=correction_payloads)
    return _revision_out(db, revision)


@router.get("", response_model=list[ChapterRevisionOut])
def list_revisions(project_id: str, db: Session = Depends(get_db)):
    revisions = db.query(ChapterRevision).filter(ChapterRevision.project_id == project_id).order_by(
        ChapterRevision.chapter_index.asc(),
        ChapterRevision.revision_index.asc(),
    ).all()
    return [_revision_out(db, revision) for revision in revisions]


@router.get("/{revision_id}", response_model=ChapterRevisionOut)
def get_revision(project_id: str, revision_id: str, db: Session = Depends(get_db)):
    revision = db.query(ChapterRevision).filter(
        ChapterRevision.project_id == project_id,
        ChapterRevision.id == revision_id,
    ).first()
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found")
    return _revision_out(db, revision)


@router.post("/{revision_id}/regenerate", response_model=ChapterOut)
async def regenerate_revision(project_id: str, revision_id: str, db: Session = Depends(get_db)):
    revision = db.query(ChapterRevision).filter(
        ChapterRevision.project_id == project_id,
        ChapterRevision.id == revision_id,
    ).first()
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found")
    if revision.status == "completed":
        chapter = db.query(ChapterContent).filter(ChapterContent.id == revision.chapter_id).first()
        if chapter:
            return chapter

    annotations = db.query(RevisionAnnotation).filter(RevisionAnnotation.revision_id == revision.id).all()
    corrections = db.query(RevisionCorrection).filter(RevisionCorrection.revision_id == revision.id).all()
    feedback = format_revision_feedback(
        annotations=[
            {
                "paragraph_index": item.paragraph_index,
                "selected_text": item.selected_text,
                "comment": item.comment,
            }
            for item in annotations
        ],
        corrections=[
            {
                "paragraph_index": item.paragraph_index,
                "original_text": item.original_text,
                "corrected_text": item.corrected_text,
            }
            for item in corrections
        ],
    )

    try:
        _ensure_base_version(db, revision)
        chapter = await create_or_replace_chapter(db, project_id, revision.chapter_index, extra_feedback=feedback)
    except Exception as exc:
        db.rollback()
        revision = db.query(ChapterRevision).filter(ChapterRevision.id == revision_id).first()
        if revision:
            revision.status = "failed"
            revision.completed_at = datetime.now(UTC)
            db.commit()
        raise HTTPException(status_code=500, detail=f"Revision regeneration failed: {exc}") from exc
    result_version = _create_chapter_version(
        db,
        chapter,
        description=f"Revision {revision.revision_index} regenerated result",
        author="ai_system",
    )
    revision.status = "completed"
    revision.completed_at = datetime.now(UTC)
    revision.chapter_id = chapter.id
    revision.result_version_id = result_version.id
    _persist_regeneration_messages(db, project_id, revision, chapter)
    db.commit()
    db.refresh(chapter)
    return chapter

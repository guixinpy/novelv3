from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ChapterContent, Outline, Project, Setup, Storyline, Version
from app.schemas import ProjectDiagnosisOut
from app.services.dialog.messages import DEFAULT_MESSAGE_CONTENT_PREVIEW_CHARS, DialogMessageService
from app.services.writing.writing_state_service import WritingStateService

CHAPTER_BOOTSTRAP_LIMIT = 200
VERSION_BOOTSTRAP_LIMIT = 50
DIALOG_BOOTSTRAP_MESSAGE_CONTENT_LIMIT = DEFAULT_MESSAGE_CONTENT_PREVIEW_CHARS


def build_project_diagnosis(db: Session, project_id: str) -> ProjectDiagnosisOut:
    setup_status = db.query(Setup.status).filter(Setup.project_id == project_id).scalar()
    storyline_status = db.query(Storyline.status).filter(Storyline.project_id == project_id).scalar()
    outline_status = db.query(Outline.status).filter(Outline.project_id == project_id).scalar()
    chapters = db.query(func.count(ChapterContent.id)).filter(ChapterContent.project_id == project_id).scalar() or 0

    completed = []
    missing = []
    next_step = None

    if setup_status == "generated":
        completed.append("setup")
    else:
        missing.append("setup")
        next_step = "preview_setup"

    if storyline_status == "generated":
        completed.append("storyline")
    else:
        missing.append("storyline")
        if not next_step:
            next_step = "preview_storyline"

    if outline_status == "generated":
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


class WorkspaceBootstrapService:
    def __init__(self, db: Session):
        self.db = db
        self.messages = DialogMessageService(db)

    def build(self, project_id: str) -> dict | None:
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None

        chapter_filters = [ChapterContent.project_id == project_id]
        chapters_total = self.db.query(func.count(ChapterContent.id)).filter(*chapter_filters).scalar() or 0
        chapters_latest_index = self.db.query(func.max(ChapterContent.chapter_index)).filter(*chapter_filters).scalar()
        chapters = (
            self.db.query(
                ChapterContent.id,
                ChapterContent.chapter_index,
                ChapterContent.title,
                ChapterContent.word_count,
                ChapterContent.status,
            )
            .filter(*chapter_filters)
            .order_by(ChapterContent.chapter_index)
            .limit(CHAPTER_BOOTSTRAP_LIMIT)
            .all()
        )
        setup_row = (
            self.db.query(
                Setup.id,
                Setup.project_id,
                Setup.status,
                Setup.created_at,
                Setup.updated_at,
            )
            .filter(Setup.project_id == project_id)
            .first()
        )
        setup = _setup_bootstrap_summary(setup_row) if setup_row else None
        storyline_row = (
            self.db.query(
                Storyline.id,
                Storyline.project_id,
                Storyline.status,
                Storyline.created_at,
                Storyline.updated_at,
                func.coalesce(func.json_array_length(Storyline.plotlines), 0).label("plotlines_count"),
                func.coalesce(func.json_array_length(Storyline.foreshadowing), 0).label("foreshadowing_count"),
            )
            .filter(Storyline.project_id == project_id)
            .first()
        )
        storyline = _storyline_bootstrap_summary(storyline_row) if storyline_row else None
        outline_row = (
            self.db.query(
                Outline.id,
                Outline.project_id,
                Outline.total_chapters,
                Outline.status,
                Outline.created_at,
                Outline.updated_at,
            )
            .filter(Outline.project_id == project_id)
            .first()
        )
        outline = _outline_bootstrap_summary(outline_row) if outline_row else None
        versions_total = self.db.query(func.count(Version.id)).filter(Version.project_id == project_id).scalar() or 0
        versions = (
            self.db.query(
                Version.id,
                Version.version_number,
                Version.node_type,
                Version.node_id,
                Version.description,
                Version.author,
                Version.created_at,
            )
            .filter(Version.project_id == project_id)
            .order_by(Version.created_at.desc(), Version.version_number.desc(), Version.id.desc())
            .limit(VERSION_BOOTSTRAP_LIMIT)
            .all()
        )

        return {
            "project": project,
            "diagnosis": build_project_diagnosis(self.db, project_id),
            "setup": setup,
            "setup_partial": setup is not None,
            "storyline": storyline,
            "storyline_partial": storyline is not None,
            "outline": outline,
            "outline_partial": outline is not None,
            "chapters": [
                {
                    "id": chapter.id,
                    "chapter_index": chapter.chapter_index,
                    "title": chapter.title or f"第{chapter.chapter_index}章",
                    "word_count": chapter.word_count or 0,
                    "status": chapter.status or "generated",
                }
                for chapter in chapters
            ],
            "chapters_total": chapters_total,
            "chapters_offset": 0,
            "chapters_limit": CHAPTER_BOOTSTRAP_LIMIT,
            "chapters_has_more": len(chapters) < chapters_total,
            "chapters_latest_index": chapters_latest_index,
            "versions": [
                {
                    "id": version.id,
                    "version_number": version.version_number,
                    "node_type": version.node_type,
                    "node_id": version.node_id,
                    "description": version.description,
                    "author": version.author,
                    "created_at": version.created_at,
                }
                for version in versions
            ],
            "versions_total": versions_total,
            "versions_offset": 0,
            "versions_limit": VERSION_BOOTSTRAP_LIMIT,
            "versions_has_more": len(versions) < versions_total,
            "writing_state": WritingStateService(self.db).state(project_id).model_dump(exclude_none=True),
            "dialogs": {
                "hermes": {
                    "messages": self.messages.list_messages(
                        project_id,
                        dialog_type="hermes",
                        limit=80,
                        max_content_chars=DIALOG_BOOTSTRAP_MESSAGE_CONTENT_LIMIT,
                    )
                },
                "athena": {
                    "messages": self.messages.list_messages(
                        project_id,
                        dialog_type="athena",
                        limit=80,
                        max_content_chars=DIALOG_BOOTSTRAP_MESSAGE_CONTENT_LIMIT,
                    )
                },
            },
        }


def _setup_bootstrap_summary(row) -> dict:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "world_building": {},
        "characters": [],
        "core_concept": {},
        "status": row.status,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _storyline_bootstrap_summary(row) -> dict:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "plotlines": [],
        "foreshadowing": [],
        "plotlines_count": int(row.plotlines_count or 0),
        "foreshadowing_count": int(row.foreshadowing_count or 0),
        "status": row.status,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _outline_bootstrap_summary(row) -> dict:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "total_chapters": row.total_chapters or 0,
        "chapters": [],
        "plotlines": [],
        "foreshadowing": [],
        "status": row.status,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }

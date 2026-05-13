from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ChapterContent, Outline, Project, Setup, Storyline, Version
from app.schemas import ProjectDiagnosisOut
from app.services.dialog.messages import DialogMessageService

CHAPTER_BOOTSTRAP_LIMIT = 200


def build_project_diagnosis(db: Session, project_id: str) -> ProjectDiagnosisOut:
    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    storyline = db.query(Storyline).filter(Storyline.project_id == project_id).first()
    outline = db.query(Outline).filter(Outline.project_id == project_id).first()
    chapters = db.query(func.count(ChapterContent.id)).filter(ChapterContent.project_id == project_id).scalar() or 0

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
        setup = self.db.query(Setup).filter(Setup.project_id == project_id).first()
        storyline = self.db.query(Storyline).filter(Storyline.project_id == project_id).first()
        outline = self.db.query(Outline).filter(Outline.project_id == project_id).first()
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
            .order_by(Version.created_at.desc())
            .limit(20)
            .all()
        )

        return {
            "project": project,
            "diagnosis": build_project_diagnosis(self.db, project_id),
            "setup": setup,
            "storyline": storyline,
            "outline": outline,
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
            "dialogs": {
                "hermes": {"messages": self.messages.list_messages(project_id, dialog_type="hermes", limit=80)},
                "athena": {"messages": self.messages.list_messages(project_id, dialog_type="athena", limit=80)},
            },
        }

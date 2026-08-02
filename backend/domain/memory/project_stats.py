from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ChapterContent, Project


def chapter_word_count_sum(db: Session, project_id: str) -> int:
    total = (
        db.query(func.coalesce(func.sum(ChapterContent.word_count), 0))
        .filter(ChapterContent.project_id == project_id)
        .scalar()
    )
    return int(total or 0)


def reconcile_project_word_count(db: Session, project: Project, *, commit: bool = True) -> Project:
    total = chapter_word_count_sum(db, project.id)
    if (project.current_word_count or 0) != total:
        project.current_word_count = total
        if commit:
            db.commit()
            db.refresh(project)
        else:
            db.flush()
    return project

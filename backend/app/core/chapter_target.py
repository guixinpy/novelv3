from sqlalchemy.orm import Session

from app.models import Outline, Project


def effective_chapter_target(db: Session, project: Project) -> int:
    project_target = int(project.target_chapter_count or 0)
    if project_target > 0:
        return project_target
    outline_total = (
        db.query(Outline.total_chapters)
        .filter(Outline.project_id == project.id, Outline.total_chapters > 0)
        .order_by(Outline.created_at.desc(), Outline.id.desc())
        .limit(1)
        .scalar()
    )
    return int(outline_total or 0)


def chapter_index_exceeds_target(db: Session, project: Project, chapter_index: int) -> bool:
    target = effective_chapter_target(db, project)
    return target > 0 and int(chapter_index or 0) > target

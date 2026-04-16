from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Project, ChapterContent, Setup, ConsistencyCheck
from app.schemas import ConsistencyIssueOut
from app.core.consistency_checker import ConsistencyChecker

router = APIRouter(prefix="/api/v1/projects/{project_id}/consistency", tags=["consistency"])


@router.post("/chapters/{chapter_index}/check")
def run_check(project_id: str, chapter_index: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    chapter = db.query(ChapterContent).filter(
        ChapterContent.project_id == project_id,
        ChapterContent.chapter_index == chapter_index,
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    checker = ConsistencyChecker()
    issues = checker.check(project_id, chapter, setup)

    db.query(ConsistencyCheck).filter(
        ConsistencyCheck.project_id == project_id,
        ConsistencyCheck.chapter_index == chapter_index,
    ).delete()

    for issue in issues:
        db.add(ConsistencyCheck(**issue))

    db.commit()

    return {"issues": issues}


@router.get("/issues", response_model=list[ConsistencyIssueOut])
def list_issues(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return db.query(ConsistencyCheck).filter(ConsistencyCheck.project_id == project_id).all()

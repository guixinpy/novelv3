import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deprecation import add_deprecation_header
from app.core.consistency_checker import ConsistencyChecker
from app.db import get_db
from app.models import BackgroundTask, ChapterContent, ConsistencyCheck, Project, Setup
from app.schemas import ConsistencyIssueOut

router = APIRouter(prefix="/api/v1/projects/{project_id}/consistency", tags=["consistency"])


@router.post("/chapters/{chapter_index}/check")
async def run_check(project_id: str, chapter_index: int, depth: str = "l1", db: Session = Depends(get_db), response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/consistency/chapters/{chapter_index}/check")
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    chapter = db.query(ChapterContent).filter(
        ChapterContent.project_id == project_id,
        ChapterContent.chapter_index == chapter_index,
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    if depth == "l2":
        task = BackgroundTask(
            project_id=project_id,
            task_type="consistency_deep_check",
            payload={"chapter_index": chapter_index},
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        async def _run_deep():
            from app.core.background_analyzer import BackgroundAnalyzer
            from app.db import SessionLocal
            dbs = SessionLocal()
            try:
                t = dbs.query(BackgroundTask).filter(BackgroundTask.id == task.id).first()
                t.status = "running"
                t.started_at = datetime.now(UTC)
                dbs.commit()

                analyzer = BackgroundAnalyzer()
                result = await analyzer.run_deep_check(project_id, chapter_index)

                t = dbs.query(BackgroundTask).filter(BackgroundTask.id == task.id).first()
                t.status = "completed"
                t.result = result
                t.finished_at = datetime.now(UTC)
                dbs.commit()
            except Exception as e:
                t = dbs.query(BackgroundTask).filter(BackgroundTask.id == task.id).first()
                t.status = "failed"
                t.error = str(e)
                t.finished_at = datetime.now(UTC)
                dbs.commit()
            finally:
                dbs.close()

        asyncio.ensure_future(_run_deep())
        return {"task_id": task.id, "status": "pending"}

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
def list_issues(project_id: str, db: Session = Depends(get_db), response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/consistency")
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return db.query(ConsistencyCheck).filter(ConsistencyCheck.project_id == project_id).all()

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.writing_scheduler import WritingScheduler
from app.db import get_db
from app.models import BackgroundTask, Project
from app.schemas import WritingStateOut
from app.services.tasks.background_task_service import BackgroundTaskService
from app.services.tasks.local_task_runner import LocalTaskRunner

router = APIRouter(prefix="/api/v1/projects/{project_id}/writing", tags=["writing"])
scheduler = WritingScheduler()


@router.post("/start", response_model=WritingStateOut)
def start_writing(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return scheduler.start(project_id, db)


@router.post("/pause", response_model=WritingStateOut)
def pause_writing(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return scheduler.pause(project_id, db)


@router.post("/resume", response_model=WritingStateOut)
def resume_writing(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return scheduler.resume(project_id, db)


@router.post("/chapters/{chapter_index}/retry", response_model=WritingStateOut)
async def retry_chapter(project_id: str, chapter_index: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    task = BackgroundTaskService(db).create(
        project_id=project_id,
        task_type="retry_chapter",
        payload={"chapter_index": chapter_index},
    )

    async def _regen(rdb: Session, running_task: BackgroundTask):
        from app.api.chapters import generate_chapter as _gen_chapter

        chapter = await _gen_chapter(project_id, chapter_index, rdb)
        return {"chapter_index": chapter.chapter_index}

    LocalTaskRunner().start(task.id, _regen)
    return scheduler.state(project_id, db)

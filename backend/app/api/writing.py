from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.writing_scheduler import WritingScheduler
from app.db import get_db
from app.models import BackgroundTask, Project
from app.schemas import WritingStateOut
from app.services.tasks.background_task_service import BackgroundTaskService
from app.services.tasks.local_task_runner import LocalTaskRunner
from app.services.writing.writing_state_service import WritingStateService

router = APIRouter(prefix="/api/v1/projects/{project_id}/writing", tags=["writing"])
scheduler = WritingScheduler()


@router.post("/start", response_model=WritingStateOut)
async def start_writing(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    state = scheduler.start(project_id, db)
    _queue_generate_chapter_task(db, project_id, state.current_chapter)
    return state


@router.post("/pause", response_model=WritingStateOut)
def pause_writing(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return scheduler.pause(project_id, db)


@router.post("/resume", response_model=WritingStateOut)
async def resume_writing(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    state = scheduler.resume(project_id, db)
    if state.status == "running":
        _queue_generate_chapter_task(db, project_id, state.current_chapter)
    return state


@router.get("/state", response_model=WritingStateOut)
def get_writing_state(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return scheduler.state(project_id, db)


def build_retry_chapter_work(project_id: str, chapter_index: int):
    async def _regen(rdb: Session, running_task: BackgroundTask):
        from app.api.chapters import generate_chapter as _gen_chapter

        try:
            chapter = await _gen_chapter(project_id, chapter_index, rdb)
        except Exception as exc:
            WritingStateService(rdb).mark_error(project_id, str(exc))
            raise

        WritingStateService(rdb).complete_chapter(project_id, chapter_index)
        generated_index = chapter.get("chapter_index") if isinstance(chapter, dict) else chapter.chapter_index
        return {"chapter_index": generated_index}

    return _regen


def build_generate_chapter_work(project_id: str, chapter_index: int):
    async def _generate(rdb: Session, running_task: BackgroundTask):
        from app.api.chapters import generate_chapter as _gen_chapter

        try:
            chapter = await _gen_chapter(project_id, chapter_index, rdb)
        except Exception as exc:
            WritingStateService(rdb).mark_error(project_id, str(exc))
            raise

        generated_index = chapter.get("chapter_index") if isinstance(chapter, dict) else chapter.chapter_index
        return {"chapter_index": generated_index}

    return _generate


def _queue_generate_chapter_task(db: Session, project_id: str, chapter_index: int) -> BackgroundTask:
    task = BackgroundTaskService(db).create(
        project_id=project_id,
        task_type="generate_chapter",
        payload={"chapter_index": chapter_index},
    )
    LocalTaskRunner().start(task.id, build_generate_chapter_work(project_id, chapter_index))
    return task


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

    LocalTaskRunner().start(task.id, build_retry_chapter_work(project_id, chapter_index))
    return scheduler.run_chapter(project_id, chapter_index, db)

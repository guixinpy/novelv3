from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.writing_scheduler import WritingScheduler
from app.db import get_db
from app.models import BackgroundTask, Project
from app.schemas import WritingControlOut, WritingStateOut
from app.services.tasks.background_task_service import ACTIVE_TASK_STATUSES, BackgroundTaskService
from app.services.tasks.local_task_runner import LocalTaskRunner
from app.services.writing.writing_state_service import WritingStateService

router = APIRouter(prefix="/api/v1/projects/{project_id}/writing", tags=["writing"])
scheduler = WritingScheduler()


@router.post("/start", response_model=WritingControlOut, response_model_exclude_none=True)
async def start_writing(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    state = scheduler.start(project_id, db)
    task = _queue_generate_chapter_task(db, project_id, state.current_chapter)
    return _control_out(state, task)


@router.post("/pause", response_model=WritingStateOut)
def pause_writing(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return scheduler.pause(project_id, db)


@router.post("/resume", response_model=WritingControlOut, response_model_exclude_none=True)
async def resume_writing(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    state = scheduler.resume(project_id, db)
    if state.status == "running":
        task = _queue_generate_chapter_task(db, project_id, state.current_chapter)
        return _control_out(state, task)
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
    active_task = (
        db.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == project_id,
            BackgroundTask.task_type == "generate_chapter",
            BackgroundTask.status.in_(ACTIVE_TASK_STATUSES),
            BackgroundTask.payload["chapter_index"].as_integer() == int(chapter_index),
        )
        .order_by(BackgroundTask.created_at.desc(), BackgroundTask.id.desc())
        .first()
    )
    if active_task:
        return active_task

    task = BackgroundTaskService(db).create(
        project_id=project_id,
        task_type="generate_chapter",
        payload={"chapter_index": chapter_index},
    )
    LocalTaskRunner().start(task.id, build_generate_chapter_work(project_id, chapter_index))
    return task


def _control_out(state: WritingStateOut, task: BackgroundTask) -> WritingControlOut:
    return WritingControlOut(**state.model_dump(), task_id=task.id)


@router.post("/chapters/{chapter_index}/retry", response_model=WritingControlOut, response_model_exclude_none=True)
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
    state = scheduler.run_chapter(project_id, chapter_index, db)
    return _control_out(state, task)

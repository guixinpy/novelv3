from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.writing_scheduler import WritingScheduler
from app.db import get_db
from app.models import Project
from app.schemas import WritingStateOut

router = APIRouter(prefix="/api/v1/projects/{project_id}/writing", tags=["writing"])
scheduler = WritingScheduler()


@router.post("/start", response_model=WritingStateOut)
def start_writing(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return scheduler.start(project_id)


@router.post("/pause", response_model=WritingStateOut)
def pause_writing(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return scheduler.pause(project_id)


@router.post("/resume", response_model=WritingStateOut)
def resume_writing(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return scheduler.resume(project_id)


@router.post("/chapters/{chapter_index}/retry", response_model=WritingStateOut)
async def retry_chapter(project_id: str, chapter_index: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Trigger chapter regeneration in background
    import asyncio

    from app.api.chapters import generate_chapter as _gen_chapter
    from app.db import SessionLocal

    async def _regen():
        rdb = SessionLocal()
        try:
            await _gen_chapter(project_id, chapter_index, rdb)
        except Exception:
            pass
        finally:
            rdb.close()

    asyncio.ensure_future(_regen())
    return scheduler.state(project_id)

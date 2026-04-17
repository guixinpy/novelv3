from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Project, BackgroundTask
from app.core.ui_hints import build_ui_hint, action_to_refresh_targets

router = APIRouter(tags=["background-tasks"])


@router.get("/api/v1/projects/{project_id}/background-tasks")
def list_background_tasks(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    tasks = db.query(BackgroundTask).filter(BackgroundTask.project_id == project_id).order_by(BackgroundTask.created_at.desc()).limit(20).all()
    return {"tasks": [{"task_id": t.id, "task_type": t.task_type, "status": t.status, "created_at": t.created_at.isoformat() if t.created_at else None, "started_at": t.started_at.isoformat() if t.started_at else None, "finished_at": t.finished_at.isoformat() if t.finished_at else None} for t in tasks]}


@router.get("/api/v1/background-tasks/{task_id}")
def get_background_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "result": task.result,
        "error": task.error,
        "ui_hint": build_ui_hint(
            action_type=task.task_type,
            dialog_state=(task.status or "idle").upper(),
            status=task.status or "pending",
        ),
        "refresh_targets": action_to_refresh_targets(task.task_type, task.status),
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }

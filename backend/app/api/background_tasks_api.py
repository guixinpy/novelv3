from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.ui_hints import action_to_refresh_targets, build_ui_hint, task_status_to_dialog_state
from app.db import get_db
from app.models import BackgroundTask, Project

router = APIRouter(tags=["background-tasks"])


def _compact_result(result: dict | None) -> dict | None:
    if not isinstance(result, dict):
        return None
    progress = result.get("progress")
    if not isinstance(progress, dict):
        return None
    return {"progress": progress}


def _compact_progress_result(db: Session, task_id: str, task_type: str, status: str) -> dict | None:
    if task_type != "generate_chapter" or status not in {"pending", "running"}:
        return None
    result = db.query(BackgroundTask.result).filter(BackgroundTask.id == task_id).scalar()
    return _compact_result(result)


@router.get("/api/v1/projects/{project_id}/background-tasks")
def list_background_tasks(
    project_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    total = (
        db.query(func.count(BackgroundTask.id))
        .filter(BackgroundTask.project_id == project_id)
        .scalar()
        or 0
    )
    tasks = (
        db.query(
            BackgroundTask.id,
            BackgroundTask.task_type,
            BackgroundTask.status,
            BackgroundTask.created_at,
            BackgroundTask.started_at,
            BackgroundTask.finished_at,
        )
        .filter(BackgroundTask.project_id == project_id)
        .order_by(BackgroundTask.created_at.desc(), BackgroundTask.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "tasks": [
            {
                "task_id": t.id,
                "task_type": t.task_type,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "started_at": t.started_at.isoformat() if t.started_at else None,
                "finished_at": t.finished_at.isoformat() if t.finished_at else None,
            }
            for t in tasks
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(tasks) < total,
    }


@router.get("/api/v1/background-tasks/{task_id}")
def get_background_task(
    task_id: str,
    compact: bool = Query(False),
    db: Session = Depends(get_db),
):
    if compact:
        task = (
            db.query(
                BackgroundTask.id,
                BackgroundTask.task_type,
                BackgroundTask.status,
                BackgroundTask.created_at,
                BackgroundTask.started_at,
                BackgroundTask.finished_at,
            )
            .filter(BackgroundTask.id == task_id)
            .first()
        )
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        error_preview = None
        if task.status in {"failed", "cancelled"}:
            error_preview = (
                db.query(func.substr(BackgroundTask.error, 1, 240))
                .filter(BackgroundTask.id == task_id)
                .scalar()
            )
        return {
            "task_id": task.id,
            "task_type": task.task_type,
            "status": task.status,
            "payload": None,
            "result": _compact_progress_result(db, task.id, task.task_type, task.status),
            "error": error_preview,
            "ui_hint": build_ui_hint(
                action_type=task.task_type,
                dialog_state=task_status_to_dialog_state(task.status),
                status=task.status or "pending",
                reason="后台任务状态更新",
            ),
            "refresh_targets": action_to_refresh_targets(task.task_type, task.status),
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        }

    task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "payload": task.payload or {},
        "result": task.result,
        "error": task.error,
        "ui_hint": build_ui_hint(
            action_type=task.task_type,
            dialog_state=task_status_to_dialog_state(task.status),
            status=task.status or "pending",
            reason="后台任务状态更新",
        ),
        "refresh_targets": action_to_refresh_targets(task.task_type, task.status),
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }

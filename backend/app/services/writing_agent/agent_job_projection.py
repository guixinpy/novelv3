from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import BackgroundTask, Project, WritingAgentRun
from app.services.tasks.background_task_service import BackgroundTaskService

AGENT_JOB_PROJECTION_VERSION = "phase75.agent_job_projection.v1"
DEFAULT_JOB_LIMIT = 20
MAX_JOB_LIMIT = 100
ERROR_PREVIEW_LIMIT = 240


def inspect_agent_job_projection(
    db: Session,
    project_id: str,
    *,
    task_id: str | None = None,
    task_type: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    _require_project(db, project_id)
    clamped_limit = _clamp_limit(limit)
    selected_task = _selected_task(db, project_id=project_id, task_id=task_id)
    if task_id and selected_task is None:
        return _json_safe_output(
            {
                "status": "not_found",
                "project_id": project_id,
                "selector": _selector(task_id=task_id, task_type=task_type, status=status),
                "summary": _summary(total=0, returned=0, limit=clamped_limit, by_status={}),
                "queue": _queue_projection([]),
                "tasks": [],
                "selected_task": None,
                "recommended_tools": ["inspect_agent_trace_audit"],
                "trace": _projection_trace_metadata(),
            }
        )

    query = _base_query(db, project_id)
    if task_type:
        query = query.filter(BackgroundTask.task_type == task_type)
    if status:
        query = query.filter(BackgroundTask.status == status)
    total = query.with_entities(func.count(BackgroundTask.id)).order_by(None).scalar() or 0
    tasks = query.order_by(BackgroundTask.created_at.desc(), BackgroundTask.id.desc()).limit(clamped_limit).all()
    by_status = _status_counts(tasks)
    selected_projection = _detailed_task(db, selected_task) if selected_task is not None else None
    recommended_tools = _recommended_tools(tasks=tasks, selected_task=selected_projection)
    return _json_safe_output(
        {
            "status": "completed",
            "project_id": project_id,
            "selector": _selector(task_id=task_id, task_type=task_type, status=status),
            "summary": _summary(total=int(total), returned=len(tasks), limit=clamped_limit, by_status=by_status),
            "queue": _queue_projection(tasks),
            "tasks": [_compact_task(task) for task in tasks],
            "selected_task": selected_projection,
            "recommended_tools": recommended_tools,
            "trace": _projection_trace_metadata(),
        }
    )


def _require_project(db: Session, project_id: str) -> None:
    if db.query(Project.id).filter(Project.id == project_id).first() is None:
        raise HTTPException(status_code=404, detail="Project not found")


def _base_query(db: Session, project_id: str):
    return db.query(BackgroundTask).filter(BackgroundTask.project_id == project_id)


def _selected_task(db: Session, *, project_id: str, task_id: str | None) -> BackgroundTask | None:
    if not task_id:
        return None
    return _base_query(db, project_id).filter(BackgroundTask.id == task_id).first()


def _selector(*, task_id: str | None, task_type: str | None, status: str | None) -> dict[str, str] | None:
    selector = {}
    if task_id:
        selector["task_id"] = task_id
    if task_type:
        selector["task_type"] = task_type
    if status:
        selector["status"] = status
    return selector or None


def _summary(*, total: int, returned: int, limit: int, by_status: dict[str, int]) -> dict[str, Any]:
    return {
        "total": total,
        "returned": returned,
        "limit": limit,
        "by_status": by_status,
    }


def _queue_projection(tasks: list[BackgroundTask]) -> dict[str, Any]:
    by_status = _status_counts(tasks)
    terminal = sum(by_status.get(status, 0) for status in ("completed", "failed", "cancelled"))
    return {
        "depth": len(tasks),
        "active": len(tasks) - terminal,
        "terminal": terminal,
        "by_status": by_status,
    }


def _status_counts(tasks: list[BackgroundTask]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in tasks:
        status = str(task.status or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _compact_task(task: BackgroundTask) -> dict[str, Any]:
    payload = task.payload if isinstance(task.payload, dict) else {}
    result = task.result if isinstance(task.result, dict) else {}
    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "chapter_index": payload.get("chapter_index"),
        "chapter_range": _chapter_range(payload),
        "control_plane": _control_plane(payload),
        "progress": _progress(result),
        "created_at": task.created_at,
        "started_at": task.started_at,
        "finished_at": task.finished_at,
    }


def _detailed_task(db: Session, task: BackgroundTask | None) -> dict[str, Any] | None:
    if task is None:
        return None
    payload = task.payload if isinstance(task.payload, dict) else {}
    result = task.result if isinstance(task.result, dict) else {}
    return {
        **_compact_task(task),
        "payload_summary": _payload_summary(payload),
        "result_summary": _result_summary(result),
        "resume": _resume_summary(db, task),
        "recovery": _recovery_summary(task),
        "agent_runs": _agent_runs_for_task(db, task),
        "error_preview": _error_preview(task.error),
    }


def _chapter_range(payload: dict[str, Any]) -> dict[str, Any] | None:
    chapter_range = payload.get("chapter_range")
    return chapter_range if isinstance(chapter_range, dict) else None


def _control_plane(payload: dict[str, Any]) -> dict[str, Any] | None:
    control_plane = payload.get("control_plane")
    return control_plane if isinstance(control_plane, dict) else None


def _progress(result: dict[str, Any]) -> dict[str, Any] | None:
    progress = result.get("progress")
    return progress if isinstance(progress, dict) else None


def _payload_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "keys": sorted(payload.keys()),
        "chapter_range": _chapter_range(payload),
        "has_control_plane": isinstance(payload.get("control_plane"), dict),
        "retry_of_task_id": payload.get("retry_of_task_id"),
        "resume_from_chapter_index": payload.get("resume_from_chapter_index"),
    }


def _result_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "keys": sorted(result.keys()),
        "has_progress": isinstance(result.get("progress"), dict),
        "agent_run_id": result.get("agent_run_id"),
        "agent_run_count": len(result.get("agent_runs") or []) if isinstance(result.get("agent_runs"), list) else 0,
    }


def _resume_summary(db: Session, task: BackgroundTask) -> dict[str, Any]:
    progress = _progress(task.result if isinstance(task.result, dict) else {})
    pending_chapter_indexes: list[int] = []
    if _chapter_range(task.payload if isinstance(task.payload, dict) else {}) is not None:
        try:
            pending_chapter_indexes = BackgroundTaskService(db).pending_chapter_indexes(task.id)
        except ValueError:
            pending_chapter_indexes = []
    return {
        "can_resume": bool(progress.get("can_resume")) if progress else bool(pending_chapter_indexes),
        "next_chapter_index": progress.get("next_chapter_index") if progress else (pending_chapter_indexes[0] if pending_chapter_indexes else None),
        "pending_chapter_indexes": pending_chapter_indexes,
        "completed_count": int(progress.get("completed_count") or 0) if progress else 0,
    }


def _recovery_summary(task: BackgroundTask) -> dict[str, Any]:
    can_retry = task.status in {"failed", "cancelled"}
    return {
        "can_retry": can_retry,
        "recommended_tools": ["inspect_agent_trace_audit", "plan_recovery_tools"] if can_retry else [],
        "reason": task.error if can_retry else None,
    }


def _agent_runs_for_task(db: Session, task: BackgroundTask) -> list[dict[str, Any]]:
    rows = (
        db.query(WritingAgentRun)
        .filter(WritingAgentRun.project_id == task.project_id, WritingAgentRun.background_task_id == task.id)
        .order_by(WritingAgentRun.created_at.desc(), WritingAgentRun.id.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "id": run.id,
            "goal": run.goal,
            "status": run.status,
            "entrypoint": run.entrypoint,
            "created_at": run.created_at,
        }
        for run in rows
    ]


def _recommended_tools(*, tasks: list[BackgroundTask], selected_task: dict[str, Any] | None) -> list[str]:
    if selected_task is not None:
        recovery = selected_task.get("recovery") if isinstance(selected_task.get("recovery"), dict) else {}
        if recovery.get("can_retry") is True:
            return list(recovery.get("recommended_tools") or [])
        return ["inspect_agent_trace_audit"]
    if not tasks:
        return ["plan_longform_chapter_batch"]
    if any(task.status in {"failed", "cancelled"} for task in tasks):
        return ["inspect_agent_trace_audit", "plan_recovery_tools"]
    if any(task.status in {"pending", "running"} for task in tasks):
        return ["inspect_agent_trace_audit"]
    return ["plan_longform_chapter_batch"]


def _error_preview(error: str | None) -> str | None:
    if not error:
        return None
    return str(error)[:ERROR_PREVIEW_LIMIT]


def _clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_JOB_LIMIT
    return min(max(int(limit), 1), MAX_JOB_LIMIT)


def _projection_trace_metadata() -> dict[str, Any]:
    return {
        "source": "inspect_agent_job_projection",
        "version": AGENT_JOB_PROJECTION_VERSION,
        "mutability": "read",
    }


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

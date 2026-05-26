from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import BackgroundTask, Project, WritingAgentRun, WritingAgentStep

AGENT_EVENT_PROJECTION_VERSION = "phase234.agent_event_projection.v1"
DEFAULT_EVENT_LIMIT = 100
MAX_EVENT_LIMIT = 500
ERROR_PREVIEW_LIMIT = 240


def inspect_agent_event_projection(
    db: Session,
    project_id: str,
    *,
    task_id: str | None = None,
    run_id: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    _require_project(db, project_id)
    clamped_limit = _clamp_limit(limit)
    task_ids = _resolved_task_ids(db, project_id=project_id, task_id=task_id, run_id=run_id)
    tasks = _tasks(db, project_id=project_id, task_ids=task_ids, task_id=task_id, limit=clamped_limit)
    runs = _runs(db, project_id=project_id, task_ids=task_ids, run_id=run_id, limit=clamped_limit)
    steps = _steps(db, project_id=project_id, task_ids=task_ids, run_id=run_id, limit=clamped_limit)

    events = [*_task_events(tasks), *_run_events(runs), *_step_events(steps)]
    events = sorted(events, key=_event_sort_key)[:clamped_limit]
    return _json_safe_output(
        {
            "status": "completed",
            "version": AGENT_EVENT_PROJECTION_VERSION,
            "project_id": project_id,
            "selector": _selector(task_id=task_id, run_id=run_id, limit=clamped_limit),
            "boundary": {
                "decision": "projection_only",
                "persistence": "not_required",
                "reason": "existing task, run, and step records preserve enough causality for current recovery loops",
            },
            "summary": _summary(events),
            "events": events,
            "recommended_tools": ["inspect_agent_job_projection"],
            "trace": {
                "selected_sources": ["background_tasks", "writing_agent_runs", "writing_agent_steps"],
                "rejected_sources": [{"source": "event_bus", "reason": "not_required_for_current_projection"}],
                "mutability": "read",
            },
        }
    )


def event_projection_summary_for_task(db: Session, task: BackgroundTask) -> dict[str, Any]:
    projection = inspect_agent_event_projection(db, task.project_id, task_id=task.id, limit=40)
    events = projection.get("events") if isinstance(projection.get("events"), list) else []
    return {
        "status": projection.get("status"),
        "version": projection.get("version"),
        "boundary": projection.get("boundary"),
        "summary": projection.get("summary"),
        "latest_events": events[-5:],
        "recommended_tools": ["inspect_agent_event_projection"],
    }


def _require_project(db: Session, project_id: str) -> None:
    if db.query(Project.id).filter(Project.id == project_id).first() is None:
        raise HTTPException(status_code=404, detail="Project not found")


def _resolved_task_ids(
    db: Session,
    *,
    project_id: str,
    task_id: str | None,
    run_id: str | None,
) -> set[str]:
    resolved = {str(task_id)} if task_id else set()
    if run_id:
        run = (
            db.query(WritingAgentRun.background_task_id)
            .filter(WritingAgentRun.project_id == project_id, WritingAgentRun.id == run_id)
            .first()
        )
        if run is not None and run.background_task_id:
            resolved.add(str(run.background_task_id))
    return resolved


def _tasks(
    db: Session,
    *,
    project_id: str,
    task_ids: set[str],
    task_id: str | None,
    limit: int,
) -> list[BackgroundTask]:
    query = db.query(BackgroundTask).filter(BackgroundTask.project_id == project_id)
    if task_ids:
        query = query.filter(BackgroundTask.id.in_(task_ids))
    elif task_id:
        query = query.filter(BackgroundTask.id == task_id)
    return query.order_by(BackgroundTask.created_at.asc(), BackgroundTask.id.asc()).limit(limit).all()


def _runs(
    db: Session,
    *,
    project_id: str,
    task_ids: set[str],
    run_id: str | None,
    limit: int,
) -> list[WritingAgentRun]:
    query = db.query(WritingAgentRun).filter(WritingAgentRun.project_id == project_id)
    if run_id:
        query = query.filter(WritingAgentRun.id == run_id)
    elif task_ids:
        query = query.filter(WritingAgentRun.background_task_id.in_(task_ids))
    return query.order_by(WritingAgentRun.created_at.asc(), WritingAgentRun.id.asc()).limit(limit).all()


def _steps(
    db: Session,
    *,
    project_id: str,
    task_ids: set[str],
    run_id: str | None,
    limit: int,
) -> list[WritingAgentStep]:
    query = db.query(WritingAgentStep).filter(WritingAgentStep.project_id == project_id)
    if run_id:
        query = query.filter(WritingAgentStep.run_id == run_id)
    elif task_ids:
        query = query.filter(WritingAgentStep.background_task_id.in_(task_ids))
    return query.order_by(WritingAgentStep.created_at.asc(), WritingAgentStep.step_index.asc()).limit(limit).all()


def _task_events(tasks: list[BackgroundTask]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for task in tasks:
        events.append(_base_event("task_created", "background_task", task.id, task.project_id, at=task.created_at))
        if task.started_at is not None:
            events.append(
                _base_event(
                    "task_started",
                    "background_task",
                    task.id,
                    task.project_id,
                    at=task.started_at,
                    status=task.status,
                    task_id=task.id,
                )
            )
        terminal_event = _terminal_task_event(task)
        if terminal_event:
            events.append(terminal_event)
    return events


def _run_events(runs: list[WritingAgentRun]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for run in runs:
        base = {"run_id": run.id, "task_id": run.background_task_id, "status": run.status}
        events.append(
            _base_event(
                "run_created",
                "writing_agent_run",
                run.id,
                run.project_id,
                at=run.created_at,
                **base,
            )
        )
        if run.started_at is not None:
            events.append(
                _base_event(
                    "run_started",
                    "writing_agent_run",
                    run.id,
                    run.project_id,
                    at=run.started_at,
                    **base,
                )
            )
        terminal_event = _terminal_run_event(run)
        if terminal_event:
            events.append(terminal_event)
    return events


def _step_events(steps: list[WritingAgentStep]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for step in steps:
        base = {
            "task_id": step.background_task_id,
            "run_id": step.run_id,
            "step_id": step.id,
            "step_index": step.step_index,
            "tool_name": step.tool_name,
            "status": step.status,
            "chapter_index": step.chapter_index,
            "trace_id": step.trace_id,
        }
        events.append(
            _base_event(
                "tool_started",
                "writing_agent_step",
                step.id,
                step.project_id,
                at=step.started_at or step.created_at,
                **base,
            )
        )
        terminal_type = _terminal_step_event_type(step.status)
        if terminal_type is None:
            continue
        events.append(
            _base_event(
                terminal_type,
                "writing_agent_step",
                step.id,
                step.project_id,
                at=step.finished_at or step.created_at,
                error_preview=_error_preview(step),
                **base,
            )
        )
    return events


def _terminal_task_event(task: BackgroundTask) -> dict[str, Any] | None:
    event_type = {
        "completed": "task_completed",
        "failed": "task_error",
        "cancelled": "task_cancelled",
    }.get(str(task.status or ""))
    if event_type is None:
        return None
    return _base_event(
        event_type,
        "background_task",
        task.id,
        task.project_id,
        at=task.finished_at or task.created_at,
        status=task.status,
        task_id=task.id,
        error_preview=task.error[:ERROR_PREVIEW_LIMIT] if task.error else None,
    )


def _terminal_run_event(run: WritingAgentRun) -> dict[str, Any] | None:
    event_type = {
        "success": "run_completed",
        "completed": "run_completed",
        "failed": "run_error",
        "blocked": "run_blocked",
        "cancelled": "run_cancelled",
    }.get(str(run.status or ""))
    if event_type is None:
        return None
    return _base_event(
        event_type,
        "writing_agent_run",
        run.id,
        run.project_id,
        at=run.finished_at or run.updated_at or run.created_at,
        status=run.status,
        run_id=run.id,
        task_id=run.background_task_id,
        error_preview=run.error[:ERROR_PREVIEW_LIMIT] if run.error else None,
    )


def _terminal_step_event_type(status: str | None) -> str | None:
    if status == "success":
        return "tool_completed"
    if status in {"failed", "blocked"}:
        return "tool_error"
    return None


def _base_event(
    event_type: str,
    source_type: str,
    source_id: str,
    project_id: str,
    *,
    at: Any,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "event_id": f"{source_type}:{source_id}:{event_type}",
        "event_type": event_type,
        "source_type": source_type,
        "source_id": source_id,
        "project_id": project_id,
        "at": at,
        **{key: value for key, value in extra.items() if value is not None},
    }


def _error_preview(step: WritingAgentStep) -> str | None:
    output = step.output if isinstance(step.output, dict) else {}
    value = step.error or output.get("error") or output.get("reason")
    if not value:
        return None
    return str(value)[:ERROR_PREVIEW_LIMIT]


def _summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    by_event_type: dict[str, int] = {}
    by_source_type: dict[str, int] = {}
    for event in events:
        event_type = str(event.get("event_type") or "unknown")
        source_type = str(event.get("source_type") or "unknown")
        by_event_type[event_type] = by_event_type.get(event_type, 0) + 1
        by_source_type[source_type] = by_source_type.get(source_type, 0) + 1
    return {
        "total": len(events),
        "by_event_type": by_event_type,
        "by_source_type": by_source_type,
    }


def _selector(*, task_id: str | None, run_id: str | None, limit: int) -> dict[str, Any]:
    selector: dict[str, Any] = {"limit": limit}
    if task_id:
        selector["task_id"] = task_id
    if run_id:
        selector["run_id"] = run_id
    return selector


def _event_sort_key(event: dict[str, Any]) -> tuple[str, str]:
    return (str(event.get("at") or ""), str(event.get("event_id") or ""))


def _clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_EVENT_LIMIT
    return min(max(int(limit), 1), MAX_EVENT_LIMIT)


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

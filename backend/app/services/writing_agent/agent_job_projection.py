from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import BackgroundTask, Project, WritingAgentRun
from app.services.writing_agent.command_contract_projection import (
    command_contracts_from_run_input,
    command_contracts_needs_attention,
)
from app.services.writing_agent.control_plane_readiness_projection import (
    control_plane_readiness_from_run_input,
    control_plane_readiness_needs_attention,
)
from app.services.tasks.background_task_service import ACTIVE_TASK_STATUSES, BackgroundTaskService

AGENT_JOB_PROJECTION_VERSION = "phase75.agent_job_projection.v1"
DEFAULT_JOB_LIMIT = 20
MAX_JOB_LIMIT = 100
ERROR_PREVIEW_LIMIT = 240
CHAPTER_TARGET_SOURCE_LABELS = {
    "single_task": "单章生成任务",
    "range_task": "批量生成任务",
}


def inspect_agent_job_projection(
    db: Session,
    project_id: str,
    *,
    task_id: str | None = None,
    task_type: str | None = None,
    status: str | None = None,
    limit: int | None = None,
    chapter_index: int | None = None,
) -> dict[str, Any]:
    _require_project(db, project_id)
    clamped_limit = _clamp_limit(limit)
    normalized_chapter_index = _optional_positive_int(chapter_index)
    selected_task = _selected_task(db, project_id=project_id, task_id=task_id)
    if task_id and selected_task is None:
        return _json_safe_output(
            {
                "status": "not_found",
                "project_id": project_id,
                "selector": _selector(
                    task_id=task_id,
                    task_type=task_type,
                    status=status,
                    chapter_index=normalized_chapter_index,
                ),
                "summary": _summary(total=0, returned=0, limit=clamped_limit, by_status={}),
                "queue": _queue_projection([]),
                "tasks": [],
                "selected_task": None,
                "chapter_reservation": _chapter_reservation_projection([], normalized_chapter_index),
                "recommended_tools": ["inspect_agent_trace_audit"],
                "trace": _projection_trace_metadata(),
            }
        )

    query = _base_query(db, project_id)
    if task_type:
        query = query.filter(BackgroundTask.task_type == task_type)
    if status:
        query = query.filter(BackgroundTask.status == status)
    ordered_query = query.order_by(BackgroundTask.created_at.desc(), BackgroundTask.id.desc())
    if normalized_chapter_index is not None:
        matching_tasks = [
            task for task in ordered_query.all() if _task_covers_chapter(task, normalized_chapter_index)
        ]
        total = len(matching_tasks)
        tasks = matching_tasks[:clamped_limit]
    else:
        total = query.with_entities(func.count(BackgroundTask.id)).order_by(None).scalar() or 0
        matching_tasks = ordered_query.limit(clamped_limit).all()
        tasks = matching_tasks
    by_status = _status_counts(tasks)
    selected_projection = _detailed_task(db, selected_task) if selected_task is not None else None
    recommended_tools = _recommended_tools(tasks=tasks, selected_task=selected_projection)
    return _json_safe_output(
        {
            "status": "completed",
            "project_id": project_id,
            "selector": _selector(
                task_id=task_id,
                task_type=task_type,
                status=status,
                chapter_index=normalized_chapter_index,
            ),
            "summary": _summary(total=int(total), returned=len(tasks), limit=clamped_limit, by_status=by_status),
            "queue": _queue_projection(tasks),
            "tasks": [_compact_task(task) for task in tasks],
            "selected_task": selected_projection,
            "chapter_reservation": _chapter_reservation_projection(matching_tasks, normalized_chapter_index),
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


def _selector(
    *,
    task_id: str | None,
    task_type: str | None,
    status: str | None,
    chapter_index: int | None,
) -> dict[str, str] | None:
    selector = {}
    if task_id:
        selector["task_id"] = task_id
    if task_type:
        selector["task_type"] = task_type
    if status:
        selector["status"] = status
    if chapter_index is not None:
        selector["chapter_index"] = str(chapter_index)
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
    agent_runs = _agent_runs_for_task(db, task)
    return {
        **_compact_task(task),
        "payload_summary": _payload_summary(payload),
        "result_summary": _result_summary(result),
        "resume": _resume_summary(db, task),
        "recovery": _recovery_summary(task),
        "agent_runs": agent_runs,
        "control_plane_readiness": _latest_control_plane_readiness(agent_runs),
        "command_contracts": _latest_command_contracts(agent_runs),
        "error_preview": _error_preview(task.error),
    }


def _chapter_range(payload: dict[str, Any]) -> dict[str, Any] | None:
    chapter_range = payload.get("chapter_range")
    return chapter_range if isinstance(chapter_range, dict) else None


def _task_covers_chapter(task: BackgroundTask, chapter_index: int | None) -> bool:
    if chapter_index is None:
        return True
    payload = task.payload if isinstance(task.payload, dict) else {}
    return chapter_index in _chapter_index_sources_from_task_payload(payload)


def _chapter_index_sources_from_task_payload(payload: dict[str, Any] | None) -> dict[int, str]:
    if not isinstance(payload, dict):
        return {}
    if payload.get("action_type") not in {None, "generate_chapter", "generate_chapter_range"}:
        return {}

    sources: dict[int, str] = {}
    chapter_range = payload.get("chapter_range") if isinstance(payload.get("chapter_range"), dict) else {}
    start = _optional_positive_int(chapter_range.get("start"))
    end = _optional_positive_int(chapter_range.get("end"))
    if start is not None and end is not None and start <= end:
        for index in range(start, end + 1):
            sources[index] = "range_task"

    action_params = payload.get("action_params") if isinstance(payload.get("action_params"), dict) else {}
    chapter_index = _optional_positive_int(action_params.get("chapter_index") or payload.get("chapter_index"))
    if chapter_index is not None:
        sources.setdefault(chapter_index, "single_task")

    tools = payload.get("tools") if isinstance(payload.get("tools"), list) else []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        params = tool.get("params") if isinstance(tool.get("params"), dict) else {}
        chapter_index = _optional_positive_int(params.get("chapter_index"))
        if chapter_index is not None:
            sources.setdefault(chapter_index, "single_task")
    return sources


def _chapter_reservation_projection(tasks: list[BackgroundTask], chapter_index: int | None) -> dict[str, Any] | None:
    if chapter_index is None:
        return None
    active_tasks = [task for task in tasks if task.status in ACTIVE_TASK_STATUSES and _task_covers_chapter(task, chapter_index)]
    return {
        "chapter_index": chapter_index,
        "status": "reserved" if active_tasks else "available",
        "active_task_count": len(active_tasks),
        "tasks": [_chapter_reservation_task(task, chapter_index) for task in active_tasks],
        "recommended_tools": ["inspect_agent_job_projection", "inspect_agent_trace_audit"] if active_tasks else [],
        "recovery_options": [
            {
                "action": "inspect_occupying_task",
                "tool_name": "inspect_agent_job_projection",
                "params": {"task_id": task.id},
            }
            for task in active_tasks
        ],
    }


def _chapter_reservation_task(task: BackgroundTask, chapter_index: int) -> dict[str, Any]:
    payload = task.payload if isinstance(task.payload, dict) else {}
    sources = _chapter_index_sources_from_task_payload(payload)
    source = sources.get(chapter_index, "single_task")
    return {
        "task_id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "source": source,
        "source_label": CHAPTER_TARGET_SOURCE_LABELS.get(source, "占用任务"),
        "chapter_index": _payload_chapter_index(payload),
        "chapter_range": _chapter_range(payload),
    }


def _payload_chapter_index(payload: dict[str, Any]) -> int | None:
    action_params = payload.get("action_params") if isinstance(payload.get("action_params"), dict) else {}
    return _optional_positive_int(action_params.get("chapter_index") or payload.get("chapter_index"))


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
            "control_plane_readiness": control_plane_readiness_from_run_input(run.input),
            "command_contracts": command_contracts_from_run_input(run.input),
            "created_at": run.created_at,
        }
        for run in rows
    ]


def _recommended_tools(*, tasks: list[BackgroundTask], selected_task: dict[str, Any] | None) -> list[str]:
    if selected_task is not None:
        recovery = selected_task.get("recovery") if isinstance(selected_task.get("recovery"), dict) else {}
        if recovery.get("can_retry") is True:
            return list(recovery.get("recommended_tools") or [])
        if control_plane_readiness_needs_attention(selected_task.get("control_plane_readiness")):
            return ["inspect_agent_control_plane_readiness", "inspect_agent_trace_audit"]
        if command_contracts_needs_attention(selected_task.get("command_contracts")):
            return ["inspect_agent_command_contracts", "inspect_agent_trace_audit"]
        return ["inspect_agent_trace_audit"]
    if not tasks:
        return ["plan_longform_chapter_batch"]
    if any(task.status in {"failed", "cancelled"} for task in tasks):
        return ["inspect_agent_trace_audit", "plan_recovery_tools"]
    if any(task.status in {"pending", "running"} for task in tasks):
        return ["inspect_agent_trace_audit"]
    return ["plan_longform_chapter_batch"]


def _latest_control_plane_readiness(agent_runs: list[dict[str, Any]]) -> dict[str, Any] | None:
    for run in agent_runs:
        readiness = run.get("control_plane_readiness") if isinstance(run, dict) else None
        if isinstance(readiness, dict):
            return readiness
    return None


def _latest_command_contracts(agent_runs: list[dict[str, Any]]) -> dict[str, Any] | None:
    for run in agent_runs:
        contracts = run.get("command_contracts") if isinstance(run, dict) else None
        if isinstance(contracts, dict):
            return contracts
    return None


def _error_preview(error: str | None) -> str | None:
    if not error:
        return None
    return str(error)[:ERROR_PREVIEW_LIMIT]


def _clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_JOB_LIMIT
    return min(max(int(limit), 1), MAX_JOB_LIMIT)


def _optional_positive_int(value: object) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _projection_trace_metadata() -> dict[str, Any]:
    return {
        "source": "inspect_agent_job_projection",
        "version": AGENT_JOB_PROJECTION_VERSION,
        "mutability": "read",
    }


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

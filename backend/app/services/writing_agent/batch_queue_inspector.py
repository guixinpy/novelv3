from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import BackgroundTask, Project
from app.services.writing_agent.batch_enqueue import BATCH_TASK_TYPE

INSPECT_VERSION = "phase59.longform_batch_inspect.v1"
DEFAULT_LIMIT = 10
MAX_LIMIT = 20


def inspect_longform_chapter_batch_queue(
    db: Session,
    project_id: str,
    *,
    task_id: str | None = None,
    plan_hash: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}

    selector = _selector(task_id=task_id, plan_hash=plan_hash)
    selected_task = _selected_task(db, project_id=project_id, task_id=task_id, plan_hash=plan_hash)
    if selector and selected_task is None:
        return {
            "status": "not_found",
            "inspect_version": INSPECT_VERSION,
            "project_id": project_id,
            "selector": selector,
            "summary": _summary(0, 0, _clamp_limit(limit), selected=False),
            "tasks": [],
            "selected_task": None,
            "trace": {
                "selected_tools": ["inspect_longform_chapter_batch"],
                "rejected_tools": [{"tool_name": "inspect_longform_chapter_batch", "reason": "selected_task_not_found"}],
            },
        }

    clamped_limit = _clamp_limit(limit)
    query = _base_query(db, project_id)
    if plan_hash:
        query = query.filter(BackgroundTask.payload["plan_hash"].as_string() == plan_hash)
    total = query.with_entities(func.count(BackgroundTask.id)).order_by(None).scalar() or 0
    tasks = (
        query.order_by(BackgroundTask.created_at.desc(), BackgroundTask.id.desc())
        .limit(clamped_limit)
        .all()
    )
    by_status = _status_counts(tasks)
    return {
        "status": "completed",
        "inspect_version": INSPECT_VERSION,
        "project_id": project_id,
        "selector": selector,
        "summary": _summary(int(total), len(tasks), clamped_limit, selected=selected_task is not None, by_status=by_status),
        "queue": _queue_projection(tasks, by_status),
        "tasks": [_compact_task(task) for task in tasks],
        "selected_task": _detailed_task(selected_task) if selected_task is not None else None,
        "trace": {
            "selected_tools": ["inspect_longform_chapter_batch"],
            "rejected_tools": [],
        },
    }


def _base_query(db: Session, project_id: str):
    return db.query(BackgroundTask).filter(
        BackgroundTask.project_id == project_id,
        BackgroundTask.task_type == BATCH_TASK_TYPE,
    )


def _selected_task(
    db: Session,
    *,
    project_id: str,
    task_id: str | None,
    plan_hash: str | None,
) -> BackgroundTask | None:
    if task_id:
        return _base_query(db, project_id).filter(BackgroundTask.id == task_id).first()
    if plan_hash:
        return (
            _base_query(db, project_id)
            .filter(BackgroundTask.payload["plan_hash"].as_string() == plan_hash)
            .order_by(BackgroundTask.created_at.desc(), BackgroundTask.id.desc())
            .first()
        )
    return None


def _selector(*, task_id: str | None, plan_hash: str | None) -> dict[str, str] | None:
    if task_id:
        return {"task_id": task_id}
    if plan_hash:
        return {"plan_hash": plan_hash}
    return None


def _summary(
    total: int,
    returned: int,
    limit: int,
    *,
    selected: bool,
    by_status: dict[str, int] | None = None,
) -> dict[str, Any]:
    return {
        "total": total,
        "returned": returned,
        "limit": limit,
        "selected": selected,
        "task_type": BATCH_TASK_TYPE,
        "by_status": by_status or {},
    }


def _queue_projection(tasks: list[BackgroundTask], by_status: dict[str, int]) -> dict[str, Any]:
    terminal = sum(by_status.get(status, 0) for status in ("completed", "failed", "cancelled"))
    active = len(tasks) - terminal
    return {
        "depth": len(tasks),
        "active": active,
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
    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "plan_hash": payload.get("plan_hash"),
        "chapter_range": _chapter_range(payload),
        "queue_policy": _queue_policy(payload),
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }


def _detailed_task(task: BackgroundTask) -> dict[str, Any]:
    payload = task.payload if isinstance(task.payload, dict) else {}
    result = task.result if isinstance(task.result, dict) else {}
    progress = result.get("progress") if isinstance(result.get("progress"), dict) else None
    batch_execution_result = (
        result.get("batch_execution_result") if isinstance(result.get("batch_execution_result"), dict) else None
    )
    queue_policy = _queue_policy(payload)
    return {
        **_compact_task(task),
        "batch": payload.get("batch") if isinstance(payload.get("batch"), dict) else {},
        "dag": _dag_summary(payload.get("dag")),
        "tools": payload.get("tools") if isinstance(payload.get("tools"), list) else [],
        "progress": progress,
        "preflight_checkpoint": result.get("preflight_checkpoint")
        if isinstance(result.get("preflight_checkpoint"), dict)
        else None,
        "execution_checkpoints": result.get("execution_checkpoints")
        if isinstance(result.get("execution_checkpoints"), list)
        else [],
        "attempt_manifest": result.get("attempt_manifest") if isinstance(result.get("attempt_manifest"), dict) else None,
        "approval_contract": result.get("approval_contract")
        if isinstance(result.get("approval_contract"), dict)
        else None,
        "batch_execution_result": batch_execution_result,
        "resume": _resume_payload(progress, queue_policy),
        "execution_readiness": _execution_readiness(queue_policy, result),
        "error": task.error,
    }


def _chapter_range(payload: dict[str, Any]) -> dict[str, Any] | None:
    chapter_range = payload.get("chapter_range")
    return chapter_range if isinstance(chapter_range, dict) else None


def _queue_policy(payload: dict[str, Any]) -> dict[str, Any]:
    policy = payload.get("queue_policy")
    return policy if isinstance(policy, dict) else {}


def _dag_summary(dag: object) -> dict[str, Any]:
    if not isinstance(dag, dict):
        return {"node_count": 0, "node_ids": [], "edges": []}
    nodes = dag.get("nodes") if isinstance(dag.get("nodes"), list) else []
    return {
        "node_count": int(dag.get("node_count") or len(nodes)),
        "node_ids": [str(node.get("node_id") or "") for node in nodes if isinstance(node, dict)],
        "edges": dag.get("edges") if isinstance(dag.get("edges"), list) else [],
    }


def _resume_payload(progress: dict[str, Any] | None, queue_policy: dict[str, Any]) -> dict[str, Any]:
    if not progress:
        return {
            "can_resume": False,
            "strategy": queue_policy.get("resume_strategy"),
            "next_chapter_index": None,
            "completed_count": 0,
        }
    return {
        "can_resume": bool(progress.get("can_resume")),
        "strategy": queue_policy.get("resume_strategy"),
        "next_chapter_index": progress.get("next_chapter_index"),
        "completed_count": int(progress.get("completed_count") or 0),
    }


def _execution_readiness(queue_policy: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    if isinstance(result.get("batch_execution_result"), dict):
        return {
            "status": "phase62_executed",
            "can_execute": False,
            "reason": "This materialized batch already has Phase62 execution evidence.",
        }
    if isinstance(result.get("approval_contract"), dict):
        return {
            "status": "approval_contract_ready",
            "can_execute": True,
            "reason": "Phase61 approval contract is ready for execute_longform_chapter_batch.",
        }
    if queue_policy.get("starts_runner") is False:
        return {
            "status": "materialized_only",
            "can_execute": False,
            "reason": "Phase59 exposes queue state before batch execution is implemented.",
        }
    return {"status": "runner_managed", "can_execute": True, "reason": None}


def _clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    return min(max(int(limit), 1), MAX_LIMIT)

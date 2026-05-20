from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.services.tasks.background_task_service import BackgroundTaskService
from app.services.writing_agent.batch_planner import build_longform_chapter_batch_plan

BATCH_ENQUEUE_VERSION = "phase58.longform_batch_enqueue.v1"
BATCH_TASK_TYPE = "longform_chapter_batch"


def build_longform_chapter_batch_enqueue(
    db: Session,
    project_id: str,
    *,
    source_run_id: str | None = None,
    start_chapter: int | None = None,
    batch_size: int | None = None,
    confirm_enqueue: bool = False,
    plan_hash: str | None = None,
) -> dict[str, Any]:
    plan = build_longform_chapter_batch_plan(
        db,
        project_id,
        source_run_id=source_run_id,
        start_chapter=start_chapter,
        batch_size=batch_size,
    )
    status = str(plan.get("status") or "failed")
    if status in {"blocked", "failed"}:
        return {
            **plan,
            "can_enqueue": False,
            "preview_only": True,
            "queue_policy": _queue_policy(),
            "trace": _with_enqueue_rejection(plan.get("trace"), "plan_not_enqueueable"),
        }

    hash_payload = _hash_payload(project_id, source_run_id, plan)
    actual_hash = _stable_hash(hash_payload)
    preview = {
        "status": "confirmation_required",
        "enqueue_version": BATCH_ENQUEUE_VERSION,
        "preview_only": True,
        "can_enqueue": True,
        "requires_confirmation": True,
        "plan_hash": actual_hash,
        "hash_payload": hash_payload,
        "required_confirmation": {"confirm_enqueue": True, "plan_hash": actual_hash},
        "project_id": project_id,
        "source_run_id": source_run_id,
        "batch": plan.get("batch") or {},
        "dag": plan.get("dag") or {},
        "tools": plan.get("tools") or [],
        "queue_policy": _queue_policy(),
        "trace": {
            "selected_tools": ["enqueue_longform_chapter_batch"],
            "rejected_tools": [],
            "plan_trace": plan.get("trace") if isinstance(plan.get("trace"), dict) else {},
        },
    }
    if not confirm_enqueue:
        return preview

    provided_hash = str(plan_hash or "").strip()
    if provided_hash != actual_hash:
        return {
            **preview,
            "status": "hash_mismatch",
            "can_enqueue": False,
            "provided_plan_hash": provided_hash,
            "expected_plan_hash": actual_hash,
            "trace": _with_enqueue_rejection(preview.get("trace"), "plan_hash_mismatch"),
        }

    batch = preview["batch"]
    start = _optional_int(batch.get("start_chapter"))
    end = _optional_int(batch.get("end_chapter"))
    if start is None or end is None:
        return {
            **preview,
            "status": "failed",
            "can_enqueue": False,
            "error": "Batch plan does not define a valid chapter range",
            "trace": _with_enqueue_rejection(preview.get("trace"), "invalid_chapter_range"),
        }

    task = BackgroundTaskService(db).create_chapter_range(
        project_id=project_id,
        task_type=BATCH_TASK_TYPE,
        start_chapter_index=start,
        end_chapter_index=end,
        payload={
            "enqueue_version": BATCH_ENQUEUE_VERSION,
            "plan_hash": actual_hash,
            "source_run_id": source_run_id,
            "batch": batch,
            "dag": preview["dag"],
            "tools": preview["tools"],
            "queue_policy": preview["queue_policy"],
            "hash_payload": hash_payload,
        },
        idempotency_key=_idempotency_key(project_id, start, end, actual_hash),
    )
    return {
        **preview,
        "status": "queued",
        "preview_only": False,
        "requires_confirmation": False,
        "can_enqueue": False,
        "task": _task_payload(task),
        "trace": {
            **(preview.get("trace") if isinstance(preview.get("trace"), dict) else {}),
            "queued_task_id": task.id,
        },
    }


def _hash_payload(project_id: str, source_run_id: str | None, plan: dict[str, Any]) -> dict[str, Any]:
    dag = plan.get("dag") if isinstance(plan.get("dag"), dict) else {}
    nodes = dag.get("nodes") if isinstance(dag.get("nodes"), list) else []
    return {
        "enqueue_version": BATCH_ENQUEUE_VERSION,
        "plan_version": plan.get("plan_version"),
        "project_id": project_id,
        "source_run_id": source_run_id,
        "batch": plan.get("batch") if isinstance(plan.get("batch"), dict) else {},
        "dag_node_ids": [str(node.get("node_id") or "") for node in nodes if isinstance(node, dict)],
        "dag_edges": dag.get("edges") if isinstance(dag.get("edges"), list) else [],
        "tools": plan.get("tools") if isinstance(plan.get("tools"), list) else [],
    }


def _stable_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _queue_policy() -> dict[str, Any]:
    return {
        "mode": "materialize_only",
        "starts_runner": False,
        "requires_confirmation": True,
        "resume_strategy": "background_task_chapter_range",
    }


def _idempotency_key(project_id: str, start: int, end: int, plan_hash: str) -> str:
    return f"longform_batch:{project_id}:{start}:{end}:{plan_hash}"


def _task_payload(task) -> dict[str, Any]:
    chapter_range = (task.payload or {}).get("chapter_range")
    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "chapter_range": chapter_range if isinstance(chapter_range, dict) else None,
    }


def _with_enqueue_rejection(trace: object, reason: str) -> dict[str, Any]:
    next_trace = dict(trace) if isinstance(trace, dict) else {}
    rejected = list(next_trace.get("rejected_tools") or [])
    rejected.append({"tool_name": "enqueue_longform_chapter_batch", "reason": reason})
    next_trace["rejected_tools"] = rejected
    return next_trace


def _optional_int(value: object) -> int | None:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None

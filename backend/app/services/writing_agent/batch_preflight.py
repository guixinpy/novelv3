from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, object_session

from app.models import BackgroundTask, ChapterContent, Project
from app.services.tasks.background_task_service import TASK_CANCELLED, TASK_COMPLETED, TASK_FAILED
from app.services.writing_agent.batch_enqueue import BATCH_TASK_TYPE
from app.services.writing_agent.run_service import WritingAgentRunService

PREFLIGHT_VERSION = "phase60.longform_batch_execute_preflight.v1"
DEFAULT_MAX_CHAPTERS = 1
MAX_PREFLIGHT_CHAPTERS = 3
SAFE_NODES_EXECUTED = ["preflight_gate"]
STOPPED_BEFORE_NODE = "chapter_generation"
SKIPPED_SIDE_EFFECTS = ["start_runner", "generate_chapter", "world_model_apply"]
TERMINAL_STATUSES = {TASK_COMPLETED, TASK_FAILED, TASK_CANCELLED}


def execute_longform_chapter_batch_preflight(
    db: Session,
    project_id: str,
    *,
    task_id: str | None,
    max_chapters: int | None = None,
    confirm_checkpoint: bool = False,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    if not task_id:
        return {
            "status": "failed",
            "error": "task_id is required",
            "project_id": project_id,
            "preflight_version": PREFLIGHT_VERSION,
        }

    task = (
        db.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == project_id,
            BackgroundTask.task_type == BATCH_TASK_TYPE,
            BackgroundTask.id == task_id,
        )
        .first()
    )
    if task is None:
        return {
            "status": "not_found",
            "preflight_version": PREFLIGHT_VERSION,
            "project_id": project_id,
            "task_id": task_id,
            "trace": {
                "selected_tools": ["execute_longform_chapter_batch_preflight"],
                "rejected_tools": [
                    {"tool_name": "execute_longform_chapter_batch_preflight", "reason": "selected_task_not_found"}
                ],
            },
        }
    if str(task.status or "") in TERMINAL_STATUSES:
        return _blocked_output(
            task,
            reason="task_status_is_terminal",
            gates=[_gate("task_status_allows_execution", "blocked", task_status=task.status)],
            chapter_preflights=[],
            selected_chapters=[],
        )

    payload = task.payload if isinstance(task.payload, dict) else {}
    chapter_indexes = _chapter_indexes(payload)
    selected_chapters = chapter_indexes[: _clamp_max_chapters(max_chapters)]
    if not selected_chapters:
        return _blocked_output(
            task,
            reason="empty_chapter_range",
            gates=[_gate("chapter_range", "blocked")],
            chapter_preflights=[],
            selected_chapters=[],
        )
    if confirm_checkpoint is not True:
        return _blocked_output(
            task,
            reason="checkpoint_confirmation_required",
            gates=[_gate("checkpoint_confirmation", "blocked")],
            chapter_preflights=[],
            selected_chapters=selected_chapters,
            required_confirmation={"confirm_checkpoint": True, "task_id": task.id},
        )

    preflights = [_compact_preflight(_run_preflight(db, project_id, index)) for index in selected_chapters]
    blocked = any(item["status"] == "blocked" for item in preflights)
    checkpoint = _checkpoint(
        task=task,
        selected_chapters=selected_chapters,
        chapter_preflights=preflights,
        status="blocked" if blocked else "ready",
    )
    _persist_checkpoint(db, task, checkpoint)

    output = _base_output(task, selected_chapters=selected_chapters, checkpoint=checkpoint)
    output.update(
        {
            "status": checkpoint["status"],
            "gates": _gates(task, blocked=blocked, chapter_preflights=preflights),
            "recommended_next_tools": _recommended_next_tools(blocked),
            "trace": {
                "selected_tools": ["execute_longform_chapter_batch_preflight"],
                "rejected_tools": [
                    {"tool_name": name, "reason": "phase60_preflight_stops_before_generation"}
                    for name in ("start_runner", "generate_chapter", "apply_world_model_proposal_resolution")
                ],
                "source": "persisted_task_payload_plus_live_preflight",
            },
        }
    )
    return output


def _run_preflight(db: Session, project_id: str, chapter_index: int) -> dict[str, Any]:
    return WritingAgentRunService(db)._preflight_writing(project_id, {"chapter_index": chapter_index})


def _compact_preflight(preflight: dict[str, Any]) -> dict[str, Any]:
    issues = preflight.get("issues") if isinstance(preflight.get("issues"), list) else []
    blockers = [item for item in issues if isinstance(item, dict) and item.get("severity") == "blocker"]
    warnings = [item for item in issues if isinstance(item, dict) and item.get("severity") == "warning"]
    return {
        "chapter_index": _optional_int(preflight.get("chapter_index")),
        "status": str(preflight.get("status") or "failed"),
        "issue_codes": [str(item.get("code") or "") for item in issues if isinstance(item, dict)],
        "blockers": blockers,
        "warnings": warnings,
        "checks": preflight.get("checks") if isinstance(preflight.get("checks"), dict) else {},
    }


def _checkpoint(
    *,
    task: BackgroundTask,
    selected_chapters: list[int],
    chapter_preflights: list[dict[str, Any]],
    status: str,
) -> dict[str, Any]:
    ready_chapters = [
        int(item["chapter_index"])
        for item in chapter_preflights
        if item.get("status") == "ready" and _optional_int(item.get("chapter_index")) is not None
    ]
    blocked_chapters = [
        int(item["chapter_index"])
        for item in chapter_preflights
        if item.get("status") == "blocked" and _optional_int(item.get("chapter_index")) is not None
    ]
    return {
        "version": PREFLIGHT_VERSION,
        "checkpointed_at": datetime.now(UTC).isoformat(),
        "task_id": task.id,
        "status": status,
        "safe_nodes_executed": list(SAFE_NODES_EXECUTED),
        "stopped_before_node": STOPPED_BEFORE_NODE,
        "generation_started": False,
        "selected_chapter_indexes": selected_chapters,
        "ready_chapter_indexes": ready_chapters,
        "blocked_chapter_indexes": blocked_chapters,
        "chapter_preflights": chapter_preflights,
    }


def _persist_checkpoint(db: Session, task: BackgroundTask, checkpoint: dict[str, Any]) -> None:
    result = dict(task.result) if isinstance(task.result, dict) else {}
    history = result.get("execution_checkpoints") if isinstance(result.get("execution_checkpoints"), list) else []
    result["preflight_checkpoint"] = checkpoint
    result["execution_checkpoints"] = [*history[-9:], checkpoint]
    task.result = result
    db.add(task)
    db.commit()
    db.refresh(task)


def _base_output(
    task: BackgroundTask,
    *,
    selected_chapters: list[int],
    checkpoint: dict[str, Any],
    checkpoint_persisted: bool = True,
) -> dict[str, Any]:
    payload = task.payload if isinstance(task.payload, dict) else {}
    chapter_indexes = _chapter_indexes(payload)
    return {
        "preflight_version": PREFLIGHT_VERSION,
        "project_id": task.project_id,
        "task": _task_payload(task),
        "canonical_execution_plan": {
            "plan_hash": payload.get("plan_hash"),
            "chapter_indexes": chapter_indexes,
            "chapters_to_run": selected_chapters,
            "chapters_already_completed": _generated_chapters(task, chapter_indexes),
            "resume_from_chapter_index": selected_chapters[0] if selected_chapters else None,
            "dag_node_ids": _dag_node_ids(payload),
            "stopped_before_node": STOPPED_BEFORE_NODE,
        },
        "checkpoint": checkpoint,
        "resume": {
            "can_resume": True,
            "strategy": _queue_policy(payload).get("resume_strategy"),
            "next_chapter_index": selected_chapters[0] if selected_chapters else None,
            "completed_count": 0,
            "decision": "blocked" if checkpoint["status"] == "blocked" else "fresh_start",
        },
        "execution_policy": {
            "mode": "preflight_only",
            "can_execute_after_confirmation": False,
            "requires_confirmation": True,
            "starts_runner": False,
            "high_risk_side_effects_executed": False,
        },
        "required_confirmation": {
            "tool_name": "execute_longform_chapter_batch",
            "available": False,
            "task_id": task.id,
            "plan_hash": payload.get("plan_hash"),
        },
        "side_effects": {
            "executed": ["background_task_result_checkpoint"] if checkpoint_persisted else [],
            "skipped": list(SKIPPED_SIDE_EFFECTS)
            if checkpoint_persisted
            else ["background_task_result_checkpoint", *SKIPPED_SIDE_EFFECTS],
            "blocked_high_risk": ["chapter_generation", "world_model_intake"],
        },
        "expected_evidence": [
            "chapter_content_written",
            "quality_review_recorded",
            "continuity_review_recorded",
            "world_model_proposals_recorded",
            "task_progress_checkpoint_updated",
        ],
    }


def _blocked_output(
    task: BackgroundTask,
    *,
    reason: str,
    gates: list[dict[str, Any]],
    chapter_preflights: list[dict[str, Any]],
    selected_chapters: list[int],
    required_confirmation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checkpoint = _checkpoint(
        task=task,
        selected_chapters=selected_chapters,
        chapter_preflights=chapter_preflights,
        status="blocked",
    )
    output = _base_output(task, selected_chapters=selected_chapters, checkpoint=checkpoint, checkpoint_persisted=False)
    output.update(
        {
            "status": "blocked",
            "reason": reason,
            "gates": gates,
            "recommended_next_tools": ["inspect_longform_chapter_batch", "plan_recovery_tools"],
            "trace": {
                "selected_tools": ["execute_longform_chapter_batch_preflight"],
                "rejected_tools": [{"tool_name": "execute_longform_chapter_batch_preflight", "reason": reason}],
            },
        }
    )
    if required_confirmation is not None:
        output["required_confirmation"] = required_confirmation
    return output


def _gates(task: BackgroundTask, *, blocked: bool, chapter_preflights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload = task.payload if isinstance(task.payload, dict) else {}
    return [
        _gate("project_exists", "passed"),
        _gate("task_selected", "passed", task_id=task.id),
        _gate("plan_hash_bound", "passed", plan_hash=payload.get("plan_hash")),
        _gate("task_status_allows_execution", "passed", task_status=task.status),
        _gate(
            "chapter_dependencies_ready",
            "blocked" if blocked else "passed",
            per_chapter=[
                {
                    "chapter_index": item.get("chapter_index"),
                    "status": item.get("status"),
                    "issue_codes": item.get("issue_codes", []),
                }
                for item in chapter_preflights
            ],
        ),
        _gate("high_risk_side_effects_skipped", "passed", skipped=list(SKIPPED_SIDE_EFFECTS)),
    ]


def _gate(name: str, status: str, **extra: Any) -> dict[str, Any]:
    return {"name": name, "status": status, **extra}


def _recommended_next_tools(blocked: bool) -> list[str]:
    if blocked:
        return ["inspect_longform_chapter_batch", "plan_recovery_tools"]
    return ["inspect_longform_chapter_batch"]


def _task_payload(task: BackgroundTask) -> dict[str, Any]:
    payload = task.payload if isinstance(task.payload, dict) else {}
    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "plan_hash": payload.get("plan_hash"),
        "chapter_range": payload.get("chapter_range") if isinstance(payload.get("chapter_range"), dict) else None,
        "queue_policy": _queue_policy(payload),
    }


def _chapter_indexes(payload: dict[str, Any]) -> list[int]:
    batch = payload.get("batch") if isinstance(payload.get("batch"), dict) else {}
    values = batch.get("chapter_indexes") if isinstance(batch.get("chapter_indexes"), list) else []
    return [int(value) for value in values if _optional_int(value) is not None]


def _dag_node_ids(payload: dict[str, Any]) -> list[str]:
    dag = payload.get("dag") if isinstance(payload.get("dag"), dict) else {}
    nodes = dag.get("nodes") if isinstance(dag.get("nodes"), list) else []
    return [str(node.get("node_id") or "") for node in nodes if isinstance(node, dict)]


def _queue_policy(payload: dict[str, Any]) -> dict[str, Any]:
    policy = payload.get("queue_policy")
    return policy if isinstance(policy, dict) else {}


def _generated_chapters(task: BackgroundTask, chapter_indexes: list[int]) -> list[int]:
    if not chapter_indexes:
        return []
    db = object_session(task)
    if db is None:
        return []
    rows = (
        db.query(ChapterContent.chapter_index)
        .filter(
            ChapterContent.project_id == task.project_id,
            ChapterContent.chapter_index.in_(chapter_indexes),
            ChapterContent.content.isnot(None),
            ChapterContent.content != "",
        )
        .order_by(ChapterContent.chapter_index.asc())
        .all()
    )
    return [int(row.chapter_index) for row in rows]


def _clamp_max_chapters(value: int | None) -> int:
    if value is None:
        return DEFAULT_MAX_CHAPTERS
    return min(max(int(value), 1), MAX_PREFLIGHT_CHAPTERS)


def _optional_int(value: object) -> int | None:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None

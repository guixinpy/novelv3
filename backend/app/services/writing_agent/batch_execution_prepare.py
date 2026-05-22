from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import BackgroundTask, ChapterContent, Project
from app.services.tasks.background_task_service import TASK_CANCELLED, TASK_COMPLETED, TASK_FAILED
from app.services.writing_agent.approval_contract import build_agent_plan_approval_contract
from app.services.writing_agent.batch_enqueue import BATCH_TASK_TYPE

PREPARE_VERSION = "phase61.longform_batch_execution_prepare.v1"
REQUIRED_PREFLIGHT_VERSION = "phase60.longform_batch_execute_preflight.v1"
REQUIRED_SAFE_NODES = ["preflight_gate"]
STOPPED_BEFORE_NODE = "chapter_generation"
SKIPPED_SIDE_EFFECTS = ["start_runner", "generate_chapter", "world_model_apply"]
TERMINAL_STATUSES = {TASK_COMPLETED, TASK_FAILED, TASK_CANCELLED}


def prepare_longform_chapter_batch_execution(
    db: Session,
    project_id: str,
    *,
    task_id: str | None,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    if not task_id:
        return {
            "status": "failed",
            "error": "task_id is required",
            "project_id": project_id,
            "prepare_version": PREPARE_VERSION,
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
            "prepare_version": PREPARE_VERSION,
            "project_id": project_id,
            "task_id": task_id,
            "trace": {
                "selected_tools": ["prepare_longform_chapter_batch_execution"],
                "rejected_tools": [
                    {"tool_name": "prepare_longform_chapter_batch_execution", "reason": "selected_task_not_found"}
                ],
            },
        }
    if str(task.status or "") in TERMINAL_STATUSES:
        return _blocked_output(task, reason="task_status_is_terminal")

    result = task.result if isinstance(task.result, dict) else {}
    checkpoint = result.get("preflight_checkpoint") if isinstance(result.get("preflight_checkpoint"), dict) else None
    validation_error = _validate_preflight_checkpoint(task, checkpoint)
    if validation_error:
        return _blocked_output(task, reason=validation_error)

    selected_chapters = [int(value) for value in checkpoint.get("selected_chapter_indexes", [])]
    generated = _generated_chapters(db, task.project_id, selected_chapters)
    if generated:
        return _blocked_output(task, reason="chapter_state_drift", extra={"generated_chapter_indexes": generated})

    attempt_payload = _attempt_manifest_payload(task, checkpoint, selected_chapters)
    attempt_hash = _stable_hash(attempt_payload)
    attempt_manifest = {
        **attempt_payload,
        "hash": attempt_hash,
        "prepared_at": datetime.now(UTC).isoformat(),
    }
    agent_plan = _agent_plan_payload(task, selected_chapters, attempt_hash=attempt_hash)
    agent_plan_approval_contract = build_agent_plan_approval_contract(agent_plan)
    agent_plan_approval_hash = str(
        ((agent_plan_approval_contract.get("approval") or {}).get("approval_contract_hash")) or ""
    )
    contract_payload = _approval_contract_payload(
        task,
        attempt_hash,
        agent_plan_approval_contract=agent_plan_approval_contract,
    )
    contract_hash = _stable_hash(contract_payload)
    approval_contract = {
        **contract_payload,
        "hash": contract_hash,
        "required_confirmation": {
            **contract_payload["required_confirmation"],
            "approval_contract_hash": contract_hash,
        },
    }
    _persist_prepare(db, task, attempt_manifest, approval_contract, agent_plan, agent_plan_approval_contract)

    return {
        "status": "approval_required",
        "prepare_version": PREPARE_VERSION,
        "project_id": project_id,
        "task": _task_payload(task),
        "attempt_manifest_hash": attempt_hash,
        "approval_contract_hash": contract_hash,
        "attempt_manifest": attempt_manifest,
        "approval_contract": approval_contract,
        "agent_plan": agent_plan,
        "agent_plan_approval_contract": agent_plan_approval_contract,
        "agent_plan_approval_contract_hash": agent_plan_approval_hash,
        "side_effects": {
            "executed": ["background_task_result_execution_prepare"],
            "skipped": list(SKIPPED_SIDE_EFFECTS),
            "blocked_high_risk": ["chapter_generation", "world_model_intake"],
        },
        "recommended_next_tools": ["execute_longform_chapter_batch"],
        "trace": {
            "selected_tools": ["prepare_longform_chapter_batch_execution"],
            "rejected_tools": [
                {"tool_name": name, "reason": "phase61_prepare_stops_before_execution"}
                for name in ("start_runner", "generate_chapter", "apply_world_model_proposal_resolution")
            ],
            "source": "persisted_task_payload_plus_ready_preflight_checkpoint",
        },
    }


def _validate_preflight_checkpoint(task: BackgroundTask, checkpoint: dict[str, Any] | None) -> str | None:
    if checkpoint is None:
        return "missing_ready_preflight_checkpoint"
    if checkpoint.get("version") != REQUIRED_PREFLIGHT_VERSION:
        return "preflight_checkpoint_version_mismatch"
    if checkpoint.get("task_id") != task.id:
        return "preflight_checkpoint_task_mismatch"
    if checkpoint.get("status") != "ready":
        return "missing_ready_preflight_checkpoint"
    if checkpoint.get("generation_started") is not False:
        return "preflight_checkpoint_generation_started"
    if checkpoint.get("stopped_before_node") != STOPPED_BEFORE_NODE:
        return "preflight_checkpoint_boundary_mismatch"
    if checkpoint.get("safe_nodes_executed") != REQUIRED_SAFE_NODES:
        return "preflight_checkpoint_safe_nodes_mismatch"
    selected_chapters = checkpoint.get("selected_chapter_indexes")
    if not isinstance(selected_chapters, list) or not selected_chapters:
        return "preflight_checkpoint_empty_chapters"
    ready_chapters = checkpoint.get("ready_chapter_indexes")
    blocked_chapters = checkpoint.get("blocked_chapter_indexes")
    if ready_chapters != selected_chapters or blocked_chapters not in ([], None):
        return "preflight_checkpoint_not_ready"
    payload_chapters = set(_chapter_indexes(task.payload if isinstance(task.payload, dict) else {}))
    selected_set = {int(value) for value in selected_chapters}
    if not selected_set.issubset(payload_chapters):
        return "preflight_checkpoint_chapter_mismatch"
    return None


def _attempt_manifest_payload(
    task: BackgroundTask,
    checkpoint: dict[str, Any],
    selected_chapters: list[int],
) -> dict[str, Any]:
    payload = task.payload if isinstance(task.payload, dict) else {}
    return {
        "version": PREPARE_VERSION,
        "task_id": task.id,
        "project_id": task.project_id,
        "task_type": task.task_type,
        "plan_hash": payload.get("plan_hash"),
        "chapter_range": payload.get("chapter_range") if isinstance(payload.get("chapter_range"), dict) else None,
        "chapter_indexes": selected_chapters,
        "dag_node_ids": _dag_node_ids(payload),
        "preflight_checkpoint": {
            "version": checkpoint.get("version"),
            "checkpointed_at": checkpoint.get("checkpointed_at"),
            "status": checkpoint.get("status"),
            "safe_nodes_executed": checkpoint.get("safe_nodes_executed"),
            "stopped_before_node": checkpoint.get("stopped_before_node"),
        },
        "stopped_before_node": STOPPED_BEFORE_NODE,
        "resume_from_chapter_index": selected_chapters[0] if selected_chapters else None,
        "execution_steps": [
            {
                "node_id": "chapter_generation",
                "tool_name": "generate_chapter",
                "chapter_indexes": selected_chapters,
                "side_effect": "write_chapter_content",
                "requires_confirmation": True,
            },
            {
                "node_id": "quality_review",
                "tool_name": "review_chapter_quality",
                "chapter_indexes": selected_chapters,
                "side_effect": "write_quality_evidence",
                "requires_confirmation": True,
            },
            {
                "node_id": "continuity_review",
                "tool_name": "review_chapter_continuity",
                "chapter_indexes": selected_chapters,
                "side_effect": "write_continuity_evidence",
                "requires_confirmation": True,
            },
            {
                "node_id": "world_model_intake",
                "tool_name": "analyze_chapter_world_model",
                "chapter_indexes": selected_chapters,
                "side_effect": "write_world_model_proposals",
                "requires_confirmation": True,
            },
        ],
    }


def _agent_plan_payload(task: BackgroundTask, selected_chapters: list[int], *, attempt_hash: str) -> dict[str, Any]:
    payload = task.payload if isinstance(task.payload, dict) else {}
    chapter_index = selected_chapters[0] if selected_chapters else None
    return {
        "project_id": task.project_id,
        "intent_class": "longform_batch_execute_chapter",
        "trace": {
            "plan_id": f"longform-batch:{task.id}:chapter-generation:{attempt_hash[:12]}",
            "source_projection_id": attempt_hash,
            "planner_version": PREPARE_VERSION,
        },
        "steps": [
            {
                "step_index": 1,
                "step_id": f"longform-batch:{task.id}:generate_chapter",
                "tool_name": "generate_chapter",
                "params": {"chapter_index": chapter_index},
                "mutability": "write",
                "requires_confirmation": True,
                "reason": "执行已通过批次预检的章节正文生成。",
            }
        ],
    }


def _approval_contract_payload(
    task: BackgroundTask,
    attempt_hash: str,
    *,
    agent_plan_approval_contract: dict[str, Any],
) -> dict[str, Any]:
    payload = task.payload if isinstance(task.payload, dict) else {}
    agent_plan_approval_hash = str(
        ((agent_plan_approval_contract.get("approval") or {}).get("approval_contract_hash")) or ""
    )
    return {
        "version": PREPARE_VERSION,
        "task_id": task.id,
        "project_id": task.project_id,
        "plan_hash": payload.get("plan_hash"),
        "attempt_manifest_hash": attempt_hash,
        "agent_plan_approval_contract_hash": agent_plan_approval_hash,
        "consume_tool": "execute_longform_chapter_batch",
        "required_confirmation": {
            "confirm_execute": True,
            "task_id": task.id,
            "attempt_manifest_hash": attempt_hash,
        },
        "state_bindings": [
            "task.payload.plan_hash",
            "task.payload.chapter_range",
            "task.result.preflight_checkpoint",
            "chapter_content_absence_for_selected_range",
        ],
        "ask_fallback": "deny",
        "high_risk_side_effects": ["chapter_generation", "world_model_intake"],
    }


def _persist_prepare(
    db: Session,
    task: BackgroundTask,
    attempt_manifest: dict[str, Any],
    approval_contract: dict[str, Any],
    agent_plan: dict[str, Any],
    agent_plan_approval_contract: dict[str, Any],
) -> None:
    result = dict(task.result) if isinstance(task.result, dict) else {}
    history = result.get("execution_checkpoints") if isinstance(result.get("execution_checkpoints"), list) else []
    result["attempt_manifest"] = attempt_manifest
    result["approval_contract"] = approval_contract
    result["agent_plan"] = agent_plan
    result["agent_plan_approval_contract"] = agent_plan_approval_contract
    result["agent_plan_approval_contract_hash"] = (agent_plan_approval_contract.get("approval") or {}).get(
        "approval_contract_hash"
    )
    result["execution_checkpoints"] = [
        *history[-9:],
        {
            "version": PREPARE_VERSION,
            "checkpoint_type": "execution_prepare",
            "checkpointed_at": datetime.now(UTC).isoformat(),
            "task_id": task.id,
            "status": "approval_required",
            "attempt_manifest_hash": attempt_manifest["hash"],
            "approval_contract_hash": approval_contract["hash"],
        },
    ]
    task.result = result
    db.add(task)
    db.commit()
    db.refresh(task)


def _blocked_output(task: BackgroundTask, *, reason: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    output = {
        "status": "blocked",
        "prepare_version": PREPARE_VERSION,
        "project_id": task.project_id,
        "task": _task_payload(task),
        "reason": reason,
        "side_effects": {
            "executed": [],
            "skipped": ["background_task_result_execution_prepare", *SKIPPED_SIDE_EFFECTS],
            "blocked_high_risk": ["chapter_generation", "world_model_intake"],
        },
        "recommended_next_tools": _recommended_next_tools(reason),
        "trace": {
            "selected_tools": ["prepare_longform_chapter_batch_execution"],
            "rejected_tools": [{"tool_name": "prepare_longform_chapter_batch_execution", "reason": reason}],
        },
    }
    if extra:
        output.update(extra)
    return output


def _recommended_next_tools(reason: str) -> list[str]:
    if reason in {
        "missing_ready_preflight_checkpoint",
        "preflight_checkpoint_not_ready",
        "preflight_checkpoint_version_mismatch",
        "preflight_checkpoint_boundary_mismatch",
        "preflight_checkpoint_safe_nodes_mismatch",
    }:
        return ["execute_longform_chapter_batch_preflight"]
    return ["inspect_longform_chapter_batch"]


def _task_payload(task: BackgroundTask) -> dict[str, Any]:
    payload = task.payload if isinstance(task.payload, dict) else {}
    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "plan_hash": payload.get("plan_hash"),
        "chapter_range": payload.get("chapter_range") if isinstance(payload.get("chapter_range"), dict) else None,
        "queue_policy": payload.get("queue_policy") if isinstance(payload.get("queue_policy"), dict) else {},
    }


def _chapter_indexes(payload: dict[str, Any]) -> list[int]:
    batch = payload.get("batch") if isinstance(payload.get("batch"), dict) else {}
    values = batch.get("chapter_indexes") if isinstance(batch.get("chapter_indexes"), list) else []
    return [int(value) for value in values if _optional_int(value) is not None]


def _dag_node_ids(payload: dict[str, Any]) -> list[str]:
    dag = payload.get("dag") if isinstance(payload.get("dag"), dict) else {}
    nodes = dag.get("nodes") if isinstance(dag.get("nodes"), list) else []
    return [str(node.get("node_id") or "") for node in nodes if isinstance(node, dict)]


def _generated_chapters(db: Session, project_id: str, chapter_indexes: list[int]) -> list[int]:
    if not chapter_indexes:
        return []
    rows = (
        db.query(ChapterContent.chapter_index)
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.chapter_index.in_(chapter_indexes),
            ChapterContent.content.isnot(None),
            ChapterContent.content != "",
        )
        .order_by(ChapterContent.chapter_index.asc())
        .all()
    )
    return [int(row.chapter_index) for row in rows]


def _stable_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _optional_int(value: object) -> int | None:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None

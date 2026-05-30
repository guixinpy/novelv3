from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.models import BackgroundTask, ChapterContent, Project
from app.services.actions.action_execution_service import ActionExecutionService
from app.services.tasks.background_task_service import (
    TASK_CANCELLED,
    TASK_COMPLETED,
    TASK_FAILED,
    TASK_PENDING,
    BackgroundTaskService,
)
from app.services.writing_agent.approval_contract import verify_agent_plan_approval_contract
from app.services.writing_agent.approval_verification_event import build_approval_verification_event
from app.services.writing_agent.agent_step_binding import verify_resource_binding_target
from app.services.writing_agent.batch_enqueue import BATCH_TASK_TYPE
from app.services.writing_agent.batch_execution_prepare import PREPARE_VERSION
from app.services.writing_agent.batch_preflight import PREFLIGHT_VERSION

EXECUTE_VERSION = "phase62.longform_batch_execute_one.v1"
STOPPED_BEFORE_NODE = "chapter_generation"
REQUIRED_SAFE_NODES = ["preflight_gate"]
TERMINAL_STATUSES = {TASK_COMPLETED, TASK_FAILED, TASK_CANCELLED}


def execution_checkpoints_for_resume(task: BackgroundTask) -> list[dict[str, Any]]:
    result = task.result if isinstance(task.result, dict) else {}
    checkpoints = result.get("execution_checkpoints") if isinstance(result.get("execution_checkpoints"), list) else []
    normalized: list[dict[str, Any]] = []
    for checkpoint in checkpoints:
        if not isinstance(checkpoint, dict):
            continue
        chapter_index = _optional_int(checkpoint.get("chapter_index"))
        if chapter_index is None:
            selected = checkpoint.get("selected_chapter_indexes")
            if isinstance(selected, list) and selected:
                chapter_index = _optional_int(selected[0])
        if chapter_index is None:
            continue
        normalized.append(
            {
                "checkpoint_type": str(checkpoint.get("checkpoint_type") or ""),
                "status": str(checkpoint.get("status") or ""),
                "chapter_index": chapter_index,
                "task_id": str(checkpoint.get("task_id") or task.id),
                "trace_id": checkpoint.get("trace_id"),
                "error": checkpoint.get("error"),
                "checkpointed_at": checkpoint.get("checkpointed_at"),
            }
        )
    return normalized


async def execute_longform_chapter_batch(
    db: Session,
    project_id: str,
    *,
    task_id: str | None,
    confirm_execute: bool,
    attempt_manifest_hash: str | None,
    approval_contract_hash: str | None,
    approval_tool_metadata_provider: Callable[[dict[str, Any]], dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    if not task_id:
        return {
            "status": "failed",
            "error": "task_id is required",
            "project_id": project_id,
            "execute_version": EXECUTE_VERSION,
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
            "execute_version": EXECUTE_VERSION,
            "project_id": project_id,
            "task_id": task_id,
            "trace": {
                "selected_tools": ["execute_longform_chapter_batch"],
                "rejected_tools": [{"tool_name": "execute_longform_chapter_batch", "reason": "selected_task_not_found"}],
            },
        }

    blocked_reason = _validate_execution_request(
        task,
        confirm_execute=confirm_execute,
        attempt_manifest_hash=attempt_manifest_hash,
        approval_contract_hash=approval_contract_hash,
    )
    if blocked_reason:
        return _blocked_output(task, reason=blocked_reason)

    agent_plan_approval_verification = _verify_agent_plan_approval(
        task,
        approval_tool_metadata_provider=approval_tool_metadata_provider,
    )
    if agent_plan_approval_verification.get("status") != "ready":
        return _blocked_output(
            task,
            reason=_agent_plan_approval_block_reason(agent_plan_approval_verification),
            extra={
                "agent_plan_approval_verification": agent_plan_approval_verification,
                "approval_verification_event": build_approval_verification_event(agent_plan_approval_verification),
            },
        )

    result = task.result if isinstance(task.result, dict) else {}
    attempt_manifest = result["attempt_manifest"]
    selected_chapters = [int(value) for value in attempt_manifest.get("chapter_indexes", [])]
    generated = _generated_chapters(db, task.project_id, selected_chapters)
    if generated:
        return _blocked_output(
            task,
            reason="chapter_state_drift",
            extra={"generated_chapter_indexes": generated},
        )

    chapter_index = selected_chapters[0]
    binding_check = verify_resource_binding_target(
        agent_plan_approval_verification,
        tool_name="generate_chapter",
        target_type="chapter",
        target_id=f"chapter:{chapter_index}",
    )
    if binding_check.get("status") != "ready":
        return _blocked_output(
            task,
            reason=str(binding_check.get("reason") or "resource_binding_target_mismatch"),
            extra={
                "agent_plan_approval_verification": agent_plan_approval_verification,
                "approval_verification_event": build_approval_verification_event(agent_plan_approval_verification),
                "execution_resource_binding": binding_check,
            },
        )

    generation = await ActionExecutionService(db).execute(
        "generate_chapter",
        project_id,
        action_params={"chapter_index": chapter_index},
    )
    if not isinstance(generation, dict):
        generation = {"status": "failed", "error": "generate_chapter returned non-dict result"}

    generation_status = str(generation.get("status") or "")
    if generation_status == "failed":
        _persist_execution_failure(db, task, chapter_index=chapter_index, generation=generation)
        return {
            "status": "failed",
            "execute_version": EXECUTE_VERSION,
            "project_id": project_id,
            "task": _task_payload(task),
            "chapter_index": chapter_index,
            "generation": generation,
            "error": str(generation.get("error") or "generate_chapter failed"),
            "side_effects": _side_effects(executed=["generate_chapter"], failed=True),
            "trace": _trace(reason="generate_chapter_failed"),
        }

    if not _chapter_content_exists(db, task.project_id, chapter_index):
        failure = {**generation, "status": "failed", "error": "chapter_content_missing_after_generation"}
        _persist_execution_failure(db, task, chapter_index=chapter_index, generation=failure)
        return {
            "status": "failed",
            "execute_version": EXECUTE_VERSION,
            "project_id": project_id,
            "task": _task_payload(task),
            "chapter_index": chapter_index,
            "generation": failure,
            "error": "chapter_content_missing_after_generation",
            "side_effects": _side_effects(executed=["generate_chapter"], failed=True),
            "trace": _trace(reason="chapter_content_missing_after_generation"),
        }

    persisted_task, execution_checkpoint, batch_execution_result = _persist_execution_success(
        db,
        task,
        chapter_index=chapter_index,
        generation=generation,
        attempt_manifest_hash=str(attempt_manifest_hash),
        approval_contract_hash=str(approval_contract_hash),
    )
    trace_id = str(generation.get("trace_id") or "") or None
    return {
        "status": "completed",
        "execute_version": EXECUTE_VERSION,
        "project_id": project_id,
        "task": _task_payload(persisted_task),
        "chapter_index": chapter_index,
        "executed_chapter_indexes": [chapter_index],
        "attempt_manifest_hash": attempt_manifest_hash,
        "approval_contract_hash": approval_contract_hash,
        "generation": generation,
        "trace_id": trace_id,
        "evidence": {
            "chapter_content_written": True,
            "task_progress_checkpoint_updated": True,
            "execution_checkpoint_written": True,
            "trace_id": trace_id,
            "agent_plan_approval_verified": True,
        },
        "execution_checkpoint": execution_checkpoint,
        "batch_execution_result": batch_execution_result,
        "agent_plan_approval_verification": agent_plan_approval_verification,
        "approval_verification_event": build_approval_verification_event(agent_plan_approval_verification),
        "execution_resource_binding": binding_check,
        "side_effects": _side_effects(
            executed=[
                "generate_chapter",
                "background_task_result_execution_checkpoint",
                "background_task_range_progress",
            ],
            failed=False,
        ),
        "recommended_next_tools": [
            "review_chapter_quality",
            "review_chapter_continuity",
            "analyze_chapter_world_model",
            "inspect_longform_chapter_batch",
        ],
        "trace": _trace(),
    }


def _validate_execution_request(
    task: BackgroundTask,
    *,
    confirm_execute: bool,
    attempt_manifest_hash: str | None,
    approval_contract_hash: str | None,
) -> str | None:
    if str(task.status or "") in TERMINAL_STATUSES:
        return "task_status_is_terminal"
    if str(task.status or "") != TASK_PENDING:
        return "task_status_not_pending"
    if confirm_execute is not True:
        return "confirmation_required"

    result = task.result if isinstance(task.result, dict) else {}
    attempt_manifest = result.get("attempt_manifest") if isinstance(result.get("attempt_manifest"), dict) else None
    approval_contract = result.get("approval_contract") if isinstance(result.get("approval_contract"), dict) else None
    if attempt_manifest is None or approval_contract is None:
        return "missing_approval_contract"
    if attempt_manifest.get("hash") != str(attempt_manifest_hash or ""):
        return "attempt_manifest_hash_mismatch"
    if approval_contract.get("hash") != str(approval_contract_hash or ""):
        return "approval_contract_hash_mismatch"
    if _stable_hash(_attempt_payload_for_hash(attempt_manifest)) != attempt_manifest.get("hash"):
        return "attempt_manifest_integrity_mismatch"
    if _stable_hash(_contract_payload_for_hash(approval_contract)) != approval_contract.get("hash"):
        return "approval_contract_integrity_mismatch"

    required_confirmation = approval_contract.get("required_confirmation")
    if required_confirmation != {
        "confirm_execute": True,
        "task_id": task.id,
        "attempt_manifest_hash": attempt_manifest.get("hash"),
        "approval_contract_hash": approval_contract.get("hash"),
    }:
        return "approval_contract_confirmation_mismatch"
    if approval_contract.get("consume_tool") != "execute_longform_chapter_batch":
        return "approval_contract_consume_tool_mismatch"
    if attempt_manifest.get("version") != PREPARE_VERSION or approval_contract.get("version") != PREPARE_VERSION:
        return "approval_contract_version_mismatch"
    if attempt_manifest.get("task_id") != task.id or approval_contract.get("task_id") != task.id:
        return "approval_contract_task_mismatch"
    if attempt_manifest.get("project_id") != task.project_id or approval_contract.get("project_id") != task.project_id:
        return "approval_contract_project_mismatch"
    if attempt_manifest.get("task_type") != BATCH_TASK_TYPE:
        return "attempt_manifest_task_type_mismatch"

    payload = task.payload if isinstance(task.payload, dict) else {}
    if attempt_manifest.get("plan_hash") != payload.get("plan_hash"):
        return "task_plan_hash_drift"
    if approval_contract.get("plan_hash") != payload.get("plan_hash"):
        return "approval_contract_plan_hash_drift"
    if approval_contract.get("attempt_manifest_hash") != attempt_manifest.get("hash"):
        return "approval_contract_attempt_hash_mismatch"
    if attempt_manifest.get("chapter_range") != payload.get("chapter_range"):
        return "task_chapter_range_drift"
    if attempt_manifest.get("dag_node_ids") != _dag_node_ids(payload):
        return "task_dag_drift"

    selected_chapters = [_optional_int(value) for value in attempt_manifest.get("chapter_indexes", [])]
    if any(value is None for value in selected_chapters):
        return "attempt_manifest_invalid_chapter_indexes"
    chapter_indexes = [int(value) for value in selected_chapters if value is not None]
    if len(chapter_indexes) != 1:
        return "phase62_requires_single_chapter_manifest"
    if chapter_indexes != _chapter_indexes(payload):
        return "task_batch_chapter_drift"

    checkpoint = result.get("preflight_checkpoint") if isinstance(result.get("preflight_checkpoint"), dict) else None
    checkpoint_error = _validate_preflight_checkpoint(task, checkpoint, selected_chapters=chapter_indexes)
    if checkpoint_error:
        return checkpoint_error
    if attempt_manifest.get("preflight_checkpoint") != _attempt_preflight_checkpoint(checkpoint):
        return "attempt_manifest_preflight_drift"
    return None


def _verify_agent_plan_approval(
    task: BackgroundTask,
    *,
    approval_tool_metadata_provider: Callable[[dict[str, Any]], dict[str, dict[str, Any]]] | None,
) -> dict[str, Any]:
    result = task.result if isinstance(task.result, dict) else {}
    agent_plan = result.get("agent_plan") if isinstance(result.get("agent_plan"), dict) else None
    agent_plan_approval_contract = (
        result.get("agent_plan_approval_contract")
        if isinstance(result.get("agent_plan_approval_contract"), dict)
        else None
    )
    phase61_approval_contract = (
        result.get("approval_contract") if isinstance(result.get("approval_contract"), dict) else None
    )
    if agent_plan is None or agent_plan_approval_contract is None or phase61_approval_contract is None:
        return _agent_plan_approval_blocked("agent_plan_approval_verification_missing")

    agent_plan_approval_hash = str(
        ((agent_plan_approval_contract.get("approval") or {}).get("approval_contract_hash")) or ""
    )
    if not agent_plan_approval_hash:
        return _agent_plan_approval_blocked("agent_plan_approval_verification_missing")
    if phase61_approval_contract.get("agent_plan_approval_contract_hash") != agent_plan_approval_hash:
        return _agent_plan_approval_blocked("agent_plan_approval_hash_mismatch")
    if approval_tool_metadata_provider is None:
        return _agent_plan_approval_blocked("agent_plan_tool_metadata_missing")

    return verify_agent_plan_approval_contract(
        agent_plan,
        approval_contract_hash=agent_plan_approval_hash,
        approval_contract=agent_plan_approval_contract,
        project_id=task.project_id,
        tool_metadata_by_name=approval_tool_metadata_provider(agent_plan),
    )


def _agent_plan_approval_blocked(reason: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "version": "phase111.agent_plan_approval_execution_gate.v1",
        "reason": reason,
        "recommended_next_tools": _recommended_next_tools(reason),
        "trace": {"reason": reason},
    }


def _agent_plan_approval_block_reason(verification: dict[str, Any]) -> str:
    reason = str(verification.get("reason") or "")
    if reason in {"agent_plan_approval_verification_missing", "agent_plan_tool_metadata_missing"}:
        return reason
    if reason == "approval_contract_hash_mismatch":
        return "agent_plan_approval_hash_mismatch"
    if reason == "approval_contract_snapshot_mismatch":
        return "agent_plan_approval_snapshot_mismatch"
    if reason == "approval_contract_project_mismatch":
        return "agent_plan_approval_project_mismatch"
    if reason == "tool_contract_drift":
        return "agent_plan_tool_contract_drift"
    return "agent_plan_approval_not_ready"


def _validate_preflight_checkpoint(
    task: BackgroundTask,
    checkpoint: dict[str, Any] | None,
    *,
    selected_chapters: list[int],
) -> str | None:
    if checkpoint is None:
        return "missing_ready_preflight_checkpoint"
    if checkpoint.get("version") != PREFLIGHT_VERSION:
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
    if checkpoint.get("selected_chapter_indexes") != selected_chapters:
        return "preflight_checkpoint_chapter_mismatch"
    if checkpoint.get("ready_chapter_indexes") != selected_chapters:
        return "preflight_checkpoint_not_ready"
    if checkpoint.get("blocked_chapter_indexes") not in ([], None):
        return "preflight_checkpoint_not_ready"
    return None


def _persist_execution_success(
    db: Session,
    task: BackgroundTask,
    *,
    chapter_index: int,
    generation: dict[str, Any],
    attempt_manifest_hash: str,
    approval_contract_hash: str,
) -> tuple[BackgroundTask, dict[str, Any], dict[str, Any]]:
    task = BackgroundTaskService(db).mark_range_progress(task.id, completed_chapter_index=chapter_index)
    result = dict(task.result) if isinstance(task.result, dict) else {}
    history = result.get("execution_checkpoints") if isinstance(result.get("execution_checkpoints"), list) else []
    now = datetime.now(UTC).isoformat()
    checkpoint = {
        "version": EXECUTE_VERSION,
        "checkpoint_type": "chapter_generation",
        "checkpointed_at": now,
        "task_id": task.id,
        "status": "completed",
        "chapter_index": chapter_index,
        "attempt_manifest_hash": attempt_manifest_hash,
        "approval_contract_hash": approval_contract_hash,
        "trace_id": generation.get("trace_id"),
    }
    batch_execution_result = {
        "version": EXECUTE_VERSION,
        "status": "chapter_generated",
        "executed_at": now,
        "chapter_index": chapter_index,
        "executed_chapter_indexes": [chapter_index],
        "attempt_manifest_hash": attempt_manifest_hash,
        "approval_contract_hash": approval_contract_hash,
        "generation": generation,
        "trace_id": generation.get("trace_id"),
    }
    result["batch_execution_result"] = batch_execution_result
    result["execution_checkpoints"] = [*history[-9:], checkpoint]
    task.result = result
    db.add(task)
    db.commit()
    db.refresh(task)
    return task, checkpoint, batch_execution_result


def _persist_execution_failure(
    db: Session,
    task: BackgroundTask,
    *,
    chapter_index: int,
    generation: dict[str, Any],
) -> None:
    result = dict(task.result) if isinstance(task.result, dict) else {}
    history = result.get("execution_checkpoints") if isinstance(result.get("execution_checkpoints"), list) else []
    checkpoint = {
        "version": EXECUTE_VERSION,
        "checkpoint_type": "chapter_generation",
        "checkpointed_at": datetime.now(UTC).isoformat(),
        "task_id": task.id,
        "status": "failed",
        "chapter_index": chapter_index,
        "error": generation.get("error"),
        "trace_id": generation.get("trace_id"),
    }
    result["batch_execution_result"] = {
        "version": EXECUTE_VERSION,
        "status": "failed",
        "chapter_index": chapter_index,
        "generation": generation,
        "trace_id": generation.get("trace_id"),
    }
    result["execution_checkpoints"] = [*history[-9:], checkpoint]
    task.result = result
    db.add(task)
    db.commit()
    db.refresh(task)


def _blocked_output(task: BackgroundTask, *, reason: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    output = {
        "status": "blocked",
        "execute_version": EXECUTE_VERSION,
        "project_id": task.project_id,
        "task": _task_payload(task),
        "reason": reason,
        "side_effects": _side_effects(executed=[], failed=False),
        "recommended_next_tools": _recommended_next_tools(reason),
        "trace": _trace(reason=reason),
    }
    if extra:
        output.update(extra)
    return output


def _recommended_next_tools(reason: str) -> list[str]:
    if reason in {
        "agent_plan_approval_verification_missing",
        "agent_plan_approval_hash_mismatch",
        "agent_plan_approval_snapshot_mismatch",
        "agent_plan_approval_project_mismatch",
        "agent_plan_approval_not_ready",
    }:
        return ["prepare_longform_chapter_batch_execution"]
    if reason in {"agent_plan_tool_contract_drift", "agent_plan_tool_metadata_missing"}:
        return ["inspect_agent_tool_contracts"]
    if reason in {"resource_binding_missing", "resource_binding_target_mismatch"}:
        return ["prepare_longform_chapter_batch_execution"]
    if reason in {
        "missing_ready_preflight_checkpoint",
        "preflight_checkpoint_version_mismatch",
        "preflight_checkpoint_boundary_mismatch",
        "preflight_checkpoint_safe_nodes_mismatch",
        "preflight_checkpoint_not_ready",
    }:
        return ["prepare_longform_chapter_batch_preflight"]
    if reason in {"missing_approval_contract", "attempt_manifest_preflight_drift"}:
        return ["prepare_longform_chapter_batch_execution"]
    return ["inspect_longform_chapter_batch"]


def _side_effects(*, executed: list[str], failed: bool) -> dict[str, Any]:
    return {
        "executed": executed,
        "skipped": [
            "start_runner",
            "quality_review",
            "continuity_review",
            "world_model_resolution",
            "auto_resume_next_chapter",
        ],
        "inherited": ["inherited_generate_chapter_post_generation_hooks"] if executed else [],
        "failed": failed,
    }


def _trace(reason: str | None = None) -> dict[str, Any]:
    rejected = []
    if reason:
        rejected.append({"tool_name": "execute_longform_chapter_batch", "reason": reason})
    rejected.extend(
        [
            {"tool_name": "start_runner", "reason": "phase62_no_runner"},
            {"tool_name": "review_chapter_quality", "reason": "phase62_generation_only"},
            {"tool_name": "review_chapter_continuity", "reason": "phase62_generation_only"},
            {"tool_name": "analyze_chapter_world_model", "reason": "phase62_generation_only"},
        ]
    )
    return {
        "selected_tools": ["execute_longform_chapter_batch", "generate_chapter"] if reason is None else [],
        "rejected_tools": rejected,
        "source": "phase61_approval_contract_plus_live_task_state",
    }


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


def _attempt_payload_for_hash(attempt_manifest: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in attempt_manifest.items() if key not in {"hash", "prepared_at"}}


def _contract_payload_for_hash(approval_contract: dict[str, Any]) -> dict[str, Any]:
    payload = {key: value for key, value in approval_contract.items() if key != "hash"}
    confirmation = dict(payload.get("required_confirmation") or {})
    confirmation.pop("approval_contract_hash", None)
    payload["required_confirmation"] = confirmation
    return payload


def _attempt_preflight_checkpoint(checkpoint: dict[str, Any] | None) -> dict[str, Any] | None:
    if checkpoint is None:
        return None
    return {
        "version": checkpoint.get("version"),
        "checkpointed_at": checkpoint.get("checkpointed_at"),
        "status": checkpoint.get("status"),
        "safe_nodes_executed": checkpoint.get("safe_nodes_executed"),
        "stopped_before_node": checkpoint.get("stopped_before_node"),
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


def _chapter_content_exists(db: Session, project_id: str, chapter_index: int) -> bool:
    return (
        db.query(ChapterContent.id)
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.chapter_index == chapter_index,
            ChapterContent.content.isnot(None),
            ChapterContent.content != "",
        )
        .first()
        is not None
    )


def _stable_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _optional_int(value: object) -> int | None:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None

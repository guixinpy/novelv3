from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import BackgroundTask, Project
from app.services.writing_agent.agent_step_binding import build_agent_step_binding, verify_resource_binding_target
from app.services.writing_agent.approval_contract import (
    build_agent_plan_approval_contract,
    verify_agent_plan_approval_contract,
)
from app.services.writing_agent.approval_verification_event import build_approval_verification_event
from app.services.writing_agent.batch_enqueue import BATCH_TASK_TYPE
from app.services.writing_agent.batch_execution_prepare import prepare_longform_chapter_batch_execution
from app.services.writing_agent.mutation_fingerprint import build_mutation_fingerprint

PREPARE_LONGFORM_CHAPTER_BATCH_EXECUTION_PREPARE_VERSION = "phase201.longform_batch_execution_prepare_prepare.v1"
EXECUTE_LONGFORM_CHAPTER_BATCH_EXECUTION_PREPARE_WITH_APPROVAL_VERSION = (
    "phase201.longform_batch_execution_prepare_with_approval_execute.v1"
)
APPROVAL_GATE_VERSION = "phase201.longform_batch_execution_prepare_agent_plan_approval.v1"
TARGET_TYPE = "background_task_execution_prepare"


def prepare_longform_chapter_batch_execution_prepare(
    db: Session,
    project_id: str,
    *,
    task_id: str | None,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    task = _find_batch_task(db, project_id, task_id)
    if task is None:
        return _not_found_output(project_id, task_id, prepare=True)

    preview = prepare_longform_chapter_batch_execution(
        db,
        project_id,
        task_id=task.id,
        confirm_prepare=False,
    )
    if not (preview.get("status") == "blocked" and preview.get("reason") == "prepare_confirmation_required"):
        return {
            **preview,
            "prepare_gate_version": PREPARE_LONGFORM_CHAPTER_BATCH_EXECUTION_PREPARE_VERSION,
            "target_type": TARGET_TYPE,
            "side_effects": {"executed": [], "skipped": ["background_task_result_execution_prepare"]},
        }

    agent_plan = _direct_execution_prepare_agent_plan(project_id, task_id=task.id)
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    return {
        "status": "approval_required",
        "prepare_version": PREPARE_LONGFORM_CHAPTER_BATCH_EXECUTION_PREPARE_VERSION,
        "project_id": project_id,
        "target_type": TARGET_TYPE,
        "task": _task_payload(task),
        "execution_prepare_preview": preview,
        "mutation_fingerprint": first_step.get("mutation_fingerprint"),
        "tool_call_id": first_step.get("tool_call_id"),
        "resource_binding": first_step.get("resource_binding"),
        "agent_plan": agent_plan,
        "agent_plan_approval_contract": approval_contract,
        "agent_plan_approval_contract_hash": approval_hash,
        "required_confirmation": {
            "confirm_execute": True,
            "approval_contract_hash": approval_hash,
        },
        "side_effects": {"executed": [], "skipped": ["background_task_result_execution_prepare"]},
        "recommended_next_tools": ["execute_longform_chapter_batch_execution_prepare_with_approval"],
        "trace": {
            "selected_tools": ["prepare_longform_chapter_batch_execution_prepare"],
            "rejected_tools": [
                {"tool_name": "prepare_longform_chapter_batch_execution", "reason": "approval_required_before_write"}
            ],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def execute_longform_chapter_batch_execution_prepare_with_approval(
    db: Session,
    project_id: str,
    *,
    task_id: str | None,
    confirm_execute: bool,
    approval_contract_hash: str | None,
    approval_contract: dict[str, Any] | None,
    approval_tool_metadata_provider,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    task = _find_batch_task(db, project_id, task_id)
    if task is None:
        return _not_found_output(project_id, task_id, prepare=False)
    if confirm_execute is not True:
        return _blocked_output(project_id, task_id=task.id, reason="confirmation_required")
    if not approval_contract_hash or not isinstance(approval_contract, dict):
        return _blocked_output(project_id, task_id=task.id, reason="approval_contract_required")
    if approval_tool_metadata_provider is None:
        return _blocked_output(project_id, task_id=task.id, reason="agent_plan_tool_metadata_missing")

    agent_plan = _direct_execution_prepare_agent_plan(project_id, task_id=task.id)
    verification = verify_agent_plan_approval_contract(
        agent_plan,
        approval_contract_hash=approval_contract_hash,
        approval_contract=approval_contract,
        project_id=project_id,
        tool_metadata_by_name=approval_tool_metadata_provider(agent_plan),
    )
    if verification.get("status") != "ready":
        return _blocked_output(
            project_id,
            task_id=task.id,
            reason=str(verification.get("reason") or "agent_plan_approval_not_ready"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
            },
        )

    binding_check = verify_resource_binding_target(
        verification,
        tool_name="prepare_longform_chapter_batch_execution",
        target_type=TARGET_TYPE,
        target_id=_target_id(task.id),
    )
    if binding_check.get("status") != "ready":
        return _blocked_output(
            project_id,
            task_id=task.id,
            reason=str(binding_check.get("reason") or "resource_binding_target_mismatch"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
                "execution_resource_binding": binding_check,
            },
        )

    result = prepare_longform_chapter_batch_execution(
        db,
        project_id,
        task_id=task.id,
        confirm_prepare=True,
    )
    return {
        **result,
        "execute_version": EXECUTE_LONGFORM_CHAPTER_BATCH_EXECUTION_PREPARE_WITH_APPROVAL_VERSION,
        "target_type": TARGET_TYPE,
        "agent_plan_approval_verification": verification,
        "approval_verification_event": build_approval_verification_event(verification),
        "execution_resource_binding": binding_check,
        "evidence": {
            "agent_plan_approval_verified": True,
            "legacy_action": "prepare_longform_chapter_batch_execution",
            "execution_route": "static_adapter",
        },
        "trace": {
            **(result.get("trace") if isinstance(result.get("trace"), dict) else {}),
            "selected_tools": ["execute_longform_chapter_batch_execution_prepare_with_approval"],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def _direct_execution_prepare_agent_plan(project_id: str, *, task_id: str) -> dict[str, Any]:
    params = {"task_id": task_id}
    plan_id = f"direct-longform-batch-execution-prepare:{task_id}"
    mutation_fingerprint = build_mutation_fingerprint(project_id, "prepare_longform_chapter_batch_execution", params)
    step = {
        "step_index": 1,
        "step_id": plan_id,
        "tool_name": "prepare_longform_chapter_batch_execution",
        "approval_executor_tool_name": "execute_longform_chapter_batch_execution_prepare_with_approval",
        "params": params,
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": "将已通过预检的长篇章节批次固化为执行尝试清单和审批契约。",
    }
    step.update(
        build_agent_step_binding(
            project_id=project_id,
            plan_id=plan_id,
            source_projection_id=None,
            step=step,
            mutation_fingerprint=mutation_fingerprint,
        )
    )
    return {
        "project_id": project_id,
        "intent_class": "direct_longform_batch_execution_prepare",
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": None,
            "planner_version": PREPARE_LONGFORM_CHAPTER_BATCH_EXECUTION_PREPARE_VERSION,
        },
        "steps": [step],
    }


def _find_batch_task(db: Session, project_id: str, task_id: str | None) -> BackgroundTask | None:
    if not task_id:
        return None
    return (
        db.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == project_id,
            BackgroundTask.task_type == BATCH_TASK_TYPE,
            BackgroundTask.id == task_id,
        )
        .first()
    )


def _not_found_output(project_id: str, task_id: str | None, *, prepare: bool) -> dict[str, Any]:
    version_key = "prepare_version" if prepare else "execute_version"
    version = (
        PREPARE_LONGFORM_CHAPTER_BATCH_EXECUTION_PREPARE_VERSION
        if prepare
        else EXECUTE_LONGFORM_CHAPTER_BATCH_EXECUTION_PREPARE_WITH_APPROVAL_VERSION
    )
    return {
        "status": "not_found",
        version_key: version,
        "project_id": project_id,
        "task_id": task_id,
        "target_type": TARGET_TYPE,
        "side_effects": {"executed": [], "skipped": ["background_task_result_execution_prepare"]},
        "trace": {
            "selected_tools": [
                "prepare_longform_chapter_batch_execution_prepare"
                if prepare
                else "execute_longform_chapter_batch_execution_prepare_with_approval"
            ],
            "rejected_tools": [{"tool_name": "prepare_longform_chapter_batch_execution", "reason": "task_not_found"}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def _blocked_output(
    project_id: str,
    *,
    task_id: str,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = {
        "status": "blocked",
        "execute_version": EXECUTE_LONGFORM_CHAPTER_BATCH_EXECUTION_PREPARE_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "task_id": task_id,
        "target_type": TARGET_TYPE,
        "reason": reason,
        "side_effects": {"executed": [], "skipped": ["background_task_result_execution_prepare"]},
        "recommended_next_tools": ["prepare_longform_chapter_batch_execution_prepare"],
        "trace": {
            "selected_tools": ["execute_longform_chapter_batch_execution_prepare_with_approval"],
            "rejected_tools": [{"tool_name": "prepare_longform_chapter_batch_execution", "reason": reason}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }
    if extra:
        output.update(extra)
    return output


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


def _target_id(task_id: str) -> str:
    return f"{TARGET_TYPE}:{task_id}"

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
from app.services.writing_agent.batch_preflight import execute_longform_chapter_batch_preflight
from app.services.writing_agent.mutation_fingerprint import build_mutation_fingerprint

PREPARE_LONGFORM_CHAPTER_BATCH_PREFLIGHT_VERSION = "phase200.longform_batch_preflight_prepare.v1"
EXECUTE_LONGFORM_CHAPTER_BATCH_PREFLIGHT_WITH_APPROVAL_VERSION = (
    "phase200.longform_batch_preflight_with_approval_execute.v1"
)
APPROVAL_GATE_VERSION = "phase200.longform_batch_preflight_agent_plan_approval.v1"
TARGET_TYPE = "background_task_checkpoint"


def prepare_longform_chapter_batch_preflight(
    db: Session,
    project_id: str,
    *,
    task_id: str | None,
    max_chapters: int | None = None,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    task = _find_batch_task(db, project_id, task_id)
    if task is None:
        return _not_found_output(project_id, task_id, prepare=True)

    agent_plan = _direct_preflight_agent_plan(project_id, task_id=task.id, max_chapters=max_chapters)
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    return {
        "status": "approval_required",
        "prepare_version": PREPARE_LONGFORM_CHAPTER_BATCH_PREFLIGHT_VERSION,
        "project_id": project_id,
        "target_type": TARGET_TYPE,
        "task": _task_payload(task),
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
        "side_effects": {"executed": [], "skipped": ["background_task_result_checkpoint"]},
        "recommended_next_tools": ["execute_longform_chapter_batch_preflight_with_approval"],
        "trace": {
            "selected_tools": ["prepare_longform_chapter_batch_preflight"],
            "rejected_tools": [
                {"tool_name": "execute_longform_chapter_batch_preflight", "reason": "approval_required_before_write"}
            ],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def execute_longform_chapter_batch_preflight_with_approval(
    db: Session,
    project_id: str,
    *,
    task_id: str | None,
    max_chapters: int | None = None,
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

    agent_plan = _direct_preflight_agent_plan(project_id, task_id=task.id, max_chapters=max_chapters)
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
        tool_name="execute_longform_chapter_batch_preflight",
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

    result = execute_longform_chapter_batch_preflight(
        db,
        project_id,
        task_id=task.id,
        max_chapters=max_chapters,
        confirm_checkpoint=True,
    )
    return {
        **result,
        "execute_version": EXECUTE_LONGFORM_CHAPTER_BATCH_PREFLIGHT_WITH_APPROVAL_VERSION,
        "target_type": TARGET_TYPE,
        "agent_plan_approval_verification": verification,
        "approval_verification_event": build_approval_verification_event(verification),
        "execution_resource_binding": binding_check,
        "evidence": {
            "agent_plan_approval_verified": True,
            "legacy_action": "execute_longform_chapter_batch_preflight",
            "execution_route": "static_adapter",
        },
        "trace": {
            **(result.get("trace") if isinstance(result.get("trace"), dict) else {}),
            "selected_tools": ["execute_longform_chapter_batch_preflight_with_approval"],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def _direct_preflight_agent_plan(project_id: str, *, task_id: str, max_chapters: int | None) -> dict[str, Any]:
    params: dict[str, Any] = {"task_id": task_id}
    if max_chapters is not None:
        params["max_chapters"] = max_chapters
    plan_id = f"direct-longform-batch-preflight:{task_id}"
    mutation_fingerprint = build_mutation_fingerprint(project_id, "execute_longform_chapter_batch_preflight", params)
    step = {
        "step_index": 1,
        "step_id": plan_id,
        "tool_name": "execute_longform_chapter_batch_preflight",
        "approval_executor_tool_name": "execute_longform_chapter_batch_preflight_with_approval",
        "params": params,
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": "对长篇章节批次执行安全预检并写入可恢复断点。",
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
        "intent_class": "direct_longform_batch_preflight_checkpoint",
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": None,
            "planner_version": PREPARE_LONGFORM_CHAPTER_BATCH_PREFLIGHT_VERSION,
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
        PREPARE_LONGFORM_CHAPTER_BATCH_PREFLIGHT_VERSION
        if prepare
        else EXECUTE_LONGFORM_CHAPTER_BATCH_PREFLIGHT_WITH_APPROVAL_VERSION
    )
    return {
        "status": "not_found",
        version_key: version,
        "project_id": project_id,
        "task_id": task_id,
        "target_type": TARGET_TYPE,
        "side_effects": {"executed": [], "skipped": ["background_task_result_checkpoint"]},
        "trace": {
            "selected_tools": [
                "prepare_longform_chapter_batch_preflight"
                if prepare
                else "execute_longform_chapter_batch_preflight_with_approval"
            ],
            "rejected_tools": [{"tool_name": "execute_longform_chapter_batch_preflight", "reason": "task_not_found"}],
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
        "execute_version": EXECUTE_LONGFORM_CHAPTER_BATCH_PREFLIGHT_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "task_id": task_id,
        "target_type": TARGET_TYPE,
        "reason": reason,
        "side_effects": {"executed": [], "skipped": ["background_task_result_checkpoint"]},
        "recommended_next_tools": ["prepare_longform_chapter_batch_preflight"],
        "trace": {
            "selected_tools": ["execute_longform_chapter_batch_preflight_with_approval"],
            "rejected_tools": [{"tool_name": "execute_longform_chapter_batch_preflight", "reason": reason}],
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
    return f"{TARGET_TYPE}:{task_id}:preflight"

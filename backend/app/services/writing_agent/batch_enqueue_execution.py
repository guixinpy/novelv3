from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Project
from app.services.writing_agent.agent_step_binding import build_agent_step_binding, verify_resource_binding_target
from app.services.writing_agent.approval_contract import (
    build_agent_plan_approval_contract,
    verify_agent_plan_approval_contract,
)
from app.services.writing_agent.approval_verification_event import build_approval_verification_event
from app.services.writing_agent.batch_enqueue import build_longform_chapter_batch_enqueue
from app.services.writing_agent.mutation_fingerprint import build_mutation_fingerprint

PREPARE_ENQUEUE_LONGFORM_CHAPTER_BATCH_VERSION = "phase199.longform_batch_enqueue_prepare.v1"
EXECUTE_ENQUEUE_LONGFORM_CHAPTER_BATCH_WITH_APPROVAL_VERSION = (
    "phase199.longform_batch_enqueue_with_approval_execute.v1"
)
APPROVAL_GATE_VERSION = "phase199.longform_batch_enqueue_agent_plan_approval.v1"
TARGET_TYPE = "background_task_enqueue"


def prepare_enqueue_longform_chapter_batch(
    db: Session,
    project_id: str,
    *,
    source_run_id: str | None = None,
    start_chapter: int | None = None,
    batch_size: int | None = None,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}

    preview = build_longform_chapter_batch_enqueue(
        db,
        project_id,
        source_run_id=source_run_id,
        start_chapter=start_chapter,
        batch_size=batch_size,
        confirm_enqueue=False,
        plan_hash=None,
    )
    if preview.get("can_enqueue") is not True:
        return {
            **preview,
            "prepare_version": PREPARE_ENQUEUE_LONGFORM_CHAPTER_BATCH_VERSION,
            "target_type": TARGET_TYPE,
            "side_effects": {"executed": [], "skipped": ["enqueue_longform_chapter_batch"]},
        }

    plan_hash = str(preview.get("plan_hash") or "")
    agent_plan = _direct_enqueue_longform_chapter_batch_agent_plan(
        project_id,
        plan_hash=plan_hash,
        source_run_id=source_run_id,
        start_chapter=start_chapter,
        batch_size=batch_size,
    )
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    return {
        "status": "approval_required",
        "prepare_version": PREPARE_ENQUEUE_LONGFORM_CHAPTER_BATCH_VERSION,
        "project_id": project_id,
        "target_type": TARGET_TYPE,
        "plan_hash": plan_hash,
        "enqueue_preview": preview,
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
        "side_effects": {"executed": [], "skipped": ["enqueue_longform_chapter_batch"]},
        "recommended_next_tools": ["execute_enqueue_longform_chapter_batch_with_approval"],
        "trace": {
            "selected_tools": ["prepare_enqueue_longform_chapter_batch"],
            "rejected_tools": [
                {"tool_name": "enqueue_longform_chapter_batch", "reason": "approval_required_before_write"}
            ],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def execute_enqueue_longform_chapter_batch_with_approval(
    db: Session,
    project_id: str,
    *,
    source_run_id: str | None = None,
    start_chapter: int | None = None,
    batch_size: int | None = None,
    plan_hash: str | None,
    confirm_execute: bool,
    approval_contract_hash: str | None,
    approval_contract: dict[str, Any] | None,
    approval_tool_metadata_provider,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    if confirm_execute is not True:
        return _blocked_output(project_id, reason="confirmation_required")
    if not plan_hash:
        return _blocked_output(project_id, reason="plan_hash_required")
    if not approval_contract_hash or not isinstance(approval_contract, dict):
        return _blocked_output(project_id, reason="approval_contract_required")
    if approval_tool_metadata_provider is None:
        return _blocked_output(project_id, reason="agent_plan_tool_metadata_missing")

    agent_plan = _direct_enqueue_longform_chapter_batch_agent_plan(
        project_id,
        plan_hash=plan_hash,
        source_run_id=source_run_id,
        start_chapter=start_chapter,
        batch_size=batch_size,
    )
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
            reason=str(verification.get("reason") or "agent_plan_approval_not_ready"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
            },
        )

    binding_check = verify_resource_binding_target(
        verification,
        tool_name="enqueue_longform_chapter_batch",
        target_type=TARGET_TYPE,
        target_id=f"{TARGET_TYPE}:{project_id}:{plan_hash}",
    )
    if binding_check.get("status") != "ready":
        return _blocked_output(
            project_id,
            reason=str(binding_check.get("reason") or "resource_binding_target_mismatch"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
                "execution_resource_binding": binding_check,
            },
        )

    result = build_longform_chapter_batch_enqueue(
        db,
        project_id,
        source_run_id=source_run_id,
        start_chapter=start_chapter,
        batch_size=batch_size,
        confirm_enqueue=True,
        plan_hash=plan_hash,
    )
    return {
        **result,
        "execute_version": EXECUTE_ENQUEUE_LONGFORM_CHAPTER_BATCH_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "target_type": TARGET_TYPE,
        "agent_plan_approval_verification": verification,
        "approval_verification_event": build_approval_verification_event(verification),
        "execution_resource_binding": binding_check,
        "evidence": {
            "agent_plan_approval_verified": True,
            "legacy_action": "enqueue_longform_chapter_batch",
            "execution_route": "static_adapter",
        },
        "side_effects": {"executed": ["enqueue_longform_chapter_batch"], "skipped": []},
        "trace": {
            **(result.get("trace") if isinstance(result.get("trace"), dict) else {}),
            "selected_tools": ["execute_enqueue_longform_chapter_batch_with_approval"],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def _direct_enqueue_longform_chapter_batch_agent_plan(
    project_id: str,
    *,
    plan_hash: str,
    source_run_id: str | None,
    start_chapter: int | None,
    batch_size: int | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"plan_hash": plan_hash}
    if source_run_id:
        params["source_run_id"] = source_run_id
    if start_chapter is not None:
        params["start_chapter"] = start_chapter
    if batch_size is not None:
        params["batch_size"] = batch_size

    plan_id = f"direct-enqueue-longform-chapter-batch:{project_id}:{plan_hash}"
    mutation_fingerprint = build_mutation_fingerprint(project_id, "enqueue_longform_chapter_batch", params)
    step = {
        "step_index": 1,
        "step_id": plan_id,
        "tool_name": "enqueue_longform_chapter_batch",
        "approval_executor_tool_name": "execute_enqueue_longform_chapter_batch_with_approval",
        "params": params,
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": "将长篇章节批次计划写入后台任务队列。",
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
        "intent_class": "direct_enqueue_longform_chapter_batch",
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": None,
            "planner_version": PREPARE_ENQUEUE_LONGFORM_CHAPTER_BATCH_VERSION,
        },
        "steps": [step],
    }


def _blocked_output(
    project_id: str,
    *,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = {
        "status": "blocked",
        "execute_version": EXECUTE_ENQUEUE_LONGFORM_CHAPTER_BATCH_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "target_type": TARGET_TYPE,
        "reason": reason,
        "side_effects": {"executed": [], "skipped": ["enqueue_longform_chapter_batch"]},
        "recommended_next_tools": ["prepare_enqueue_longform_chapter_batch"],
        "trace": {
            "selected_tools": ["execute_enqueue_longform_chapter_batch_with_approval"],
            "rejected_tools": [{"tool_name": "enqueue_longform_chapter_batch", "reason": reason}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }
    if extra:
        output.update(extra)
    return output

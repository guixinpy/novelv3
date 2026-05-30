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
from app.services.writing_agent.mutation_fingerprint import build_mutation_fingerprint
from app.services.writing_agent.revision_patch_tool import apply_planner_revision_patch_tool

PREPARE_APPLY_PLANNER_REVISION_PATCH_EXECUTION_VERSION = "phase195.revision_patch_execution_prepare.v1"
EXECUTE_APPLY_PLANNER_REVISION_PATCH_WITH_APPROVAL_VERSION = "phase195.revision_patch_with_approval_execute.v1"
APPROVAL_GATE_VERSION = "phase195.revision_patch_agent_plan_approval.v1"


def prepare_apply_planner_revision_patch_execution(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    revision_id: str | None,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}

    revision_id = _clean_revision_id(revision_id)
    agent_plan = _direct_apply_planner_revision_patch_agent_plan(project_id, chapter_index, revision_id)
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    return {
        "status": "approval_required",
        "prepare_version": PREPARE_APPLY_PLANNER_REVISION_PATCH_EXECUTION_VERSION,
        "project_id": project_id,
        "chapter_index": chapter_index,
        "revision_id": revision_id,
        "target_type": "chapter_revision_patch",
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
        "side_effects": {"executed": [], "skipped": ["apply_planner_revision_patch"]},
        "recommended_next_tools": ["execute_apply_planner_revision_patch_with_approval"],
        "trace": {
            "selected_tools": ["prepare_apply_planner_revision_patch_execution"],
            "rejected_tools": [
                {"tool_name": "apply_planner_revision_patch", "reason": "approval_required_before_write"}
            ],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def execute_apply_planner_revision_patch_with_approval(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    revision_id: str | None,
    confirm_execute: bool,
    approval_contract_hash: str | None,
    approval_contract: dict[str, Any] | None,
    approval_tool_metadata_provider,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}

    revision_id = _clean_revision_id(revision_id)
    if confirm_execute is not True:
        return _blocked_output(project_id, chapter_index, revision_id, reason="confirmation_required")
    if not approval_contract_hash or not isinstance(approval_contract, dict):
        return _blocked_output(project_id, chapter_index, revision_id, reason="approval_contract_required")
    if approval_tool_metadata_provider is None:
        return _blocked_output(project_id, chapter_index, revision_id, reason="agent_plan_tool_metadata_missing")

    agent_plan = _direct_apply_planner_revision_patch_agent_plan(project_id, chapter_index, revision_id)
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
            chapter_index,
            revision_id,
            reason=str(verification.get("reason") or "agent_plan_approval_not_ready"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
            },
        )

    binding_check = verify_resource_binding_target(
        verification,
        tool_name="apply_planner_revision_patch",
        target_type="chapter_revision_patch",
        target_id=_revision_patch_target_id(chapter_index, revision_id),
    )
    if binding_check.get("status") != "ready":
        return _blocked_output(
            project_id,
            chapter_index,
            revision_id,
            reason=str(binding_check.get("reason") or "resource_binding_target_mismatch"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
                "execution_resource_binding": binding_check,
            },
        )

    result = apply_planner_revision_patch_tool(
        db,
        project_id,
        chapter_index=chapter_index,
        revision_id=revision_id,
    )
    return {
        **result,
        "execute_version": EXECUTE_APPLY_PLANNER_REVISION_PATCH_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "target_type": "chapter_revision_patch",
        "agent_plan_approval_verification": verification,
        "approval_verification_event": build_approval_verification_event(verification),
        "execution_resource_binding": binding_check,
        "evidence": {
            "agent_plan_approval_verified": True,
            "legacy_action": "apply_planner_revision_patch",
            "execution_route": "static_adapter",
        },
        "side_effects": {"executed": ["apply_planner_revision_patch"], "skipped": []},
        "trace": {
            "selected_tools": ["execute_apply_planner_revision_patch_with_approval"],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def _direct_apply_planner_revision_patch_agent_plan(
    project_id: str,
    chapter_index: int,
    revision_id: str | None,
) -> dict[str, Any]:
    params = {"chapter_index": chapter_index, "revision_id": revision_id or ""}
    safe_revision_id = revision_id or "missing"
    plan_id = f"direct-apply-planner-revision-patch:{project_id}:chapter:{chapter_index}:revision:{safe_revision_id}"
    mutation_fingerprint = build_mutation_fingerprint(project_id, "apply_planner_revision_patch", params)
    step = {
        "step_index": 1,
        "step_id": plan_id,
        "tool_name": "apply_planner_revision_patch",
        "approval_executor_tool_name": "execute_apply_planner_revision_patch_with_approval",
        "params": params,
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": "应用章节修订补丁并写入正文版本。",
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
        "intent_class": "direct_apply_planner_revision_patch",
        "chapter_index": chapter_index,
        "revision_id": revision_id,
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": None,
            "planner_version": PREPARE_APPLY_PLANNER_REVISION_PATCH_EXECUTION_VERSION,
        },
        "steps": [step],
    }


def _blocked_output(
    project_id: str,
    chapter_index: int,
    revision_id: str | None,
    *,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = {
        "status": "blocked",
        "execute_version": EXECUTE_APPLY_PLANNER_REVISION_PATCH_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "chapter_index": chapter_index,
        "revision_id": revision_id,
        "target_type": "chapter_revision_patch",
        "reason": reason,
        "side_effects": {"executed": [], "skipped": ["apply_planner_revision_patch"]},
        "recommended_next_tools": ["prepare_apply_planner_revision_patch_execution"],
        "trace": {
            "selected_tools": ["execute_apply_planner_revision_patch_with_approval"],
            "rejected_tools": [{"tool_name": "apply_planner_revision_patch", "reason": reason}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }
    if extra:
        output.update(extra)
    return output


def _revision_patch_target_id(chapter_index: int, revision_id: str | None) -> str:
    return f"chapter_revision_patch:{chapter_index}:{revision_id or ''}"


def _clean_revision_id(revision_id: str | None) -> str | None:
    cleaned = str(revision_id or "").strip()
    return cleaned or None

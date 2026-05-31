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
from app.services.writing_agent.world_model_resolution_apply_tool import apply_world_model_proposal_resolution_tool

PREPARE_APPLY_WORLD_MODEL_PROPOSAL_RESOLUTION_VERSION = "phase204.world_model_proposal_apply_prepare.v1"
EXECUTE_APPLY_WORLD_MODEL_PROPOSAL_RESOLUTION_WITH_APPROVAL_VERSION = (
    "phase204.world_model_proposal_apply_with_approval_execute.v1"
)
APPROVAL_GATE_VERSION = "phase204.world_model_proposal_apply_agent_plan_approval.v1"
TARGET_TYPE = "world_model_proposal_resolution"
DIRECT_TOOL = "apply_world_model_proposal_resolution"
EXECUTE_TOOL = "execute_apply_world_model_proposal_resolution_with_approval"


def prepare_apply_world_model_proposal_resolution(
    db: Session,
    project_id: str,
    *,
    decisions: object,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    normalized_decisions = _decisions(decisions)
    preview = apply_world_model_proposal_resolution_tool(
        db,
        project_id,
        decisions=normalized_decisions,
        confirm_apply=False,
    )
    if preview.get("requires_confirmation") is not True:
        return {
            **preview,
            "prepare_version": PREPARE_APPLY_WORLD_MODEL_PROPOSAL_RESOLUTION_VERSION,
            "target_type": TARGET_TYPE,
            "side_effects": {"executed": [], "skipped": [DIRECT_TOOL]},
        }

    agent_plan = _direct_apply_agent_plan(project_id, decisions=normalized_decisions)
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    return {
        "status": "approval_required",
        "prepare_version": PREPARE_APPLY_WORLD_MODEL_PROPOSAL_RESOLUTION_VERSION,
        "project_id": project_id,
        "target_type": TARGET_TYPE,
        "apply_preview": preview,
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
        "side_effects": {"executed": [], "skipped": [DIRECT_TOOL]},
        "recommended_next_tools": [EXECUTE_TOOL],
        "trace": {
            "selected_tools": ["prepare_apply_world_model_proposal_resolution"],
            "rejected_tools": [{"tool_name": DIRECT_TOOL, "reason": "approval_required_before_write"}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def execute_apply_world_model_proposal_resolution_with_approval(
    db: Session,
    project_id: str,
    *,
    decisions: object,
    confirm_execute: bool,
    approval_contract_hash: str | None,
    approval_contract: dict[str, Any] | None,
    approval_tool_metadata_provider,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    normalized_decisions = _decisions(decisions)
    if confirm_execute is not True:
        return _blocked_output(project_id, decisions=normalized_decisions, reason="confirmation_required")
    if not approval_contract_hash or not isinstance(approval_contract, dict):
        return _blocked_output(project_id, decisions=normalized_decisions, reason="approval_contract_required")
    if approval_tool_metadata_provider is None:
        return _blocked_output(project_id, decisions=normalized_decisions, reason="agent_plan_tool_metadata_missing")

    agent_plan = _direct_apply_agent_plan(project_id, decisions=normalized_decisions)
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
            decisions=normalized_decisions,
            reason=str(verification.get("reason") or "agent_plan_approval_not_ready"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
            },
        )

    target = _mutation_target(project_id, normalized_decisions)
    binding_check = verify_resource_binding_target(
        verification,
        tool_name=DIRECT_TOOL,
        target_type=str(target.get("target_type") or ""),
        target_id=str(target.get("target_id") or ""),
    )
    if binding_check.get("status") != "ready":
        return _blocked_output(
            project_id,
            decisions=normalized_decisions,
            reason=str(binding_check.get("reason") or "resource_binding_target_mismatch"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
                "execution_resource_binding": binding_check,
            },
        )

    result = apply_world_model_proposal_resolution_tool(
        db,
        project_id,
        decisions=normalized_decisions,
        confirm_apply=True,
    )
    return {
        **result,
        "execute_version": EXECUTE_APPLY_WORLD_MODEL_PROPOSAL_RESOLUTION_WITH_APPROVAL_VERSION,
        "target_type": TARGET_TYPE,
        "agent_plan_approval_verification": verification,
        "approval_verification_event": build_approval_verification_event(verification),
        "execution_resource_binding": binding_check,
        "evidence": {
            "agent_plan_approval_verified": True,
            "legacy_action": DIRECT_TOOL,
            "execution_route": "static_adapter",
        },
        "side_effects": {"executed": [DIRECT_TOOL], "skipped": []},
        "trace": {
            "selected_tools": [EXECUTE_TOOL],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def _direct_apply_agent_plan(project_id: str, *, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    params = {"decisions": decisions}
    plan_id = f"direct-world-model-proposal-apply:{project_id}:{_target_label(project_id, decisions)}"
    mutation_fingerprint = build_mutation_fingerprint(project_id, DIRECT_TOOL, params)
    step = {
        "step_index": 1,
        "step_id": plan_id,
        "tool_name": DIRECT_TOOL,
        "approval_executor_tool_name": EXECUTE_TOOL,
        "params": params,
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": "应用 Athena 世界模型提案处理决策，写入提案评审结果并影响后续长篇记忆状态。",
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
        "intent_class": "direct_world_model_proposal_apply",
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": None,
            "planner_version": PREPARE_APPLY_WORLD_MODEL_PROPOSAL_RESOLUTION_VERSION,
        },
        "steps": [step],
    }


def _blocked_output(
    project_id: str,
    *,
    decisions: list[dict[str, Any]],
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = {
        "status": "blocked",
        "execute_version": EXECUTE_APPLY_WORLD_MODEL_PROPOSAL_RESOLUTION_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "target_type": TARGET_TYPE,
        "reason": reason,
        "side_effects": {"executed": [], "skipped": [DIRECT_TOOL]},
        "recommended_next_tools": ["prepare_apply_world_model_proposal_resolution"],
        "trace": {
            "selected_tools": [EXECUTE_TOOL],
            "rejected_tools": [{"tool_name": DIRECT_TOOL, "reason": reason}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
        "mutation_fingerprint": build_mutation_fingerprint(project_id, DIRECT_TOOL, {"decisions": decisions}),
    }
    if extra:
        output.update(extra)
    return output


def _mutation_target(project_id: str, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    fingerprint = build_mutation_fingerprint(project_id, DIRECT_TOOL, {"decisions": decisions})
    components = fingerprint.get("components") if isinstance(fingerprint.get("components"), dict) else {}
    return {
        "target_type": components.get("target_type"),
        "target_id": components.get("target_id"),
    }


def _target_label(project_id: str, decisions: list[dict[str, Any]]) -> str:
    target = _mutation_target(project_id, decisions)
    return str(target.get("target_id") or "unbound").replace(":", "-")


def _decisions(decisions: object) -> list[dict[str, Any]]:
    if not isinstance(decisions, list):
        return []
    return [dict(item) for item in decisions if isinstance(item, dict)]

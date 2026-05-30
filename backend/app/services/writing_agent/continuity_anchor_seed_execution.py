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
from app.services.writing_agent.continuity_anchor_seed_tool import seed_continuity_anchor_proposals_tool
from app.services.writing_agent.mutation_fingerprint import build_mutation_fingerprint

PREPARE_SEED_CONTINUITY_ANCHOR_PROPOSALS_EXECUTION_VERSION = (
    "phase198.continuity_anchor_seed_execution_prepare.v1"
)
EXECUTE_SEED_CONTINUITY_ANCHOR_PROPOSALS_WITH_APPROVAL_VERSION = (
    "phase198.continuity_anchor_seed_with_approval_execute.v1"
)
APPROVAL_GATE_VERSION = "phase198.continuity_anchor_seed_agent_plan_approval.v1"
TARGET_TYPE = "world_model_continuity_anchor_seed"


def prepare_seed_continuity_anchor_proposals_execution(db: Session, project_id: str) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}

    agent_plan = _direct_seed_continuity_anchor_proposals_agent_plan(project_id)
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    return {
        "status": "approval_required",
        "prepare_version": PREPARE_SEED_CONTINUITY_ANCHOR_PROPOSALS_EXECUTION_VERSION,
        "project_id": project_id,
        "target_type": TARGET_TYPE,
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
        "side_effects": {"executed": [], "skipped": ["seed_continuity_anchor_proposals"]},
        "recommended_next_tools": ["execute_seed_continuity_anchor_proposals_with_approval"],
        "trace": {
            "selected_tools": ["prepare_seed_continuity_anchor_proposals_execution"],
            "rejected_tools": [
                {"tool_name": "seed_continuity_anchor_proposals", "reason": "approval_required_before_write"}
            ],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def execute_seed_continuity_anchor_proposals_with_approval(
    db: Session,
    project_id: str,
    *,
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
    if not approval_contract_hash or not isinstance(approval_contract, dict):
        return _blocked_output(project_id, reason="approval_contract_required")
    if approval_tool_metadata_provider is None:
        return _blocked_output(project_id, reason="agent_plan_tool_metadata_missing")

    agent_plan = _direct_seed_continuity_anchor_proposals_agent_plan(project_id)
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
        tool_name="seed_continuity_anchor_proposals",
        target_type=TARGET_TYPE,
        target_id=f"{TARGET_TYPE}:{project_id}",
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

    result = seed_continuity_anchor_proposals_tool(db, project_id)
    return {
        **result,
        "execute_version": EXECUTE_SEED_CONTINUITY_ANCHOR_PROPOSALS_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "target_type": TARGET_TYPE,
        "agent_plan_approval_verification": verification,
        "approval_verification_event": build_approval_verification_event(verification),
        "execution_resource_binding": binding_check,
        "evidence": {
            "agent_plan_approval_verified": True,
            "legacy_action": "seed_continuity_anchor_proposals",
            "execution_route": "static_adapter",
        },
        "side_effects": {"executed": ["seed_continuity_anchor_proposals"], "skipped": []},
        "trace": {
            "selected_tools": ["execute_seed_continuity_anchor_proposals_with_approval"],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def _direct_seed_continuity_anchor_proposals_agent_plan(project_id: str) -> dict[str, Any]:
    plan_id = f"direct-seed-continuity-anchor-proposals:{project_id}"
    mutation_fingerprint = build_mutation_fingerprint(project_id, "seed_continuity_anchor_proposals", {})
    step = {
        "step_index": 1,
        "step_id": plan_id,
        "tool_name": "seed_continuity_anchor_proposals",
        "approval_executor_tool_name": "execute_seed_continuity_anchor_proposals_with_approval",
        "params": {},
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": "创建缺失的稳定连续性锚点世界模型提案。",
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
        "intent_class": "direct_seed_continuity_anchor_proposals",
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": None,
            "planner_version": PREPARE_SEED_CONTINUITY_ANCHOR_PROPOSALS_EXECUTION_VERSION,
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
        "execute_version": EXECUTE_SEED_CONTINUITY_ANCHOR_PROPOSALS_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "target_type": TARGET_TYPE,
        "reason": reason,
        "side_effects": {"executed": [], "skipped": ["seed_continuity_anchor_proposals"]},
        "recommended_next_tools": ["prepare_seed_continuity_anchor_proposals_execution"],
        "trace": {
            "selected_tools": ["execute_seed_continuity_anchor_proposals_with_approval"],
            "rejected_tools": [{"tool_name": "seed_continuity_anchor_proposals", "reason": reason}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }
    if extra:
        output.update(extra)
    return output

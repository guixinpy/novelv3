from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Project, Setup
from app.services.writing_agent.agent_step_binding import build_agent_step_binding, verify_resource_binding_target
from app.services.writing_agent.approval_contract import (
    build_agent_plan_approval_contract,
    verify_agent_plan_approval_contract,
)
from app.services.writing_agent.approval_verification_event import build_approval_verification_event
from app.services.writing_agent.mutation_fingerprint import build_mutation_fingerprint

PREVIEW_GENERATE_STORYLINE_EXECUTION_VERSION = "phase187.generate_storyline_execution_preview.v1"
PREPARE_GENERATE_STORYLINE_EXECUTION_VERSION = "phase187.generate_storyline_execution_prepare.v1"
EXECUTE_GENERATE_STORYLINE_WITH_APPROVAL_VERSION = "phase187.generate_storyline_with_approval_execute.v1"
APPROVAL_GATE_VERSION = "phase187.storyline_agent_plan_approval.v1"
_APPROVAL_PARAM_NAMES = {"confirm_execute", "approval_contract_hash", "approval_contract"}


def preview_generate_storyline_execution(
    db: Session,
    project_id: str,
    *,
    command_args: str | None = None,
) -> dict[str, Any]:
    readiness = _storyline_generation_readiness(db, project_id)
    if readiness is not None:
        return readiness

    agent_plan = _direct_generate_storyline_agent_plan(project_id, command_args)
    first_step = agent_plan["steps"][0]
    return {
        "status": "completed",
        "preview_version": PREVIEW_GENERATE_STORYLINE_EXECUTION_VERSION,
        "project_id": project_id,
        "target_type": "storyline",
        "command_args": command_args,
        "mutation_fingerprint": first_step.get("mutation_fingerprint"),
        "tool_call_id": first_step.get("tool_call_id"),
        "resource_binding": first_step.get("resource_binding"),
        "agent_plan": agent_plan,
        "side_effects": {"executed": [], "skipped": ["generate_storyline"]},
        "recommended_next_tools": ["prepare_generate_storyline_execution"],
        "trace": {
            "selected_tools": ["preview_generate_storyline_execution"],
            "rejected_tools": [{"tool_name": "generate_storyline", "reason": "approval_required_before_write"}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def prepare_generate_storyline_execution(
    db: Session,
    project_id: str,
    *,
    command_args: str | None = None,
) -> dict[str, Any]:
    readiness = _storyline_generation_readiness(db, project_id)
    if readiness is not None:
        return readiness

    agent_plan = _direct_generate_storyline_agent_plan(project_id, command_args)
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    return {
        "status": "approval_required",
        "prepare_version": PREPARE_GENERATE_STORYLINE_EXECUTION_VERSION,
        "project_id": project_id,
        "command_args": command_args,
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
        "side_effects": {"executed": [], "skipped": ["generate_storyline"]},
        "recommended_next_tools": ["execute_generate_storyline_with_approval"],
        "trace": {
            "selected_tools": ["prepare_generate_storyline_execution"],
            "rejected_tools": [{"tool_name": "generate_storyline", "reason": "approval_required_before_write"}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


async def execute_generate_storyline_with_approval(
    db: Session,
    project_id: str,
    *,
    confirm_execute: bool,
    approval_contract_hash: str | None,
    approval_contract: dict[str, Any] | None,
    approval_tool_metadata_provider,
    command_args: str | None = None,
    action_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    readiness = _storyline_generation_readiness(db, project_id)
    if readiness is not None:
        return readiness
    if confirm_execute is not True:
        return _blocked_output(project_id, command_args, reason="confirmation_required")
    if not approval_contract_hash or not isinstance(approval_contract, dict):
        return _blocked_output(project_id, command_args, reason="approval_contract_required")
    if approval_tool_metadata_provider is None:
        return _blocked_output(project_id, command_args, reason="agent_plan_tool_metadata_missing")

    agent_plan = _direct_generate_storyline_agent_plan(project_id, command_args)
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
            command_args,
            reason=str(verification.get("reason") or "agent_plan_approval_not_ready"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
            },
        )

    binding_check = verify_resource_binding_target(
        verification,
        tool_name="generate_storyline",
        target_type="storyline",
        target_id=f"storyline:{project_id}",
    )
    if binding_check.get("status") != "ready":
        return _blocked_output(
            project_id,
            command_args,
            reason=str(binding_check.get("reason") or "resource_binding_target_mismatch"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
                "execution_resource_binding": binding_check,
            },
        )

    from app.api.storylines import generate_storyline

    await generate_storyline(project_id, db, command_args=command_args)
    trace_id = _latest_storyline_trace_id(db, project_id)
    return {
        "status": "success",
        "execute_version": EXECUTE_GENERATE_STORYLINE_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "target_type": "storyline",
        "trace_id": trace_id,
        "agent_plan_approval_verification": verification,
        "approval_verification_event": build_approval_verification_event(verification),
        "execution_resource_binding": binding_check,
        "evidence": {
            "agent_plan_approval_verified": True,
            "legacy_action": "generate_storyline",
            "execution_route": "static_adapter",
        },
        "side_effects": {"executed": ["generate_storyline"], "skipped": []},
        "recommended_next_tools": ["inspect_agent_tool_contracts"],
        "trace": {
            "selected_tools": ["execute_generate_storyline_with_approval"],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def _direct_generate_storyline_agent_plan(project_id: str, command_args: str | None) -> dict[str, Any]:
    params = _generation_action_params({"command_args": command_args} if command_args else {})
    plan_id = f"direct-generate:{project_id}:storyline"
    mutation_fingerprint = build_mutation_fingerprint(project_id, "generate_storyline", params)
    step = {
        "step_index": 1,
        "step_id": plan_id,
        "tool_name": "generate_storyline",
        "approval_executor_tool_name": "execute_generate_storyline_with_approval",
        "params": params,
        "mutability": "write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": "基于已生成设定生成故事线、支线和伏笔。",
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
        "intent_class": "direct_generate_storyline",
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": None,
            "planner_version": PREPARE_GENERATE_STORYLINE_EXECUTION_VERSION,
        },
        "steps": [step],
    }


def _storyline_generation_readiness(db: Session, project_id: str) -> dict[str, Any] | None:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    setup = db.query(Setup.id).filter(Setup.project_id == project_id).first()
    if setup is None:
        return {"status": "failed", "error": "Setup not generated yet", "project_id": project_id}
    return None


def _generation_action_params(action_params: dict[str, Any] | None = None) -> dict[str, Any]:
    return {key: value for key, value in (action_params or {}).items() if key not in _APPROVAL_PARAM_NAMES}


def _blocked_output(
    project_id: str,
    command_args: str | None,
    *,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = {
        "status": "blocked",
        "execute_version": EXECUTE_GENERATE_STORYLINE_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "target_type": "storyline",
        "command_args": command_args,
        "reason": reason,
        "side_effects": {"executed": [], "skipped": ["generate_storyline"]},
        "recommended_next_tools": ["prepare_generate_storyline_execution"],
        "trace": {
            "selected_tools": ["execute_generate_storyline_with_approval"],
            "rejected_tools": [{"tool_name": "generate_storyline", "reason": reason}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }
    if extra:
        output.update(extra)
    return output


def _latest_storyline_trace_id(db: Session, project_id: str) -> str | None:
    from app.models import AIModelCallTrace

    trace = (
        db.query(AIModelCallTrace)
        .filter(AIModelCallTrace.project_id == project_id, AIModelCallTrace.trace_type == "storyline_generation")
        .order_by(AIModelCallTrace.created_at.desc(), AIModelCallTrace.id.desc())
        .first()
    )
    return trace.id if trace else None

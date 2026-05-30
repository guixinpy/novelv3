from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Project
from app.services.writing_agent.approval_contract import (
    build_agent_plan_approval_contract,
    verify_agent_plan_approval_contract,
)
from app.services.writing_agent.approval_verification_event import build_approval_verification_event
from app.services.writing_agent.agent_step_binding import build_agent_step_binding, verify_resource_binding_target
from app.services.writing_agent.mutation_fingerprint import build_mutation_fingerprint

PREPARE_GENERATE_CHAPTER_EXECUTION_VERSION = "phase114.generate_chapter_execution_prepare.v1"
EXECUTE_GENERATE_CHAPTER_WITH_APPROVAL_VERSION = "phase114.generate_chapter_with_approval_execute.v1"
APPROVAL_GATE_VERSION = "phase114.direct_generate_agent_plan_approval.v1"
_APPROVAL_PARAM_NAMES = {"confirm_execute", "approval_contract_hash", "approval_contract"}


def prepare_generate_chapter_execution(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}

    agent_plan = _direct_generate_chapter_agent_plan(project_id, chapter_index)
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    return {
        "status": "approval_required",
        "prepare_version": PREPARE_GENERATE_CHAPTER_EXECUTION_VERSION,
        "project_id": project_id,
        "chapter_index": chapter_index,
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
        "side_effects": {"executed": [], "skipped": ["generate_chapter"]},
        "recommended_next_tools": ["execute_generate_chapter_with_approval"],
        "trace": {
            "selected_tools": ["prepare_generate_chapter_execution"],
            "rejected_tools": [{"tool_name": "generate_chapter", "reason": "approval_required_before_write"}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


async def execute_generate_chapter_with_approval(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    confirm_execute: bool,
    approval_contract_hash: str | None,
    approval_contract: dict[str, Any] | None,
    approval_tool_metadata_provider,
    command_args: str | None = None,
    action_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    if confirm_execute is not True:
        return _blocked_output(project_id, chapter_index, reason="confirmation_required")
    if not approval_contract_hash or not isinstance(approval_contract, dict):
        return _blocked_output(project_id, chapter_index, reason="approval_contract_required")
    if approval_tool_metadata_provider is None:
        return _blocked_output(project_id, chapter_index, reason="agent_plan_tool_metadata_missing")

    agent_plan = _direct_generate_chapter_agent_plan(project_id, chapter_index)
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
            reason=str(verification.get("reason") or "agent_plan_approval_not_ready"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
            },
        )
    binding_check = verify_resource_binding_target(
        verification,
        tool_name="generate_chapter",
        target_type="chapter",
        target_id=f"chapter:{chapter_index}",
    )
    if binding_check.get("status") != "ready":
        return _blocked_output(
            project_id,
            chapter_index,
            reason=str(binding_check.get("reason") or "resource_binding_target_mismatch"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
                "execution_resource_binding": binding_check,
            },
        )

    from app.services.writing_agent.chapter_generation_tool import execute_generate_chapter_tool

    generation = await execute_generate_chapter_tool(
        db,
        project_id,
        chapter_index=chapter_index,
        command_args=command_args,
        action_params=_generation_action_params(action_params, chapter_index),
    )
    if isinstance(generation, dict):
        generation.setdefault("execute_version", EXECUTE_GENERATE_CHAPTER_WITH_APPROVAL_VERSION)
        generation.setdefault("project_id", project_id)
        generation["agent_plan_approval_verification"] = verification
        generation["evidence"] = {
            **(generation.get("evidence") if isinstance(generation.get("evidence"), dict) else {}),
            "agent_plan_approval_verified": True,
        }
        generation["approval_verification_event"] = build_approval_verification_event(verification)
        generation["execution_resource_binding"] = binding_check
        generation["trace"] = {
            **(generation.get("trace") if isinstance(generation.get("trace"), dict) else {}),
            "approval_gate_version": APPROVAL_GATE_VERSION,
        }
        return generation
    return {
        "status": "failed",
        "error": "generate_chapter returned non-dict result",
        "execute_version": EXECUTE_GENERATE_CHAPTER_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "chapter_index": chapter_index,
        "agent_plan_approval_verification": verification,
    }


def _direct_generate_chapter_agent_plan(project_id: str, chapter_index: int) -> dict[str, Any]:
    params = {"chapter_index": chapter_index}
    plan_id = f"direct-generate:{project_id}:chapter:{chapter_index}"
    mutation_fingerprint = build_mutation_fingerprint(project_id, "generate_chapter", params)
    step = {
        "step_index": 1,
        "step_id": plan_id,
        "tool_name": "generate_chapter",
        "params": params,
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": "直接生成指定章节正文。",
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
        "intent_class": "direct_generate_chapter",
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": None,
            "planner_version": PREPARE_GENERATE_CHAPTER_EXECUTION_VERSION,
        },
        "steps": [step],
    }


def _generation_action_params(action_params: dict[str, Any] | None, chapter_index: int) -> dict[str, Any]:
    params = {key: value for key, value in (action_params or {}).items() if key not in _APPROVAL_PARAM_NAMES}
    params["chapter_index"] = chapter_index
    return params


def _blocked_output(
    project_id: str,
    chapter_index: int,
    *,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = {
        "status": "blocked",
        "execute_version": EXECUTE_GENERATE_CHAPTER_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "chapter_index": chapter_index,
        "reason": reason,
        "side_effects": {"executed": [], "skipped": ["generate_chapter"]},
        "recommended_next_tools": ["prepare_generate_chapter_execution"],
        "trace": {
            "selected_tools": ["execute_generate_chapter_with_approval"],
            "rejected_tools": [{"tool_name": "generate_chapter", "reason": reason}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }
    if extra:
        output.update(extra)
    return output

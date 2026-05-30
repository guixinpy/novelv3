from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.outline_lookup import backfill_missing_outline_chapters_from_content
from app.models import Project
from app.services.writing_agent.agent_step_binding import build_agent_step_binding, verify_resource_binding_target
from app.services.writing_agent.approval_contract import (
    build_agent_plan_approval_contract,
    verify_agent_plan_approval_contract,
)
from app.services.writing_agent.approval_verification_event import build_approval_verification_event
from app.services.writing_agent.mutation_fingerprint import build_mutation_fingerprint

PREPARE_BACKFILL_OUTLINE_GAPS_EXECUTION_VERSION = "phase193.outline_backfill_execution_prepare.v1"
EXECUTE_BACKFILL_OUTLINE_GAPS_WITH_APPROVAL_VERSION = "phase193.outline_backfill_with_approval_execute.v1"
APPROVAL_GATE_VERSION = "phase193.outline_backfill_agent_plan_approval.v1"


def prepare_backfill_outline_gaps_execution(
    db: Session,
    project_id: str,
    *,
    before_chapter: int | None = None,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}

    agent_plan = _backfill_outline_gaps_agent_plan(project_id, before_chapter)
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    return {
        "status": "approval_required",
        "prepare_version": PREPARE_BACKFILL_OUTLINE_GAPS_EXECUTION_VERSION,
        "project_id": project_id,
        "before_chapter": before_chapter,
        "target_type": "outline",
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
        "side_effects": {"executed": [], "skipped": ["backfill_outline_gaps"]},
        "recommended_next_tools": ["execute_backfill_outline_gaps_with_approval"],
        "trace": {
            "selected_tools": ["prepare_backfill_outline_gaps_execution"],
            "rejected_tools": [{"tool_name": "backfill_outline_gaps", "reason": "approval_required_before_write"}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def execute_backfill_outline_gaps_with_approval(
    db: Session,
    project_id: str,
    *,
    before_chapter: int | None,
    confirm_execute: bool,
    approval_contract_hash: str | None,
    approval_contract: dict[str, Any] | None,
    approval_tool_metadata_provider,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    if confirm_execute is not True:
        return _blocked_output(project_id, before_chapter, reason="confirmation_required")
    if not approval_contract_hash or not isinstance(approval_contract, dict):
        return _blocked_output(project_id, before_chapter, reason="approval_contract_required")
    if approval_tool_metadata_provider is None:
        return _blocked_output(project_id, before_chapter, reason="agent_plan_tool_metadata_missing")

    agent_plan = _backfill_outline_gaps_agent_plan(project_id, before_chapter)
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
            before_chapter,
            reason=str(verification.get("reason") or "agent_plan_approval_not_ready"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
            },
        )

    binding_check = verify_resource_binding_target(
        verification,
        tool_name="backfill_outline_gaps",
        target_type="outline",
        target_id=_outline_backfill_target_id(project_id, before_chapter),
    )
    if binding_check.get("status") != "ready":
        return _blocked_output(
            project_id,
            before_chapter,
            reason=str(binding_check.get("reason") or "resource_binding_target_mismatch"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
                "execution_resource_binding": binding_check,
            },
        )

    result = backfill_missing_outline_chapters_from_content(
        db,
        project_id,
        before_chapter=before_chapter,
    )
    return {
        **result,
        "execute_version": EXECUTE_BACKFILL_OUTLINE_GAPS_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "before_chapter": before_chapter,
        "target_type": "outline",
        "agent_plan_approval_verification": verification,
        "approval_verification_event": build_approval_verification_event(verification),
        "execution_resource_binding": binding_check,
        "evidence": {
            "agent_plan_approval_verified": True,
            "legacy_action": "backfill_outline_gaps",
            "execution_route": "static_adapter",
        },
        "side_effects": {"executed": ["backfill_outline_gaps"], "skipped": []},
        "trace": {
            "selected_tools": ["execute_backfill_outline_gaps_with_approval"],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def _backfill_outline_gaps_agent_plan(project_id: str, before_chapter: int | None) -> dict[str, Any]:
    params = _backfill_params(before_chapter)
    target_label = before_chapter if before_chapter is not None else "all"
    plan_id = f"direct-backfill-outline-gaps:{project_id}:before:{target_label}"
    mutation_fingerprint = build_mutation_fingerprint(project_id, "backfill_outline_gaps", params)
    step = {
        "step_index": 1,
        "step_id": plan_id,
        "tool_name": "backfill_outline_gaps",
        "approval_executor_tool_name": "execute_backfill_outline_gaps_with_approval",
        "params": params,
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": "根据已生成正文回填缺失章节大纲。",
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
        "intent_class": "direct_backfill_outline_gaps",
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": None,
            "planner_version": PREPARE_BACKFILL_OUTLINE_GAPS_EXECUTION_VERSION,
        },
        "steps": [step],
    }


def _backfill_params(before_chapter: int | None) -> dict[str, int]:
    return {"before_chapter": before_chapter} if before_chapter is not None else {}


def _outline_backfill_target_id(project_id: str, before_chapter: int | None) -> str:
    target_label = before_chapter if before_chapter is not None else "all"
    return f"outline_backfill:{project_id}:before:{target_label}"


def _blocked_output(
    project_id: str,
    before_chapter: int | None,
    *,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = {
        "status": "blocked",
        "execute_version": EXECUTE_BACKFILL_OUTLINE_GAPS_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "before_chapter": before_chapter,
        "target_type": "outline",
        "reason": reason,
        "side_effects": {"executed": [], "skipped": ["backfill_outline_gaps"]},
        "recommended_next_tools": ["prepare_backfill_outline_gaps_execution"],
        "trace": {
            "selected_tools": ["execute_backfill_outline_gaps_with_approval"],
            "rejected_tools": [{"tool_name": "backfill_outline_gaps", "reason": reason}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }
    if extra:
        output.update(extra)
    return output

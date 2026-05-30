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
from app.services.writing_agent.setup_world_model_import_tool import import_setup_world_model_tool

PREPARE_IMPORT_SETUP_WORLD_MODEL_EXECUTION_VERSION = "phase191.setup_world_model_import_execution_prepare.v1"
EXECUTE_IMPORT_SETUP_WORLD_MODEL_WITH_APPROVAL_VERSION = "phase191.setup_world_model_import_with_approval_execute.v1"
APPROVAL_GATE_VERSION = "phase191.setup_world_model_import_agent_plan_approval.v1"


def prepare_import_setup_world_model_execution(db: Session, project_id: str) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}

    agent_plan = _direct_import_setup_world_model_agent_plan(project_id)
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    return {
        "status": "approval_required",
        "prepare_version": PREPARE_IMPORT_SETUP_WORLD_MODEL_EXECUTION_VERSION,
        "project_id": project_id,
        "target_type": "world_model",
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
        "side_effects": {"executed": [], "skipped": ["import_setup_world_model"]},
        "recommended_next_tools": ["execute_import_setup_world_model_with_approval"],
        "trace": {
            "selected_tools": ["prepare_import_setup_world_model_execution"],
            "rejected_tools": [{"tool_name": "import_setup_world_model", "reason": "approval_required_before_write"}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def execute_import_setup_world_model_with_approval(
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

    agent_plan = _direct_import_setup_world_model_agent_plan(project_id)
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
        tool_name="import_setup_world_model",
        target_type="world_model",
        target_id=f"world_model:{project_id}",
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

    result = import_setup_world_model_tool(db, project_id)
    return {
        **result,
        "execute_version": EXECUTE_IMPORT_SETUP_WORLD_MODEL_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "target_type": "world_model",
        "agent_plan_approval_verification": verification,
        "approval_verification_event": build_approval_verification_event(verification),
        "execution_resource_binding": binding_check,
        "evidence": {
            "agent_plan_approval_verified": True,
            "legacy_action": "import_setup_world_model",
            "execution_route": "static_adapter",
        },
        "side_effects": {"executed": ["import_setup_world_model"], "skipped": []},
        "trace": {
            "selected_tools": ["execute_import_setup_world_model_with_approval"],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def _direct_import_setup_world_model_agent_plan(project_id: str) -> dict[str, Any]:
    plan_id = f"direct-import-setup-world-model:{project_id}"
    mutation_fingerprint = build_mutation_fingerprint(project_id, "import_setup_world_model", {})
    step = {
        "step_index": 1,
        "step_id": plan_id,
        "tool_name": "import_setup_world_model",
        "approval_executor_tool_name": "execute_import_setup_world_model_with_approval",
        "params": {},
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": "将项目设定导入 Athena 世界模型 profile。",
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
        "intent_class": "direct_import_setup_world_model",
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": None,
            "planner_version": PREPARE_IMPORT_SETUP_WORLD_MODEL_EXECUTION_VERSION,
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
        "execute_version": EXECUTE_IMPORT_SETUP_WORLD_MODEL_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "target_type": "world_model",
        "reason": reason,
        "side_effects": {"executed": [], "skipped": ["import_setup_world_model"]},
        "recommended_next_tools": ["prepare_import_setup_world_model_execution"],
        "trace": {
            "selected_tools": ["execute_import_setup_world_model_with_approval"],
            "rejected_tools": [{"tool_name": "import_setup_world_model", "reason": reason}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }
    if extra:
        output.update(extra)
    return output

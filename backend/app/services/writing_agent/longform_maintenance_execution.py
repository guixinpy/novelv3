from __future__ import annotations

import json
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

PREPARE_REPAIR_LONGFORM_MAINTENANCE_VERSION = "phase190.longform_maintenance_prepare.v1"
EXECUTE_REPAIR_LONGFORM_MAINTENANCE_WITH_APPROVAL_VERSION = "phase190.longform_maintenance_with_approval_execute.v1"
APPROVAL_GATE_VERSION = "phase190.longform_maintenance_agent_plan_approval.v1"
_APPROVAL_PARAM_NAMES = {
    "confirm_execute",
    "approval_contract_hash",
    "approval_contract",
    "post_approval_continuation_tools",
}


def prepare_repair_longform_maintenance(
    db: Session,
    project_id: str,
    *,
    action_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}

    agent_plan = _repair_longform_maintenance_agent_plan(project_id, action_params)
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    post_approval_continuation_tools = _post_approval_continuation_tools(action_params)
    return {
        "status": "approval_required",
        "prepare_version": PREPARE_REPAIR_LONGFORM_MAINTENANCE_VERSION,
        "project_id": project_id,
        "target_type": "longform_maintenance",
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
        "side_effects": {"executed": [], "skipped": ["repair_longform_maintenance"]},
        "recommended_next_tools": ["execute_repair_longform_maintenance_with_approval"],
        "post_approval_continuation_tools": post_approval_continuation_tools,
        "trace": {
            "selected_tools": ["prepare_repair_longform_maintenance"],
            "rejected_tools": [{"tool_name": "repair_longform_maintenance", "reason": "approval_required_before_write"}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
            "post_approval_continuation_count": len(post_approval_continuation_tools),
        },
    }


def execute_repair_longform_maintenance_with_approval(
    db: Session,
    project_id: str,
    *,
    confirm_execute: bool,
    approval_contract_hash: str | None,
    approval_contract: dict[str, Any] | None,
    approval_tool_metadata_provider,
    action_params: dict[str, Any] | None = None,
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

    agent_plan = _repair_longform_maintenance_agent_plan(project_id, action_params)
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
        tool_name="repair_longform_maintenance",
        target_type="longform_maintenance",
        target_id=f"longform_maintenance:{project_id}",
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

    params = _repair_action_params(action_params)
    from app.core.longform_memory import repair_longform_maintenance

    repair_result = _json_safe_output(
        repair_longform_maintenance(
            db,
            project_id,
            limit=int(params["limit"]),
            repair_limit=int(params["repair_limit"]),
        )
    )
    if repair_result.get("status") != "completed":
        return _blocked_output(
            project_id,
            reason="longform_maintenance_repair_failed",
            extra={
                "repair_result": repair_result,
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
                "execution_resource_binding": binding_check,
            },
        )

    post_approval_continuation_tools = _post_approval_continuation_tools(action_params)
    recommended_next_tools = _continuation_tool_names(post_approval_continuation_tools) or ["inspect_agent_memory_route"]
    return {
        "status": "success",
        "execute_version": EXECUTE_REPAIR_LONGFORM_MAINTENANCE_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "target_type": "longform_maintenance",
        "repaired_memory_count": repair_result.get("repaired_memory_count"),
        "repaired_retrieval_count": repair_result.get("repaired_retrieval_count"),
        "remaining": repair_result.get("remaining"),
        "repair_result": repair_result,
        "agent_plan_approval_verification": verification,
        "approval_verification_event": build_approval_verification_event(verification),
        "execution_resource_binding": binding_check,
        "evidence": {
            "agent_plan_approval_verified": True,
            "legacy_action": "repair_longform_maintenance",
            "execution_route": "static_adapter",
        },
        "side_effects": {"executed": ["repair_longform_maintenance"], "skipped": []},
        "recommended_next_tools": recommended_next_tools,
        "post_approval_continuation_tools": post_approval_continuation_tools,
        "trace": {
            "selected_tools": ["execute_repair_longform_maintenance_with_approval"],
            "approval_gate_version": APPROVAL_GATE_VERSION,
            "post_approval_continuation_count": len(post_approval_continuation_tools),
        },
    }


def _repair_longform_maintenance_agent_plan(
    project_id: str,
    action_params: dict[str, Any] | None,
) -> dict[str, Any]:
    params = _repair_action_params(action_params)
    plan_id = f"longform-maintenance:{project_id}"
    mutation_fingerprint = build_mutation_fingerprint(project_id, "repair_longform_maintenance", params)
    step = {
        "step_index": 1,
        "step_id": plan_id,
        "tool_name": "repair_longform_maintenance",
        "approval_executor_tool_name": "execute_repair_longform_maintenance_with_approval",
        "params": params,
        "mutability": "write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": "修复长篇记忆和检索维护缺口，避免后续章节在过期上下文上继续生成。",
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
        "intent_class": "repair_longform_maintenance",
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": None,
            "planner_version": PREPARE_REPAIR_LONGFORM_MAINTENANCE_VERSION,
        },
        "steps": [step],
    }


def _repair_action_params(action_params: dict[str, Any] | None) -> dict[str, int]:
    raw = {key: value for key, value in (action_params or {}).items() if key not in _APPROVAL_PARAM_NAMES}
    return {
        "limit": _positive_int(raw.get("limit")) or 20,
        "repair_limit": _positive_int(raw.get("repair_limit")) or 100,
    }


def _post_approval_continuation_tools(action_params: dict[str, Any] | None) -> list[dict[str, Any]]:
    raw_tools = (action_params or {}).get("post_approval_continuation_tools")
    if not isinstance(raw_tools, list):
        return []
    tools: list[dict[str, Any]] = []
    for item in raw_tools:
        if not isinstance(item, dict):
            continue
        tool_name = str(item.get("tool_name") or "").strip()
        if not tool_name:
            continue
        params = item.get("params") if isinstance(item.get("params"), dict) else {}
        tool: dict[str, Any] = {"tool_name": tool_name, "params": dict(params)}
        for field in ("reason", "expected_output"):
            value = str(item.get(field) or "").strip()
            if value:
                tool[field] = value
        tools.append(tool)
    return _json_safe_output({"tools": tools})["tools"]


def _continuation_tool_names(tools: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    names: list[str] = []
    for tool in tools:
        tool_name = str(tool.get("tool_name") or "").strip()
        if not tool_name or tool_name in seen:
            continue
        seen.add(tool_name)
        names.append(tool_name)
    return names


def _blocked_output(
    project_id: str,
    *,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = {
        "status": "blocked",
        "execute_version": EXECUTE_REPAIR_LONGFORM_MAINTENANCE_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "target_type": "longform_maintenance",
        "reason": reason,
        "side_effects": {"executed": [], "skipped": ["repair_longform_maintenance"]},
        "recommended_next_tools": ["prepare_repair_longform_maintenance"],
        "trace": {
            "selected_tools": ["execute_repair_longform_maintenance_with_approval"],
            "rejected_tools": [{"tool_name": "repair_longform_maintenance", "reason": reason}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }
    if extra:
        output.update(extra)
    return output


def _positive_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

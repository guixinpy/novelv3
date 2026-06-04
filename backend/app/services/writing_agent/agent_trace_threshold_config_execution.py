from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import Project
from app.services.writing_agent.agent_step_binding import build_agent_step_binding, verify_resource_binding_target
from app.services.writing_agent.agent_trace_audit import TRACE_ANOMALY_THRESHOLDS_CONFIG_KEY
from app.services.writing_agent.approval_contract import (
    build_agent_plan_approval_contract,
    verify_agent_plan_approval_contract,
)
from app.services.writing_agent.approval_verification_event import build_approval_verification_event
from app.services.writing_agent.mutation_fingerprint import build_mutation_fingerprint

PREPARE_RECORD_TRACE_ANOMALY_THRESHOLD_CONFIG_VERSION = "phase241.trace_anomaly_threshold_config_prepare.v1"
EXECUTE_RECORD_TRACE_ANOMALY_THRESHOLD_CONFIG_WITH_APPROVAL_VERSION = (
    "phase241.trace_anomaly_threshold_config_with_approval_execute.v1"
)
APPROVAL_GATE_VERSION = "phase241.trace_anomaly_threshold_config_agent_plan_approval.v1"
_TARGET_TYPE = "agent_trace_anomaly_threshold_config"
_RECORD_TOOL = "record_agent_trace_anomaly_threshold_config"
_PREPARE_TOOL = "prepare_record_agent_trace_anomaly_threshold_config"
_EXECUTE_TOOL = "execute_record_agent_trace_anomaly_threshold_config_with_approval"
_APPROVAL_PARAM_NAMES = {
    "confirm_execute",
    "approval_contract_hash",
    "approval_contract",
    "post_approval_continuation_tools",
}


def prepare_record_agent_trace_anomaly_threshold_config(
    db: Session,
    project_id: str,
    *,
    action_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}

    params, diagnostics = _threshold_action_params(action_params)
    if diagnostics:
        return _prepare_blocked_output(project_id, reason="invalid_threshold_config", diagnostics=diagnostics)

    agent_plan = _trace_anomaly_threshold_config_agent_plan(project_id, params)
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    post_approval_continuation_tools = _post_approval_continuation_tools(action_params)
    return _json_safe_output(
        {
            "status": "approval_required",
            "prepare_version": PREPARE_RECORD_TRACE_ANOMALY_THRESHOLD_CONFIG_VERSION,
            "project_id": project_id,
            "target_type": _TARGET_TYPE,
            "thresholds": _thresholds_from_params(params),
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
            "side_effects": {"executed": [], "skipped": [_RECORD_TOOL]},
            "recommended_next_tools": [_EXECUTE_TOOL],
            "post_approval_continuation_tools": post_approval_continuation_tools,
            "trace": {
                "selected_tools": [_PREPARE_TOOL],
                "rejected_tools": [{"tool_name": _RECORD_TOOL, "reason": "approval_required_before_write"}],
                "approval_gate_version": APPROVAL_GATE_VERSION,
                "post_approval_continuation_count": len(post_approval_continuation_tools),
            },
        }
    )


def execute_record_agent_trace_anomaly_threshold_config_with_approval(
    db: Session,
    project_id: str,
    *,
    confirm_execute: bool,
    approval_contract_hash: str | None,
    approval_contract: dict[str, Any] | None,
    approval_tool_metadata_provider,
    action_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    if confirm_execute is not True:
        return _execute_blocked_output(project_id, reason="confirmation_required")
    if not approval_contract_hash or not isinstance(approval_contract, dict):
        return _execute_blocked_output(project_id, reason="approval_contract_required")
    if approval_tool_metadata_provider is None:
        return _execute_blocked_output(project_id, reason="agent_plan_tool_metadata_missing")

    params, diagnostics = _threshold_action_params(action_params)
    if diagnostics:
        return _execute_blocked_output(
            project_id,
            reason="invalid_threshold_config",
            extra={"diagnostics": diagnostics},
        )

    agent_plan = _trace_anomaly_threshold_config_agent_plan(project_id, params)
    verification = verify_agent_plan_approval_contract(
        agent_plan,
        approval_contract_hash=approval_contract_hash,
        approval_contract=approval_contract,
        project_id=project_id,
        tool_metadata_by_name=approval_tool_metadata_provider(agent_plan),
    )
    if verification.get("status") != "ready":
        return _execute_blocked_output(
            project_id,
            reason=str(verification.get("reason") or "agent_plan_approval_not_ready"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
            },
        )

    target_id = _target_id_from_plan(agent_plan)
    binding_check = verify_resource_binding_target(
        verification,
        tool_name=_RECORD_TOOL,
        target_type=_TARGET_TYPE,
        target_id=target_id,
    )
    if binding_check.get("status") != "ready":
        return _execute_blocked_output(
            project_id,
            reason=str(binding_check.get("reason") or "resource_binding_target_mismatch"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
                "execution_resource_binding": binding_check,
            },
        )

    thresholds = _thresholds_from_params(params)
    style_config = dict(project.style_config) if isinstance(project.style_config, dict) else {}
    previous_thresholds = style_config.get(TRACE_ANOMALY_THRESHOLDS_CONFIG_KEY)
    style_config[TRACE_ANOMALY_THRESHOLDS_CONFIG_KEY] = thresholds
    project.style_config = style_config
    db.add(project)
    db.commit()
    db.refresh(project)

    post_approval_continuation_tools = _post_approval_continuation_tools(action_params)
    recommended_next_tools = _continuation_tool_names(post_approval_continuation_tools) or [
        "inspect_agent_trace_anomaly_trends"
    ]
    return _json_safe_output(
        {
            "status": "success",
            "execute_version": EXECUTE_RECORD_TRACE_ANOMALY_THRESHOLD_CONFIG_WITH_APPROVAL_VERSION,
            "project_id": project_id,
            "target_type": _TARGET_TYPE,
            "thresholds": thresholds,
            "previous_thresholds": previous_thresholds if isinstance(previous_thresholds, dict) else None,
            "agent_plan_approval_verification": verification,
            "approval_verification_event": build_approval_verification_event(verification),
            "execution_resource_binding": binding_check,
            "evidence": {
                "agent_plan_approval_verified": True,
                "legacy_action": _RECORD_TOOL,
                "execution_route": "static_adapter",
                "config_key": TRACE_ANOMALY_THRESHOLDS_CONFIG_KEY,
            },
            "side_effects": {"executed": [_RECORD_TOOL], "skipped": []},
            "recommended_next_tools": recommended_next_tools,
            "post_approval_continuation_tools": post_approval_continuation_tools,
            "trace": {
                "selected_tools": [_EXECUTE_TOOL],
                "approval_gate_version": APPROVAL_GATE_VERSION,
                "post_approval_continuation_count": len(post_approval_continuation_tools),
            },
        }
    )


def _trace_anomaly_threshold_config_agent_plan(project_id: str, params: dict[str, Any]) -> dict[str, Any]:
    mutation_fingerprint = build_mutation_fingerprint(project_id, _RECORD_TOOL, params)
    target_suffix = str(mutation_fingerprint.get("fingerprint") or "pending")[:16]
    plan_id = f"trace-anomaly-threshold-config:{project_id}:{target_suffix}"
    step = {
        "step_index": 1,
        "step_id": plan_id,
        "tool_name": _RECORD_TOOL,
        "approval_executor_tool_name": _EXECUTE_TOOL,
        "params": params,
        "mutability": "write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": "Persist reviewed trace anomaly thresholds to project style_config.",
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
        "intent_class": _RECORD_TOOL,
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": None,
            "planner_version": PREPARE_RECORD_TRACE_ANOMALY_THRESHOLD_CONFIG_VERSION,
        },
        "steps": [step],
    }


def _threshold_action_params(action_params: dict[str, Any] | None) -> tuple[dict[str, Any], list[dict[str, str]]]:
    raw = {key: value for key, value in (action_params or {}).items() if key not in _APPROVAL_PARAM_NAMES}
    diagnostics: list[dict[str, str]] = []
    affected = _rate_threshold(raw.get("affected_run_rate_delta"))
    critical = _rate_threshold(raw.get("critical_issue_rate_delta"))
    if affected is None:
        diagnostics.append(
            {
                "code": "invalid_affected_run_rate_delta",
                "message": "affected_run_rate_delta must be a number greater than 0 and less than or equal to 1",
            }
        )
    if critical is None:
        diagnostics.append(
            {
                "code": "invalid_critical_issue_rate_delta",
                "message": "critical_issue_rate_delta must be a number greater than 0 and less than or equal to 1",
            }
        )
    params: dict[str, Any] = {}
    if affected is not None:
        params["affected_run_rate_delta"] = affected
    if critical is not None:
        params["critical_issue_rate_delta"] = critical
    source = _clean_string(raw.get("source"))
    if source:
        params["source"] = source
    reviewed_run_count = _non_negative_int(raw.get("reviewed_run_count"))
    if reviewed_run_count is not None:
        params["reviewed_run_count"] = reviewed_run_count
    reason = _clean_string(raw.get("reason"))
    if reason:
        params["reason"] = reason
    return params, diagnostics


def _thresholds_from_params(params: dict[str, Any]) -> dict[str, float]:
    return {
        "affected_run_rate_delta": float(params["affected_run_rate_delta"]),
        "critical_issue_rate_delta": float(params["critical_issue_rate_delta"]),
    }


def _target_id_from_plan(agent_plan: dict[str, Any]) -> str:
    step = agent_plan["steps"][0]
    fingerprint = step.get("mutation_fingerprint") if isinstance(step.get("mutation_fingerprint"), dict) else {}
    components = fingerprint.get("components") if isinstance(fingerprint.get("components"), dict) else {}
    return str(components.get("target_id") or "")


def _post_approval_continuation_tools(action_params: dict[str, Any] | None) -> list[dict[str, Any]]:
    raw_tools = (action_params or {}).get("post_approval_continuation_tools")
    if not isinstance(raw_tools, list):
        return []
    tools: list[dict[str, Any]] = []
    for item in raw_tools:
        if not isinstance(item, dict):
            continue
        tool_name = _clean_string(item.get("tool_name"))
        if not tool_name:
            continue
        params = item.get("params") if isinstance(item.get("params"), dict) else {}
        tool: dict[str, Any] = {"tool_name": tool_name, "params": dict(params)}
        for field in ("reason", "expected_output"):
            value = _clean_string(item.get(field))
            if value:
                tool[field] = value
        tools.append(tool)
    return _json_safe_output({"tools": tools})["tools"]


def _continuation_tool_names(tools: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    names: list[str] = []
    for tool in tools:
        tool_name = _clean_string(tool.get("tool_name"))
        if not tool_name or tool_name in seen:
            continue
        seen.add(tool_name)
        names.append(tool_name)
    return names


def _prepare_blocked_output(
    project_id: str,
    *,
    reason: str,
    diagnostics: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "prepare_version": PREPARE_RECORD_TRACE_ANOMALY_THRESHOLD_CONFIG_VERSION,
        "project_id": project_id,
        "target_type": _TARGET_TYPE,
        "reason": reason,
        "diagnostics": diagnostics,
        "side_effects": {"executed": [], "skipped": [_RECORD_TOOL]},
        "recommended_next_tools": [_PREPARE_TOOL],
        "trace": {
            "selected_tools": [_PREPARE_TOOL],
            "rejected_tools": [{"tool_name": _RECORD_TOOL, "reason": reason}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def _execute_blocked_output(
    project_id: str,
    *,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = {
        "status": "blocked",
        "execute_version": EXECUTE_RECORD_TRACE_ANOMALY_THRESHOLD_CONFIG_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "target_type": _TARGET_TYPE,
        "reason": reason,
        "side_effects": {"executed": [], "skipped": [_RECORD_TOOL]},
        "recommended_next_tools": [_PREPARE_TOOL],
        "trace": {
            "selected_tools": [_EXECUTE_TOOL],
            "rejected_tools": [{"tool_name": _RECORD_TOOL, "reason": reason}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }
    if extra:
        output.update(extra)
    return _json_safe_output(output)


def _rate_threshold(value: object) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0 or parsed > 1:
        return None
    return round(parsed, 2)


def _non_negative_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _clean_string(value: object) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

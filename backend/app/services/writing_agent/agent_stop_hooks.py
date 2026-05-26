from __future__ import annotations

from typing import Any

from app.models import WritingAgentRun, WritingAgentStep
from app.services.writing_agent.agent_loop_risk import build_agent_loop_risk
from app.services.writing_agent.tool_registry import allowed_tool_names

AGENT_STOP_HOOKS_VERSION = "phase226.agent_stop_hooks.v1"
APPROVAL_MISSING_REASONS = {
    "agent_plan_approval_verification_missing",
    "approval_contract_missing",
    "approval_contract_hash_missing",
}


def evaluate_agent_stop_hooks(
    run: WritingAgentRun,
    steps: list[WritingAgentStep],
    latest_output: dict[str, Any] | None,
) -> dict[str, Any]:
    output = latest_output if isinstance(latest_output, dict) else {}
    hooks = [
        hook
        for hook in (
            _critical_loop_hook(run, steps),
            _missing_approval_hook(output),
            _memory_provenance_hook(output),
            _context_guard_hook(output),
        )
        if hook is not None
    ]
    if not hooks:
        return {
            "version": AGENT_STOP_HOOKS_VERSION,
            "status": "clear",
            "reason": "no_stop_hook_triggered",
            "severity": "none",
            "allow_continue": True,
            "recommended_tools": [],
            "hooks": [],
        }
    severity = "error" if any(hook.get("severity") == "error" for hook in hooks) else "warning"
    primary = hooks[0]
    return {
        "version": AGENT_STOP_HOOKS_VERSION,
        "status": "blocked" if severity == "error" else "warning",
        "reason": primary.get("reason"),
        "severity": severity,
        "allow_continue": False if severity == "error" else primary.get("allow_continue") is not False,
        "recommended_tools": _dedupe(
            [tool for hook in hooks for tool in _string_list(hook.get("recommended_tools"))]
        ),
        "hooks": hooks,
    }


def _critical_loop_hook(run: WritingAgentRun, steps: list[WritingAgentStep]) -> dict[str, Any] | None:
    risk = build_agent_loop_risk(
        steps,
        planned_tools=_planned_tool_rows(run),
        known_tool_names=allowed_tool_names(),
    )
    if risk.get("status") != "critical":
        return None
    action = risk.get("recommended_next_action") if isinstance(risk.get("recommended_next_action"), dict) else {}
    return {
        "code": "critical_loop_risk",
        "reason": "loop_risk_critical",
        "severity": "error",
        "allow_continue": False,
        "detector": risk.get("detector"),
        "recommended_tools": _dedupe(
            _string_list(action.get("recommended_tools")) + ["inspect_agent_trace_audit"]
        ),
        "evidence": risk.get("detectors") if isinstance(risk.get("detectors"), list) else [],
    }


def _missing_approval_hook(output: dict[str, Any]) -> dict[str, Any] | None:
    reason = str(output.get("reason") or output.get("error") or "").strip()
    verification = (
        output.get("agent_plan_approval_verification")
        if isinstance(output.get("agent_plan_approval_verification"), dict)
        else {}
    )
    verification_reason = str(verification.get("reason") or "").strip()
    if reason not in APPROVAL_MISSING_REASONS and verification_reason not in APPROVAL_MISSING_REASONS:
        return None
    return {
        "code": "missing_approval_contract",
        "reason": "approval_required",
        "severity": "error",
        "allow_continue": False,
        "recommended_tools": ["preview_agent_plan_approval_contract", "verify_agent_plan_approval_contract"],
    }


def _memory_provenance_hook(output: dict[str, Any]) -> dict[str, Any] | None:
    provenance = output.get("memory_provenance") if isinstance(output.get("memory_provenance"), dict) else {}
    recovery = provenance.get("recovery") if isinstance(provenance.get("recovery"), dict) else {}
    if provenance.get("status") != "blocked" and recovery.get("status") != "recommended":
        return None
    next_tools = recovery.get("next_tools") if isinstance(recovery.get("next_tools"), list) else []
    return {
        "code": "memory_provenance_blocked",
        "reason": "memory_provenance_blocked",
        "severity": "error",
        "allow_continue": False,
        "recommended_tools": _string_list(next_tools),
        "provenance_status": provenance.get("status"),
        "recovery_status": recovery.get("status"),
    }


def _context_guard_hook(output: dict[str, Any]) -> dict[str, Any] | None:
    risks = output.get("risks") if isinstance(output.get("risks"), list) else []
    has_context_guard = any(isinstance(risk, dict) and risk.get("code") == "context_guard_open" for risk in risks)
    recovery = output.get("recovery") if isinstance(output.get("recovery"), dict) else {}
    if output.get("status") != "blocked" or not has_context_guard:
        return None
    return {
        "code": "context_guard_open",
        "reason": "context_guard_open",
        "severity": "error",
        "allow_continue": False,
        "recommended_tools": _string_list(recovery.get("next_tools")),
    }


def _planned_tool_rows(run: WritingAgentRun) -> list[dict[str, Any]]:
    run_input = run.input if isinstance(run.input, dict) else {}
    tools = run_input.get("tools") if isinstance(run_input.get("tools"), list) else []
    return [tool for tool in tools if isinstance(tool, dict)]


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    cleaned = str(value).strip()
    return [cleaned] if cleaned else []


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result

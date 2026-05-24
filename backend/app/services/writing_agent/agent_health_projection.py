from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Project
from app.services.writing_agent.agent_trace_audit import inspect_agent_trace_audit
from app.services.writing_agent.slash_command_route import inspect_agent_route_preference_projection
from app.services.writing_agent.tool_contracts import build_agent_tool_contract_snapshot
from app.services.writing_agent.tool_registry import build_agent_tool_plan
from app.services.writing_agent.write_gate_coverage import inspect_agent_write_gate_coverage

AGENT_HEALTH_PROJECTION_VERSION = "phase218.agent_health_projection.v1"


def inspect_agent_health_projection(
    db: Session,
    project_id: str,
    *,
    run_id: str | None = None,
    source: str | None = None,
    chapter_index: int | None = None,
    adapter_metadata_by_name: dict[str, dict[str, Any]] | None = None,
    static_adapter_tool_names: set[str] | None = None,
    action_execution_tool_names: set[str] | None = None,
    tool_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _require_project(db, project_id)
    adapter_metadata_by_name = adapter_metadata_by_name or {}
    static_adapter_tool_names = static_adapter_tool_names or set()
    action_execution_tool_names = action_execution_tool_names or set()

    resolved_tool_plan = (
        tool_plan
        if isinstance(tool_plan, dict)
        else build_agent_tool_plan(
            db,
            project_id,
            chapter_index=chapter_index,
            adapter_metadata_by_name=adapter_metadata_by_name,
        )
    )
    profile_policy = _profile_policy_audit_summary(_profile_policy_audit_from_tool_plan(resolved_tool_plan))
    route_preference = _route_preference_summary(
        inspect_agent_route_preference_projection(
            source=source,
            static_adapter_tool_names=static_adapter_tool_names,
            action_execution_tool_names=action_execution_tool_names,
        )
    )
    tool_contracts = _tool_contract_summary(
        build_agent_tool_contract_snapshot(
            adapter_metadata_by_name=adapter_metadata_by_name,
            include_gap_details=False,
        )
    )
    write_gate = _write_gate_summary(inspect_agent_write_gate_coverage(adapter_metadata_by_name=adapter_metadata_by_name))
    trace_audit = _trace_audit_summary(db, project_id, run_id)

    diagnostics = _diagnostics(
        profile_policy=profile_policy,
        route_preference=route_preference,
        tool_contracts=tool_contracts,
        write_gate=write_gate,
        trace_audit=trace_audit,
    )
    recommended_tools = _recommended_tools(diagnostics)
    return _json_safe_output(
        {
            "status": _health_status(diagnostics),
            "version": AGENT_HEALTH_PROJECTION_VERSION,
            "project_id": project_id,
            "selector": {"run_id": run_id, "source": source, "chapter_index": chapter_index},
            "profile_policy": profile_policy,
            "route_preference": route_preference,
            "tool_contracts": tool_contracts,
            "write_gate": write_gate,
            "trace_audit": trace_audit,
            "diagnostics": diagnostics,
            "recommended_tools": recommended_tools,
            "recommended_next_tools": recommended_tools,
            "trace": {
                "source": "inspect_agent_health_projection",
                "version": AGENT_HEALTH_PROJECTION_VERSION,
                "mutability": "read",
                "runtime_behavior_changed": False,
            },
        }
    )


def _require_project(db: Session, project_id: str) -> None:
    if db.query(Project.id).filter(Project.id == project_id).first() is None:
        raise HTTPException(status_code=404, detail="Project not found")


def _profile_policy_audit_from_tool_plan(tool_plan: dict[str, Any]) -> dict[str, Any] | None:
    projection = (
        tool_plan.get("agent_profile_tool_projection")
        if isinstance(tool_plan.get("agent_profile_tool_projection"), dict)
        else {}
    )
    audit = projection.get("consistency_audit")
    return dict(audit) if isinstance(audit, dict) else None


def _profile_policy_audit_summary(audit: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(audit, dict):
        return None
    summary = audit.get("summary") if isinstance(audit.get("summary"), dict) else {}
    issues = audit.get("issues") if isinstance(audit.get("issues"), list) else []
    return {
        "version": str(audit.get("version") or ""),
        "status": str(audit.get("status") or ""),
        "summary": {
            "issues": _non_negative_int(summary.get("issues")),
            "delegate_edges": _non_negative_int(summary.get("delegate_edges")),
        },
        "issues": [_profile_policy_issue_summary(issue) for issue in issues if isinstance(issue, dict)],
    }


def _profile_policy_issue_summary(issue: dict[str, Any]) -> dict[str, Any]:
    summary = {
        "code": str(issue.get("code") or ""),
        "severity": str(issue.get("severity") or ""),
        "profile": str(issue.get("profile") or ""),
    }
    target = str(issue.get("target") or "").strip()
    if target:
        summary["target"] = target
    return summary


def _route_preference_summary(output: dict[str, Any]) -> dict[str, Any]:
    summary = output.get("summary") if isinstance(output.get("summary"), dict) else {}
    trace = output.get("trace") if isinstance(output.get("trace"), dict) else {}
    return {
        "status": str(output.get("status") or ""),
        "version": output.get("version"),
        "summary": {
            "route_count": _non_negative_int(summary.get("route_count")),
            "recommended_migration_count": _non_negative_int(summary.get("recommended_migration_count")),
            "missing_preferred_tool_count": _non_negative_int(summary.get("missing_preferred_tool_count")),
        },
        "missing_preferred_tools": _string_list(trace.get("missing_preferred_tools")),
    }


def _tool_contract_summary(output: dict[str, Any]) -> dict[str, Any]:
    summary = output.get("summary") if isinstance(output.get("summary"), dict) else {}
    return {
        "status": str(output.get("status") or ""),
        "summary": {
            "total_tools": _non_negative_int(summary.get("total_tools")),
            "tools_needing_work": _non_negative_int(summary.get("tools_needing_work")),
            "gap_count": _non_negative_int(summary.get("gap_count")),
        },
        "coverage": output.get("coverage") if isinstance(output.get("coverage"), dict) else {},
        "recommended_next_steps": _string_list(output.get("recommended_next_steps")),
    }


def _write_gate_summary(output: dict[str, Any]) -> dict[str, Any]:
    summary = output.get("summary") if isinstance(output.get("summary"), dict) else {}
    return {
        "status": str(output.get("status") or ""),
        "summary": {
            "write_tool_count": _non_negative_int(summary.get("write_tool_count")),
            "missing_agent_plan_gate_count": _non_negative_int(summary.get("missing_agent_plan_gate_count")),
            "high_risk_direct_write_count": _non_negative_int(summary.get("high_risk_direct_write_count")),
        },
        "recommended_next_targets": output.get("recommended_next_targets")
        if isinstance(output.get("recommended_next_targets"), list)
        else [],
    }


def _trace_audit_summary(db: Session, project_id: str, run_id: str | None) -> dict[str, Any] | None:
    if not run_id:
        return None
    output = inspect_agent_trace_audit(db, project_id, run_id=run_id)
    audit = output.get("audit") if isinstance(output.get("audit"), dict) else {}
    return {
        "run_id": run_id,
        "status": audit.get("status"),
        "profile_policy_status": audit.get("profile_policy_status"),
        "profile_policy_issue_count": _non_negative_int(audit.get("profile_policy_issue_count")),
        "recommended_actions": output.get("recommended_actions") if isinstance(output.get("recommended_actions"), list) else [],
    }


def _diagnostics(
    *,
    profile_policy: dict[str, Any] | None,
    route_preference: dict[str, Any],
    tool_contracts: dict[str, Any],
    write_gate: dict[str, Any],
    trace_audit: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    if profile_policy and profile_policy.get("status") not in {"passed", ""}:
        diagnostics.append(
            {
                "code": "agent_profile_policy_needs_attention",
                "severity": "error",
                "message": "Agent profile 与工具策略存在一致性风险，规划前应检查工具面。",
                "issue_count": profile_policy.get("summary", {}).get("issues", 0),
            }
        )
    if trace_audit and trace_audit.get("profile_policy_status") not in {None, "passed"}:
        diagnostics.append(
            {
                "code": "latest_run_profile_policy_needs_attention",
                "severity": "warning",
                "message": "最近运行的 Trace 审计显示 profile policy 需要关注。",
                "issue_count": trace_audit.get("profile_policy_issue_count", 0),
            }
        )
    route_summary = route_preference.get("summary") if isinstance(route_preference.get("summary"), dict) else {}
    if route_preference.get("status") != "ready" or _non_negative_int(route_summary.get("missing_preferred_tool_count")):
        diagnostics.append(
            {
                "code": "agent_route_preference_degraded",
                "severity": "warning",
                "message": "对话入口 Agent 路由偏好存在缺口或推荐工具链不可用。",
                "missing_preferred_tool_count": route_summary.get("missing_preferred_tool_count", 0),
            }
        )
    contract_summary = tool_contracts.get("summary") if isinstance(tool_contracts.get("summary"), dict) else {}
    if _non_negative_int(contract_summary.get("gap_count")):
        diagnostics.append(
            {
                "code": "agent_tool_contract_gaps",
                "severity": "warning",
                "message": "Agent 工具契约仍存在迁移或 schema 差距。",
                "gap_count": contract_summary.get("gap_count", 0),
                "tools_needing_work": contract_summary.get("tools_needing_work", 0),
            }
        )
    write_summary = write_gate.get("summary") if isinstance(write_gate.get("summary"), dict) else {}
    if _non_negative_int(write_summary.get("high_risk_direct_write_count")):
        diagnostics.append(
            {
                "code": "agent_write_gate_high_risk",
                "severity": "warning",
                "message": "仍存在高风险写入工具缺少 Agent 计划审批门禁。",
                "high_risk_direct_write_count": write_summary.get("high_risk_direct_write_count", 0),
            }
        )
    return diagnostics


def _health_status(diagnostics: list[dict[str, Any]]) -> str:
    severities = {str(item.get("severity") or "") for item in diagnostics}
    if "error" in severities:
        return "needs_attention"
    if diagnostics:
        return "degraded"
    return "ready"


def _recommended_tools(diagnostics: list[dict[str, Any]]) -> list[str]:
    tools_by_code = {
        "agent_profile_policy_needs_attention": ["describe_agent_tools"],
        "latest_run_profile_policy_needs_attention": ["inspect_agent_trace_audit"],
        "agent_route_preference_degraded": ["inspect_agent_route_preference_projection"],
        "agent_tool_contract_gaps": ["inspect_agent_tool_contracts"],
        "agent_write_gate_high_risk": ["inspect_agent_write_gate_coverage"],
    }
    tools: list[str] = []
    for diagnostic in diagnostics:
        tools.extend(tools_by_code.get(str(diagnostic.get("code") or ""), []))
    return _dedupe(tools)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    cleaned = str(value).strip()
    return [cleaned] if cleaned else []


def _non_negative_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

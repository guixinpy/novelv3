from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Project, WritingAgentRun, WritingAgentStep
from app.services.writing_agent.agent_loop_risk import build_agent_loop_risk
from app.services.writing_agent.agent_command_contracts import inspect_agent_command_contracts
from app.services.writing_agent.agent_context_compression_projection import inspect_agent_context_compression_projection
from app.services.writing_agent.agent_control_plane_readiness import inspect_agent_control_plane_readiness
from app.services.writing_agent.agent_trace_audit import inspect_agent_trace_audit
from app.services.writing_agent.memory_activation import build_memory_activation_plan
from app.services.writing_agent.narrative_trend_projection import inspect_narrative_trend_projection
from app.services.writing_agent.slash_command_route import inspect_agent_route_preference_projection
from app.services.writing_agent.tool_contracts import build_agent_tool_contract_snapshot
from app.services.writing_agent.tool_registry import allowed_tool_names, build_agent_tool_plan
from app.services.writing_agent.write_gate_coverage import inspect_agent_write_gate_coverage

AGENT_HEALTH_PROJECTION_VERSION = "phase218.agent_health_projection.v1"
CREATIVE_QUALITY_REVIEW_TOOLS = ("review_chapter_quality", "review_chapter_continuity")


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
    raw_tool_contracts = build_agent_tool_contract_snapshot(
        adapter_metadata_by_name=adapter_metadata_by_name,
        include_gap_details=False,
    )
    tool_contracts = _tool_contract_summary(raw_tool_contracts)
    raw_command_contracts = inspect_agent_command_contracts(
        adapter_names_provider=lambda: static_adapter_tool_names,
    )
    command_contracts = _command_contract_summary(raw_command_contracts)
    control_plane_readiness = _control_plane_readiness_summary(
        inspect_agent_control_plane_readiness(
            tool_contract_snapshot_provider=lambda: raw_tool_contracts,
            command_contract_provider=lambda: raw_command_contracts,
        )
    )
    write_gate = _write_gate_summary(inspect_agent_write_gate_coverage(adapter_metadata_by_name=adapter_metadata_by_name))
    trace_audit = _trace_audit_summary(db, project_id, run_id)
    loop_risk = _loop_risk_summary(db, project_id, run_id)
    creative_quality = _creative_quality_summary(db, project_id)
    context_compression = _context_compression_summary(db, project_id, chapter_index)
    memory_activation = _memory_activation_summary(db, project_id, chapter_index)
    narrative_trends = inspect_narrative_trend_projection(db, project_id, chapter_index=chapter_index)

    diagnostics = _diagnostics(
        profile_policy=profile_policy,
        route_preference=route_preference,
        tool_contracts=tool_contracts,
        command_contracts=command_contracts,
        write_gate=write_gate,
        trace_audit=trace_audit,
        loop_risk=loop_risk,
        creative_quality=creative_quality,
        context_compression=context_compression,
        memory_activation=memory_activation,
        narrative_trends=narrative_trends,
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
            "command_contracts": command_contracts,
            "control_plane_readiness": control_plane_readiness,
            "write_gate": write_gate,
            "trace_audit": trace_audit,
            "loop_risk": loop_risk,
            "creative_quality": creative_quality,
            "context_compression": context_compression,
            "memory_activation": memory_activation,
            "narrative_trends": narrative_trends,
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


def _command_contract_summary(output: dict[str, Any]) -> dict[str, Any]:
    summary = output.get("summary") if isinstance(output.get("summary"), dict) else {}
    return {
        "status": str(output.get("status") or ""),
        "version": output.get("version"),
        "summary": {
            "total_commands": _non_negative_int(summary.get("total_commands")),
            "agent_control_commands": _non_negative_int(summary.get("agent_control_commands")),
            "commands_with_control_projection": _non_negative_int(summary.get("commands_with_control_projection")),
            "gap_count": _non_negative_int(summary.get("gap_count")),
        },
        "recommended_next_tools": _string_list(output.get("recommended_next_tools")),
    }


def _control_plane_readiness_summary(output: dict[str, Any]) -> dict[str, Any]:
    summary = output.get("summary") if isinstance(output.get("summary"), dict) else {}
    return {
        "status": str(output.get("status") or ""),
        "version": output.get("version"),
        "summary": {
            "total_tools": _non_negative_int(summary.get("total_tools")),
            "tools_needing_work": _non_negative_int(summary.get("tools_needing_work")),
            "tool_gap_count": _non_negative_int(summary.get("tool_gap_count")),
            "total_commands": _non_negative_int(summary.get("total_commands")),
            "agent_control_commands": _non_negative_int(summary.get("agent_control_commands")),
            "commands_with_control_projection": _non_negative_int(summary.get("commands_with_control_projection")),
            "command_gap_count": _non_negative_int(summary.get("command_gap_count")),
            "total_gap_count": _non_negative_int(summary.get("total_gap_count")),
        },
        "recommended_next_tools": _string_list(output.get("recommended_next_tools")),
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


def _loop_risk_summary(db: Session, project_id: str, run_id: str | None) -> dict[str, Any] | None:
    run_query = db.query(WritingAgentRun).filter(WritingAgentRun.project_id == project_id)
    if run_id:
        run = run_query.filter(WritingAgentRun.id == run_id).first()
    else:
        run = run_query.order_by(WritingAgentRun.created_at.desc(), WritingAgentRun.id.desc()).first()
    if run is None:
        return None
    steps = (
        db.query(WritingAgentStep)
        .filter(WritingAgentStep.run_id == run.id)
        .order_by(WritingAgentStep.step_index.asc(), WritingAgentStep.id.asc())
        .all()
    )
    run_input = run.input if isinstance(run.input, dict) else {}
    planned_tools = run_input.get("tools") if isinstance(run_input.get("tools"), list) else []
    risk = build_agent_loop_risk(
        steps,
        planned_tools=[tool for tool in planned_tools if isinstance(tool, dict)],
        known_tool_names=allowed_tool_names(),
    )
    return {"run_id": run.id, **risk}


def _context_compression_summary(db: Session, project_id: str, chapter_index: int | None) -> dict[str, Any] | None:
    if not chapter_index:
        return None
    return inspect_agent_context_compression_projection(db, project_id, chapter_index=chapter_index)


def _memory_activation_summary(db: Session, project_id: str, chapter_index: int | None) -> dict[str, Any] | None:
    if not chapter_index:
        return None
    output = build_memory_activation_plan(db, project_id, chapter_index=chapter_index)
    return {
        "status": str(output.get("status") or ""),
        "coverage": output.get("coverage") if isinstance(output.get("coverage"), dict) else {},
        "risks": output.get("risks") if isinstance(output.get("risks"), list) else [],
        "recommended_next_tools": _string_list(output.get("recommended_next_tools")),
        "trace": output.get("trace") if isinstance(output.get("trace"), dict) else {},
    }


def _creative_quality_summary(db: Session, project_id: str) -> dict[str, Any]:
    steps = (
        db.query(WritingAgentStep)
        .filter(WritingAgentStep.project_id == project_id)
        .filter(WritingAgentStep.tool_name.in_(CREATIVE_QUALITY_REVIEW_TOOLS))
        .filter(WritingAgentStep.status == "success")
        .order_by(WritingAgentStep.chapter_index.asc(), WritingAgentStep.created_at.asc(), WritingAgentStep.id.asc())
        .all()
    )
    chapters_by_index: dict[int, dict[str, Any]] = {}
    review_step_count = 0
    for step in steps:
        chapter_index = _review_chapter_index(step)
        if chapter_index is None:
            continue
        review_step_count += 1
        output = step.output if isinstance(step.output, dict) else {}
        warnings = _review_warning_count(output)
        blockers = _review_blocker_count(output)
        findings = output.get("findings") if isinstance(output.get("findings"), list) else []
        chapter = chapters_by_index.setdefault(
            chapter_index,
            {
                "chapter_index": chapter_index,
                "review_step_count": 0,
                "warning_count": 0,
                "blocker_count": 0,
                "finding_count": 0,
                "finding_codes": [],
                "tools": [],
            },
        )
        chapter["review_step_count"] += 1
        chapter["warning_count"] += warnings
        chapter["blocker_count"] += blockers
        chapter["finding_count"] += _non_negative_int(output.get("finding_count") or len(findings))
        chapter["finding_codes"] = _dedupe(chapter["finding_codes"] + _finding_codes(findings))
        chapter["tools"].append(
            {
                "tool_name": step.tool_name,
                "status": str(output.get("status") or step.status or ""),
                "warning_count": warnings,
                "blocker_count": blockers,
            }
        )

    chapters = []
    for chapter in sorted(chapters_by_index.values(), key=lambda item: item["chapter_index"]):
        chapter["risk_score"] = chapter["blocker_count"] * 3 + chapter["warning_count"]
        chapters.append(chapter)

    if not chapters:
        return {
            "status": "insufficient_data",
            "trend": "insufficient_data",
            "window": {"chapter_count": 0, "review_step_count": 0, "latest_chapter_index": None},
            "chapters": [],
            "recommended_next_tools": list(CREATIVE_QUALITY_REVIEW_TOOLS),
        }

    risk_scores = [_non_negative_int(chapter.get("risk_score")) for chapter in chapters]
    has_blockers = any(_non_negative_int(chapter.get("blocker_count")) for chapter in chapters)
    has_warnings = any(_non_negative_int(chapter.get("warning_count")) for chapter in chapters)
    risk_rising = len(risk_scores) >= 2 and risk_scores[-1] > 0 and risk_scores[-1] > risk_scores[0]
    if risk_rising:
        trend = "risk_rising"
    elif has_blockers or has_warnings:
        trend = "risk_present"
    else:
        trend = "clear"
    if has_blockers or risk_rising:
        status = "needs_attention"
    elif has_warnings:
        status = "degraded"
    else:
        status = "ready"
    recommended_tools = list(CREATIVE_QUALITY_REVIEW_TOOLS)
    if status in {"needs_attention", "degraded"}:
        recommended_tools.append("plan_chapter_revision")
    return {
        "status": status,
        "trend": trend,
        "window": {
            "chapter_count": len(chapters),
            "review_step_count": review_step_count,
            "latest_chapter_index": chapters[-1]["chapter_index"],
        },
        "chapters": chapters,
        "recommended_next_tools": recommended_tools,
    }


def _review_chapter_index(step: WritingAgentStep) -> int | None:
    if step.chapter_index is not None:
        return _non_negative_int(step.chapter_index)
    output = step.output if isinstance(step.output, dict) else {}
    if output.get("chapter_index") is not None:
        return _non_negative_int(output.get("chapter_index"))
    input_payload = step.input if isinstance(step.input, dict) else {}
    params = input_payload.get("params") if isinstance(input_payload.get("params"), dict) else {}
    if params.get("chapter_index") is not None:
        return _non_negative_int(params.get("chapter_index"))
    return None


def _review_warning_count(output: dict[str, Any]) -> int:
    if output.get("warning_count") is not None:
        return _non_negative_int(output.get("warning_count"))
    findings = output.get("findings") if isinstance(output.get("findings"), list) else []
    return sum(1 for finding in findings if isinstance(finding, dict) and finding.get("severity") == "warning")


def _review_blocker_count(output: dict[str, Any]) -> int:
    if output.get("blocker_count") is not None:
        return _non_negative_int(output.get("blocker_count"))
    findings = output.get("findings") if isinstance(output.get("findings"), list) else []
    return sum(1 for finding in findings if isinstance(finding, dict) and finding.get("severity") == "blocker")


def _finding_codes(findings: list[Any]) -> list[str]:
    codes: list[str] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        code = str(finding.get("code") or "").strip()
        if code:
            codes.append(code)
    return codes


def _diagnostics(
    *,
    profile_policy: dict[str, Any] | None,
    route_preference: dict[str, Any],
    tool_contracts: dict[str, Any],
    command_contracts: dict[str, Any],
    write_gate: dict[str, Any],
    trace_audit: dict[str, Any] | None,
    loop_risk: dict[str, Any] | None,
    creative_quality: dict[str, Any],
    context_compression: dict[str, Any] | None,
    memory_activation: dict[str, Any] | None,
    narrative_trends: dict[str, Any],
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
    if loop_risk and loop_risk.get("status") in {"warning", "critical"}:
        action = (
            loop_risk.get("recommended_next_action")
            if isinstance(loop_risk.get("recommended_next_action"), dict)
            else {}
        )
        status = str(loop_risk.get("status") or "")
        diagnostics.append(
            {
                "code": f"agent_loop_risk_{status}",
                "severity": "error" if status == "critical" else "warning",
                "message": "最近运行的 Agent 工具循环存在可解释风险，继续执行前应检查 Trace 和恢复建议。",
                "detector": loop_risk.get("detector"),
                "reason": action.get("reason"),
                "next_tool": action.get("next_tool"),
                "recommended_tools": _dedupe(
                    ["inspect_agent_trace_audit"] + _string_list(action.get("recommended_tools"))
                ),
            }
        )
    if creative_quality.get("trend") == "risk_rising":
        window = creative_quality.get("window") if isinstance(creative_quality.get("window"), dict) else {}
        chapters = creative_quality.get("chapters") if isinstance(creative_quality.get("chapters"), list) else []
        latest_chapter = chapters[-1] if chapters and isinstance(chapters[-1], dict) else {}
        diagnostics.append(
            {
                "code": "creative_quality_risk_rising",
                "severity": "error" if creative_quality.get("status") == "needs_attention" else "warning",
                "message": "最近章节的质量或连续性审查风险正在上升，继续生成前应先规划修订。",
                "latest_chapter_index": window.get("latest_chapter_index"),
                "risk_score": latest_chapter.get("risk_score"),
                "recommended_tools": _string_list(creative_quality.get("recommended_next_tools")),
            }
        )
    if context_compression and context_compression.get("status") in {"warning", "blocked"}:
        status = str(context_compression.get("status") or "")
        risks = context_compression.get("risks") if isinstance(context_compression.get("risks"), list) else []
        risk_codes = [str(risk.get("code") or "") for risk in risks if isinstance(risk, dict)]
        diagnostics.append(
            {
                "code": f"agent_context_compression_{status}",
                "severity": "error" if status == "blocked" else "warning",
                "message": "章节上下文窗口或压缩断路器存在风险，继续生成前应检查上下文来源和恢复建议。",
                "risk_codes": risk_codes,
                "recommended_tools": _string_list(context_compression.get("recommended_next_tools")),
            }
        )
    if memory_activation and memory_activation.get("status") in {"degraded", "blocked"}:
        status = str(memory_activation.get("status") or "")
        risks = memory_activation.get("risks") if isinstance(memory_activation.get("risks"), list) else []
        risk_codes = [str(risk.get("code") or "") for risk in risks if isinstance(risk, dict)]
        diagnostics.append(
            {
                "code": f"agent_memory_activation_{status}",
                "severity": "error" if status == "blocked" else "warning",
                "message": "目标章节的长记忆激活存在覆盖债务或冲突风险，继续生成前应修复或明确降级使用。",
                "risk_codes": risk_codes,
                "coverage": memory_activation.get("coverage") if isinstance(memory_activation.get("coverage"), dict) else {},
                "recommended_tools": _string_list(memory_activation.get("recommended_next_tools")),
            }
        )
    if narrative_trends.get("status") in {"watch", "needs_human_judgment"}:
        status = str(narrative_trends.get("status") or "")
        diagnostics.append(
            {
                "code": f"narrative_trend_{status}",
                "severity": "error" if status == "needs_human_judgment" else "warning",
                "message": "长期叙事趋势存在风格、世界模型、伏笔或节奏风险，继续生成前应先处理趋势诊断。",
                "summary": narrative_trends.get("summary") if isinstance(narrative_trends.get("summary"), dict) else {},
                "recommended_tools": _string_list(narrative_trends.get("recommended_next_tools")),
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
    command_summary = command_contracts.get("summary") if isinstance(command_contracts.get("summary"), dict) else {}
    if _non_negative_int(command_summary.get("gap_count")):
        diagnostics.append(
            {
                "code": "agent_command_contract_gaps",
                "severity": "warning",
                "message": "Hermes 命令控制面存在 Agent 契约缺口，可能影响自主编排或状态反馈。",
                "gap_count": command_summary.get("gap_count", 0),
                "agent_control_commands": command_summary.get("agent_control_commands", 0),
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
        "agent_tool_contract_gaps": ["inspect_agent_control_plane_readiness", "inspect_agent_tool_contracts"],
        "agent_command_contract_gaps": ["inspect_agent_control_plane_readiness", "inspect_agent_command_contracts"],
        "agent_write_gate_high_risk": ["inspect_agent_write_gate_coverage"],
    }
    tools: list[str] = []
    for diagnostic in diagnostics:
        tools.extend(tools_by_code.get(str(diagnostic.get("code") or ""), []))
        tools.extend(_string_list(diagnostic.get("recommended_tools")))
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

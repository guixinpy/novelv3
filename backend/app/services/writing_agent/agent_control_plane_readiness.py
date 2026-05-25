from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.services.writing_agent.agent_command_contracts import inspect_agent_command_contracts
from app.services.writing_agent.tool_contracts import build_agent_tool_contract_snapshot


CONTROL_PLANE_READINESS_VERSION = "phase46.agent_control_plane_readiness.v1"
SnapshotProvider = Callable[[], dict[str, Any]]


def inspect_agent_control_plane_readiness(
    *,
    adapter_metadata_by_name: dict[str, dict[str, Any]] | None = None,
    static_adapter_tool_names: set[str] | None = None,
    tool_contract_snapshot_provider: SnapshotProvider | None = None,
    command_contract_provider: SnapshotProvider | None = None,
) -> dict[str, Any]:
    adapter_metadata_by_name = adapter_metadata_by_name or {}
    static_adapter_tool_names = static_adapter_tool_names or set()
    tool_contracts = (
        tool_contract_snapshot_provider()
        if tool_contract_snapshot_provider is not None
        else build_agent_tool_contract_snapshot(
            adapter_metadata_by_name=adapter_metadata_by_name,
            include_gap_details=False,
        )
    )
    command_contracts = (
        command_contract_provider()
        if command_contract_provider is not None
        else inspect_agent_command_contracts(adapter_names_provider=lambda: static_adapter_tool_names)
    )

    tool_summary = _tool_summary(tool_contracts)
    command_summary = _command_summary(command_contracts)
    diagnostics = _diagnostics(tool_summary=tool_summary, command_summary=command_summary)
    recommended_next_tools = _recommended_next_tools(diagnostics)
    status = "degraded" if diagnostics else "ready"
    summary = {
        **tool_summary,
        **command_summary,
        "total_gap_count": tool_summary["tool_gap_count"] + command_summary["command_gap_count"],
    }
    return {
        "status": status,
        "version": CONTROL_PLANE_READINESS_VERSION,
        "summary": summary,
        "diagnostics": diagnostics,
        "recommended_next_tools": recommended_next_tools,
        "control_surfaces": {
            "tool_contracts": {
                "status": str(tool_contracts.get("status") or ""),
                "coverage": tool_contracts.get("coverage") if isinstance(tool_contracts.get("coverage"), dict) else {},
                "summary": tool_summary,
            },
            "command_contracts": {
                "status": str(command_contracts.get("status") or ""),
                "version": command_contracts.get("version"),
                "summary": command_summary,
            },
        },
        "trace": {
            "source": "inspect_agent_control_plane_readiness",
            "version": CONTROL_PLANE_READINESS_VERSION,
            "bounded_summary": True,
            "omitted_fields": ["tools", "commands", "gaps"],
        },
    }


def _tool_summary(output: dict[str, Any]) -> dict[str, int]:
    summary = output.get("summary") if isinstance(output.get("summary"), dict) else {}
    return {
        "total_tools": _non_negative_int(summary.get("total_tools")),
        "tools_needing_work": _non_negative_int(summary.get("tools_needing_work")),
        "tool_gap_count": _non_negative_int(summary.get("gap_count")),
    }


def _command_summary(output: dict[str, Any]) -> dict[str, int]:
    summary = output.get("summary") if isinstance(output.get("summary"), dict) else {}
    return {
        "total_commands": _non_negative_int(summary.get("total_commands")),
        "agent_control_commands": _non_negative_int(summary.get("agent_control_commands")),
        "commands_with_control_projection": _non_negative_int(summary.get("commands_with_control_projection")),
        "command_gap_count": _non_negative_int(summary.get("gap_count")),
    }


def _diagnostics(
    *,
    tool_summary: dict[str, int],
    command_summary: dict[str, int],
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    if tool_summary["tool_gap_count"]:
        diagnostics.append(
            {
                "code": "agent_tool_contract_gaps",
                "severity": "warning",
                "message": "Agent 工具契约存在缺口，编排前应检查工具契约快照。",
                "gap_count": tool_summary["tool_gap_count"],
                "tools_needing_work": tool_summary["tools_needing_work"],
            }
        )
    if command_summary["command_gap_count"]:
        diagnostics.append(
            {
                "code": "agent_command_contract_gaps",
                "severity": "warning",
                "message": "Agent 命令控制面存在缺口，可能影响对话控制与状态投影。",
                "gap_count": command_summary["command_gap_count"],
                "agent_control_commands": command_summary["agent_control_commands"],
            }
        )
    return diagnostics


def _recommended_next_tools(diagnostics: list[dict[str, Any]]) -> list[str]:
    tools: list[str] = []
    for diagnostic in diagnostics:
        code = str(diagnostic.get("code") or "")
        if code == "agent_tool_contract_gaps":
            tools.append("inspect_agent_tool_contracts")
        elif code == "agent_command_contract_gaps":
            tools.append("inspect_agent_command_contracts")
    tools.append("inspect_agent_health_projection")
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


def _non_negative_int(value: object) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)

from __future__ import annotations

from typing import Any


CONTROL_PLANE_READINESS_SOURCE = "planner_trace.agent_health_projection.control_plane_readiness"


def control_plane_readiness_from_run_input(run_input: object) -> dict[str, Any] | None:
    if not isinstance(run_input, dict):
        return None
    planner = run_input.get("planner") if isinstance(run_input.get("planner"), dict) else {}
    trace = planner.get("trace") if isinstance(planner.get("trace"), dict) else {}
    health = trace.get("agent_health_projection") if isinstance(trace.get("agent_health_projection"), dict) else {}
    readiness = (
        health.get("control_plane_readiness") if isinstance(health.get("control_plane_readiness"), dict) else {}
    )
    summary = readiness.get("summary") if isinstance(readiness.get("summary"), dict) else {}
    if not summary:
        return None
    return {
        "source": CONTROL_PLANE_READINESS_SOURCE,
        "status": str(readiness.get("status") or "unknown"),
        "version": readiness.get("version"),
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
        "recommended_next_tools": _string_list(readiness.get("recommended_next_tools")),
    }


def control_plane_readiness_needs_attention(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    summary = value.get("summary") if isinstance(value.get("summary"), dict) else {}
    return str(value.get("status") or "") not in {"", "ready"} or _non_negative_int(summary.get("total_gap_count")) > 0


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    cleaned = str(value).strip()
    return [cleaned] if cleaned else []


def _non_negative_int(value: object) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)

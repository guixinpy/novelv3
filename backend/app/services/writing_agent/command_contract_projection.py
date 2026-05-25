from __future__ import annotations

from typing import Any


COMMAND_CONTRACTS_SOURCE = "planner_trace.agent_health_projection.command_contracts"


def command_contracts_from_run_input(run_input: object) -> dict[str, Any] | None:
    if not isinstance(run_input, dict):
        return None
    planner = run_input.get("planner") if isinstance(run_input.get("planner"), dict) else {}
    trace = planner.get("trace") if isinstance(planner.get("trace"), dict) else {}
    health = trace.get("agent_health_projection") if isinstance(trace.get("agent_health_projection"), dict) else {}
    contracts = health.get("command_contracts") if isinstance(health.get("command_contracts"), dict) else {}
    summary = contracts.get("summary") if isinstance(contracts.get("summary"), dict) else {}
    if not summary:
        return None
    return {
        "source": COMMAND_CONTRACTS_SOURCE,
        "summary": {
            "total_commands": _optional_int(summary.get("total_commands")) or 0,
            "public_commands": _optional_int(summary.get("public_commands")) or 0,
            "agent_control_commands": _optional_int(summary.get("agent_control_commands")) or 0,
            "available_commands": _optional_int(summary.get("available_commands")) or 0,
            "gap_count": _optional_int(summary.get("gap_count")) or 0,
        },
    }


def command_contracts_needs_attention(command_contracts: dict[str, Any] | None) -> bool:
    if not isinstance(command_contracts, dict):
        return False
    summary = command_contracts.get("summary") if isinstance(command_contracts.get("summary"), dict) else {}
    return (_optional_int(summary.get("gap_count")) or 0) > 0


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

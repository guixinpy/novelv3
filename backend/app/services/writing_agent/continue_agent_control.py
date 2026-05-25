from __future__ import annotations

from typing import Any

from app.core.chat_commands import CONTINUE_REQUIRED_AGENT_TOOLS

CONTINUE_AGENT_CONTROL_VERSION = "phase32.continue_agent_control.v1"


def build_continue_agent_control_projection(
    *,
    selected_route: str,
    reason_code: str,
    source_run_id: str | None = None,
    source: str = "slash_command",
) -> dict[str, Any]:
    return {
        "version": CONTINUE_AGENT_CONTROL_VERSION,
        "command_name": "continue",
        "source": source,
        "selected_route": selected_route,
        "reason_code": reason_code,
        "source_run_id": source_run_id,
        "required_agent_tools": list(CONTINUE_REQUIRED_AGENT_TOOLS),
    }


def continue_agent_control_to_route_decision(agent_control: dict[str, Any]) -> dict[str, Any]:
    route_decision = {
        "version": "phase20.dialog_continue_route_decision.v1",
        "trigger": "low_detail_continue",
        "selected_route": str(agent_control.get("selected_route") or ""),
        "reason_code": str(agent_control.get("reason_code") or ""),
        "priority": ["recover_blocked_run", "recommended_followups", "chapter_generation"],
    }
    source_run_id = agent_control.get("source_run_id")
    if source_run_id:
        route_decision["source_run_id"] = str(source_run_id)
    return route_decision

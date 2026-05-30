from __future__ import annotations

from typing import Any


def approval_required_redirect(
    *,
    project_id: str,
    tool_name: str,
    target_type: str,
    prepare_tool: str,
    execute_tool: str,
    command_args: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": "approval_required_before_write",
        "project_id": project_id,
        "target_type": target_type,
        "command_args": command_args,
        **(extra or {}),
        "required_approval": {
            "prepare_tool": prepare_tool,
            "execute_tool": execute_tool,
            "approval_scope": "agent_plan_approval",
        },
        "side_effects": {"executed": [], "skipped": [tool_name]},
        "recommended_next_tools": [prepare_tool],
        "trace": {
            "selected_tools": [],
            "rejected_tools": [{"tool_name": tool_name, "reason": "approval_required_before_write"}],
            "source": "direct_agent_write_guard",
        },
    }

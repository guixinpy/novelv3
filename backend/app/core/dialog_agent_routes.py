from __future__ import annotations

from typing import Literal

DIALOG_AGENT_ROUTE_VERSION = "phase104.dialog_agent_route.v1"

DialogAgentRouteSource = Literal["slash_command", "text_intent", "button_action"]

_DIALOG_ACTION_TO_AGENT_TOOL: dict[str, str] = {
    "preview_setup": "generate_setup",
    "preview_storyline": "generate_storyline",
    "preview_outline": "generate_outline",
    "preview_chapter": "generate_chapter",
    "generate_setup": "generate_setup",
    "generate_storyline": "generate_storyline",
    "generate_outline": "generate_outline",
    "generate_chapter": "generate_chapter",
}

_PREVIEW_DIALOG_ACTION_TYPES = (
    "preview_setup",
    "preview_storyline",
    "preview_outline",
    "preview_chapter",
)


def preview_dialog_action_types() -> tuple[str, ...]:
    return _PREVIEW_DIALOG_ACTION_TYPES


def dialog_action_to_agent_tool_name(action_type: str | None) -> str | None:
    return _DIALOG_ACTION_TO_AGENT_TOOL.get((action_type or "").strip())


def build_dialog_agent_route(
    action_type: str | None,
    *,
    source: DialogAgentRouteSource,
    command_name: str | None = None,
) -> dict[str, str | bool] | None:
    normalized_action_type = (action_type or "").strip()
    agent_tool_name = dialog_action_to_agent_tool_name(normalized_action_type)
    if not normalized_action_type or not agent_tool_name:
        return None
    route: dict[str, str | bool] = {
        "version": DIALOG_AGENT_ROUTE_VERSION,
        "source": source,
        "action_type": normalized_action_type,
        "agent_action_type": agent_tool_name,
        "agent_tool_name": agent_tool_name,
        "requires_confirmation": True,
        "entrypoint": "dialog_pending_action",
    }
    normalized_command_name = (command_name or "").strip().lower()
    if normalized_command_name:
        route["command_name"] = normalized_command_name
    return route

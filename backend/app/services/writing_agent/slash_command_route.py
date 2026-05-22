from __future__ import annotations

from typing import Any

from app.core.chat_commands import CHAT_COMMAND_REGISTRY, agent_slash_command_routes
from app.services.writing_agent.tool_registry import get_agent_tool_descriptor

SLASH_COMMAND_ROUTE_PROJECTION_VERSION = "phase103.slash_command_route_projection.v1"


def inspect_agent_slash_command_route(
    command_name: str | None = None,
    *,
    static_adapter_tool_names: set[str] | None = None,
    action_execution_tool_names: set[str] | None = None,
) -> dict[str, Any]:
    selected_command_name = (command_name or "").strip().lower() or None
    static_adapter_tool_names = static_adapter_tool_names or set()
    action_execution_tool_names = action_execution_tool_names or set()
    routes = [
        route
        for route in agent_slash_command_routes()
        if selected_command_name is None or route["command_name"] == selected_command_name
    ]

    enriched_routes: list[dict[str, Any]] = []
    missing_tools: list[str] = []
    unsupported_tools: list[str] = []
    for route in routes:
        tool_name = str(route["agent_tool_name"])
        descriptor = get_agent_tool_descriptor(tool_name)
        if descriptor is None:
            missing_tools.append(tool_name)
        execution_backend: str | None = None
        if tool_name in static_adapter_tool_names:
            execution_backend = "static_adapter"
        elif tool_name in action_execution_tool_names:
            execution_backend = "action_execution_service"
        if execution_backend is None:
            unsupported_tools.append(tool_name)
        enriched_routes.append(
            {
                **route,
                "tool_registered": descriptor is not None,
                "tool_module": descriptor.module if descriptor is not None else None,
                "tool_category": descriptor.category if descriptor is not None else None,
                "execution_supported": execution_backend is not None,
                "execution_backend": execution_backend,
            }
        )

    non_agent_commands = [
        name
        for name, spec in CHAT_COMMAND_REGISTRY.items()
        if spec.agent_tool_name is None
    ]

    return {
        "status": "ready" if not missing_tools and not unsupported_tools else "degraded",
        "version": SLASH_COMMAND_ROUTE_PROJECTION_VERSION,
        "routes": enriched_routes,
        "trace": {
            "selected_command_name": selected_command_name,
            "non_agent_commands": non_agent_commands,
            "missing_tools": missing_tools,
            "unsupported_tools": unsupported_tools,
        },
    }

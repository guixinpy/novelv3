from __future__ import annotations

from typing import Any

from app.core.chat_commands import CHAT_COMMAND_REGISTRY, agent_slash_command_routes
from app.core.dialog_agent_routes import (
    build_dialog_agent_route,
    dialog_action_to_agent_tool_name,
    preview_dialog_action_types,
)
from app.services.writing_agent.tool_registry import get_agent_tool_descriptor

SLASH_COMMAND_ROUTE_PROJECTION_VERSION = "phase103.slash_command_route_projection.v1"
DIALOG_ROUTE_PROJECTION_VERSION = "phase104.dialog_route_projection.v1"


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

    enriched_routes, missing_tools, unsupported_tools = _enrich_routes(
        routes,
        static_adapter_tool_names=static_adapter_tool_names,
        action_execution_tool_names=action_execution_tool_names,
    )

    non_agent_commands = [
        name
        for name, spec in CHAT_COMMAND_REGISTRY.items()
        if dialog_action_to_agent_tool_name(spec.action_type) is None
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


def inspect_agent_dialog_route_projection(
    *,
    source: str | None = None,
    static_adapter_tool_names: set[str] | None = None,
    action_execution_tool_names: set[str] | None = None,
) -> dict[str, Any]:
    selected_source = (source or "").strip() or None
    sources = ("slash_command", "text_intent", "button_action")
    routes: list[dict[str, str | bool]] = []
    if selected_source in (None, "slash_command"):
        routes.extend(agent_slash_command_routes())
    for route_source in ("text_intent", "button_action"):
        if selected_source not in (None, route_source):
            continue
        for action_type in preview_dialog_action_types():
            route = build_dialog_agent_route(action_type, source=route_source)
            if route is not None:
                routes.append(route)

    enriched_routes, missing_tools, unsupported_tools = _enrich_routes(
        routes,
        static_adapter_tool_names=static_adapter_tool_names or set(),
        action_execution_tool_names=action_execution_tool_names or set(),
    )

    return {
        "status": "ready" if not missing_tools and not unsupported_tools else "degraded",
        "version": DIALOG_ROUTE_PROJECTION_VERSION,
        "routes": enriched_routes,
        "trace": {
            "selected_source": selected_source,
            "sources": [item for item in sources if selected_source in (None, item)],
            "missing_tools": missing_tools,
            "unsupported_tools": unsupported_tools,
        },
    }


def _enrich_routes(
    routes: list[dict[str, str | bool]],
    *,
    static_adapter_tool_names: set[str],
    action_execution_tool_names: set[str],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
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
    return enriched_routes, missing_tools, unsupported_tools

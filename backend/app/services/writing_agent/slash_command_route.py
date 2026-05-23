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
ROUTE_PREFERENCE_PROJECTION_VERSION = "phase115.route_preference_projection.v1"
APPROVED_GENERATION_CHAINS = {
    ("generate_setup", "preview_setup"): (
        "prepare_generate_setup_execution",
        "execute_generate_setup_with_approval",
    ),
    ("generate_storyline", "preview_storyline"): (
        "prepare_generate_storyline_execution",
        "execute_generate_storyline_with_approval",
    ),
    ("generate_outline", "preview_outline"): (
        "prepare_generate_outline_execution",
        "execute_generate_outline_with_approval",
    ),
    ("generate_chapter", "preview_chapter"): (
        "prepare_generate_chapter_execution",
        "execute_generate_chapter_with_approval",
    ),
    ("generate_chapter", "generate_chapter"): (
        "prepare_generate_chapter_execution",
        "execute_generate_chapter_with_approval",
    ),
}
APPROVED_GENERATION_APPROVAL_FIELDS = (
    "confirm_execute",
    "approval_contract_hash",
    "approval_contract",
)
APPROVED_GENERATION_REASON_CODES = {
    "generate_chapter": "chapter_generation_should_use_approved_agent_gate",
}


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


def inspect_agent_route_preference_projection(
    *,
    source: str | None = None,
    static_adapter_tool_names: set[str] | None = None,
    action_execution_tool_names: set[str] | None = None,
) -> dict[str, Any]:
    static_adapter_tool_names = static_adapter_tool_names or set()
    action_execution_tool_names = action_execution_tool_names or set()
    route_projection = inspect_agent_dialog_route_projection(
        source=source,
        static_adapter_tool_names=static_adapter_tool_names,
        action_execution_tool_names=action_execution_tool_names,
    )

    routes: list[dict[str, Any]] = []
    missing_preferred_tools: set[str] = set()
    recommended_migration_count = 0
    for route in route_projection.get("routes") or []:
        if not isinstance(route, dict):
            continue
        preference = _route_preference(
            route,
            static_adapter_tool_names=static_adapter_tool_names,
            action_execution_tool_names=action_execution_tool_names,
        )
        missing_preferred_tools.update(preference["missing_preferred_tools"])
        if preference["migration_status"] == "recommended_not_applied":
            recommended_migration_count += 1
        routes.append(preference)

    status = (
        "ready"
        if route_projection.get("status") == "ready" and not missing_preferred_tools
        else "degraded"
    )
    return {
        "status": status,
        "version": ROUTE_PREFERENCE_PROJECTION_VERSION,
        "summary": {
            "route_count": len(routes),
            "recommended_migration_count": recommended_migration_count,
            "missing_preferred_tool_count": len(missing_preferred_tools),
        },
        "routes": routes,
        "trace": {
            "selected_source": route_projection.get("trace", {}).get("selected_source"),
            "runtime_behavior_changed": False,
            "missing_tools": route_projection.get("trace", {}).get("missing_tools", []),
            "unsupported_tools": route_projection.get("trace", {}).get("unsupported_tools", []),
            "missing_preferred_tools": sorted(missing_preferred_tools),
        },
    }


def _route_preference(
    route: dict[str, Any],
    *,
    static_adapter_tool_names: set[str],
    action_execution_tool_names: set[str],
) -> dict[str, Any]:
    current_tool_name = str(route.get("agent_tool_name") or "")
    preferred_tool_chain = _preferred_tool_chain(route, current_tool_name)
    missing_preferred_tools = [
        tool_name
        for tool_name in preferred_tool_chain
        if not _tool_execution_supported(
            tool_name,
            static_adapter_tool_names=static_adapter_tool_names,
            action_execution_tool_names=action_execution_tool_names,
        )
    ]
    approval_gate_required = preferred_tool_chain != [current_tool_name]
    preferred_prepare_tool = preferred_tool_chain[0] if approval_gate_required else None
    preferred_execute_tool = preferred_tool_chain[-1] if approval_gate_required else None
    return {
        **route,
        "current_tool_name": current_tool_name,
        "runtime_tool_name": current_tool_name,
        "current_execution_backend": route.get("execution_backend"),
        "preferred_tool_chain": preferred_tool_chain,
        "preferred_prepare_tool_name": preferred_prepare_tool,
        "preferred_execute_tool_name": preferred_execute_tool,
        "preferred_execution_supported": not missing_preferred_tools,
        "missing_preferred_tools": missing_preferred_tools,
        "approval_gate_required": approval_gate_required,
        "required_approval_fields": (
            list(APPROVED_GENERATION_APPROVAL_FIELDS)
            if approval_gate_required
            else []
        ),
        "runtime_route_changed": False,
        "runtime_behavior_changed": False,
        "migration_status": "recommended_not_applied" if approval_gate_required else "no_change",
        "reason_code": (
            _approved_generation_reason_code(current_tool_name)
            if approval_gate_required
            else "current_route_is_preferred"
        ),
    }


def _preferred_tool_chain(route: dict[str, Any], current_tool_name: str) -> list[str]:
    action_type = str(route.get("action_type") or "")
    chain = APPROVED_GENERATION_CHAINS.get((current_tool_name, action_type))
    if chain is not None:
        return list(chain)
    return [current_tool_name]


def _approved_generation_reason_code(current_tool_name: str) -> str:
    return APPROVED_GENERATION_REASON_CODES.get(
        current_tool_name,
        f"{current_tool_name}_should_use_approved_agent_gate",
    )


def _tool_execution_supported(
    tool_name: str,
    *,
    static_adapter_tool_names: set[str],
    action_execution_tool_names: set[str],
) -> bool:
    if get_agent_tool_descriptor(tool_name) is None:
        return False
    return tool_name in static_adapter_tool_names or tool_name in action_execution_tool_names


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

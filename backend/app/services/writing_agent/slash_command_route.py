from __future__ import annotations

import copy
from typing import Any

from app.core.chat_commands import CHAT_COMMAND_REGISTRY, agent_slash_command_routes
from app.core.dialog_agent_routes import (
    DIALOG_AGENT_ROUTE_APPROVAL_CHAIN_OPT_IN_KEY,
    build_dialog_agent_route,
    dialog_action_to_agent_tool_name,
    preview_dialog_action_types,
)
from app.services.writing_agent.tool_registry import get_agent_tool_descriptor

SLASH_COMMAND_ROUTE_PROJECTION_VERSION = "phase103.slash_command_route_projection.v1"
DIALOG_ROUTE_PROJECTION_VERSION = "phase104.dialog_route_projection.v1"
ROUTE_PREFERENCE_PROJECTION_VERSION = "phase115.route_preference_projection.v1"
ROUTE_APPROVAL_OPT_IN_PLAN_VERSION = "phase196.route_approval_opt_in_plan.v1"
PENDING_ACTION_ROUTE_OPT_IN_APPLY_PREVIEW_VERSION = "phase198.pending_action_route_opt_in_apply_preview.v1"
DIALOG_ROUTE_SOURCES = {"slash_command", "text_intent", "button_action"}
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
    approval_chain_opt_in_action_types: Any = None,
    static_adapter_tool_names: set[str] | None = None,
    action_execution_tool_names: set[str] | None = None,
) -> dict[str, Any]:
    selected_source = (source or "").strip() or None
    opt_in_action_types = _normalize_action_type_filter(approval_chain_opt_in_action_types)
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
    routes = [
        _route_with_approval_chain_opt_in(route, approval_chain_opt_in_action_types=opt_in_action_types)
        for route in routes
    ]

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
            "approval_chain_opt_in_action_types": sorted(opt_in_action_types),
            "missing_tools": missing_tools,
            "unsupported_tools": unsupported_tools,
        },
    }


def inspect_agent_route_preference_projection(
    *,
    source: str | None = None,
    approval_chain_opt_in_action_types: Any = None,
    static_adapter_tool_names: set[str] | None = None,
    action_execution_tool_names: set[str] | None = None,
) -> dict[str, Any]:
    static_adapter_tool_names = static_adapter_tool_names or set()
    action_execution_tool_names = action_execution_tool_names or set()
    route_projection = inspect_agent_dialog_route_projection(
        source=source,
        approval_chain_opt_in_action_types=approval_chain_opt_in_action_types,
        static_adapter_tool_names=static_adapter_tool_names,
        action_execution_tool_names=action_execution_tool_names,
    )

    routes: list[dict[str, Any]] = []
    missing_preferred_tools: set[str] = set()
    recommended_migration_count = 0
    opt_in_declared_count = 0
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
        if preference["approval_chain_opt_in_declared"] is True:
            opt_in_declared_count += 1
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
            "opt_in_declared_count": opt_in_declared_count,
            "missing_preferred_tool_count": len(missing_preferred_tools),
        },
        "routes": routes,
        "trace": {
            "selected_source": route_projection.get("trace", {}).get("selected_source"),
            "runtime_behavior_changed": False,
            "approval_chain_opt_in_action_types": route_projection.get("trace", {}).get(
                "approval_chain_opt_in_action_types",
                [],
            ),
            "missing_tools": route_projection.get("trace", {}).get("missing_tools", []),
            "unsupported_tools": route_projection.get("trace", {}).get("unsupported_tools", []),
            "missing_preferred_tools": sorted(missing_preferred_tools),
        },
    }


def plan_agent_route_approval_opt_in(
    *,
    action_type: str | None = None,
    source: str | None = None,
    command_name: str | None = None,
    agent_route: dict[str, Any] | None = None,
    static_adapter_tool_names: set[str] | None = None,
    action_execution_tool_names: set[str] | None = None,
) -> dict[str, Any]:
    static_adapter_tool_names = static_adapter_tool_names or set()
    action_execution_tool_names = action_execution_tool_names or set()
    route = _route_from_plan_input(
        action_type=action_type,
        source=source,
        command_name=command_name,
        agent_route=agent_route,
    )
    if route is None:
        return {
            "status": "blocked",
            "version": ROUTE_APPROVAL_OPT_IN_PLAN_VERSION,
            "can_apply": False,
            "write_performed": False,
            "metadata_patch": {},
            "route_before": None,
            "route_after": None,
            "preference": None,
            "suggestion": None,
            "missing_preferred_tools": [],
            "risk": {
                "codes": ["route_not_available"],
                "missing_preferred_tools": [],
                "guardrails": _approval_opt_in_guardrails(),
            },
            "trace": {
                "reason_code": "route_not_available",
                "runtime_behavior_changed": False,
            },
        }

    route_before = dict(route)
    preference = _route_preference(
        route_before,
        static_adapter_tool_names=static_adapter_tool_names,
        action_execution_tool_names=action_execution_tool_names,
    )
    suggestion = preference.get("approval_chain_opt_in_suggestion")
    metadata_patch = dict(suggestion.get("route_metadata_patch") or {}) if isinstance(suggestion, dict) else {}
    route_after = {**route_before, **metadata_patch} if metadata_patch else dict(route_before)
    suggestion_status = str(suggestion.get("status") or "") if isinstance(suggestion, dict) else ""
    status = _prewrite_plan_status(suggestion_status, has_suggestion=isinstance(suggestion, dict))
    missing_preferred_tools = list(preference.get("missing_preferred_tools") or [])
    return {
        "status": status,
        "version": ROUTE_APPROVAL_OPT_IN_PLAN_VERSION,
        "can_apply": status == "ready",
        "write_performed": False,
        "metadata_patch": metadata_patch if status in {"ready", "already_declared", "blocked"} else {},
        "route_before": route_before,
        "route_after": route_after if status != "noop" else dict(route_before),
        "preference": preference,
        "suggestion": suggestion,
        "missing_preferred_tools": missing_preferred_tools,
        "risk": _prewrite_plan_risk(
            route_before=route_before,
            status=status,
            missing_preferred_tools=missing_preferred_tools,
        ),
        "trace": {
            "reason_code": suggestion_status or "approval_gate_not_required",
            "runtime_behavior_changed": False,
        },
    }


def preview_pending_action_route_approval_opt_in_apply(
    *,
    pending_action_id: str,
    pending_action_type: str | None,
    pending_params: dict[str, Any] | None,
    route_plan: dict[str, Any],
) -> dict[str, Any]:
    params_before = copy.deepcopy(dict(pending_params or {}))
    plan_status = str(route_plan.get("status") or "")
    metadata_patch = copy.deepcopy(dict(route_plan.get("metadata_patch") or {}))
    route_after = copy.deepcopy(route_plan.get("route_after")) if isinstance(route_plan.get("route_after"), dict) else None
    params_after = copy.deepcopy(params_before)
    params_diff: dict[str, Any] = {}
    if plan_status == "ready" and metadata_patch and route_after is not None:
        before_route = params_before.get("agent_route")
        params_after["agent_route"] = route_after
        if before_route != route_after:
            params_diff["agent_route"] = {"before": before_route, "after": route_after}
    status = plan_status if plan_status in {"ready", "already_declared", "blocked", "noop"} else "blocked"
    return {
        "status": status,
        "version": PENDING_ACTION_ROUTE_OPT_IN_APPLY_PREVIEW_VERSION,
        "write_performed": False,
        "pending_action_id": pending_action_id,
        "pending_action_type": pending_action_type,
        "params_before": params_before,
        "params_after": params_after,
        "params_diff": params_diff,
        "route_plan": route_plan,
        "risk": dict(route_plan.get("risk") or {}),
        "trace": {
            "pending_action_id": pending_action_id,
            "pending_action_type": pending_action_type,
            "runtime_behavior_changed": False,
        },
    }


def blocked_pending_action_route_approval_opt_in_apply_preview(
    *,
    pending_action_id: str,
    pending_action_type: str | None,
    pending_params: dict[str, Any] | None,
    risk_code: str,
) -> dict[str, Any]:
    route_plan = {
        "status": "blocked",
        "version": ROUTE_APPROVAL_OPT_IN_PLAN_VERSION,
        "can_apply": False,
        "write_performed": False,
        "metadata_patch": {},
        "route_before": None,
        "route_after": None,
        "preference": None,
        "suggestion": None,
        "missing_preferred_tools": [],
        "risk": {
            "codes": [risk_code],
            "missing_preferred_tools": [],
            "guardrails": _approval_opt_in_guardrails(),
        },
        "trace": {"reason_code": risk_code, "runtime_behavior_changed": False},
    }
    return preview_pending_action_route_approval_opt_in_apply(
        pending_action_id=pending_action_id,
        pending_action_type=pending_action_type,
        pending_params=pending_params,
        route_plan=route_plan,
    )


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
    approval_chain_opt_in_declared = route.get(DIALOG_AGENT_ROUTE_APPROVAL_CHAIN_OPT_IN_KEY) is True
    preferred_prepare_tool = preferred_tool_chain[0] if approval_gate_required else None
    preferred_execute_tool = preferred_tool_chain[-1] if approval_gate_required else None
    preferred_execution_supported = not missing_preferred_tools
    return {
        **route,
        "current_tool_name": current_tool_name,
        "runtime_tool_name": current_tool_name,
        "current_execution_backend": route.get("execution_backend"),
        "preferred_tool_chain": preferred_tool_chain,
        "preferred_prepare_tool_name": preferred_prepare_tool,
        "preferred_execute_tool_name": preferred_execute_tool,
        "preferred_execution_supported": preferred_execution_supported,
        "missing_preferred_tools": missing_preferred_tools,
        "approval_gate_required": approval_gate_required,
        "approval_chain_opt_in_param_name": DIALOG_AGENT_ROUTE_APPROVAL_CHAIN_OPT_IN_KEY,
        "approval_chain_opt_in_declared": approval_chain_opt_in_declared,
        "approval_chain_opt_in_available": approval_gate_required and preferred_execution_supported,
        "approval_chain_opt_in_suggestion": _approval_chain_opt_in_suggestion(
            approval_gate_required=approval_gate_required,
            approval_chain_opt_in_declared=approval_chain_opt_in_declared,
            preferred_execution_supported=preferred_execution_supported,
            preferred_prepare_tool=preferred_prepare_tool,
            preferred_execute_tool=preferred_execute_tool,
        ),
        "required_approval_fields": (
            list(APPROVED_GENERATION_APPROVAL_FIELDS)
            if approval_gate_required
            else []
        ),
        "runtime_route_changed": False,
        "runtime_behavior_changed": False,
        "migration_status": "opt_in_declared"
        if approval_gate_required and approval_chain_opt_in_declared
        else "recommended_not_applied"
        if approval_gate_required
        else "no_change",
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


def _route_from_plan_input(
    *,
    action_type: str | None,
    source: str | None,
    command_name: str | None,
    agent_route: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if isinstance(agent_route, dict):
        return dict(agent_route)
    normalized_source = str(source or "slash_command").strip() or "slash_command"
    if normalized_source not in DIALOG_ROUTE_SOURCES:
        return None
    route = build_dialog_agent_route(
        action_type,
        source=normalized_source,  # type: ignore[arg-type]
        command_name=command_name,
    )
    return dict(route) if route is not None else None


def _prewrite_plan_status(suggestion_status: str, *, has_suggestion: bool) -> str:
    if not has_suggestion:
        return "noop"
    if suggestion_status == "available":
        return "ready"
    if suggestion_status == "already_declared":
        return "already_declared"
    return "blocked"


def _prewrite_plan_risk(
    *,
    route_before: dict[str, Any],
    status: str,
    missing_preferred_tools: list[str],
) -> dict[str, Any]:
    codes: list[str] = []
    action_type = str(route_before.get("action_type") or "")
    if status == "ready":
        codes.append("requires_explicit_opt_in")
    elif status == "already_declared":
        codes.append("already_declared")
    elif status == "noop":
        if action_type.startswith("generate_"):
            codes.append("action_type_not_dialog_route")
        codes.append("approval_gate_not_required")
    elif missing_preferred_tools:
        codes.append("missing_preferred_tools")
    return {
        "codes": codes,
        "missing_preferred_tools": missing_preferred_tools,
        "guardrails": _approval_opt_in_guardrails(),
    }


def _approval_chain_opt_in_suggestion(
    *,
    approval_gate_required: bool,
    approval_chain_opt_in_declared: bool,
    preferred_execution_supported: bool,
    preferred_prepare_tool: str | None,
    preferred_execute_tool: str | None,
) -> dict[str, Any] | None:
    if not approval_gate_required:
        return None
    status = "already_declared" if approval_chain_opt_in_declared else "available"
    if not preferred_execution_supported:
        status = "blocked_missing_tools"
    return {
        "status": status,
        "param_name": DIALOG_AGENT_ROUTE_APPROVAL_CHAIN_OPT_IN_KEY,
        "route_metadata_patch": {DIALOG_AGENT_ROUTE_APPROVAL_CHAIN_OPT_IN_KEY: True},
        "expected_prepare_tool_name": preferred_prepare_tool,
        "expected_execute_tool_name": preferred_execute_tool,
        "runtime_default_preserved": True,
        "guardrails": _approval_opt_in_guardrails(),
    }


def _approval_opt_in_guardrails() -> list[str]:
    return [
        "apply_only_when_explicitly_requested",
        "preserve_default_dialog_routes",
        "strip_control_plane_params_before_tool_execution",
    ]


def _normalize_action_type_filter(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value.strip()} if value.strip() else set()
    if isinstance(value, (list, tuple, set)):
        return {str(item).strip() for item in value if str(item).strip()}
    return set()


def _route_with_approval_chain_opt_in(
    route: dict[str, str | bool],
    *,
    approval_chain_opt_in_action_types: set[str],
) -> dict[str, str | bool]:
    if route.get("action_type") not in approval_chain_opt_in_action_types:
        return route
    return {**route, DIALOG_AGENT_ROUTE_APPROVAL_CHAIN_OPT_IN_KEY: True}


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

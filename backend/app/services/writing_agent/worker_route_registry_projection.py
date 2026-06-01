from __future__ import annotations

from typing import Any


WORKER_ROUTE_REGISTRY_SOURCE = "planner_trace.agent_health_projection.agent_worker_route_registry"


def worker_route_registry_from_run_input(run_input: object) -> dict[str, Any] | None:
    if not isinstance(run_input, dict):
        return None
    planner = run_input.get("planner") if isinstance(run_input.get("planner"), dict) else {}
    trace = planner.get("trace") if isinstance(planner.get("trace"), dict) else {}
    health = trace.get("agent_health_projection") if isinstance(trace.get("agent_health_projection"), dict) else {}
    registry = (
        health.get("agent_worker_route_registry")
        if isinstance(health.get("agent_worker_route_registry"), dict)
        else {}
    )
    summary = registry.get("summary") if isinstance(registry.get("summary"), dict) else {}
    if not summary:
        return None
    return {
        "source": WORKER_ROUTE_REGISTRY_SOURCE,
        "status": str(registry.get("status") or "unknown"),
        "version": registry.get("version"),
        "summary": {
            "routes": _non_negative_int(summary.get("routes")),
            "ready_routes": _non_negative_int(summary.get("ready_routes")),
            "unrouted_allowed_tools": _non_negative_int(summary.get("unrouted_allowed_tools")),
            "issues": _non_negative_int(summary.get("issues")),
        },
    }


def _non_negative_int(value: object) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)

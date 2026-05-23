from __future__ import annotations

from typing import Any

from app.services.writing_agent.tool_contracts import agent_tool_execution_metadata
from app.services.writing_agent.tool_registry import get_agent_tool_descriptor


LEGACY_HERMES_ACTIONS = (
    {
        "tool_name": "generate_setup",
        "target_type": "setup",
        "artifact": "setup",
        "hash_field": "setup_plan_hash",
    },
    {
        "tool_name": "generate_storyline",
        "target_type": "storyline",
        "artifact": "storyline",
        "hash_field": "storyline_plan_hash",
    },
    {
        "tool_name": "generate_outline",
        "target_type": "outline",
        "artifact": "outline",
        "hash_field": "outline_plan_hash",
    },
)


def inspect_legacy_hermes_action_migration(
    *,
    adapter_metadata_by_name: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    adapter_metadata_by_name = adapter_metadata_by_name or {}
    tools = [
        _migration_item(action, adapter_metadata_by_name.get(str(action["tool_name"])))
        for action in LEGACY_HERMES_ACTIONS
    ]
    return {
        "status": "completed",
        "version": "phase185.legacy_hermes_migration_projection.v1",
        "summary": {
            "legacy_action_count": len(tools),
            "legacy_action_fallback_count": sum(
                1 for tool in tools if tool["current_execution_route"] == "legacy_action_fallback"
            ),
            "agent_native_ready_count": sum(1 for tool in tools if tool["migration_stage"] == "agent_native_ready"),
        },
        "tools": tools,
        "recommended_next_tools": ["inspect_agent_tool_contracts"],
        "trace": {"source": "inspect_legacy_hermes_action_migration"},
    }


def _migration_item(action: dict[str, str], adapter_metadata: dict[str, Any] | None) -> dict[str, Any]:
    tool_name = action["tool_name"]
    descriptor = get_agent_tool_descriptor(tool_name)
    execution_metadata = agent_tool_execution_metadata(descriptor, adapter_metadata)
    return {
        "tool_name": tool_name,
        "target_type": action["target_type"],
        "current_execution_route": _execution_route(descriptor, adapter_metadata),
        "current_mutability": execution_metadata["mutability"],
        "migration_stage": "agent_native_ready" if adapter_metadata else "needs_agent_native_adapter",
        "recommended_agent_native_shape": {
            "preview_tool": f"preview_{tool_name}_execution",
            "approval_tool": f"prepare_{tool_name}_execution",
            "execute_tool": f"execute_{tool_name}_with_approval",
            "artifact": action["artifact"],
        },
        "required_guards": ["confirm_execute", action["hash_field"]],
        "required_evidence": ["trace_id", "execution_route", "agent_tool_result"],
        "risk": {
            "level": "high" if adapter_metadata is None else "medium",
            "reason": "legacy_action_fallback_without_agent_native_approval"
            if adapter_metadata is None
            else "agent_native_adapter_available",
        },
    }


def _execution_route(descriptor: Any | None, adapter_metadata: dict[str, Any] | None) -> str:
    if adapter_metadata:
        adapter_type = str(adapter_metadata.get("adapter_type") or "adapter")
        return f"{adapter_type}_adapter"
    if descriptor is None:
        return "unsupported"
    if getattr(descriptor, "internal", False):
        return "unsupported_internal"
    return "legacy_action_fallback"

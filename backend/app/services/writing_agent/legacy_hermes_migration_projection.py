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
    tools = [_migration_item(action, adapter_metadata_by_name) for action in LEGACY_HERMES_ACTIONS]
    return {
        "status": "completed",
        "version": "phase185.legacy_hermes_migration_projection.v1",
        "summary": {
            "legacy_action_count": len(tools),
            "legacy_action_fallback_count": sum(
                1 for tool in tools if tool["current_execution_route"] == "legacy_action_fallback"
            ),
            "agent_native_ready_count": sum(1 for tool in tools if _agent_native_ready(tool)),
        },
        "tools": tools,
        "recommended_next_tools": ["inspect_agent_tool_contracts"],
        "trace": {"source": "inspect_legacy_hermes_action_migration"},
    }


def _migration_item(
    action: dict[str, str],
    adapter_metadata_by_name: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    tool_name = action["tool_name"]
    descriptor = get_agent_tool_descriptor(tool_name)
    adapter_metadata = adapter_metadata_by_name.get(tool_name)
    recommended_shape = _recommended_agent_native_shape(action)
    approval_wrapper = _approval_wrapper(recommended_shape, adapter_metadata_by_name)
    execution_metadata = agent_tool_execution_metadata(descriptor, adapter_metadata)
    migration_stage = _migration_stage(adapter_metadata, approval_wrapper)
    return {
        "tool_name": tool_name,
        "target_type": action["target_type"],
        "current_execution_route": _execution_route(descriptor, adapter_metadata),
        "agent_native_execution_route": approval_wrapper["execute_route"],
        "current_mutability": execution_metadata["mutability"],
        "migration_stage": migration_stage,
        "recommended_agent_native_shape": recommended_shape,
        "approval_wrapper": approval_wrapper,
        "required_guards": ["confirm_execute", action["hash_field"]],
        "required_evidence": ["trace_id", "execution_route", "agent_tool_result"],
        "risk": {
            "level": _risk_level(migration_stage),
            "reason": _risk_reason(migration_stage),
        },
    }


def _recommended_agent_native_shape(action: dict[str, str]) -> dict[str, str]:
    tool_name = action["tool_name"]
    return {
        "preview_tool": f"preview_{tool_name}_execution",
        "approval_tool": f"prepare_{tool_name}_execution",
        "execute_tool": f"execute_{tool_name}_with_approval",
        "artifact": action["artifact"],
    }


def _approval_wrapper(
    recommended_shape: dict[str, str],
    adapter_metadata_by_name: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    execute_tool = recommended_shape["execute_tool"]
    execute_metadata = adapter_metadata_by_name.get(execute_tool)
    return {
        "preview_tool": recommended_shape["preview_tool"],
        "approval_tool": recommended_shape["approval_tool"],
        "execute_tool": execute_tool,
        "execute_adapter_exists": execute_metadata is not None,
        "execute_route": _adapter_execution_route(execute_metadata),
        "execute_handler_name": execute_metadata.get("handler_name") if execute_metadata else None,
    }


def _migration_stage(adapter_metadata: dict[str, Any] | None, approval_wrapper: dict[str, Any]) -> str:
    if adapter_metadata is not None:
        return "agent_native_ready"
    if approval_wrapper.get("execute_adapter_exists") is True:
        return "agent_native_wrapper_ready"
    return "needs_agent_native_adapter"


def _agent_native_ready(tool: dict[str, Any]) -> bool:
    return tool.get("migration_stage") in {"agent_native_ready", "agent_native_wrapper_ready"}


def _risk_level(migration_stage: str) -> str:
    if migration_stage == "agent_native_ready":
        return "medium"
    if migration_stage == "agent_native_wrapper_ready":
        return "low"
    return "high"


def _risk_reason(migration_stage: str) -> str:
    if migration_stage == "agent_native_ready":
        return "agent_native_adapter_available"
    if migration_stage == "agent_native_wrapper_ready":
        return "agent_native_approval_wrapper_available"
    return "legacy_action_fallback_without_agent_native_approval"


def _adapter_execution_route(adapter_metadata: dict[str, Any] | None) -> str:
    if adapter_metadata:
        adapter_type = str(adapter_metadata.get("adapter_type") or "adapter")
        return f"{adapter_type}_adapter"
    return "missing"


def _execution_route(descriptor: Any | None, adapter_metadata: dict[str, Any] | None) -> str:
    if adapter_metadata:
        adapter_type = str(adapter_metadata.get("adapter_type") or "adapter")
        return f"{adapter_type}_adapter"
    if descriptor is None:
        return "unsupported"
    if getattr(descriptor, "internal", False):
        return "unsupported_internal"
    return "legacy_action_fallback"

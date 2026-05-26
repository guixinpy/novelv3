from __future__ import annotations

from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.agent_tool_surface_policy import build_agent_profile_definition
from app.services.writing_agent.tool_adapter_types import WritingAgentToolContext
from app.services.writing_agent.tool_contracts import agent_tool_execution_metadata
from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor

TOOL_LIFECYCLE_HOOKS_VERSION = "phase228.tool_lifecycle_hooks.v1"
CHILD_AGENT_ROLES = frozenset({"worker"})


def run_before_tool_call_hooks(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
    *,
    descriptor: AgentToolDescriptor | None,
    adapter_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    del context
    agent_profile = _agent_profile(tool)
    metadata = agent_tool_execution_metadata(descriptor, adapter_metadata)
    mutability = str(metadata.get("mutability") or "unclassified")
    requires_confirmation = metadata.get("requires_confirmation") is True
    reason_code = _denial_reason(agent_profile, mutability)
    allow_call = reason_code is None
    event = {
        "event_type": "tool_call_before",
        "tool_name": tool.tool_name,
        "agent_profile": agent_profile,
        "mutability": mutability,
        "requires_confirmation": requires_confirmation,
        "status": "allowed" if allow_call else "denied",
        "allow_call": allow_call,
    }
    if reason_code is not None:
        event["reason_code"] = reason_code
    return {
        "version": TOOL_LIFECYCLE_HOOKS_VERSION,
        "hook": "before_tool_call",
        "tool_name": tool.tool_name,
        "agent_profile": agent_profile,
        "mutability": mutability,
        "requires_confirmation": requires_confirmation,
        "status": "allowed" if allow_call else "denied",
        "allow_call": allow_call,
        "reason_code": reason_code,
        "events": [event],
    }


def run_after_tool_call_hooks(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
    output: dict[str, Any],
    *,
    descriptor: AgentToolDescriptor | None,
    adapter_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    del context
    agent_profile = _agent_profile(tool)
    metadata = agent_tool_execution_metadata(descriptor, adapter_metadata)
    result_status = str(output.get("status") or "completed")
    event = {
        "event_type": "tool_call_after",
        "tool_name": tool.tool_name,
        "agent_profile": agent_profile,
        "mutability": str(metadata.get("mutability") or "unclassified"),
        "requires_confirmation": metadata.get("requires_confirmation") is True,
        "status": "completed",
        "result_status": result_status,
        "output_keys": sorted(str(key) for key in output),
    }
    return {
        "version": TOOL_LIFECYCLE_HOOKS_VERSION,
        "hook": "after_tool_call",
        "tool_name": tool.tool_name,
        "agent_profile": agent_profile,
        "status": "completed",
        "events": [event],
    }


def run_tool_error_hooks(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
    error: BaseException,
    *,
    descriptor: AgentToolDescriptor | None,
    adapter_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    del context
    agent_profile = _agent_profile(tool)
    metadata = agent_tool_execution_metadata(descriptor, adapter_metadata)
    event = {
        "event_type": "tool_call_error",
        "tool_name": tool.tool_name,
        "agent_profile": agent_profile,
        "mutability": str(metadata.get("mutability") or "unclassified"),
        "requires_confirmation": metadata.get("requires_confirmation") is True,
        "status": "failed",
        "error_type": type(error).__name__,
        "message": str(error),
    }
    return {
        "version": TOOL_LIFECYCLE_HOOKS_VERSION,
        "hook": "on_tool_error",
        "tool_name": tool.tool_name,
        "agent_profile": agent_profile,
        "status": "failed",
        "events": [event],
    }


def build_tool_lifecycle_hooks(
    *,
    before: dict[str, Any],
    after: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    hooks = {
        "version": TOOL_LIFECYCLE_HOOKS_VERSION,
        "before": before,
    }
    if after is not None:
        hooks["after"] = after
    if error is not None:
        hooks["error"] = error
    return hooks


def _denial_reason(agent_profile: str | None, mutability: str) -> str | None:
    if agent_profile and mutability == "guarded_write" and _is_child_agent(agent_profile):
        return "child_agent_guarded_write_denied"
    return None


def _is_child_agent(agent_profile: str) -> bool:
    definition = build_agent_profile_definition(agent_profile, source="tool_lifecycle_hooks")
    if not isinstance(definition, dict):
        return False
    return str(definition.get("role") or "").strip() in CHILD_AGENT_ROLES


def _agent_profile(tool: WritingAgentToolRequest) -> str | None:
    params_profile = _string_value(tool.params.get("agent_profile"))
    if params_profile:
        return params_profile
    return _string_value(tool.planner.get("agent_profile") or tool.planner.get("profile"))


def _string_value(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None

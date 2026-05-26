from __future__ import annotations

import inspect
from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.approval_tool_metadata import build_approval_tool_metadata_by_name
from app.services.writing_agent.agent_core_tool_adapters import build_agent_core_tool_adapters
from app.services.writing_agent.agent_generation_tool_adapters import build_agent_generation_tool_adapters
from app.services.writing_agent.agent_memory_trace_tool_adapters import AGENT_MEMORY_TRACE_TOOL_ADAPTERS
from app.services.writing_agent.agent_task_queue_tool_adapters import AGENT_TASK_QUEUE_TOOL_ADAPTERS
from app.services.writing_agent.knowledge_base_tool_adapters import KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS
from app.services.writing_agent.longform_tool_adapters import build_longform_agent_tool_adapters
from app.services.writing_agent.memory_tree_tool_adapters import MEMORY_TREE_TOOL_ADAPTERS
from app.services.writing_agent.outline_generation_tool_adapters import build_outline_generation_agent_tool_adapters
from app.services.writing_agent.review_revision_tool_adapters import REVIEW_REVISION_AGENT_TOOL_ADAPTERS
from app.services.writing_agent.setup_generation_tool_adapters import build_setup_generation_agent_tool_adapters
from app.services.writing_agent.storyline_generation_tool_adapters import build_storyline_generation_agent_tool_adapters
from app.services.writing_agent.tool_adapter_types import WritingAgentToolExecutionResult
from app.services.writing_agent.tool_lifecycle_hooks import (
    build_tool_lifecycle_hooks,
    run_after_tool_call_hooks,
    run_before_tool_call_hooks,
    run_tool_error_hooks,
)
from app.services.writing_agent.tool_registry import get_agent_tool_descriptor, internal_tool_names
from app.services.writing_agent.world_model_tool_adapters import WORLD_MODEL_AGENT_TOOL_ADAPTERS


async def execute_writing_agent_tool(
    context: Any,
    tool: WritingAgentToolRequest,
    *,
    preflight_writing: Any | None = None,
) -> WritingAgentToolExecutionResult:
    descriptor = get_agent_tool_descriptor(tool.tool_name)
    if descriptor is None:
        return WritingAgentToolExecutionResult(handled=False)

    adapter = _STATIC_TOOL_ADAPTERS.get(tool.tool_name)
    if adapter is not None:
        adapter_metadata = adapter.to_metadata()
        before = run_before_tool_call_hooks(
            context,
            tool,
            descriptor=descriptor,
            adapter_metadata=adapter_metadata,
        )
        if before["allow_call"] is not True:
            return WritingAgentToolExecutionResult(
                handled=True,
                output=_blocked_by_lifecycle_hook(tool, before),
                lifecycle_hooks=build_tool_lifecycle_hooks(before=before),
            )
        try:
            output = adapter.handler(context, tool)
            if inspect.isawaitable(output):
                output = await output
        except ValueError:
            raise
        except Exception as exc:
            error = run_tool_error_hooks(
                context,
                tool,
                exc,
                descriptor=descriptor,
                adapter_metadata=adapter_metadata,
            )
            return WritingAgentToolExecutionResult(
                handled=True,
                output=_failed_by_lifecycle_hook(tool, exc),
                lifecycle_hooks=build_tool_lifecycle_hooks(before=before, error=error),
            )
        after = run_after_tool_call_hooks(
            context,
            tool,
            output,
            descriptor=descriptor,
            adapter_metadata=adapter_metadata,
        )
        return WritingAgentToolExecutionResult(
            handled=True,
            output=output,
            lifecycle_hooks=build_tool_lifecycle_hooks(before=before, after=after),
        )

    if tool.tool_name == "preflight_writing" and preflight_writing is not None:
        adapter_metadata = writing_agent_tool_adapter_metadata("preflight_writing")
        before = run_before_tool_call_hooks(
            context,
            tool,
            descriptor=descriptor,
            adapter_metadata=adapter_metadata,
        )
        if before["allow_call"] is not True:
            return WritingAgentToolExecutionResult(
                handled=True,
                output=_blocked_by_lifecycle_hook(tool, before),
                lifecycle_hooks=build_tool_lifecycle_hooks(before=before),
            )
        try:
            output = preflight_writing(context.project_id, tool.params)
        except ValueError:
            raise
        except Exception as exc:
            error = run_tool_error_hooks(
                context,
                tool,
                exc,
                descriptor=descriptor,
                adapter_metadata=adapter_metadata,
            )
            return WritingAgentToolExecutionResult(
                handled=True,
                output=_failed_by_lifecycle_hook(tool, exc),
                lifecycle_hooks=build_tool_lifecycle_hooks(before=before, error=error),
            )
        after = run_after_tool_call_hooks(
            context,
            tool,
            output,
            descriptor=descriptor,
            adapter_metadata=adapter_metadata,
        )
        return WritingAgentToolExecutionResult(
            handled=True,
            output=output,
            lifecycle_hooks=build_tool_lifecycle_hooks(before=before, after=after),
        )

    if not descriptor.internal:
        return WritingAgentToolExecutionResult(handled=False)

    return WritingAgentToolExecutionResult(handled=False)


def static_writing_agent_tool_adapter_names() -> set[str]:
    return set(_STATIC_TOOL_ADAPTERS)


def writing_agent_tool_adapter_metadata(tool_name: str) -> dict[str, Any] | None:
    adapter = _STATIC_TOOL_ADAPTERS.get(tool_name)
    if adapter is not None:
        return adapter.to_metadata()
    if tool_name == "preflight_writing":
        return {
            "tool_name": "preflight_writing",
            "adapter_type": "injected",
            "category": "preflight",
            "mutability": "read",
            "handler_name": "preflight_writing",
        }
    return None


def writing_agent_tool_adapter_metadata_by_name() -> dict[str, dict[str, Any]]:
    metadata = _static_adapter_metadata_by_name()
    preflight_metadata = writing_agent_tool_adapter_metadata("preflight_writing")
    if preflight_metadata is not None:
        metadata["preflight_writing"] = preflight_metadata
    return metadata


def unhandled_internal_writing_agent_tool_names() -> set[str]:
    handled = static_writing_agent_tool_adapter_names() | {"preflight_writing"}
    return internal_tool_names() - handled


def _approval_tool_metadata_by_name(plan: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    return build_approval_tool_metadata_by_name(plan, adapter_metadata_by_name=_static_adapter_metadata_by_name())


def _static_adapter_metadata_by_name() -> dict[str, dict[str, Any]]:
    return {name: adapter.to_metadata() for name, adapter in _STATIC_TOOL_ADAPTERS.items()}


def _blocked_by_lifecycle_hook(tool: WritingAgentToolRequest, before: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "blocked",
        "error": "Tool lifecycle hook denied execution",
        "reason_code": before.get("reason_code"),
        "tool_name": tool.tool_name,
        "agent_profile": before.get("agent_profile"),
        "write_performed": False,
    }


def _failed_by_lifecycle_hook(tool: WritingAgentToolRequest, exc: Exception) -> dict[str, Any]:
    return {
        "status": "failed",
        "error": str(exc),
        "error_type": type(exc).__name__,
        "tool_name": tool.tool_name,
    }


_STATIC_TOOL_ADAPTERS: dict[str, Any] = dict(AGENT_TASK_QUEUE_TOOL_ADAPTERS)
_STATIC_TOOL_ADAPTERS.update(
    build_setup_generation_agent_tool_adapters(approval_tool_metadata_provider=_approval_tool_metadata_by_name)
)
_STATIC_TOOL_ADAPTERS.update(
    build_storyline_generation_agent_tool_adapters(approval_tool_metadata_provider=_approval_tool_metadata_by_name)
)
_STATIC_TOOL_ADAPTERS.update(
    build_outline_generation_agent_tool_adapters(approval_tool_metadata_provider=_approval_tool_metadata_by_name)
)
_STATIC_TOOL_ADAPTERS.update(
    build_agent_generation_tool_adapters(approval_tool_metadata_provider=_approval_tool_metadata_by_name)
)
_STATIC_TOOL_ADAPTERS.update(
    build_agent_core_tool_adapters(
        adapter_metadata_by_name_provider=lambda: writing_agent_tool_adapter_metadata_by_name(),
        static_adapter_tool_names_provider=lambda: set(_STATIC_TOOL_ADAPTERS),
    )
)
_STATIC_TOOL_ADAPTERS.update(AGENT_MEMORY_TRACE_TOOL_ADAPTERS)
_STATIC_TOOL_ADAPTERS.update(MEMORY_TREE_TOOL_ADAPTERS)
_STATIC_TOOL_ADAPTERS.update(REVIEW_REVISION_AGENT_TOOL_ADAPTERS)
_STATIC_TOOL_ADAPTERS.update(WORLD_MODEL_AGENT_TOOL_ADAPTERS)
_STATIC_TOOL_ADAPTERS.update(KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS)
_STATIC_TOOL_ADAPTERS.update(
    build_longform_agent_tool_adapters(approval_tool_metadata_provider=_approval_tool_metadata_by_name)
)

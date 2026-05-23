from __future__ import annotations

import inspect
from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.approval_tool_metadata import build_approval_tool_metadata_by_name
from app.services.writing_agent.agent_core_tool_adapters import build_agent_core_tool_adapters
from app.services.writing_agent.agent_memory_trace_tool_adapters import AGENT_MEMORY_TRACE_TOOL_ADAPTERS
from app.services.writing_agent.knowledge_base_tool_adapters import KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS
from app.services.writing_agent.longform_tool_adapters import build_longform_agent_tool_adapters
from app.services.writing_agent.review_revision_tool_adapters import REVIEW_REVISION_AGENT_TOOL_ADAPTERS
from app.services.writing_agent.tool_adapter_types import (
    PreflightWriting,
    WritingAgentToolAdapter,
    WritingAgentToolContext,
    WritingAgentToolExecutionResult,
)
from app.services.writing_agent.tool_registry import get_agent_tool_descriptor, internal_tool_names
from app.services.writing_agent.world_model_tool_adapters import WORLD_MODEL_AGENT_TOOL_ADAPTERS


async def execute_writing_agent_tool(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
    *,
    preflight_writing: PreflightWriting | None = None,
) -> WritingAgentToolExecutionResult:
    descriptor = get_agent_tool_descriptor(tool.tool_name)
    if descriptor is None:
        return WritingAgentToolExecutionResult(handled=False)

    adapter = _STATIC_TOOL_ADAPTERS.get(tool.tool_name)
    if adapter is not None:
        output = adapter.handler(context, tool)
        if inspect.isawaitable(output):
            output = await output
        return WritingAgentToolExecutionResult(handled=True, output=output)

    if tool.tool_name == "preflight_writing" and preflight_writing is not None:
        return WritingAgentToolExecutionResult(
            handled=True,
            output=preflight_writing(context.project_id, tool.params),
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


def unhandled_internal_writing_agent_tool_names() -> set[str]:
    handled = static_writing_agent_tool_adapter_names() | {"preflight_writing"}
    return internal_tool_names() - handled


async def _generate_chapter(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.chapter_generation_tool import execute_generate_chapter_tool

    chapter_index = int(tool.params.get("chapter_index") or 1)
    return await execute_generate_chapter_tool(
        context.db,
        context.project_id,
        chapter_index=chapter_index,
        command_args=tool.command_args,
        action_params=tool.params,
    )


def _prepare_generate_chapter_execution(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.chapter_generation_execution import prepare_generate_chapter_execution

    return prepare_generate_chapter_execution(
        context.db,
        context.project_id,
        chapter_index=int(tool.params.get("chapter_index") or 1),
    )


async def _execute_generate_chapter_with_approval(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.chapter_generation_execution import execute_generate_chapter_with_approval

    chapter_index = int(tool.params.get("chapter_index") or 1)
    command_args = str(tool.params.get("command_args") or tool.command_args or "").strip() or None
    approval_contract = tool.params.get("approval_contract")
    return await execute_generate_chapter_with_approval(
        context.db,
        context.project_id,
        chapter_index=chapter_index,
        command_args=command_args,
        action_params=tool.params,
        confirm_execute=tool.params.get("confirm_execute") is True,
        approval_contract_hash=str(tool.params.get("approval_contract_hash") or "").strip() or None,
        approval_contract=approval_contract if isinstance(approval_contract, dict) else None,
        approval_tool_metadata_provider=_approval_tool_metadata_by_name,
    )


def _plan_chapter_conflict_recovery(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.chapter_conflict_recovery_planner import plan_chapter_conflict_recovery

    return plan_chapter_conflict_recovery(
        context.db,
        context.project_id,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
    )


def _approval_tool_metadata_by_name(plan: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    return build_approval_tool_metadata_by_name(plan, adapter_metadata_by_name=_static_adapter_metadata_by_name())


def _inspect_agent_job_projection(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.agent_job_projection import inspect_agent_job_projection

    return inspect_agent_job_projection(
        context.db,
        context.project_id,
        task_id=str(tool.params.get("task_id") or "").strip() or None,
        task_type=str(tool.params.get("task_type") or "").strip() or None,
        status=str(tool.params.get("status") or "").strip() or None,
        limit=_optional_int(tool.params.get("limit")),
        chapter_index=_optional_int(tool.params.get("chapter_index")),
    )


def _static_adapter_metadata_by_name() -> dict[str, dict[str, Any]]:
    return {name: adapter.to_metadata() for name, adapter in _STATIC_TOOL_ADAPTERS.items()}


async def _expand_outline_window(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.outline_window_tool import expand_outline_window_tool

    start_chapter = int(tool.params.get("start_chapter") or tool.params.get("chapter_index") or 1)
    end_chapter = int(tool.params.get("end_chapter") or start_chapter)
    command_args = str(tool.params.get("command_args") or tool.command_args or "").strip() or None
    return await expand_outline_window_tool(
        context.db,
        context.project_id,
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        command_args=command_args,
    )


def _backfill_outline_gaps(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.core.outline_lookup import backfill_missing_outline_chapters_from_content

    before_chapter = tool.params.get("before_chapter") or tool.params.get("chapter_index")
    return backfill_missing_outline_chapters_from_content(
        context.db,
        context.project_id,
        before_chapter=int(before_chapter) if before_chapter else None,
    )


_STATIC_TOOL_ADAPTERS: dict[str, WritingAgentToolAdapter] = {
    "generate_chapter": WritingAgentToolAdapter(
        "generate_chapter",
        _generate_chapter,
        category="generation",
        mutability="write",
    ),
    "prepare_generate_chapter_execution": WritingAgentToolAdapter(
        "prepare_generate_chapter_execution",
        _prepare_generate_chapter_execution,
        category="generation",
        mutability="read",
    ),
    "execute_generate_chapter_with_approval": WritingAgentToolAdapter(
        "execute_generate_chapter_with_approval",
        _execute_generate_chapter_with_approval,
        category="generation",
        mutability="write",
    ),
    "plan_chapter_conflict_recovery": WritingAgentToolAdapter(
        "plan_chapter_conflict_recovery",
        _plan_chapter_conflict_recovery,
        category="task_queue",
        mutability="read",
    ),
    "inspect_agent_job_projection": WritingAgentToolAdapter(
        "inspect_agent_job_projection",
        _inspect_agent_job_projection,
        category="task_queue",
        mutability="read",
    ),
    "expand_outline_window": WritingAgentToolAdapter(
        "expand_outline_window",
        _expand_outline_window,
        category="generation",
        mutability="write",
    ),
    "backfill_outline_gaps": WritingAgentToolAdapter(
        "backfill_outline_gaps",
        _backfill_outline_gaps,
        category="maintenance",
        mutability="write",
    ),
}
_STATIC_TOOL_ADAPTERS.update(
    build_agent_core_tool_adapters(
        adapter_metadata_by_name_provider=lambda: _static_adapter_metadata_by_name(),
        static_adapter_tool_names_provider=lambda: set(_STATIC_TOOL_ADAPTERS),
    )
)
_STATIC_TOOL_ADAPTERS.update(AGENT_MEMORY_TRACE_TOOL_ADAPTERS)
_STATIC_TOOL_ADAPTERS.update(REVIEW_REVISION_AGENT_TOOL_ADAPTERS)
_STATIC_TOOL_ADAPTERS.update(WORLD_MODEL_AGENT_TOOL_ADAPTERS)
_STATIC_TOOL_ADAPTERS.update(KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS)
_STATIC_TOOL_ADAPTERS.update(
    build_longform_agent_tool_adapters(approval_tool_metadata_provider=_approval_tool_metadata_by_name)
)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

from __future__ import annotations

from collections.abc import Callable
import json
from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_adapter_types import WritingAgentToolAdapter, WritingAgentToolContext

ApprovalToolMetadataProvider = Callable[[dict[str, Any] | None], dict[str, dict[str, Any]]]


def _inspect_agent_trace_audit(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.agent_trace_audit import inspect_agent_trace_audit

    return inspect_agent_trace_audit(
        context.db,
        context.project_id,
        run_id=str(tool.params.get("run_id") or "").strip() or None,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
        task_id=str(tool.params.get("task_id") or "").strip() or None,
        limit=_optional_int(tool.params.get("limit")),
    )


def _inspect_agent_memory_route(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.agent_memory_route import inspect_agent_memory_route

    return inspect_agent_memory_route(
        context.db,
        context.project_id,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
        query=str(tool.params.get("query") or tool.command_args or "").strip() or None,
        include_context_summary=tool.params.get("include_context_summary") is True,
    )


def _summarize_longform_context(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.longform_context_summary import summarize_longform_context

    return summarize_longform_context(
        context.db,
        context.project_id,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
        query=str(tool.params.get("query") or tool.command_args or "").strip() or None,
        max_chars=_optional_int(tool.params.get("max_chars")),
        include_prompt_context=tool.params.get("include_prompt_context") is True,
    )


def _inspect_agent_context_compression_projection(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.agent_context_compression_projection import (
        inspect_agent_context_compression_projection,
    )

    return inspect_agent_context_compression_projection(
        context.db,
        context.project_id,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
        max_chars=_optional_int(tool.params.get("max_chars")),
        context_guard_failure_count=_optional_int(tool.params.get("context_guard_failure_count")) or 0,
    )


def _inspect_agent_memory_activation_plan(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.memory_activation import build_memory_activation_plan

    return build_memory_activation_plan(
        context.db,
        context.project_id,
        chapter_index=_optional_int(tool.params.get("chapter_index")) or 1,
        query=str(tool.params.get("query") or tool.command_args or "").strip() or None,
    )


def _repair_longform_maintenance(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.core.longform_memory import repair_longform_maintenance

    return _json_safe_output(
        repair_longform_maintenance(
            context.db,
            context.project_id,
            limit=_optional_int(tool.params.get("limit")) or 20,
            repair_limit=_optional_int(tool.params.get("repair_limit")) or 100,
        )
    )


def build_agent_memory_trace_tool_adapters(
    *,
    approval_tool_metadata_provider: ApprovalToolMetadataProvider,
) -> dict[str, WritingAgentToolAdapter]:
    return {
        **AGENT_MEMORY_TRACE_TOOL_ADAPTERS,
        "prepare_repair_longform_maintenance": WritingAgentToolAdapter(
            "prepare_repair_longform_maintenance",
            _prepare_repair_longform_maintenance,
            category="maintenance",
            mutability="read",
        ),
        "execute_repair_longform_maintenance_with_approval": WritingAgentToolAdapter(
            "execute_repair_longform_maintenance_with_approval",
            _execute_repair_longform_maintenance_with_approval(approval_tool_metadata_provider),
            category="maintenance",
            mutability="write",
        ),
    }


def _prepare_repair_longform_maintenance(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.longform_maintenance_execution import prepare_repair_longform_maintenance

    return prepare_repair_longform_maintenance(
        context.db,
        context.project_id,
        action_params=tool.params,
    )


def _execute_repair_longform_maintenance_with_approval(
    approval_tool_metadata_provider: ApprovalToolMetadataProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], dict[str, Any]]:
    def execute_repair_longform_maintenance_with_approval_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.services.writing_agent.longform_maintenance_execution import (
            execute_repair_longform_maintenance_with_approval,
        )

        approval_contract = tool.params.get("approval_contract")
        return execute_repair_longform_maintenance_with_approval(
            context.db,
            context.project_id,
            action_params=tool.params,
            confirm_execute=tool.params.get("confirm_execute") is True,
            approval_contract_hash=str(tool.params.get("approval_contract_hash") or "").strip() or None,
            approval_contract=approval_contract if isinstance(approval_contract, dict) else None,
            approval_tool_metadata_provider=approval_tool_metadata_provider,
        )

    execute_repair_longform_maintenance_with_approval_adapter.__name__ = (
        "_execute_repair_longform_maintenance_with_approval"
    )
    return execute_repair_longform_maintenance_with_approval_adapter


AGENT_MEMORY_TRACE_TOOL_ADAPTERS: dict[str, WritingAgentToolAdapter] = {
    "inspect_agent_trace_audit": WritingAgentToolAdapter(
        "inspect_agent_trace_audit",
        _inspect_agent_trace_audit,
        category="trace",
        mutability="read",
    ),
    "inspect_agent_memory_route": WritingAgentToolAdapter(
        "inspect_agent_memory_route",
        _inspect_agent_memory_route,
        category="longform_memory",
        mutability="read",
    ),
    "summarize_longform_context": WritingAgentToolAdapter(
        "summarize_longform_context",
        _summarize_longform_context,
        category="longform_memory",
        mutability="read",
    ),
    "inspect_agent_context_compression_projection": WritingAgentToolAdapter(
        "inspect_agent_context_compression_projection",
        _inspect_agent_context_compression_projection,
        category="longform_memory",
        mutability="read",
    ),
    "inspect_agent_memory_activation_plan": WritingAgentToolAdapter(
        "inspect_agent_memory_activation_plan",
        _inspect_agent_memory_activation_plan,
        category="longform_memory",
        mutability="read",
    ),
    "repair_longform_maintenance": WritingAgentToolAdapter(
        "repair_longform_maintenance",
        _repair_longform_maintenance,
        category="maintenance",
        mutability="write",
    ),
}


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

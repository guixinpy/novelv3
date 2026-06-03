from __future__ import annotations

from collections.abc import Callable
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


def _inspect_agent_trace_anomaly_trends(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.agent_trace_audit import inspect_agent_trace_anomaly_trends

    return inspect_agent_trace_anomaly_trends(
        context.db,
        context.project_id,
        limit=_optional_int(tool.params.get("limit")),
        chapter_index=_optional_int(tool.params.get("chapter_index")),
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


def _search_agent_retrieval_context(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.agent_retrieval_context import search_agent_retrieval_context

    return search_agent_retrieval_context(
        context.db,
        context.project_id,
        query=str(tool.params.get("query") or tool.command_args or "").strip(),
        limit=_optional_int(tool.params.get("limit")),
        source_type=str(tool.params.get("source_type") or "").strip() or None,
        max_chapter_index=_optional_int(tool.params.get("max_chapter_index")),
        candidate_limit=_optional_int(tool.params.get("candidate_limit")),
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


def _build_agent_context_compression_payload(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.agent_context_compression_projection import (
        build_agent_context_compression_payload,
    )

    return build_agent_context_compression_payload(
        context.db,
        context.project_id,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
        max_chars=_optional_int(tool.params.get("max_chars")),
        context_guard_failure_count=_optional_int(tool.params.get("context_guard_failure_count")) or 0,
    )


def _record_agent_context_compression_summary(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.agent_context_compression_projection import (
        record_agent_context_compression_summary,
    )

    return record_agent_context_compression_summary(
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
    return {
        "status": "blocked",
        "reason": "approval_required_before_write",
        "project_id": context.project_id,
        "target_type": "longform_maintenance",
        "required_approval": {
            "prepare_tool": "prepare_repair_longform_maintenance",
            "execute_tool": "execute_repair_longform_maintenance_with_approval",
            "approval_scope": "agent_plan_approval",
        },
        "side_effects": {"executed": [], "skipped": ["repair_longform_maintenance"]},
        "recommended_next_tools": ["prepare_repair_longform_maintenance"],
        "trace": {
            "selected_tools": [],
            "rejected_tools": [
                {"tool_name": "repair_longform_maintenance", "reason": "approval_required_before_write"}
            ],
            "source": "direct_agent_write_guard",
        },
    }


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
    "inspect_agent_trace_anomaly_trends": WritingAgentToolAdapter(
        "inspect_agent_trace_anomaly_trends",
        _inspect_agent_trace_anomaly_trends,
        category="trace",
        mutability="read",
    ),
    "inspect_agent_memory_route": WritingAgentToolAdapter(
        "inspect_agent_memory_route",
        _inspect_agent_memory_route,
        category="longform_memory",
        mutability="read",
    ),
    "search_agent_retrieval_context": WritingAgentToolAdapter(
        "search_agent_retrieval_context",
        _search_agent_retrieval_context,
        category="retrieval",
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
    "build_agent_context_compression_payload": WritingAgentToolAdapter(
        "build_agent_context_compression_payload",
        _build_agent_context_compression_payload,
        category="longform_memory",
        mutability="read",
    ),
    "record_agent_context_compression_summary": WritingAgentToolAdapter(
        "record_agent_context_compression_summary",
        _record_agent_context_compression_summary,
        category="longform_memory",
        mutability="write",
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
        mutability="guarded_write",
        write_policy="approval_required_redirect",
    ),
}

def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

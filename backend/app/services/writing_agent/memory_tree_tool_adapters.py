from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_adapter_types import WritingAgentToolAdapter, WritingAgentToolContext

ApprovalToolMetadataProvider = Callable[[dict[str, Any] | None], dict[str, dict[str, Any]]]


def _inspect_agent_memory_tree(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.memory_tree import inspect_agent_memory_tree

    return inspect_agent_memory_tree(
        context.db,
        context.project_id,
        level=str(tool.params.get("level") or "").strip() or None,
        node_id=str(tool.params.get("node_id") or "").strip() or None,
        expand_node_id=str(tool.params.get("expand_node_id") or "").strip() or None,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
        query=str(tool.params.get("query") or tool.command_args or "").strip() or None,
        include_ancestors=_optional_bool(tool.params.get("include_ancestors")),
        max_depth=_optional_int(tool.params.get("max_depth")),
    )


def _inspect_agent_memory_tree_quality(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.memory_tree import inspect_agent_memory_tree_quality

    return inspect_agent_memory_tree_quality(
        context.db,
        context.project_id,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
        query=str(tool.params.get("query") or tool.command_args or "").strip() or None,
    )


def _build_agent_memory_tree_llm_summary_plan(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.memory_tree import build_agent_memory_tree_llm_summary_plan

    return build_agent_memory_tree_llm_summary_plan(
        context.db,
        context.project_id,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
        query=str(tool.params.get("query") or tool.command_args or "").strip() or None,
        max_source_chars=_optional_int(tool.params.get("max_source_chars")),
    )


def _record_agent_memory_tree_summaries(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": "approval_required_before_write",
        "project_id": context.project_id,
        "target_type": "agent_memory_tree_summary",
        "required_approval": {
            "prepare_tool": "prepare_record_agent_memory_tree_summaries",
            "execute_tool": "execute_record_agent_memory_tree_summaries_with_approval",
            "approval_scope": "agent_plan_approval",
        },
        "side_effects": {"executed": [], "skipped": ["record_agent_memory_tree_summaries"]},
        "recommended_next_tools": ["prepare_record_agent_memory_tree_summaries"],
        "trace": {
            "selected_tools": [],
            "rejected_tools": [
                {"tool_name": "record_agent_memory_tree_summaries", "reason": "approval_required_before_write"}
            ],
            "source": "direct_agent_write_guard",
        },
    }


def build_memory_tree_tool_adapters(
    *,
    approval_tool_metadata_provider: ApprovalToolMetadataProvider,
) -> dict[str, WritingAgentToolAdapter]:
    return {
        **MEMORY_TREE_TOOL_ADAPTERS,
        "prepare_record_agent_memory_tree_summaries": WritingAgentToolAdapter(
            "prepare_record_agent_memory_tree_summaries",
            _prepare_record_agent_memory_tree_summaries,
            category="longform_memory",
            mutability="read",
        ),
        "execute_record_agent_memory_tree_summaries_with_approval": WritingAgentToolAdapter(
            "execute_record_agent_memory_tree_summaries_with_approval",
            _execute_record_agent_memory_tree_summaries_with_approval(approval_tool_metadata_provider),
            category="longform_memory",
            mutability="write",
        ),
    }


def _prepare_record_agent_memory_tree_summaries(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.memory_tree_summary_execution import (
        prepare_record_agent_memory_tree_summaries,
    )

    return prepare_record_agent_memory_tree_summaries(
        context.db,
        context.project_id,
        action_params=tool.params,
    )


def _execute_record_agent_memory_tree_summaries_with_approval(
    approval_tool_metadata_provider: ApprovalToolMetadataProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], dict[str, Any]]:
    def execute_record_agent_memory_tree_summaries_with_approval_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.services.writing_agent.memory_tree_summary_execution import (
            execute_record_agent_memory_tree_summaries_with_approval,
        )

        approval_contract = tool.params.get("approval_contract")
        return execute_record_agent_memory_tree_summaries_with_approval(
            context.db,
            context.project_id,
            action_params=tool.params,
            confirm_execute=tool.params.get("confirm_execute") is True,
            approval_contract_hash=str(tool.params.get("approval_contract_hash") or "").strip() or None,
            approval_contract=approval_contract if isinstance(approval_contract, dict) else None,
            approval_tool_metadata_provider=approval_tool_metadata_provider,
        )

    execute_record_agent_memory_tree_summaries_with_approval_adapter.__name__ = (
        "_execute_record_agent_memory_tree_summaries_with_approval"
    )
    return execute_record_agent_memory_tree_summaries_with_approval_adapter


MEMORY_TREE_TOOL_ADAPTERS: dict[str, WritingAgentToolAdapter] = {
    "inspect_agent_memory_tree": WritingAgentToolAdapter(
        "inspect_agent_memory_tree",
        _inspect_agent_memory_tree,
        category="longform_memory",
        mutability="read",
    ),
    "inspect_agent_memory_tree_quality": WritingAgentToolAdapter(
        "inspect_agent_memory_tree_quality",
        _inspect_agent_memory_tree_quality,
        category="longform_memory",
        mutability="read",
    ),
    "build_agent_memory_tree_llm_summary_plan": WritingAgentToolAdapter(
        "build_agent_memory_tree_llm_summary_plan",
        _build_agent_memory_tree_llm_summary_plan,
        category="longform_memory",
        mutability="read",
    ),
    "record_agent_memory_tree_summaries": WritingAgentToolAdapter(
        "record_agent_memory_tree_summaries",
        _record_agent_memory_tree_summaries,
        category="longform_memory",
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


def _optional_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)

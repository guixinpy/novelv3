from __future__ import annotations

from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_adapter_types import WritingAgentToolAdapter, WritingAgentToolContext


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


def _record_agent_memory_tree_summaries(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.memory_tree import materialize_agent_memory_tree_summaries

    return materialize_agent_memory_tree_summaries(
        context.db,
        context.project_id,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
    )


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
    "record_agent_memory_tree_summaries": WritingAgentToolAdapter(
        "record_agent_memory_tree_summaries",
        _record_agent_memory_tree_summaries,
        category="longform_memory",
        mutability="write",
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

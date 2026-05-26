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
        chapter_index=_optional_int(tool.params.get("chapter_index")),
        query=str(tool.params.get("query") or tool.command_args or "").strip() or None,
    )


MEMORY_TREE_TOOL_ADAPTERS: dict[str, WritingAgentToolAdapter] = {
    "inspect_agent_memory_tree": WritingAgentToolAdapter(
        "inspect_agent_memory_tree",
        _inspect_agent_memory_tree,
        category="longform_memory",
        mutability="read",
    ),
}


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

from __future__ import annotations

from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_adapter_types import WritingAgentToolAdapter, WritingAgentToolContext


def _inspect_agent_knowledge_base_route(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.agent_knowledge_base_route import inspect_agent_knowledge_base_route

    return inspect_agent_knowledge_base_route(
        context.db,
        context.project_id,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
        query=str(tool.params.get("query") or "").strip() or None,
        limit=_optional_int(tool.params.get("limit")),
    )


def _record_agent_knowledge_base_candidate(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.agent_knowledge_base_candidates import record_agent_knowledge_base_candidate

    source_refs = tool.params.get("source_refs")
    tags = tool.params.get("tags")
    return record_agent_knowledge_base_candidate(
        context.db,
        context.project_id,
        memory_type=str(tool.params.get("memory_type") or "").strip(),
        title=str(tool.params.get("title") or "").strip(),
        summary=str(tool.params.get("summary") or "").strip(),
        source_refs=_string_list(source_refs),
        confidence=_optional_float(tool.params.get("confidence")),
        status=str(tool.params.get("status") or "").strip() or None,
        tags=_string_list(tags),
    )


KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS: dict[str, WritingAgentToolAdapter] = {
    "inspect_agent_knowledge_base_route": WritingAgentToolAdapter(
        "inspect_agent_knowledge_base_route",
        _inspect_agent_knowledge_base_route,
        category="knowledge_base",
        mutability="read",
    ),
    "record_agent_knowledge_base_candidate": WritingAgentToolAdapter(
        "record_agent_knowledge_base_candidate",
        _record_agent_knowledge_base_candidate,
        category="knowledge_base",
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


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    cleaned = str(value).strip()
    return [cleaned] if cleaned else []

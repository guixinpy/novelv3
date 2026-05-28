from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_adapter_types import WritingAgentToolAdapter, WritingAgentToolContext

ApprovalToolMetadataProvider = Callable[[dict[str, Any] | None], dict[str, dict[str, Any]]]


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


def build_knowledge_base_agent_tool_adapters(
    *,
    approval_tool_metadata_provider: ApprovalToolMetadataProvider,
) -> dict[str, WritingAgentToolAdapter]:
    return {
        **KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS,
        "prepare_record_agent_knowledge_base_candidate": WritingAgentToolAdapter(
            "prepare_record_agent_knowledge_base_candidate",
            _prepare_record_agent_knowledge_base_candidate,
            category="knowledge_base",
            mutability="read",
        ),
        "execute_record_agent_knowledge_base_candidate_with_approval": WritingAgentToolAdapter(
            "execute_record_agent_knowledge_base_candidate_with_approval",
            _execute_record_agent_knowledge_base_candidate_with_approval(approval_tool_metadata_provider),
            category="knowledge_base",
            mutability="write",
        ),
    }


def _prepare_record_agent_knowledge_base_candidate(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.knowledge_base_candidate_execution import (
        prepare_record_agent_knowledge_base_candidate,
    )

    return prepare_record_agent_knowledge_base_candidate(
        context.db,
        context.project_id,
        action_params=tool.params,
    )


def _execute_record_agent_knowledge_base_candidate_with_approval(
    approval_tool_metadata_provider: ApprovalToolMetadataProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], dict[str, Any]]:
    def execute_record_agent_knowledge_base_candidate_with_approval_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.services.writing_agent.knowledge_base_candidate_execution import (
            execute_record_agent_knowledge_base_candidate_with_approval,
        )

        approval_contract = tool.params.get("approval_contract")
        return execute_record_agent_knowledge_base_candidate_with_approval(
            context.db,
            context.project_id,
            action_params=tool.params,
            confirm_execute=tool.params.get("confirm_execute") is True,
            approval_contract_hash=str(tool.params.get("approval_contract_hash") or "").strip() or None,
            approval_contract=approval_contract if isinstance(approval_contract, dict) else None,
            approval_tool_metadata_provider=approval_tool_metadata_provider,
        )

    execute_record_agent_knowledge_base_candidate_with_approval_adapter.__name__ = (
        "_execute_record_agent_knowledge_base_candidate_with_approval"
    )
    return execute_record_agent_knowledge_base_candidate_with_approval_adapter


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

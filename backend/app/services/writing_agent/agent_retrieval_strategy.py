from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.athena_retrieval import get_retrieval_diagnostics
from app.core.longform_memory import get_longform_maintenance_diagnostics

AGENT_RETRIEVAL_STRATEGY_VERSION = "phase253.agent_retrieval_strategy.v1"
DEFAULT_RETRIEVAL_STRATEGY_LIMIT = 8
MAX_RETRIEVAL_STRATEGY_LIMIT = 20
MAX_RETRIEVAL_STRATEGY_CANDIDATE_LIMIT = 1000
MAINTENANCE_REPAIR_PREPARE_TOOL = "prepare_repair_longform_maintenance"


def inspect_agent_retrieval_strategy(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
    query: str | None = None,
    purpose: str | None = None,
    limit: int | None = None,
    candidate_limit: int | None = None,
) -> dict[str, Any]:
    cleaned_query = _clean_text(query)
    cleaned_purpose = _clean_text(purpose)
    effective_limit = _clamp(limit, default=DEFAULT_RETRIEVAL_STRATEGY_LIMIT, maximum=MAX_RETRIEVAL_STRATEGY_LIMIT)
    effective_candidate_limit = _optional_clamp(candidate_limit, maximum=MAX_RETRIEVAL_STRATEGY_CANDIDATE_LIMIT)
    retrieval = get_retrieval_diagnostics(db, project_id)
    maintenance = get_longform_maintenance_diagnostics(db, project_id, limit=20)
    diagnostics = _diagnostics(retrieval=retrieval, maintenance=maintenance)

    strategy, recommended_calls = _strategy_and_calls(
        chapter_index=chapter_index,
        query=cleaned_query,
        purpose=cleaned_purpose,
        limit=effective_limit,
        candidate_limit=effective_candidate_limit,
        retrieval=retrieval,
        maintenance=maintenance,
    )
    status = "blocked" if strategy["name"] == "repair_retrieval_maintenance" else "completed"
    return _json_safe(
        {
            "status": status,
            "version": AGENT_RETRIEVAL_STRATEGY_VERSION,
            "project_id": project_id,
            "inputs": {
                "chapter_index": chapter_index,
                "query": cleaned_query,
                "purpose": cleaned_purpose,
                "limit": effective_limit,
                "candidate_limit": effective_candidate_limit,
            },
            "strategy": strategy,
            "retrieval": retrieval,
            "longform_maintenance": maintenance,
            "diagnostics": diagnostics,
            "recommended_next_tools": [str(call["tool_name"]) for call in recommended_calls],
            "recommended_next_tool_calls": recommended_calls,
            "side_effects": {"writes": 0, "mutability": "read"},
            "trace": {
                "source": "inspect_agent_retrieval_strategy",
                "version": AGENT_RETRIEVAL_STRATEGY_VERSION,
                "mutability": "read",
                "write_performed": False,
            },
        }
    )


def _strategy_and_calls(
    *,
    chapter_index: int | None,
    query: str | None,
    purpose: str | None,
    limit: int,
    candidate_limit: int | None,
    retrieval: dict[str, Any],
    maintenance: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    max_chapter_index = _safe_max_chapter_index(chapter_index)
    if maintenance.get("ready_for_writing") is False:
        calls = [
            {
                "tool_name": "inspect_agent_memory_route",
                "params": {
                    "chapter_index": chapter_index,
                    "query": query or purpose,
                    "include_context_summary": False,
                },
            },
            {"tool_name": MAINTENANCE_REPAIR_PREPARE_TOOL, "params": {}},
        ]
        return (
            {
                "name": "repair_retrieval_maintenance",
                "reason": "longform_memory_needs_maintenance",
                "read_mode": "diagnose_then_prepare_repair",
                "filters": {"query": query, "limit": limit, "candidate_limit": candidate_limit},
            },
            calls,
        )

    if query:
        filters = {
            "query": query,
            "limit": limit,
            "candidate_limit": candidate_limit,
            "max_chapter_index": max_chapter_index,
        }
        search_params = {key: value for key, value in filters.items() if value is not None}
        calls = [{"tool_name": "search_agent_retrieval_context", "params": search_params}]
        if chapter_index:
            calls.append(
                {
                    "tool_name": "summarize_longform_context",
                    "params": {"chapter_index": chapter_index, "query": query},
                }
            )
        return (
            {
                "name": "query_aware_retrieval",
                "reason": "query_available",
                "read_mode": "search_then_summarize" if chapter_index else "search_only",
                "filters": filters,
                "retrieval_document_count": _non_negative_int(retrieval.get("total_documents")),
            },
            calls,
        )

    if chapter_index:
        return (
            {
                "name": "chapter_context_summary",
                "reason": "chapter_available_without_query",
                "read_mode": "chapter_window_summary",
                "filters": {"chapter_index": chapter_index, "max_chapter_index": max_chapter_index},
                "retrieval_document_count": _non_negative_int(retrieval.get("total_documents")),
            },
            [{"tool_name": "summarize_longform_context", "params": {"chapter_index": chapter_index}}],
        )

    return (
        {
            "name": "memory_route_diagnostics",
            "reason": "missing_query_and_chapter",
            "read_mode": "diagnose_memory_route",
            "filters": {},
            "retrieval_document_count": _non_negative_int(retrieval.get("total_documents")),
        },
        [{"tool_name": "inspect_agent_memory_route", "params": {"include_context_summary": False}}],
    )


def _diagnostics(*, retrieval: dict[str, Any], maintenance: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    if maintenance.get("ready_for_writing") is False:
        diagnostics.append(
            {
                "code": "longform_memory_needs_maintenance",
                "severity": "warning",
                "message": "长篇记忆或检索索引存在维护缺口，应先诊断并准备修复。",
                "issue_count": _non_negative_int(maintenance.get("issue_count")),
            }
        )
    if _non_negative_int(retrieval.get("total_documents")) == 0:
        diagnostics.append(
            {
                "code": "retrieval_index_empty",
                "severity": "warning",
                "message": "检索索引为空，query-aware 检索可能无法提供证据。",
            }
        )
    return diagnostics


def _safe_max_chapter_index(chapter_index: int | None) -> int | None:
    if chapter_index is None:
        return None
    if chapter_index <= 1:
        return 1
    return chapter_index - 1


def _clean_text(value: str | None) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _clamp(value: int | None, *, default: int, maximum: int) -> int:
    if value is None:
        return default
    return min(max(int(value), 1), maximum)


def _optional_clamp(value: int | None, *, maximum: int) -> int | None:
    if value is None:
        return None
    return min(max(int(value), 1), maximum)


def _non_negative_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)


def _json_safe(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

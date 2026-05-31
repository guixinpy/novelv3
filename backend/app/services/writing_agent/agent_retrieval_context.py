from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.services.writing_agent.memory_provenance_contract import build_memory_provenance, count_window

AGENT_RETRIEVAL_CONTEXT_VERSION = "phase243.agent_retrieval_context.v1"
AGENT_RETRIEVAL_CONTEXT_PROVENANCE_VERSION = "phase243.agent_retrieval_context_provenance.v1"
DEFAULT_RETRIEVAL_LIMIT = 8
MAX_RETRIEVAL_LIMIT = 20
MAX_CANDIDATE_LIMIT = 1000


def search_agent_retrieval_context(
    db: Session,
    project_id: str,
    *,
    query: str,
    limit: int | None = None,
    source_type: str | None = None,
    max_chapter_index: int | None = None,
    candidate_limit: int | None = None,
) -> dict[str, Any]:
    cleaned_query = str(query or "").strip()
    effective_limit = _clamp(limit, default=DEFAULT_RETRIEVAL_LIMIT, maximum=MAX_RETRIEVAL_LIMIT)
    effective_candidate_limit = _optional_clamp(candidate_limit, maximum=MAX_CANDIDATE_LIMIT)
    cleaned_source_type = str(source_type or "").strip() or None
    from app.core.athena_retrieval import search_retrieval

    result = search_retrieval(
        db,
        project_id,
        cleaned_query,
        limit=effective_limit,
        source_type=cleaned_source_type,
        max_chapter_index=max_chapter_index,
        candidate_limit=effective_candidate_limit,
    )
    items = result.get("items") if isinstance(result.get("items"), list) else []
    total = _non_negative_int(result.get("total"))
    return _json_safe(
        {
            "status": "completed",
            "version": AGENT_RETRIEVAL_CONTEXT_VERSION,
            "project_id": project_id,
            "query": result.get("query") or cleaned_query,
            "filters": {
                "source_type": cleaned_source_type,
                "max_chapter_index": max_chapter_index,
                "limit": effective_limit,
                "candidate_limit": effective_candidate_limit,
            },
            "summary": {"total": total, "returned": len(items)},
            "items": items,
            "retrieval": result,
            "recommended_next_tools": _recommended_next_tools(items),
            "memory_provenance": _memory_provenance(items=items, total=total, limit=effective_limit),
            "trace": {
                "source": "search_agent_retrieval_context",
                "version": AGENT_RETRIEVAL_CONTEXT_VERSION,
                "mutability": "read",
                "write_performed": False,
            },
        }
    )


def _memory_provenance(*, items: list[Any], total: int, limit: int) -> dict[str, Any]:
    sources = []
    for item in items:
        if not isinstance(item, dict):
            continue
        source_ref = str(item.get("source_ref") or "").strip()
        source_type = str(item.get("source_type") or "").strip()
        if not source_ref or not source_type:
            continue
        sources.append(
            {
                "source_type": source_type,
                "source_ref": source_ref,
                "title": item.get("title"),
                "chapter_index": item.get("chapter_index"),
                "score": item.get("score"),
            }
        )
    return build_memory_provenance(
        version=AGENT_RETRIEVAL_CONTEXT_PROVENANCE_VERSION,
        status="available" if sources else "empty",
        sources=sources,
        windows={"retrieval_items": count_window(total, returned=len(sources), limit=limit, has_more=total > len(sources))},
        recovery={
            "status": "none" if sources else "recommended",
            "reason": "retrieval_context_available" if sources else "retrieval_context_empty",
            "next_tools": [] if sources else ["inspect_agent_memory_route", "prepare_repair_longform_maintenance"],
            "tools": []
            if sources
            else [
                {"tool_name": "inspect_agent_memory_route"},
                {"tool_name": "prepare_repair_longform_maintenance"},
            ],
        },
        trace={
            "source": "search_agent_retrieval_context",
            "version": AGENT_RETRIEVAL_CONTEXT_PROVENANCE_VERSION,
            "mutability": "read",
        },
    )


def _recommended_next_tools(items: list[Any]) -> list[str]:
    if items:
        return ["summarize_longform_context"]
    return ["inspect_agent_memory_route", "prepare_repair_longform_maintenance"]


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

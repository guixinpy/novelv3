from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.athena_retrieval import get_retrieval_diagnostics
from app.core.longform_memory import get_longform_maintenance_diagnostics, get_longform_memory_diagnostics
from app.services.writing_agent.longform_context_summary import summarize_longform_context
from app.services.writing_agent.memory_provenance_contract import count_window, ensure_memory_provenance_contract

AGENT_MEMORY_ROUTE_VERSION = "phase72.agent_memory_route.v1"
AGENT_MEMORY_ROUTE_PROVENANCE_VERSION = "phase224.agent_memory_route_provenance.v1"


def inspect_agent_memory_route(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
    query: str | None = None,
    include_context_summary: bool = False,
) -> dict[str, Any]:
    longform_memory = get_longform_memory_diagnostics(db, project_id)
    maintenance = get_longform_maintenance_diagnostics(db, project_id, limit=20)
    retrieval = get_retrieval_diagnostics(db, project_id)
    diagnostics = _route_diagnostics(
        longform_memory=longform_memory,
        maintenance=maintenance,
        retrieval=retrieval,
        chapter_index=chapter_index,
        include_context_summary=include_context_summary,
    )
    route = _route_decision(
        maintenance=maintenance,
        retrieval=retrieval,
        chapter_index=chapter_index,
        include_context_summary=include_context_summary,
    )
    memory_provenance = _memory_provenance(
        longform_memory=longform_memory,
        maintenance=maintenance,
        retrieval=retrieval,
        route=route,
        chapter_index=chapter_index,
    )
    output: dict[str, Any] = {
        "status": "completed",
        "project_id": project_id,
        "chapter_index": chapter_index,
        "query": _clean_query(query),
        "route": route,
        "longform_memory": longform_memory,
        "longform_maintenance": maintenance,
        "retrieval": retrieval,
        "memory_provenance": memory_provenance,
        "diagnostics": diagnostics,
        "trace": {
            "source": "inspect_agent_memory_route",
            "version": AGENT_MEMORY_ROUTE_VERSION,
            "mutability": "read",
        },
    }
    if chapter_index and include_context_summary:
        output["context_summary"] = summarize_longform_context(
            db,
            project_id,
            chapter_index=chapter_index,
            query=_clean_query(query),
            include_prompt_context=False,
        )
    return _json_safe_output(output)


def _route_decision(
    *,
    maintenance: dict[str, Any],
    retrieval: dict[str, Any],
    chapter_index: int | None,
    include_context_summary: bool,
) -> dict[str, Any]:
    ready_for_writing = maintenance.get("ready_for_writing") is not False
    retrieval_document_count = int(retrieval.get("total_documents") or 0)
    if not ready_for_writing:
        return {
            "status": "blocked",
            "reason": "longform_memory_needs_maintenance",
            "can_use_longform_context": False,
            "recommended_tools": ["repair_longform_maintenance"],
        }

    recommended_tools: list[str] = []
    if chapter_index and not include_context_summary:
        recommended_tools.append("summarize_longform_context")
    if chapter_index:
        recommended_tools.append("preflight_writing")
    return {
        "status": "ready",
        "reason": "longform_memory_ready",
        "can_use_longform_context": True,
        "retrieval_document_count": retrieval_document_count,
        "recommended_tools": recommended_tools,
    }


def _route_diagnostics(
    *,
    longform_memory: dict[str, Any],
    maintenance: dict[str, Any],
    retrieval: dict[str, Any],
    chapter_index: int | None,
    include_context_summary: bool,
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    if maintenance.get("ready_for_writing") is False:
        diagnostics.append(
            {
                "code": "longform_memory_needs_maintenance",
                "severity": "warning",
                "message": "长篇记忆或检索索引存在缺口，Agent 应先调用维护工具再继续生成。",
                "issue_count": int(maintenance.get("issue_count") or 0),
            }
        )
    if int(longform_memory.get("chapter_count") or 0) > 0 and int(retrieval.get("total_documents") or 0) == 0:
        diagnostics.append(
            {
                "code": "retrieval_index_empty",
                "severity": "warning",
                "message": "项目已有正文，但检索索引为空，跨章节召回质量会下降。",
            }
        )
    if include_context_summary and not chapter_index:
        diagnostics.append(
            {
                "code": "context_summary_skipped",
                "severity": "info",
                "message": "未提供目标章节，已跳过章节上下文摘要。",
            }
        )
    return diagnostics


def _memory_provenance(
    *,
    longform_memory: dict[str, Any],
    maintenance: dict[str, Any],
    retrieval: dict[str, Any],
    route: dict[str, Any],
    chapter_index: int | None,
) -> dict[str, Any]:
    chapter_count = int(longform_memory.get("chapter_count") or 0)
    memory_count = int(longform_memory.get("total_memories") or 0)
    retrieval_document_count = int(retrieval.get("total_documents") or 0)
    ready_for_writing = maintenance.get("ready_for_writing") is not False
    provenance_status = _provenance_status(
        route=route,
        chapter_count=chapter_count,
        memory_count=memory_count,
        retrieval_document_count=retrieval_document_count,
    )
    return ensure_memory_provenance_contract(
        {
            "version": AGENT_MEMORY_ROUTE_PROVENANCE_VERSION,
            "status": provenance_status,
            "source_count": 3,
            "sources": [
                {
                    "source_ref": "LongformMemory",
                    "source_type": "longform_memory",
                    "item_count": memory_count,
                    "chapter_count": chapter_count,
                    "mutability": "read",
                },
                {
                    "source_ref": "LongformMaintenance",
                    "source_type": "maintenance_diagnostics",
                    "item_count": int(maintenance.get("issue_count") or 0),
                    "ready_for_writing": ready_for_writing,
                    "mutability": "read",
                },
                {
                    "source_ref": "RetrievalDocument",
                    "source_type": "retrieval_index",
                    "item_count": retrieval_document_count,
                    "mutability": "read",
                },
            ],
            "coverage": {
                "chapter_count": chapter_count,
                "longform_memory_count": memory_count,
                "retrieval_document_count": retrieval_document_count,
                "ready_for_writing": ready_for_writing,
            },
            "boundaries": {
                "world_truth": {
                    "status": "separated",
                    "canonical_source": "Athena/world_model",
                    "memory_route_role": "longform_memory_retrieval_and_maintenance_diagnostics",
                }
            },
            "recovery": _provenance_recovery(
                route,
                provenance_status=provenance_status,
                chapter_index=chapter_index,
            ),
            "trace": {
                "source": "inspect_agent_memory_route",
                "version": AGENT_MEMORY_ROUTE_PROVENANCE_VERSION,
                "mutability": "read",
            },
        },
        windows={
            "longform_memory": count_window(memory_count),
            "chapters": count_window(chapter_count),
            "retrieval": count_window(retrieval_document_count),
            "maintenance": count_window(int(maintenance.get("issue_count") or 0), limit=20),
        },
    )


def _provenance_status(
    *,
    route: dict[str, Any],
    chapter_count: int,
    memory_count: int,
    retrieval_document_count: int,
) -> str:
    if route.get("status") == "blocked":
        return "blocked"
    if chapter_count == 0 or memory_count == 0:
        return "sparse"
    if retrieval_document_count == 0:
        return "degraded"
    return "available"


def _provenance_recovery(
    route: dict[str, Any],
    *,
    provenance_status: str,
    chapter_index: int | None,
) -> dict[str, Any]:
    recommended_tools = route.get("recommended_tools") if isinstance(route.get("recommended_tools"), list) else []
    if "repair_longform_maintenance" in recommended_tools:
        return {
            "status": "recommended",
            "reason": route.get("reason"),
            "next_tools": ["repair_longform_maintenance"],
            "tools": [{"tool_name": "repair_longform_maintenance", "params": {}}],
        }
    if provenance_status == "degraded":
        query = (
            f"检索索引为空，诊断第{chapter_index}章长篇记忆与检索覆盖。"
            if chapter_index
            else "检索索引为空，诊断长篇记忆与检索覆盖。"
        )
        return {
            "status": "optional",
            "reason": "retrieval_index_empty",
            "next_tools": ["inspect_agent_memory_route", "repair_longform_maintenance"],
            "tools": [
                {
                    "tool_name": "inspect_agent_memory_route",
                    "params": {
                        "chapter_index": chapter_index,
                        "query": query,
                        "include_context_summary": False,
                    },
                }
            ],
            "write_tools": [{"tool_name": "repair_longform_maintenance", "params": {}}],
            "write_policy": "requires_confirmation",
        }
    return {
        "status": "none",
        "reason": route.get("reason"),
        "next_tools": [],
        "tools": [],
    }


def _clean_query(query: str | None) -> str | None:
    cleaned = str(query or "").strip()
    return cleaned or None


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

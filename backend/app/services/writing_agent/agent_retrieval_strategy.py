from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.athena_retrieval import get_retrieval_diagnostics
from app.core.longform_memory import get_longform_maintenance_diagnostics
from app.services.writing_agent.dogfood_evidence_projection import inspect_agent_dogfood_evidence

AGENT_RETRIEVAL_STRATEGY_VERSION = "phase253.agent_retrieval_strategy.v1"
AGENT_RETRIEVAL_STRATEGY_QUALITY_VERSION = "phase255.agent_retrieval_strategy_quality.v1"
AGENT_RETRIEVAL_PREFETCH_PLAN_VERSION = "phase256.agent_retrieval_prefetch_plan.v1"
DEFAULT_RETRIEVAL_STRATEGY_LIMIT = 8
MAX_RETRIEVAL_STRATEGY_LIMIT = 20
MAX_RETRIEVAL_STRATEGY_CANDIDATE_LIMIT = 1000
MAINTENANCE_REPAIR_PREPARE_TOOL = "prepare_repair_longform_maintenance"
PREFETCH_READ_TOOLS = frozenset(
    {
        "inspect_agent_memory_route",
        "search_agent_retrieval_context",
        "summarize_longform_context",
    }
)


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


def inspect_agent_retrieval_strategy_quality(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
    query: str | None = None,
    purpose: str | None = None,
    limit: int | None = None,
    candidate_limit: int | None = None,
) -> dict[str, Any]:
    strategy_output = inspect_agent_retrieval_strategy(
        db,
        project_id,
        chapter_index=chapter_index,
        query=query,
        purpose=purpose,
        limit=limit,
        candidate_limit=candidate_limit,
    )
    dogfood_output = inspect_agent_dogfood_evidence()
    dogfood_evidence = _compact_dogfood_evidence(dogfood_output)
    quality = _quality_projection(strategy_output=strategy_output, dogfood_evidence=dogfood_evidence)
    diagnostics = _quality_diagnostics(
        strategy_output=strategy_output,
        dogfood_evidence=dogfood_evidence,
        quality=quality,
    )
    recommended_next_tools = _dedupe(
        [
            *[str(tool) for tool in strategy_output.get("recommended_next_tools") or []],
            *[str(tool) for tool in dogfood_evidence.get("recommended_next_tools") or []],
        ]
    )
    return _json_safe(
        {
            "status": quality["status"],
            "version": AGENT_RETRIEVAL_STRATEGY_QUALITY_VERSION,
            "project_id": project_id,
            "inputs": dict(strategy_output.get("inputs") or {}),
            "quality": quality,
            "strategy": _compact_strategy_output(strategy_output),
            "dogfood_evidence": dogfood_evidence,
            "diagnostics": diagnostics,
            "recommended_next_tools": recommended_next_tools,
            "side_effects": {"writes": 0, "mutability": "read"},
            "trace": {
                "source": "inspect_agent_retrieval_strategy_quality",
                "version": AGENT_RETRIEVAL_STRATEGY_QUALITY_VERSION,
                "mutability": "read",
                "write_performed": False,
                "strategy_version": strategy_output.get("version"),
                "dogfood_evidence_version": dogfood_output.get("version"),
            },
        }
    )


def inspect_agent_retrieval_prefetch_plan(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
    query: str | None = None,
    purpose: str | None = None,
    limit: int | None = None,
    candidate_limit: int | None = None,
) -> dict[str, Any]:
    strategy_output = inspect_agent_retrieval_strategy(
        db,
        project_id,
        chapter_index=chapter_index,
        query=query,
        purpose=purpose,
        limit=limit,
        candidate_limit=candidate_limit,
    )
    strategy = _compact_strategy_output(strategy_output)
    strategy["version"] = str(strategy_output.get("version") or "")
    prefetch_plan = _prefetch_plan(strategy_output=strategy_output)
    recommended_calls = list(prefetch_plan.get("tool_calls") or [])
    recommended_next_tools = _dedupe([str(call.get("tool_name") or "") for call in recommended_calls])
    return _json_safe(
        {
            "status": prefetch_plan["status"],
            "version": AGENT_RETRIEVAL_PREFETCH_PLAN_VERSION,
            "project_id": project_id,
            "inputs": dict(strategy_output.get("inputs") or {}),
            "strategy": strategy,
            "prefetch_plan": prefetch_plan,
            "diagnostics": list(strategy_output.get("diagnostics") or []),
            "recommended_next_tools": recommended_next_tools,
            "recommended_next_tool_calls": recommended_calls,
            "side_effects": {"writes": 0, "mutability": "read"},
            "trace": {
                "source": "inspect_agent_retrieval_prefetch_plan",
                "version": AGENT_RETRIEVAL_PREFETCH_PLAN_VERSION,
                "mutability": "read",
                "write_performed": False,
                "strategy_version": strategy_output.get("version"),
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


def _prefetch_plan(*, strategy_output: dict[str, Any]) -> dict[str, Any]:
    strategy = strategy_output.get("strategy") if isinstance(strategy_output.get("strategy"), dict) else {}
    inputs = strategy_output.get("inputs") if isinstance(strategy_output.get("inputs"), dict) else {}
    filters = strategy.get("filters") if isinstance(strategy.get("filters"), dict) else {}
    retrieval = strategy_output.get("retrieval") if isinstance(strategy_output.get("retrieval"), dict) else {}
    maintenance = (
        strategy_output.get("longform_maintenance")
        if isinstance(strategy_output.get("longform_maintenance"), dict)
        else {}
    )
    tool_calls = _read_only_prefetch_calls(strategy_output.get("recommended_next_tool_calls"))
    strategy_name = str(strategy.get("name") or "")
    status = "blocked" if strategy_output.get("status") == "blocked" else "ready"
    return {
        "status": status,
        "mode": _prefetch_mode(strategy_name=strategy_name, status=status),
        "target_chapter_index": inputs.get("chapter_index"),
        "query": inputs.get("query") or inputs.get("purpose"),
        "max_chapter_index": filters.get("max_chapter_index"),
        "read_tools": _dedupe([str(call.get("tool_name") or "") for call in tool_calls]),
        "tool_calls": tool_calls,
        "coverage": {
            "strategy_name": strategy_name,
            "retrieval_documents": _non_negative_int(retrieval.get("total_documents")),
            "retrieval_chunks": _non_negative_int(retrieval.get("total_chunks")),
            "maintenance_ready": maintenance.get("ready_for_writing") is not False,
        },
        "side_effects": {"writes": 0, "mutability": "read"},
    }


def _prefetch_mode(*, strategy_name: str, status: str) -> str:
    if status == "blocked":
        return "maintenance_blocked"
    if strategy_name == "query_aware_retrieval":
        return "query_aware_prefetch"
    if strategy_name == "chapter_context_summary":
        return "chapter_window_prefetch"
    return "diagnostic_prefetch"


def _read_only_prefetch_calls(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    calls: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        tool_name = str(item.get("tool_name") or "").strip()
        params = item.get("params") if isinstance(item.get("params"), dict) else {}
        if tool_name not in PREFETCH_READ_TOOLS:
            continue
        calls.append({"tool_name": tool_name, "params": dict(params)})
    return calls


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


def _quality_projection(
    *,
    strategy_output: dict[str, Any],
    dogfood_evidence: dict[str, Any],
) -> dict[str, Any]:
    strategy = strategy_output.get("strategy") if isinstance(strategy_output.get("strategy"), dict) else {}
    inputs = strategy_output.get("inputs") if isinstance(strategy_output.get("inputs"), dict) else {}
    retrieval = strategy_output.get("retrieval") if isinstance(strategy_output.get("retrieval"), dict) else {}
    maintenance = (
        strategy_output.get("longform_maintenance")
        if isinstance(strategy_output.get("longform_maintenance"), dict)
        else {}
    )
    summary = dogfood_evidence.get("summary") if isinstance(dogfood_evidence.get("summary"), dict) else {}
    strategy_diagnostics = strategy_output.get("diagnostics") if isinstance(strategy_output.get("diagnostics"), list) else []
    dogfood_open_findings = _non_negative_int(summary.get("open_finding_count"))
    dogfood_status = str(dogfood_evidence.get("status") or "unknown")
    if strategy_output.get("status") == "blocked":
        status = "blocked"
    elif dogfood_open_findings > 0 or dogfood_status != "ready":
        status = "needs_dogfood_review"
    elif strategy_diagnostics:
        status = "needs_retrieval_review"
    else:
        status = "ready"
    return {
        "status": status,
        "strategy_name": str(strategy.get("name") or ""),
        "query_available": bool(inputs.get("query")),
        "chapter_index": inputs.get("chapter_index"),
        "retrieval_documents": _non_negative_int(retrieval.get("total_documents")),
        "retrieval_chunks": _non_negative_int(retrieval.get("total_chunks")),
        "maintenance_ready": maintenance.get("ready_for_writing") is not False,
        "dogfood_status": dogfood_status,
        "dogfood_evidence_count": _non_negative_int(summary.get("evidence_count")),
        "dogfood_ready_evidence_count": _non_negative_int(summary.get("ready_evidence_count")),
        "dogfood_generated_chapter_count": _non_negative_int(summary.get("generated_chapter_count")),
        "dogfood_open_findings": dogfood_open_findings,
    }


def _quality_diagnostics(
    *,
    strategy_output: dict[str, Any],
    dogfood_evidence: dict[str, Any],
    quality: dict[str, Any],
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    strategy_diagnostics = strategy_output.get("diagnostics") if isinstance(strategy_output.get("diagnostics"), list) else []
    diagnostics.extend(diagnostic for diagnostic in strategy_diagnostics if isinstance(diagnostic, dict))
    dogfood_status = str(dogfood_evidence.get("status") or "unknown")
    if dogfood_status != "ready":
        diagnostics.append(
            {
                "code": "retrieval_strategy_dogfood_evidence_degraded",
                "severity": "warning",
                "message": "Dogfood evidence is not fully ready, so retrieval strategy quality needs review.",
                "dogfood_status": dogfood_status,
            }
        )
    dogfood_open_findings = _non_negative_int(quality.get("dogfood_open_findings"))
    if dogfood_open_findings > 0:
        diagnostics.append(
            {
                "code": "retrieval_strategy_dogfood_open_findings",
                "severity": "warning",
                "message": "Retrieval strategy still has open dogfood findings before it can be treated as quality-reviewed.",
                "open_finding_count": dogfood_open_findings,
            }
        )
    return diagnostics


def _compact_strategy_output(output: dict[str, Any]) -> dict[str, Any]:
    strategy = output.get("strategy") if isinstance(output.get("strategy"), dict) else {}
    return {
        "status": str(output.get("status") or ""),
        "name": str(strategy.get("name") or ""),
        "reason": str(strategy.get("reason") or ""),
        "read_mode": str(strategy.get("read_mode") or ""),
        "filters": strategy.get("filters") if isinstance(strategy.get("filters"), dict) else {},
        "recommended_next_tools": [str(tool) for tool in output.get("recommended_next_tools") or []],
        "recommended_next_tool_calls": list(output.get("recommended_next_tool_calls") or []),
    }


def _compact_dogfood_evidence(output: dict[str, Any]) -> dict[str, Any]:
    summary = output.get("summary") if isinstance(output.get("summary"), dict) else {}
    return {
        "status": str(output.get("status") or "unknown"),
        "summary": {
            "evidence_count": _non_negative_int(summary.get("evidence_count")),
            "ready_evidence_count": _non_negative_int(summary.get("ready_evidence_count")),
            "open_finding_count": _non_negative_int(summary.get("open_finding_count")),
            "generated_chapter_count": _non_negative_int(summary.get("generated_chapter_count")),
        },
        "recommended_next_tools": [str(tool) for tool in output.get("recommended_next_tools") or []],
    }


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


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _json_safe(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

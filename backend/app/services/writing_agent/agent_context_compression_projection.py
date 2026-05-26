from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Project
from app.services.writing_agent.longform_context_summary import summarize_longform_context

AGENT_CONTEXT_COMPRESSION_PROJECTION_VERSION = "phase225.agent_context_compression_projection.v1"
CONTEXT_WINDOW_PRESSURE_RATIO = 0.85
CONTEXT_GUARD_FAILURE_THRESHOLD = 3


def inspect_agent_context_compression_projection(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
    max_chars: int | None = None,
    context_guard_failure_count: int = 0,
) -> dict[str, Any]:
    _require_project(db, project_id)
    context_summary = summarize_longform_context(
        db,
        project_id,
        chapter_index=chapter_index,
        max_chars=max_chars,
        include_prompt_context=False,
    )
    prompt_context_chars = _non_negative_int(context_summary.get("prompt_context_chars"))
    limits = context_summary.get("limits") if isinstance(context_summary.get("limits"), dict) else {}
    resolved_max_chars = _non_negative_int(limits.get("max_chars") or max_chars)
    usage_ratio = round(prompt_context_chars / resolved_max_chars, 4) if resolved_max_chars else 0
    diagnostics = context_summary.get("diagnostics") if isinstance(context_summary.get("diagnostics"), list) else []
    memory_provenance = (
        context_summary.get("memory_provenance") if isinstance(context_summary.get("memory_provenance"), dict) else {}
    )
    resolved_chapter_index = chapter_index or context_summary.get("chapter_index")
    risks = _context_risks(
        usage_ratio=usage_ratio,
        diagnostics=diagnostics,
        context_guard_failure_count=context_guard_failure_count,
    )
    status = _status_for_risks(risks)
    output = {
        "status": status,
        "version": AGENT_CONTEXT_COMPRESSION_PROJECTION_VERSION,
        "project_id": project_id,
        "chapter_index": resolved_chapter_index,
        "strategy": {
            "granularity": "chapter_window",
            "protect_current_chapter": True,
            "protect_head_sections": ["project", "active_state"],
            "protect_tail_sections": ["recent_chapters", "critical_context"],
        },
        "summary": {
            "prompt_context_chars": prompt_context_chars,
            "max_chars": resolved_max_chars,
            "usage_ratio": usage_ratio,
            "truncated_section_count": _truncated_section_count(memory_provenance),
            "context_guard_failure_count": _non_negative_int(context_guard_failure_count),
        },
        "risks": risks,
        "recommended_next_tools": _recommended_next_tools(risks),
        "recovery": _recovery(
            status=status,
            risks=risks,
            chapter_index=resolved_chapter_index,
            max_chars=resolved_max_chars,
        ),
        "memory_provenance": memory_provenance,
        "trace": {
            "source": "inspect_agent_context_compression_projection",
            "version": AGENT_CONTEXT_COMPRESSION_PROJECTION_VERSION,
            "mutability": "read",
            "runtime_behavior_changed": False,
        },
    }
    return _json_safe_output(output)


def _require_project(db: Session, project_id: str) -> None:
    if db.query(Project.id).filter(Project.id == project_id).first() is None:
        raise HTTPException(status_code=404, detail="Project not found")


def _context_risks(
    *,
    usage_ratio: float,
    diagnostics: list[Any],
    context_guard_failure_count: int,
) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    if _non_negative_int(context_guard_failure_count) >= CONTEXT_GUARD_FAILURE_THRESHOLD:
        risks.append(
            {
                "code": "context_guard_open",
                "severity": "error",
                "message": "上下文压缩连续失败，已打开上下文断路器。",
                "threshold": CONTEXT_GUARD_FAILURE_THRESHOLD,
                "observed": _non_negative_int(context_guard_failure_count),
            }
        )
        return risks
    if usage_ratio >= CONTEXT_WINDOW_PRESSURE_RATIO:
        risks.append(
            {
                "code": "context_window_pressure",
                "severity": "warning",
                "message": "章节上下文接近当前摘要窗口上限，应先压缩或扩大窗口再继续生成。",
                "threshold": CONTEXT_WINDOW_PRESSURE_RATIO,
                "observed": usage_ratio,
            }
        )
    diagnostic_codes = {str(item.get("code") or "") for item in diagnostics if isinstance(item, dict)}
    if "prompt_context_truncated" in diagnostic_codes:
        risks.append(
            {
                "code": "prompt_context_truncated",
                "severity": "warning",
                "message": "完整上下文已被截断，继续生成前应复查 longform context 来源窗口。",
            }
        )
    return risks


def _status_for_risks(risks: list[dict[str, Any]]) -> str:
    severities = {str(risk.get("severity") or "") for risk in risks}
    if "error" in severities:
        return "blocked"
    if risks:
        return "warning"
    return "ready"


def _recommended_next_tools(risks: list[dict[str, Any]]) -> list[str]:
    codes = [str(risk.get("code") or "") for risk in risks]
    if "context_guard_open" in codes:
        return ["inspect_agent_memory_route"]
    tools: list[str] = []
    if "context_window_pressure" in codes:
        tools.append("summarize_longform_context")
    if "prompt_context_truncated" in codes:
        tools.append("inspect_agent_memory_route")
    return _dedupe(tools)


def _recovery(
    *,
    status: str,
    risks: list[dict[str, Any]],
    chapter_index: int | None,
    max_chars: int,
) -> dict[str, Any]:
    codes = [str(risk.get("code") or "") for risk in risks]
    if "context_guard_open" in codes:
        return {
            "status": "recommended",
            "reason": "context_guard_open",
            "next_tools": ["inspect_agent_memory_route"],
            "tools": [
                {
                    "tool_name": "inspect_agent_memory_route",
                    "params": {
                        "chapter_index": chapter_index,
                        "query": f"上下文压缩连续失败，诊断第{chapter_index}章长篇记忆、检索覆盖和压缩窗口。",
                        "include_context_summary": False,
                    },
                }
            ],
        }
    if status == "warning":
        retry_max_chars = max(max_chars * 2, max_chars + 1) if max_chars else None
        return {
            "status": "optional",
            "reason": "context_compression_window_pressure",
            "next_tools": _recommended_next_tools(risks),
            "tools": [
                {
                    "tool_name": "summarize_longform_context",
                    "params": {
                        "chapter_index": chapter_index,
                        "max_chars": retry_max_chars,
                        "include_prompt_context": False,
                    },
                }
            ],
        }
    return {
        "status": "none",
        "reason": "context_window_ready",
        "next_tools": [],
        "tools": [],
    }


def _truncated_section_count(memory_provenance: dict[str, Any]) -> int:
    windows = memory_provenance.get("windows") if isinstance(memory_provenance.get("windows"), dict) else {}
    sections = windows.get("sections") if isinstance(windows.get("sections"), dict) else {}
    return sum(1 for window in sections.values() if isinstance(window, dict) and window.get("has_more") is True)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _non_negative_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Project
from app.services.writing_agent.longform_context_summary import summarize_longform_context

AGENT_CONTEXT_COMPRESSION_PROJECTION_VERSION = "phase225.agent_context_compression_projection.v1"
AGENT_CONTEXT_COMPRESSION_PAYLOAD_VERSION = "phase236.agent_context_compression_payload.v1"
CONTEXT_WINDOW_PRESSURE_RATIO = 0.85
CONTEXT_GUARD_FAILURE_THRESHOLD = 3
HEAD_PROTECTED_SECTIONS = ["project", "active_state"]
TAIL_PROTECTED_SECTIONS = ["recent_chapters", "critical_context"]
PRETRIM_ORDER = ["source_sections", "critical_context", "recent_chapters"]


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
    compression_plan = _compression_plan(
        status=status,
        risks=risks,
        chapter_index=resolved_chapter_index,
        max_chars=resolved_max_chars,
        context_guard_failure_count=context_guard_failure_count,
    )
    output = {
        "status": status,
        "version": AGENT_CONTEXT_COMPRESSION_PROJECTION_VERSION,
        "project_id": project_id,
        "chapter_index": resolved_chapter_index,
        "strategy": {
            "granularity": "chapter_window",
            "protect_current_chapter": True,
            "protect_head_sections": HEAD_PROTECTED_SECTIONS,
            "protect_tail_sections": TAIL_PROTECTED_SECTIONS,
        },
        "summary": {
            "prompt_context_chars": prompt_context_chars,
            "max_chars": resolved_max_chars,
            "usage_ratio": usage_ratio,
            "truncated_section_count": _truncated_section_count(memory_provenance),
            "context_guard_failure_count": _non_negative_int(context_guard_failure_count),
        },
        "risks": risks,
        "compression_plan": compression_plan,
        "recommended_next_tools": _recommended_next_tools(risks),
        "recovery": _recovery(
            status=status,
            risks=risks,
            chapter_index=resolved_chapter_index,
            max_chars=resolved_max_chars,
            compression_plan=compression_plan,
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


def build_agent_context_compression_payload(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
    max_chars: int | None = None,
    context_guard_failure_count: int = 0,
) -> dict[str, Any]:
    projection = inspect_agent_context_compression_projection(
        db,
        project_id,
        chapter_index=chapter_index,
        max_chars=max_chars,
        context_guard_failure_count=context_guard_failure_count,
    )
    compression_plan = (
        projection.get("compression_plan") if isinstance(projection.get("compression_plan"), dict) else {}
    )
    resolved_chapter_index = _optional_int(projection.get("chapter_index")) or chapter_index
    target_max_chars = _non_negative_int(compression_plan.get("target_max_chars") or max_chars)

    if projection.get("status") == "blocked":
        output = {
            "status": "blocked",
            "version": AGENT_CONTEXT_COMPRESSION_PAYLOAD_VERSION,
            "project_id": project_id,
            "chapter_index": resolved_chapter_index,
            "projection": _projection_snapshot(projection),
            "compression_plan": compression_plan,
            "compression_payload": None,
            "side_effects": {"writes": [], "runtime_context_mutated": False},
            "recommended_next_tools": projection.get("recommended_next_tools") or [],
            "recovery": projection.get("recovery") or {},
            "trace": {
                "source": "build_agent_context_compression_payload",
                "version": AGENT_CONTEXT_COMPRESSION_PAYLOAD_VERSION,
                "mutability": "read",
                "runtime_behavior_changed": False,
                "blocked_by": "inspect_agent_context_compression_projection",
            },
        }
        return _json_safe_output(output)

    context_summary = summarize_longform_context(
        db,
        project_id,
        chapter_index=resolved_chapter_index,
        max_chars=target_max_chars or max_chars,
        include_prompt_context=True,
    )
    payload = _compression_payload(
        projection=projection,
        context_summary=context_summary,
        target_max_chars=target_max_chars,
    )
    output = {
        "status": "ready" if compression_plan.get("status") == "recommended" else "not_needed",
        "version": AGENT_CONTEXT_COMPRESSION_PAYLOAD_VERSION,
        "project_id": project_id,
        "chapter_index": resolved_chapter_index or context_summary.get("chapter_index"),
        "projection": _projection_snapshot(projection),
        "compression_plan": compression_plan,
        "compression_payload": payload,
        "evidence": {
            "source_section_keys": context_summary.get("source_section_keys") or [],
            "diagnostics": context_summary.get("diagnostics") or [],
            "memory_provenance": context_summary.get("memory_provenance") or {},
        },
        "side_effects": {"writes": [], "runtime_context_mutated": False},
        "recommended_next_tools": projection.get("recommended_next_tools") or [],
        "recovery": projection.get("recovery") or {},
        "trace": {
            "source": "build_agent_context_compression_payload",
            "version": AGENT_CONTEXT_COMPRESSION_PAYLOAD_VERSION,
            "mutability": "read",
            "runtime_behavior_changed": False,
            "projection_version": projection.get("version"),
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
        tools.append("build_agent_context_compression_payload")
    if "prompt_context_truncated" in codes:
        tools.append("inspect_agent_memory_route")
    return _dedupe(tools)


def _compression_plan(
    *,
    status: str,
    risks: list[dict[str, Any]],
    chapter_index: int | None,
    max_chars: int,
    context_guard_failure_count: int,
) -> dict[str, Any]:
    target_max_chars = _compression_target_chars(max_chars) if status == "warning" else max_chars
    plan = {
        "status": "recommended" if status == "warning" else ("blocked" if status == "blocked" else "not_needed"),
        "mode": "head_tail_protected_pretrim",
        "target_max_chars": target_max_chars,
        "protected_head_sections": HEAD_PROTECTED_SECTIONS,
        "protected_tail_sections": TAIL_PROTECTED_SECTIONS,
        "pretrim_order": PRETRIM_ORDER if status == "warning" else [],
        "summary_tool": None,
        "payload_tool": None,
        "llm_summary_required": status == "warning",
    }
    if status == "warning":
        plan["summary_tool"] = {
            "tool_name": "summarize_longform_context",
            "params": {
                "chapter_index": chapter_index,
                "max_chars": target_max_chars,
                "include_prompt_context": False,
            },
        }
        plan["payload_tool"] = {
            "tool_name": "build_agent_context_compression_payload",
            "params": {
                "chapter_index": chapter_index,
                "max_chars": max_chars,
                "context_guard_failure_count": _non_negative_int(context_guard_failure_count),
            },
        }
    elif any(str(risk.get("code") or "") == "context_guard_open" for risk in risks):
        plan["pretrim_order"] = PRETRIM_ORDER
    return plan


def _compression_target_chars(max_chars: int) -> int:
    if not max_chars:
        return 0
    return max(500, int(max_chars * 0.75))


def _recovery(
    *,
    status: str,
    risks: list[dict[str, Any]],
    chapter_index: int | None,
    max_chars: int,
    compression_plan: dict[str, Any],
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
        summary_tool = compression_plan.get("summary_tool") if isinstance(compression_plan.get("summary_tool"), dict) else None
        payload_tool = compression_plan.get("payload_tool") if isinstance(compression_plan.get("payload_tool"), dict) else None
        return {
            "status": "optional",
            "reason": "context_compression_window_pressure",
            "next_tools": _recommended_next_tools(risks),
            "tools": [payload_tool or summary_tool] if (payload_tool or summary_tool) else [],
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


def _optional_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _compression_payload(
    *,
    projection: dict[str, Any],
    context_summary: dict[str, Any],
    target_max_chars: int,
) -> dict[str, Any]:
    context = context_summary.get("context_summary") if isinstance(context_summary.get("context_summary"), dict) else {}
    sections = context_summary.get("sections") if isinstance(context_summary.get("sections"), list) else []
    source_sections = (
        context_summary.get("source_sections") if isinstance(context_summary.get("source_sections"), list) else []
    )
    protected_head = [
        _payload_section("project", context_summary.get("project") if isinstance(context_summary.get("project"), dict) else {}),
        _payload_section("active_state", context.get("active_state") if isinstance(context.get("active_state"), dict) else {}),
    ]
    protected_tail = [
        _payload_section("recent_chapters", context.get("recent_chapters") or _section_items(sections, "recent_chapters")),
        _payload_section("critical_context", _section_or_items(sections, "critical_context")),
    ]
    pretrimmed_sections = [
        _pretrimmed_section("source_sections", source_sections, retained_as_protected_tail=False),
        _pretrimmed_section("critical_context", _section_or_items(sections, "critical_context"), retained_as_protected_tail=True),
        _pretrimmed_section("recent_chapters", _section_or_items(sections, "recent_chapters"), retained_as_protected_tail=True),
    ]
    summary = _payload_summary(context_summary, sections=sections)
    compressed_context = _limit_chars(
        _assembled_context(
            protected_head=protected_head,
            summary=summary,
            protected_tail=protected_tail,
        ),
        target_max_chars,
    )
    original_chars = _non_negative_int(context_summary.get("prompt_context_chars"))
    compressed_chars = len(compressed_context)
    return {
        "mode": "head_tail_protected_pretrim",
        "execution_mode": "dry_run",
        "target_max_chars": target_max_chars,
        "original_prompt_context_chars": original_chars,
        "compressed_context_chars": compressed_chars,
        "compression_ratio": round(compressed_chars / original_chars, 4) if original_chars else 0,
        "protected_head": protected_head,
        "summary": summary,
        "protected_tail": protected_tail,
        "pretrimmed_sections": pretrimmed_sections,
        "compressed_context": compressed_context,
        "source_prompt_context_included": isinstance(context_summary.get("prompt_context"), str),
        "trace": {
            "source": "summarize_longform_context",
            "summary_status": context_summary.get("status"),
            "projection_status": projection.get("status"),
        },
    }


def _projection_snapshot(projection: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": projection.get("status"),
        "version": projection.get("version"),
        "summary": projection.get("summary") or {},
        "risks": projection.get("risks") or [],
        "recommended_next_tools": projection.get("recommended_next_tools") or [],
    }


def _payload_section(key: str, content: Any) -> dict[str, Any]:
    return {
        "key": key,
        "status": "included",
        "item_count": _item_count(content),
        "char_count": _json_char_count(content),
        "content": content,
    }


def _payload_summary(context_summary: dict[str, Any], *, sections: list[Any]) -> dict[str, Any]:
    context = context_summary.get("context_summary") if isinstance(context_summary.get("context_summary"), dict) else {}
    return {
        "tool_name": "summarize_longform_context",
        "status": context_summary.get("status"),
        "chapter_index": context_summary.get("chapter_index"),
        "goal": context.get("goal"),
        "section_keys": [str(section.get("key") or "") for section in sections if isinstance(section, dict)],
        "text": _limit_chars(_json_preview(context), 1000),
    }


def _pretrimmed_section(key: str, content: Any, *, retained_as_protected_tail: bool) -> dict[str, Any]:
    return {
        "key": key,
        "reason": "context_window_pressure_pretrim",
        "original_char_count": _json_char_count(content),
        "retained_char_count": _json_char_count(content) if retained_as_protected_tail else 0,
        "retained_as_protected_tail": retained_as_protected_tail,
    }


def _section_or_items(sections: list[Any], key: str) -> Any:
    for section in sections:
        if isinstance(section, dict) and section.get("key") == key:
            return section
    return []


def _section_items(sections: list[Any], key: str) -> list[Any]:
    section = _section_or_items(sections, key)
    if isinstance(section, dict) and isinstance(section.get("items"), list):
        return section["items"]
    return []


def _item_count(content: Any) -> int:
    if isinstance(content, dict):
        if "item_count" in content:
            return _non_negative_int(content.get("item_count"))
        if isinstance(content.get("items"), list):
            return len(content["items"])
        return 1 if content else 0
    if isinstance(content, list):
        return len(content)
    return 1 if content else 0


def _assembled_context(
    *,
    protected_head: list[dict[str, Any]],
    summary: dict[str, Any],
    protected_tail: list[dict[str, Any]],
) -> str:
    blocks = []
    for section in protected_head:
        blocks.append(f"[protected_head:{section['key']}]\n{_json_preview(section.get('content'))}")
    blocks.append(f"[summary:{summary['tool_name']}]\n{summary.get('text') or ''}")
    for section in protected_tail:
        blocks.append(f"[protected_tail:{section['key']}]\n{_json_preview(section.get('content'))}")
    return "\n\n".join(blocks)


def _json_char_count(content: Any) -> int:
    return len(_json_preview(content))


def _json_preview(content: Any) -> str:
    return json.dumps(content, ensure_ascii=False, sort_keys=True, default=str)


def _limit_chars(value: str, limit: int) -> str:
    if not limit or len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

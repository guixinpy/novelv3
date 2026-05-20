from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.longform_memory import build_longform_context_package, get_longform_maintenance_diagnostics
from app.core.outline_lookup import find_outline_chapter
from app.models import ChapterContent, Project

DEFAULT_MAX_CHARS = 4000
MIN_MAX_CHARS = 500
MAX_MAX_CHARS = 12000
SECTION_ITEM_LIMIT = 5
SUMMARY_TEXT_LIMIT = 220


def summarize_longform_context(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
    query: str | None = None,
    max_chars: int | None = None,
    include_prompt_context: bool = False,
) -> dict[str, Any]:
    project = _require_project(db, project_id)
    target_chapter = _target_chapter_index(db, project_id, chapter_index)
    char_limit = _clamp_max_chars(max_chars)
    goal = _clean_text(query) or f"整理第{target_chapter}章写作上下文"
    diagnostics: list[dict[str, Any]] = []

    package = build_longform_context_package(
        db,
        project_id,
        target_chapter,
        user_query=goal,
    )
    prompt_context = str(package.get("prompt_context") or "")
    raw_sections = package.get("sections") if isinstance(package.get("sections"), list) else []
    source_sections = [_source_section(section) for section in raw_sections if isinstance(section, dict)]
    sections = _compact_sections(raw_sections, diagnostics=diagnostics)
    source_section_keys = [section["key"] for section in source_sections]
    maintenance = get_longform_maintenance_diagnostics(db, project_id, limit=5)
    if maintenance.get("ready_for_writing") is False:
        diagnostics.append(
            {
                "code": "longform_memory_needs_maintenance",
                "severity": "warning",
                "message": "长篇记忆或检索索引存在缺口，建议先运行维护工具。",
                "issue_count": maintenance.get("issue_count", 0),
            }
        )
        decision = {
            "status": "blocked",
            "reason": "longform_memory_needs_maintenance",
            "message": "长篇记忆或检索索引存在缺口，建议先修复后再生成正文。",
        }
        should_generate_next_chapter = False
        recommended_actions = ["repair_longform_maintenance"]
    else:
        decision = {
            "status": "ready",
            "reason": "longform_context_ready",
            "message": "长篇上下文可用于后续生成。",
        }
        should_generate_next_chapter = True
        recommended_actions = ["preflight_writing"]
    if len(prompt_context) > char_limit:
        diagnostics.append(
            {
                "code": "prompt_context_truncated",
                "severity": "info",
                "message": "完整上下文超过本次摘要预算，已仅返回结构化摘要和来源键。",
                "prompt_context_chars": len(prompt_context),
                "max_chars": char_limit,
            }
        )

    output: dict[str, Any] = {
        "status": "completed",
        "project_id": project_id,
        "chapter_index": target_chapter,
        "project": {
            "id": project.id,
            "name": project.name,
            "genre": project.genre,
            "target_chapter_count": project.target_chapter_count or 0,
            "target_word_count": project.target_word_count or 0,
            "current_word_count": project.current_word_count or 0,
            "status": project.status,
        },
        "progress": _project_progress(db, project_id),
        "context_summary": {
            "goal": goal,
            "active_state": _active_state(db, project_id, target_chapter),
            "recent_chapters": _items_for_section(sections, "recent_chapters"),
            "critical_context": sections,
            "remaining_work": _remaining_work(maintenance),
        },
        "sections": sections,
        "source_sections": source_sections,
        "source_section_keys": source_section_keys,
        "diagnostics": diagnostics,
        "decision": decision,
        "should_generate_next_chapter": should_generate_next_chapter,
        "recommended_actions": recommended_actions,
        "prompt_context_chars": len(prompt_context),
        "limits": {
            "max_chars": char_limit,
            "include_prompt_context": include_prompt_context,
            "section_item_limit": SECTION_ITEM_LIMIT,
        },
        "trace": {
            "summary_version": "phase52.longform_context_summary.v1",
            "source": "build_longform_context_package",
            "source_section_count": len(source_sections),
        },
    }
    if include_prompt_context:
        output["prompt_context"] = _limit_text(prompt_context, char_limit)
    return output


def _require_project(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _target_chapter_index(db: Session, project_id: str, chapter_index: int | None) -> int:
    if chapter_index and chapter_index > 0:
        return int(chapter_index)
    latest = (
        db.query(func.max(ChapterContent.chapter_index))
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.content.isnot(None),
            ChapterContent.content != "",
        )
        .scalar()
    )
    return int(latest or 0) + 1


def _project_progress(db: Session, project_id: str) -> dict[str, Any]:
    generated_count, latest_index, word_count = (
        db.query(
            func.count(ChapterContent.id),
            func.max(ChapterContent.chapter_index),
            func.coalesce(func.sum(ChapterContent.word_count), 0),
        )
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.content.isnot(None),
            ChapterContent.content != "",
        )
        .one()
    )
    return {
        "generated_chapter_count": int(generated_count or 0),
        "latest_generated_chapter_index": int(latest_index) if latest_index is not None else None,
        "generated_word_count": int(word_count or 0),
    }


def _active_state(db: Session, project_id: str, chapter_index: int) -> dict[str, Any]:
    outline_result = find_outline_chapter(db, project_id, chapter_index)
    outline = outline_result[1] if outline_result else None
    previous = (
        db.query(ChapterContent.chapter_index, ChapterContent.title, ChapterContent.word_count)
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.chapter_index < chapter_index,
            ChapterContent.content.isnot(None),
            ChapterContent.content != "",
        )
        .order_by(ChapterContent.chapter_index.desc())
        .first()
    )
    return {
        "target_outline": _compact_outline(outline),
        "previous_chapter": {
            "chapter_index": previous.chapter_index,
            "title": previous.title,
            "word_count": previous.word_count or 0,
        }
        if previous
        else None,
    }


def _compact_outline(outline: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(outline, dict):
        return None
    return {
        "chapter_index": outline.get("chapter_index"),
        "title": outline.get("title"),
        "summary": _limit_text(str(outline.get("summary") or ""), SUMMARY_TEXT_LIMIT),
        "characters": outline.get("characters") if isinstance(outline.get("characters"), list) else [],
        "purpose": _limit_text(str(outline.get("purpose") or ""), 120),
    }


def _compact_sections(raw_sections: list[Any], *, diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for section in raw_sections:
        if not isinstance(section, dict):
            continue
        items = section.get("items") if isinstance(section.get("items"), list) else []
        compact_items = [_compact_item(item) for item in items[:SECTION_ITEM_LIMIT] if isinstance(item, dict)]
        if len(items) > SECTION_ITEM_LIMIT:
            diagnostics.append(
                {
                    "code": "section_items_limited",
                    "severity": "info",
                    "message": "上下文 section 条目超过摘要上限，已截断。",
                    "section_key": section.get("key"),
                    "item_count": len(items),
                    "returned_count": len(compact_items),
                }
            )
        sections.append(
            {
                "key": str(section.get("key") or ""),
                "title": str(section.get("title") or ""),
                "item_count": len(items),
                "items": compact_items,
            }
        )
    return sections


def _compact_item(item: dict[str, Any]) -> dict[str, Any]:
    compact = {
        "id": item.get("id"),
        "memory_type": item.get("memory_type"),
        "scope_key": item.get("scope_key"),
        "title": item.get("title"),
        "summary": _limit_text(str(item.get("summary") or item.get("message") or ""), SUMMARY_TEXT_LIMIT),
    }
    if item.get("start_chapter_index") is not None or item.get("end_chapter_index") is not None:
        compact["chapter_range"] = {
            "start": item.get("start_chapter_index"),
            "end": item.get("end_chapter_index"),
        }
    metadata = item.get("metadata")
    if isinstance(metadata, dict) and metadata:
        compact["metadata"] = _json_safe_preview(metadata)
    code = item.get("code")
    if code:
        compact["code"] = code
    return compact


def _source_section(section: dict[str, Any]) -> dict[str, Any]:
    items = section.get("items") if isinstance(section.get("items"), list) else []
    return {
        "key": str(section.get("key") or ""),
        "title": str(section.get("title") or ""),
        "item_count": len(items),
        "source_type": "longform_context_package",
    }


def _items_for_section(sections: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    for section in sections:
        if section.get("key") == key:
            return section.get("items", [])
    return []


def _remaining_work(maintenance: dict[str, Any]) -> list[dict[str, Any]]:
    if maintenance.get("ready_for_writing") is True:
        return []
    recommendations = maintenance.get("recommendations")
    if not isinstance(recommendations, list):
        return []
    return [item for item in recommendations[:5] if isinstance(item, dict)]


def _clamp_max_chars(value: int | None) -> int:
    try:
        parsed = int(value) if value is not None else DEFAULT_MAX_CHARS
    except (TypeError, ValueError):
        parsed = DEFAULT_MAX_CHARS
    return max(MIN_MAX_CHARS, min(MAX_MAX_CHARS, parsed))


def _clean_text(value: str | None) -> str:
    return " ".join(str(value or "").split())


def _limit_text(value: str, limit: int) -> str:
    cleaned = _clean_text(value)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 3)].rstrip() + "..."


def _json_safe_preview(value: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(value, ensure_ascii=False, default=str)
    if len(encoded) <= 500:
        return value
    return {"preview": _limit_text(encoded, 500)}

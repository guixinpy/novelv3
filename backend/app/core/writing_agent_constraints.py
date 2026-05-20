from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.model_call_trace import build_context_block
from app.models import ChapterContent, ProjectProfileVersion, Storyline, WorldFactClaim

PREVIOUS_ENDING_CHARS = 220
MAX_ACTIVE_MILESTONES = 6
RECENT_LEAD_CHAPTER_WINDOW = 3
RECENT_LEAD_EXCERPT_CHARS = 120
MAX_RECENT_ACTION_LEADS = 8
MAX_UNRESOLVED_FORESHADOWING = 8
MAX_LIMITING_FACTS = 8
IDENTIFIER_RE = re.compile(r"\b[A-Z]{1,4}-\d{2,5}(?:-\d{1,5})*\b")
LIMITING_FACT_MARKERS = (
    "未解",
    "未确认",
    "尚未",
    "不是",
    "不能",
    "不得",
    "保持",
    "限制",
    "不应",
    "not_values",
    "confirmed_limited",
    "unresolved",
    "unknown",
)


def build_agent_chapter_constraint_block(
    db: Session,
    *,
    project_id: str,
    chapter_index: int,
) -> dict | None:
    package = build_agent_chapter_constraint_package(
        db,
        project_id=project_id,
        chapter_index=chapter_index,
    )
    prompt_context = package.get("prompt_context")
    if not prompt_context:
        return None
    block = build_context_block(
        key="agent_chapter_constraints",
        kind="agent_constraints",
        title="Agent章节约束",
        content=prompt_context,
        sources=[
            {
                "source_type": "WritingAgent",
                "source_id": project_id,
                "label": f"第{chapter_index}章自动约束包",
                "source_ref": f"chapter:{chapter_index}:agent_constraints",
                "metadata": {
                    "chapter_index": chapter_index,
                    "section_keys": [
                        section.get("key")
                        for section in package.get("sections", [])
                        if isinstance(section, dict)
                    ],
                },
            }
        ],
    )
    block["metadata"] = {
        "chapter_index": chapter_index,
        "section_keys": [
            section.get("key")
            for section in package.get("sections", [])
            if isinstance(section, dict)
        ],
    }
    return block


def build_agent_chapter_constraint_package(
    db: Session,
    *,
    project_id: str,
    chapter_index: int,
) -> dict[str, Any]:
    sections: list[dict[str, Any]] = []
    lines = [
        f"目标章节：第{chapter_index}章",
        "这些约束由系统根据已有章节、故事线和世界模型自动生成；优先级高于粗略大纲中的捷径或提前揭示。",
    ]

    previous = _previous_chapter_state(db, project_id, chapter_index)
    if previous:
        sections.append({"key": "previous_chapter_state", "title": "上一章结束状态", "items": [previous]})
        lines.append("【上一章结束状态】")
        lines.append(f"- 第{previous['chapter_index']}章《{previous['title']}》结尾：{previous['ending_excerpt']}")

    storyline = _latest_storyline(db, project_id)
    active_milestones = _active_story_milestones(storyline, chapter_index) if storyline else []
    if active_milestones:
        sections.append({"key": "active_story_milestones", "title": "当前故事线窗口", "items": active_milestones})
        lines.append("【当前故事线窗口】")
        for item in active_milestones:
            lines.append(f"- {item['plotline']}（{item['chapter_range']}）：{item['goal']}")

    recent_leads = _recent_action_leads(db, project_id, chapter_index)
    if recent_leads:
        sections.append({"key": "recent_action_leads", "title": "近期行动线索", "items": recent_leads})
        lines.append("【近期行动线索】")
        for item in recent_leads:
            lines.append(
                f"- {item['term']}（第{item['chapter_index']}章《{item['title']}》）：{item['excerpt']}。"
                "后续大纲或正文不得无故遗忘；必须沿用该线索的原始语境，"
                "不得改写为无来源的新地点、新物件或新档案；如暂缓处理，需要在剧情中交代原因。"
            )

    unresolved = _unresolved_foreshadowing(storyline, chapter_index) if storyline else []
    if unresolved:
        sections.append({"key": "unresolved_foreshadowing", "title": "未回收伏笔", "items": unresolved})
        lines.append("【未回收伏笔】")
        for item in unresolved:
            resolved_label = f"计划第{item['resolved_chapter']}章回收" if item.get("resolved_chapter") else "回收章未定"
            lines.append(
                f"- {item['hint']}（埋设第{item['planted_chapter']}章，{resolved_label}）。"
                "不得提前给出终局答案；只能推进局部线索、误导、代价或下一步方向。"
            )

    limiting_facts = _limiting_world_facts(db, project_id, chapter_index)
    if limiting_facts:
        sections.append({"key": "limiting_world_facts", "title": "限制性世界事实", "items": limiting_facts})
        lines.append("【限制性世界事实】")
        for fact in limiting_facts:
            note = f"；备注：{fact['notes']}" if fact.get("notes") else ""
            lines.append(f"- {fact['subject_ref']} / {fact['predicate']}：{fact['object']}{note}")

    if len(lines) <= 2:
        return {
            "project_id": project_id,
            "chapter_index": chapter_index,
            "sections": sections,
            "prompt_context": "",
        }

    lines.append("【Agent执行规则】")
    lines.append("- 生成大纲或正文时，先遵守已确认世界事实和未回收伏笔，再使用粗略章节大纲。")
    lines.append("- 如果粗略大纲与未回收伏笔或限制性世界事实冲突，改写为暧昧线索、阶段性误解或下一步方向。")
    lines.append("- 不要把长期悬念写成已确认、已解决、已拿到终局证据或已完成关键门禁突破。")

    return {
        "project_id": project_id,
        "chapter_index": chapter_index,
        "sections": sections,
        "prompt_context": "\n".join(lines),
    }


def _previous_chapter_state(db: Session, project_id: str, chapter_index: int) -> dict[str, Any] | None:
    if chapter_index <= 1:
        return None
    chapter = (
        db.query(ChapterContent.chapter_index, ChapterContent.title, ChapterContent.content)
        .filter(ChapterContent.project_id == project_id, ChapterContent.chapter_index == chapter_index - 1)
        .first()
    )
    if chapter is None:
        return None
    content = str(chapter.content or "").strip()
    excerpt = content[-PREVIOUS_ENDING_CHARS:] if len(content) > PREVIOUS_ENDING_CHARS else content
    return {
        "chapter_index": int(chapter.chapter_index),
        "title": chapter.title or "",
        "ending_excerpt": excerpt,
    }


def _latest_storyline(db: Session, project_id: str) -> Storyline | None:
    return (
        db.query(Storyline)
        .filter(Storyline.project_id == project_id)
        .order_by(Storyline.updated_at.desc(), Storyline.created_at.desc(), Storyline.id.desc())
        .first()
    )


def _active_story_milestones(storyline: Storyline, chapter_index: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for plotline in _list_dicts(storyline.plotlines):
        plotline_name = _text(plotline.get("name")) or "未命名故事线"
        for milestone in _list_dicts(plotline.get("milestones")):
            chapter_range = _text(milestone.get("chapter_range") or milestone.get("range") or milestone.get("chapters"))
            if not _range_contains(chapter_range, chapter_index):
                continue
            goal = _text(
                milestone.get("goal")
                or milestone.get("summary")
                or milestone.get("content")
                or milestone.get("description")
            )
            if not goal:
                continue
            items.append({"plotline": plotline_name, "chapter_range": chapter_range, "goal": goal})
            if len(items) >= MAX_ACTIVE_MILESTONES:
                return items
    return items


def _recent_action_leads(db: Session, project_id: str, chapter_index: int) -> list[dict[str, Any]]:
    if chapter_index <= 1:
        return []
    start = max(1, chapter_index - RECENT_LEAD_CHAPTER_WINDOW)
    chapters = (
        db.query(ChapterContent.chapter_index, ChapterContent.title, ChapterContent.content)
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.chapter_index >= start,
            ChapterContent.chapter_index < chapter_index,
            ChapterContent.content != "",
        )
        .order_by(ChapterContent.chapter_index.desc())
        .all()
    )
    leads: list[dict[str, Any]] = []
    seen_terms: set[str] = set()
    for chapter in chapters:
        content = str(chapter.content or "")
        for match in IDENTIFIER_RE.finditer(content):
            term = match.group(0)
            if term in seen_terms:
                continue
            seen_terms.add(term)
            leads.append(
                {
                    "term": term,
                    "chapter_index": int(chapter.chapter_index),
                    "title": chapter.title or "",
                    "excerpt": _excerpt_around(content, match.start(), match.end()),
                }
            )
            if len(leads) >= MAX_RECENT_ACTION_LEADS:
                return leads
    return leads


def _unresolved_foreshadowing(storyline: Storyline, chapter_index: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in _list_dicts(storyline.foreshadowing):
        hint = _text(item.get("hint") or item.get("summary") or item.get("content"))
        if not hint:
            continue
        planted = _optional_int(item.get("planted_chapter") or item.get("chapter") or item.get("plant_chapter"))
        resolved = _optional_int(item.get("resolved_chapter") or item.get("resolve_chapter"))
        status = _text(item.get("status")).lower()
        if planted is not None and planted > chapter_index:
            continue
        if status in {"resolved", "closed", "done", "回收", "已回收"}:
            continue
        if resolved is not None and resolved <= chapter_index:
            continue
        items.append(
            {
                "hint": hint,
                "planted_chapter": planted or "未知",
                "resolved_chapter": resolved,
                "status": status or "unresolved",
            }
        )
        if len(items) >= MAX_UNRESOLVED_FORESHADOWING:
            return items
    return items


def _limiting_world_facts(db: Session, project_id: str, chapter_index: int) -> list[dict[str, Any]]:
    profile = (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc(), ProjectProfileVersion.created_at.desc())
        .first()
    )
    if profile is None:
        return []
    query = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.project_profile_version_id == profile.id,
            WorldFactClaim.profile_version == profile.version,
            WorldFactClaim.claim_status == "confirmed",
            WorldFactClaim.claim_layer == "truth",
            (WorldFactClaim.chapter_index.is_(None)) | (WorldFactClaim.chapter_index <= chapter_index),
        )
        .order_by(WorldFactClaim.chapter_index.desc().nullslast(), WorldFactClaim.intra_chapter_seq.desc(), WorldFactClaim.claim_id.asc())
        .limit(80)
    )
    facts: list[dict[str, Any]] = []
    for fact in query.all():
        object_text = _compact_json(fact.object_ref_or_value)
        notes = _text(fact.notes)
        if not _is_limiting_fact(object_text, notes):
            continue
        facts.append(
            {
                "subject_ref": fact.subject_ref,
                "predicate": fact.predicate,
                "object": object_text,
                "notes": notes,
                "chapter_index": fact.chapter_index,
            }
        )
        if len(facts) >= MAX_LIMITING_FACTS:
            break
    return facts


def _is_limiting_fact(object_text: str, notes: str) -> bool:
    combined = f"{object_text}\n{notes}"
    return any(marker in combined for marker in LIMITING_FACT_MARKERS)


def _range_contains(chapter_range: str, chapter_index: int) -> bool:
    if not chapter_range:
        return False
    match = re.search(r"(\d+)\s*(?:-|~|至|到|—|－)\s*(\d+)", chapter_range)
    if match:
        start, end = int(match.group(1)), int(match.group(2))
        return start <= chapter_index <= end
    single = re.search(r"\d+", chapter_range)
    return bool(single and int(single.group(0)) == chapter_index)


def _list_dicts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _optional_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _compact_json(value: object, max_chars: int = 240) -> str:
    if isinstance(value, str):
        text = value.strip()
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def _excerpt_around(text: str, start: int, end: int) -> str:
    half = RECENT_LEAD_EXCERPT_CHARS // 2
    left = max(0, start - half)
    right = min(len(text), end + half)
    excerpt = text[left:right].strip()
    if left > 0:
        excerpt = "..." + excerpt
    if right < len(text):
        excerpt += "..."
    return excerpt


def _text(value: object) -> str:
    return str(value or "").strip()

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.project_stats import reconcile_project_word_count
from app.models import ChapterContent, LongformMemory, Outline, Project

DEFAULT_ARC_SIZE = 20
DEFAULT_VOLUME_SIZE = 100
RECENT_CHAPTER_WINDOW = 3


def rebuild_longform_memory(
    db: Session,
    project_id: str,
    *,
    arc_size: int = DEFAULT_ARC_SIZE,
    volume_size: int = DEFAULT_VOLUME_SIZE,
) -> dict[str, Any]:
    project = _require_project(db, project_id)
    chapters = _chapters(db, project_id)
    outline_lookup = _outline_lookup(db, project_id)

    db.query(LongformMemory).filter(LongformMemory.project_id == project_id).delete(synchronize_session=False)

    memories: list[LongformMemory] = []
    for chapter in chapters:
        outline = outline_lookup.get(chapter.chapter_index)
        memories.append(_chapter_memory(project_id, chapter, outline))

    for start, group in _chapter_groups(chapters, arc_size):
        memories.append(_range_memory(project_id, memory_type="arc", start=start, chapters=group))

    for start, group in _chapter_groups(chapters, volume_size):
        memories.append(_range_memory(project_id, memory_type="volume", start=start, chapters=group))

    memories.append(_global_memory(project_id, chapters))
    db.add_all(memories)
    reconcile_project_word_count(db, project, commit=False)
    db.commit()

    counts = Counter(memory.memory_type for memory in memories)
    return {
        "status": "completed",
        "project_id": project_id,
        "counts_by_type": _ordered_counts(counts),
        "total_memories": len(memories),
        "current_word_count": project.current_word_count or 0,
    }


def get_longform_memory_diagnostics(db: Session, project_id: str) -> dict[str, Any]:
    project = _require_project(db, project_id)
    reconcile_project_word_count(db, project)
    rows = (
        db.query(LongformMemory.memory_type, func.count(LongformMemory.id))
        .filter(LongformMemory.project_id == project_id)
        .group_by(LongformMemory.memory_type)
        .all()
    )
    latest_updated_at: datetime | None = (
        db.query(func.max(LongformMemory.updated_at)).filter(LongformMemory.project_id == project_id).scalar()
    )
    counts = Counter({memory_type: count for memory_type, count in rows})
    return {
        "project_id": project_id,
        "chapter_count": db.query(ChapterContent).filter(ChapterContent.project_id == project_id).count(),
        "current_word_count": project.current_word_count or 0,
        "counts_by_type": _ordered_counts(counts),
        "total_memories": sum(counts.values()),
        "latest_updated_at": latest_updated_at,
    }


def build_longform_context_package(
    db: Session,
    project_id: str,
    chapter_index: int,
    *,
    user_query: str | None = None,
) -> dict[str, Any]:
    _require_project(db, project_id)
    sections: list[dict[str, Any]] = []
    lines = [f"【长篇上下文】目标章节：第{chapter_index}章"]

    for memory_type, key, title in [
        ("global", "global", "全书记忆"),
        ("volume", "volume", "当前卷记忆"),
        ("arc", "arc", "当前剧情弧记忆"),
    ]:
        items = _context_memory_items(db, project_id, memory_type, chapter_index)
        if items:
            sections.append({"key": key, "title": title, "items": items})
            lines.append(f"【{title}】")
            lines.extend(f"- {item['title']}：{item['summary']}" for item in items)

    recent_items = _recent_chapter_memory_items(db, project_id, chapter_index)
    if recent_items:
        sections.append({"key": "recent_chapters", "title": "近期章节记忆", "items": recent_items})
        lines.append("【近期章节记忆】")
        lines.extend(f"- {item['title']}：{item['summary']}" for item in recent_items)

    try:
        from app.core.athena_retrieval import build_query_aware_retrieval_context

        retrieval_context = build_query_aware_retrieval_context(
            db=db,
            project_id=project_id,
            chapter_index=chapter_index,
            user_query=user_query,
        )
    except Exception:
        retrieval_context = None
    if retrieval_context:
        sections.append(retrieval_context["section"])
        lines.extend(retrieval_context["prompt_lines"])

    return {
        "project_id": project_id,
        "chapter_index": chapter_index,
        "sections": sections,
        "prompt_context": "\n".join(lines),
    }


def _require_project(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _chapters(db: Session, project_id: str) -> list[ChapterContent]:
    return (
        db.query(ChapterContent)
        .filter(ChapterContent.project_id == project_id)
        .order_by(ChapterContent.chapter_index.asc())
        .all()
    )


def _outline_lookup(db: Session, project_id: str) -> dict[int, dict[str, Any]]:
    outline = db.query(Outline).filter(Outline.project_id == project_id).first()
    lookup: dict[int, dict[str, Any]] = {}
    if not outline or not outline.chapters:
        return lookup
    for item in outline.chapters:
        if not isinstance(item, dict):
            continue
        chapter_index = item.get("chapter_index", item.get("chapter"))
        if chapter_index is None:
            continue
        lookup[int(chapter_index)] = item
    return lookup


def _chapter_memory(project_id: str, chapter: ChapterContent, outline: dict[str, Any] | None) -> LongformMemory:
    title = chapter.title or f"第{chapter.chapter_index}章"
    outline_summary = str((outline or {}).get("summary") or "").strip()
    summary = outline_summary or _preview(chapter.content or "", 180) or title
    return LongformMemory(
        project_id=project_id,
        memory_type="chapter",
        scope_key=f"chapter:{chapter.chapter_index}",
        start_chapter_index=chapter.chapter_index,
        end_chapter_index=chapter.chapter_index,
        title=title,
        summary=summary,
        status="current",
        memory_metadata={
            "chapter_index": chapter.chapter_index,
            "word_count": chapter.word_count or 0,
            "status": chapter.status,
            "source": "outline" if outline_summary else "chapter_content",
        },
    )


def _range_memory(project_id: str, *, memory_type: str, start: int, chapters: list[ChapterContent]) -> LongformMemory:
    end = chapters[-1].chapter_index
    chapter_count = len(chapters)
    word_count = sum(chapter.word_count or 0 for chapter in chapters)
    title = f"第{start}-{end}章"
    summaries = [f"{chapter.title or f'第{chapter.chapter_index}章'}" for chapter in chapters[:5]]
    if chapter_count > 5:
        summaries.append(f"等 {chapter_count} 章")
    return LongformMemory(
        project_id=project_id,
        memory_type=memory_type,
        scope_key=f"{memory_type}:{start}-{end}",
        start_chapter_index=start,
        end_chapter_index=end,
        title=title,
        summary=f"覆盖{chapter_count}章，约{word_count}字；包含：" + "、".join(summaries),
        status="current",
        memory_metadata={"chapter_count": chapter_count, "word_count": word_count},
    )


def _global_memory(project_id: str, chapters: list[ChapterContent]) -> LongformMemory:
    chapter_count = len(chapters)
    word_count = sum(chapter.word_count or 0 for chapter in chapters)
    latest = chapters[-1].chapter_index if chapters else None
    return LongformMemory(
        project_id=project_id,
        memory_type="global",
        scope_key="global",
        start_chapter_index=chapters[0].chapter_index if chapters else None,
        end_chapter_index=latest,
        title="全书记忆",
        summary=f"当前已生成{chapter_count}章，约{word_count}字。" if chapter_count else "尚未生成正文。",
        status="current",
        memory_metadata={"chapter_count": chapter_count, "word_count": word_count, "latest_chapter_index": latest},
    )


def _chapter_groups(chapters: list[ChapterContent], size: int) -> list[tuple[int, list[ChapterContent]]]:
    groups: list[tuple[int, list[ChapterContent]]] = []
    for index in range(0, len(chapters), size):
        group = chapters[index:index + size]
        if group:
            groups.append((group[0].chapter_index, group))
    return groups


def _ordered_counts(counts: Counter) -> dict[str, int]:
    return {key: int(counts.get(key, 0)) for key in ["chapter", "arc", "volume", "global"] if counts.get(key, 0)}


def _preview(text: str, limit: int) -> str:
    cleaned = " ".join((text or "").split())
    return cleaned[:limit]


def _context_memory_items(db: Session, project_id: str, memory_type: str, chapter_index: int) -> list[dict[str, Any]]:
    if memory_type == "global":
        return _safe_range_context_items(
            db,
            project_id=project_id,
            memory_type="global",
            start_chapter_index=None,
            end_chapter_index=chapter_index,
            title="截至当前的全书记忆",
        )
    if memory_type == "volume":
        start_chapter_index = ((chapter_index - 1) // DEFAULT_VOLUME_SIZE) * DEFAULT_VOLUME_SIZE + 1
        return _safe_range_context_items(
            db,
            project_id=project_id,
            memory_type="volume",
            start_chapter_index=start_chapter_index,
            end_chapter_index=chapter_index,
            title=f"第{start_chapter_index}-{chapter_index}章卷内记忆",
        )
    if memory_type == "arc":
        start_chapter_index = ((chapter_index - 1) // DEFAULT_ARC_SIZE) * DEFAULT_ARC_SIZE + 1
        return _safe_range_context_items(
            db,
            project_id=project_id,
            memory_type="arc",
            start_chapter_index=start_chapter_index,
            end_chapter_index=chapter_index,
            title=f"第{start_chapter_index}-{chapter_index}章剧情弧记忆",
        )
    return []


def _safe_range_context_items(
    db: Session,
    *,
    project_id: str,
    memory_type: str,
    start_chapter_index: int | None,
    end_chapter_index: int,
    title: str,
) -> list[dict[str, Any]]:
    query = db.query(LongformMemory).filter(
        LongformMemory.project_id == project_id,
        LongformMemory.memory_type == "chapter",
        LongformMemory.end_chapter_index <= end_chapter_index,
    )
    if start_chapter_index is not None:
        query = query.filter(LongformMemory.start_chapter_index >= start_chapter_index)
    chapters = query.order_by(LongformMemory.start_chapter_index.asc()).all()
    if not chapters:
        return []
    word_count = sum((memory.memory_metadata or {}).get("word_count", 0) for memory in chapters)
    recent_titles = "、".join(memory.title for memory in chapters[-5:])
    first_chapter = chapters[0].start_chapter_index
    last_chapter = chapters[-1].end_chapter_index
    return [
        {
            "id": None,
            "memory_type": memory_type,
            "scope_key": f"{memory_type}:safe:{first_chapter}-{last_chapter}",
            "start_chapter_index": first_chapter,
            "end_chapter_index": last_chapter,
            "title": title,
            "summary": f"截至第{last_chapter}章，已纳入{len(chapters)}章，约{word_count}字；近期章节：{recent_titles}",
            "metadata": {"chapter_count": len(chapters), "word_count": word_count, "source": "safe_chapter_memory_rollup"},
        }
    ]


def _recent_chapter_memory_items(db: Session, project_id: str, chapter_index: int) -> list[dict[str, Any]]:
    memories = (
        db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == "chapter",
            LongformMemory.end_chapter_index < chapter_index,
        )
        .order_by(LongformMemory.end_chapter_index.desc())
        .limit(RECENT_CHAPTER_WINDOW)
        .all()
    )
    return [_memory_item(memory) for memory in reversed(memories)]


def _memory_item(memory: LongformMemory) -> dict[str, Any]:
    return {
        "id": memory.id,
        "memory_type": memory.memory_type,
        "scope_key": memory.scope_key,
        "start_chapter_index": memory.start_chapter_index,
        "end_chapter_index": memory.end_chapter_index,
        "title": memory.title,
        "summary": memory.summary,
        "metadata": memory.memory_metadata or {},
    }

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.core.outline_lookup import find_outline_chapter
from app.core.project_stats import reconcile_project_word_count
from app.models import ChapterContent, LongformMemory, Outline, Project, RetrievalDocument

DEFAULT_ARC_SIZE = 20
DEFAULT_VOLUME_SIZE = 100
RECENT_CHAPTER_WINDOW = 3


@dataclass
class LongformMaintenanceState:
    project_id: str
    chapter_count: int
    missing_memory_chapters: list[int]
    stale_memory_chapters: list[int]
    missing_retrieval_chapters: list[int]
    stale_retrieval_chapters: list[int]
    latest_chapter_updated_at: datetime | None
    latest_memory_updated_at: datetime | None
    latest_retrieval_updated_at: datetime | None
    latest_synced_chapter_index: int | None


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


def get_longform_maintenance_diagnostics(db: Session, project_id: str, *, limit: int = 20) -> dict[str, Any]:
    _require_project(db, project_id)
    return _maintenance_diagnostics_payload(_collect_longform_maintenance_state(db, project_id), limit=limit)


def repair_longform_maintenance(
    db: Session,
    project_id: str,
    *,
    limit: int = 20,
    repair_limit: int = 100,
) -> dict[str, Any]:
    from app.core.athena_retrieval import sync_longform_memory_retrieval_documents

    _require_project(db, project_id)
    before = _collect_longform_maintenance_state(db, project_id)
    memory_chapter_indexes = sorted(set(before.missing_memory_chapters + before.stale_memory_chapters))
    refreshed_chapter_indexes = memory_chapter_indexes[:repair_limit]
    updated_memory_ids: list[str] = []
    for chapter_index in refreshed_chapter_indexes:
        refresh_result = refresh_longform_memory_for_chapter(db, project_id, chapter_index)
        updated_memory_ids.extend(refresh_result["updated_memory_ids"])

    after_memory = _collect_longform_maintenance_state(db, project_id)
    retrieval_chapter_indexes = sorted(
        set(after_memory.missing_retrieval_chapters + after_memory.stale_retrieval_chapters)
    )[:repair_limit]
    updated_memory_ids.extend(_chapter_memory_ids(db, project_id, retrieval_chapter_indexes))
    sync_result = sync_longform_memory_retrieval_documents(db, project_id, sorted(set(updated_memory_ids)))
    remaining = get_longform_maintenance_diagnostics(db, project_id, limit=limit)
    synced_scope_keys = sync_result.get("synced_scope_keys", [])
    remaining_issue_count = _maintenance_issue_count(remaining)
    return {
        "project_id": project_id,
        "status": "completed",
        "repaired_memory_count": len(refreshed_chapter_indexes),
        "repaired_retrieval_count": len(synced_scope_keys),
        "refreshed_chapter_indexes": refreshed_chapter_indexes[:limit],
        "synced_scope_keys": synced_scope_keys,
        "has_more": remaining_issue_count > 0,
        "remaining_issue_count": remaining_issue_count,
        "remaining": remaining,
    }


def _collect_longform_maintenance_state(db: Session, project_id: str) -> LongformMaintenanceState:
    chapters = _maintained_chapters(db, project_id)
    chapter_memories = {
        memory.scope_key: memory
        for memory in db.query(LongformMemory.id, LongformMemory.scope_key, LongformMemory.updated_at)
        .filter(LongformMemory.project_id == project_id, LongformMemory.memory_type == "chapter")
        .all()
    }
    missing_memory_chapters: list[int] = []
    stale_memory_chapters: list[int] = []
    missing_retrieval_chapters: list[int] = []
    stale_retrieval_chapters: list[int] = []
    latest_chapter_updated_at = None
    latest_memory_updated_at = None
    latest_retrieval_updated_at = None
    latest_synced_chapter_index = None
    retrieval_documents = _latest_longform_retrieval_documents(db, project_id)

    for chapter in chapters:
        latest_chapter_updated_at = _max_datetime(latest_chapter_updated_at, chapter.updated_at)
        memory = chapter_memories.get(f"chapter:{chapter.chapter_index}")
        if memory is None:
            missing_memory_chapters.append(chapter.chapter_index)
            missing_retrieval_chapters.append(chapter.chapter_index)
            continue
        latest_memory_updated_at = _max_datetime(latest_memory_updated_at, memory.updated_at)
        if _is_stale(memory.updated_at, chapter.updated_at):
            stale_memory_chapters.append(chapter.chapter_index)
        retrieval_document = retrieval_documents.get(f"memory:{memory.scope_key}")
        if retrieval_document is None:
            missing_retrieval_chapters.append(chapter.chapter_index)
            continue
        latest_retrieval_updated_at = _max_datetime(latest_retrieval_updated_at, retrieval_document.updated_at)
        latest_synced_chapter_index = max(latest_synced_chapter_index or 0, chapter.chapter_index)
        if retrieval_document.source_id != memory.id or _is_stale(retrieval_document.updated_at, memory.updated_at):
            stale_retrieval_chapters.append(chapter.chapter_index)

    return LongformMaintenanceState(
        project_id=project_id,
        chapter_count=len(chapters),
        missing_memory_chapters=missing_memory_chapters,
        stale_memory_chapters=stale_memory_chapters,
        missing_retrieval_chapters=missing_retrieval_chapters,
        stale_retrieval_chapters=stale_retrieval_chapters,
        latest_chapter_updated_at=latest_chapter_updated_at,
        latest_memory_updated_at=latest_memory_updated_at,
        latest_retrieval_updated_at=latest_retrieval_updated_at,
        latest_synced_chapter_index=latest_synced_chapter_index,
    )


def _maintenance_diagnostics_payload(state: LongformMaintenanceState, *, limit: int) -> dict[str, Any]:
    stale_total = (
        len(state.missing_memory_chapters)
        + len(state.stale_memory_chapters)
        + len(state.missing_retrieval_chapters)
        + len(state.stale_retrieval_chapters)
    )
    status = "stale" if stale_total else "current"
    return {
        "project_id": state.project_id,
        "status": status,
        "chapter_count": state.chapter_count,
        "stale_memory_count": len(state.stale_memory_chapters),
        "missing_memory_count": len(state.missing_memory_chapters),
        "stale_retrieval_count": len(state.stale_retrieval_chapters),
        "missing_retrieval_count": len(state.missing_retrieval_chapters),
        "stale_chapter_indexes": state.stale_memory_chapters[:limit],
        "missing_memory_chapter_indexes": state.missing_memory_chapters[:limit],
        "stale_retrieval_chapter_indexes": state.stale_retrieval_chapters[:limit],
        "missing_retrieval_chapter_indexes": state.missing_retrieval_chapters[:limit],
        "latest_chapter_updated_at": state.latest_chapter_updated_at,
        "latest_memory_updated_at": state.latest_memory_updated_at,
        "latest_retrieval_updated_at": state.latest_retrieval_updated_at,
        "latest_synced_chapter_index": state.latest_synced_chapter_index,
    }


def _maintenance_issue_count(payload: dict[str, Any]) -> int:
    return int(
        payload.get("stale_memory_count", 0)
        + payload.get("missing_memory_count", 0)
        + payload.get("stale_retrieval_count", 0)
        + payload.get("missing_retrieval_count", 0)
    )


def refresh_longform_memory_for_chapter(
    db: Session,
    project_id: str,
    chapter_index: int,
    *,
    arc_size: int = DEFAULT_ARC_SIZE,
    volume_size: int = DEFAULT_VOLUME_SIZE,
) -> dict[str, Any]:
    project = _require_project(db, project_id)
    chapter = _chapter_for_memory(db, project_id, chapter_index)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")

    outline_chapter = find_outline_chapter(db, project_id, chapter_index)
    outline = outline_chapter[1] if outline_chapter is not None else None
    arc_chapters = _range_chapters(db, project_id, chapter_index, arc_size)
    volume_chapters = _range_chapters(db, project_id, chapter_index, volume_size)
    delete_filter = or_(
        LongformMemory.scope_key == f"chapter:{chapter_index}",
        LongformMemory.memory_type == "global",
        and_(
            LongformMemory.memory_type == "arc",
            LongformMemory.start_chapter_index <= chapter_index,
            LongformMemory.end_chapter_index >= chapter_index,
        ),
        and_(
            LongformMemory.memory_type == "volume",
            LongformMemory.start_chapter_index <= chapter_index,
            LongformMemory.end_chapter_index >= chapter_index,
        ),
    )
    db.query(LongformMemory).filter(LongformMemory.project_id == project_id, delete_filter).delete(
        synchronize_session=False
    )

    memories = [_chapter_memory(project_id, chapter, outline)]
    if arc_chapters:
        memories.append(_range_memory(project_id, memory_type="arc", start=arc_chapters[0].chapter_index, chapters=arc_chapters))
    if volume_chapters:
        memories.append(
            _range_memory(project_id, memory_type="volume", start=volume_chapters[0].chapter_index, chapters=volume_chapters)
        )
    memories.append(_global_memory_from_stats(db, project_id))
    db.add_all(memories)
    db.flush()
    updated_scope_keys = [memory.scope_key for memory in memories]
    updated_memory_ids = [memory.id for memory in memories]
    reconcile_project_word_count(db, project, commit=False)
    db.commit()
    db.refresh(project)
    counts = _memory_type_counts(db, project_id)
    return {
        "status": "completed",
        "project_id": project_id,
        "chapter_index": chapter_index,
        "updated_scope_keys": updated_scope_keys,
        "updated_memory_ids": updated_memory_ids,
        "counts_by_type": _ordered_counts(counts),
        "total_memories": sum(counts.values()),
        "current_word_count": project.current_word_count or 0,
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


def _chapters(db: Session, project_id: str) -> list[Any]:
    return (
        db.query(
            ChapterContent.chapter_index,
            ChapterContent.title,
            ChapterContent.content,
            ChapterContent.word_count,
            ChapterContent.status,
        )
        .filter(ChapterContent.project_id == project_id)
        .order_by(ChapterContent.chapter_index.asc())
        .all()
    )


def _chapter_for_memory(db: Session, project_id: str, chapter_index: int) -> Any | None:
    return (
        db.query(
            ChapterContent.chapter_index,
            ChapterContent.title,
            ChapterContent.content,
            ChapterContent.word_count,
            ChapterContent.status,
        )
        .filter(ChapterContent.project_id == project_id, ChapterContent.chapter_index == chapter_index)
        .first()
    )


def _range_chapters(db: Session, project_id: str, chapter_index: int, size: int) -> list[Any]:
    start = ((chapter_index - 1) // size) * size + 1
    end = start + size - 1
    return (
        db.query(
            ChapterContent.chapter_index,
            ChapterContent.title,
            ChapterContent.word_count,
        )
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.chapter_index >= start,
            ChapterContent.chapter_index <= end,
        )
        .order_by(ChapterContent.chapter_index.asc())
        .all()
    )


def _maintained_chapters(db: Session, project_id: str) -> list[Any]:
    return (
        db.query(ChapterContent.chapter_index, ChapterContent.updated_at)
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.content != "",
        )
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


def _chapter_memory(project_id: str, chapter: Any, outline: dict[str, Any] | None) -> LongformMemory:
    title = chapter.title or f"第{chapter.chapter_index}章"
    outline_summary = str((outline or {}).get("summary") or "").strip()
    content_summary = _preview(chapter.content or "", 180)
    summary = content_summary or outline_summary or title
    source = "chapter_content" if content_summary else "outline" if outline_summary else "title"
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
            "source": source,
        },
    )


def _range_memory(project_id: str, *, memory_type: str, start: int, chapters: list[Any]) -> LongformMemory:
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


def _global_memory(project_id: str, chapters: list[Any]) -> LongformMemory:
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


def _global_memory_from_stats(db: Session, project_id: str) -> LongformMemory:
    chapter_count, word_count, first_chapter_index, latest_chapter_index = (
        db.query(
            func.count(ChapterContent.id),
            func.coalesce(func.sum(ChapterContent.word_count), 0),
            func.min(ChapterContent.chapter_index),
            func.max(ChapterContent.chapter_index),
        )
        .filter(ChapterContent.project_id == project_id)
        .one()
    )
    chapter_count = int(chapter_count or 0)
    word_count = int(word_count or 0)
    return LongformMemory(
        project_id=project_id,
        memory_type="global",
        scope_key="global",
        start_chapter_index=first_chapter_index,
        end_chapter_index=latest_chapter_index,
        title="全书记忆",
        summary=f"当前已生成{chapter_count}章，约{word_count}字。" if chapter_count else "尚未生成正文。",
        status="current",
        memory_metadata={
            "chapter_count": chapter_count,
            "word_count": word_count,
            "latest_chapter_index": latest_chapter_index,
        },
    )


def _chapter_groups(chapters: list[Any], size: int) -> list[tuple[int, list[Any]]]:
    groups: list[tuple[int, list[Any]]] = []
    for index in range(0, len(chapters), size):
        group = chapters[index:index + size]
        if group:
            groups.append((group[0].chapter_index, group))
    return groups


def _chapter_range(chapters: list[Any], chapter_index: int, size: int) -> list[Any]:
    start = ((chapter_index - 1) // size) * size + 1
    end = start + size - 1
    return [chapter for chapter in chapters if start <= chapter.chapter_index <= end]


def _memory_type_counts(db: Session, project_id: str) -> Counter:
    rows = (
        db.query(LongformMemory.memory_type, func.count(LongformMemory.id))
        .filter(LongformMemory.project_id == project_id)
        .group_by(LongformMemory.memory_type)
        .all()
    )
    return Counter({memory_type: count for memory_type, count in rows})


def _latest_longform_retrieval_documents(db: Session, project_id: str) -> dict[str, Any]:
    documents: dict[str, Any] = {}
    rows = (
        db.query(
            RetrievalDocument.id,
            RetrievalDocument.source_ref,
            RetrievalDocument.source_id,
            RetrievalDocument.updated_at,
        )
        .filter(
            RetrievalDocument.project_id == project_id,
            RetrievalDocument.source_type == "longform_memory",
        )
        .order_by(RetrievalDocument.updated_at.asc(), RetrievalDocument.id.asc())
        .all()
    )
    for document in rows:
        documents[document.source_ref] = document
    return documents


def _chapter_memory_ids(db: Session, project_id: str, chapter_indexes: list[int]) -> list[str]:
    if not chapter_indexes:
        return []
    scope_keys = [f"chapter:{chapter_index}" for chapter_index in chapter_indexes]
    rows = (
        db.query(LongformMemory.id)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == "chapter",
            LongformMemory.scope_key.in_(scope_keys),
        )
        .all()
    )
    return [row[0] for row in rows]


def _ordered_counts(counts: Counter) -> dict[str, int]:
    return {key: int(counts.get(key, 0)) for key in ["chapter", "arc", "volume", "global"] if counts.get(key, 0)}


def _preview(text: str, limit: int) -> str:
    cleaned = " ".join((text or "").split())
    return cleaned[:limit]


def _is_stale(target_updated_at: datetime | None, source_updated_at: datetime | None) -> bool:
    if target_updated_at is None:
        return source_updated_at is not None
    if source_updated_at is None:
        return False
    return target_updated_at < source_updated_at


def _max_datetime(left: datetime | None, right: datetime | None) -> datetime | None:
    if left is None:
        return right
    if right is None:
        return left
    return max(left, right)


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
    filters = [
        LongformMemory.project_id == project_id,
        LongformMemory.memory_type == "chapter",
        LongformMemory.end_chapter_index <= end_chapter_index,
    ]
    if start_chapter_index is not None:
        filters.append(LongformMemory.start_chapter_index >= start_chapter_index)
    word_count_expr = LongformMemory.memory_metadata["word_count"].as_integer()
    chapter_count, word_count, first_chapter, last_chapter = (
        db.query(
            func.count(LongformMemory.id),
            func.coalesce(func.sum(word_count_expr), 0),
            func.min(LongformMemory.start_chapter_index),
            func.max(LongformMemory.end_chapter_index),
        )
        .filter(*filters)
        .one()
    )
    chapter_count = int(chapter_count or 0)
    if chapter_count == 0:
        return []
    latest_rows = [
        {"title": row.title, "summary": row.summary}
        for row in (
            db.query(LongformMemory.title, LongformMemory.summary)
            .filter(*filters)
            .order_by(LongformMemory.start_chapter_index.desc(), LongformMemory.id.desc())
            .limit(5)
            .all()
        )
    ]
    recent_summaries = "；".join(
        reversed(
            [
                _format_recent_memory_summary(row["title"], row["summary"])
                for row in latest_rows
                if row["title"] or row["summary"]
            ]
        )
    )
    return [
        {
            "id": None,
            "memory_type": memory_type,
            "scope_key": f"{memory_type}:safe:{first_chapter}-{last_chapter}",
            "start_chapter_index": first_chapter,
            "end_chapter_index": last_chapter,
            "title": title,
            "summary": f"截至第{last_chapter}章，已纳入{chapter_count}章，约{int(word_count or 0)}字；近期记忆：{recent_summaries}",
            "metadata": {
                "chapter_count": chapter_count,
                "word_count": int(word_count or 0),
                "source": "safe_chapter_memory_rollup",
                "recent_memory_count": len(latest_rows),
            },
        }
    ]


def _format_recent_memory_summary(title: str | None, summary: str | None) -> str:
    cleaned_summary = _preview(summary or "", 80)
    if title and cleaned_summary:
        return f"{title}：{cleaned_summary}"
    return title or cleaned_summary


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

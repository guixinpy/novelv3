import json
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import ChapterContent, Outline

BACKFILLED_OUTLINE_PURPOSE = "根据已生成正文自动回填章节大纲。"
BACKFILLED_SUMMARY_CHARS = 180


def find_outline_chapter(db: Session, project_id: str, chapter_index: int) -> tuple[str, dict[str, Any]] | None:
    row = (
        db.execute(
            text(
                """
                SELECT outlines.id AS outline_id, chapter.value AS chapter_outline
                FROM outlines, json_each(outlines.chapters) AS chapter
                WHERE outlines.project_id = :project_id
                  AND CAST(json_extract(chapter.value, '$.chapter_index') AS INTEGER) = :chapter_index
                ORDER BY outlines.updated_at DESC
                LIMIT 1
                """
            ),
            {"project_id": project_id, "chapter_index": chapter_index},
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    chapter_outline = _decode_json_value(row["chapter_outline"])
    if not isinstance(chapter_outline, dict):
        return None
    return str(row["outline_id"]), chapter_outline


def outline_chapter_indexes(db: Session, project_id: str) -> set[int]:
    rows = (
        db.execute(
            text(
                """
                SELECT CAST(json_extract(chapter.value, '$.chapter_index') AS INTEGER) AS chapter_index
                FROM outlines, json_each(outlines.chapters) AS chapter
                WHERE outlines.id = (
                    SELECT id
                    FROM outlines
                    WHERE project_id = :project_id
                    ORDER BY updated_at DESC
                    LIMIT 1
                )
                """
            ),
            {"project_id": project_id},
        )
        .mappings()
        .all()
    )
    indexes: set[int] = set()
    for row in rows:
        try:
            indexes.add(int(row["chapter_index"]))
        except (TypeError, ValueError):
            continue
    return indexes


def generated_chapter_indexes(db: Session, project_id: str, *, before_chapter: int | None = None) -> list[int]:
    query = db.query(ChapterContent.chapter_index).filter(
        ChapterContent.project_id == project_id,
        ChapterContent.status == "generated",
        ChapterContent.content.isnot(None),
        ChapterContent.content != "",
    )
    if before_chapter is not None:
        query = query.filter(ChapterContent.chapter_index < before_chapter)
    rows = query.order_by(ChapterContent.chapter_index.asc()).all()
    return [int(row.chapter_index) for row in rows]


def generated_chapters_missing_outline(
    db: Session,
    project_id: str,
    *,
    before_chapter: int | None = None,
) -> list[int]:
    outline_indexes = outline_chapter_indexes(db, project_id)
    return [
        chapter_index
        for chapter_index in generated_chapter_indexes(db, project_id, before_chapter=before_chapter)
        if chapter_index not in outline_indexes
    ]


def backfill_missing_outline_chapters_from_content(
    db: Session,
    project_id: str,
    *,
    before_chapter: int | None = None,
) -> dict[str, Any]:
    outline = (
        db.query(Outline)
        .filter(Outline.project_id == project_id)
        .order_by(Outline.updated_at.desc(), Outline.id.desc())
        .first()
    )
    if outline is None:
        return {"status": "failed", "error": "Outline not generated yet"}

    missing_before = generated_chapters_missing_outline(db, project_id, before_chapter=before_chapter)
    if not missing_before:
        return {
            "status": "completed",
            "outline_id": outline.id,
            "backfilled_chapter_indexes": [],
            "missing_before": [],
        }

    chapters = (
        db.query(ChapterContent)
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.chapter_index.in_(missing_before),
            ChapterContent.status == "generated",
        )
        .order_by(ChapterContent.chapter_index.asc())
        .all()
    )
    existing = [dict(item) for item in (outline.chapters or []) if isinstance(item, dict)]
    existing_indexes = {
        int(item.get("chapter_index"))
        for item in existing
        if _safe_int(item.get("chapter_index")) is not None
    }
    backfilled_indexes: list[int] = []
    for chapter in chapters:
        chapter_index = int(chapter.chapter_index)
        if chapter_index in existing_indexes:
            continue
        existing.append(
            {
                "chapter_index": chapter_index,
                "title": chapter.title or f"第{chapter_index}章",
                "summary": _chapter_summary_from_content(chapter.content or ""),
                "scenes": [],
                "characters": [],
                "purpose": BACKFILLED_OUTLINE_PURPOSE,
            }
        )
        existing_indexes.add(chapter_index)
        backfilled_indexes.append(chapter_index)

    existing.sort(key=lambda item: _safe_int(item.get("chapter_index")) or 10**9)
    outline.chapters = existing
    db.add(outline)
    db.commit()
    db.refresh(outline)
    return {
        "status": "completed",
        "outline_id": outline.id,
        "backfilled_chapter_indexes": backfilled_indexes,
        "missing_before": missing_before,
    }


def _decode_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _chapter_summary_from_content(content: str) -> str:
    text = re.sub(r"\s+", " ", content).strip()
    if len(text) <= BACKFILLED_SUMMARY_CHARS:
        return text
    return text[:BACKFILLED_SUMMARY_CHARS].rstrip() + "..."


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

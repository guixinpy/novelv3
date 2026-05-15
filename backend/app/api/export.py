import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChapterContent, Project, Setup

router = APIRouter(prefix="/api/v1/projects/{project_id}", tags=["export"])

CHAPTER_SUMMARY_DEFAULT_LIMIT = 200
CHAPTER_SUMMARY_MAX_LIMIT = 500
EXPORT_CHAPTER_BATCH_SIZE = 50


class ExportRequest(BaseModel):
    format: str = "markdown"
    include_setup: bool = True
    include_outline: bool = True
    chapter_range: list[int] | None = None


@router.post("/export")
def export_project(project_id: str, payload: ExportRequest, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    media = "text/markdown" if payload.format == "markdown" else "text/plain"
    ext = "md" if payload.format == "markdown" else "txt"
    from urllib.parse import quote
    filename_encoded = quote(f"{project.name}.{ext}")

    return StreamingResponse(
        _iter_export_lines(db, project_id=project_id, project_name=project.name, payload=payload),
        media_type=media,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}"},
    )


def _iter_export_lines(
    db: Session,
    *,
    project_id: str,
    project_name: str,
    payload: ExportRequest,
) -> Iterator[str]:
    yield from _emit_export_line(f"# {project_name}\n", payload.format)

    if payload.include_setup:
        setup = db.query(Setup).filter(Setup.project_id == project_id).first()
        if setup:
            yield from _emit_export_line("## 设定\n", payload.format)
            if setup.characters:
                yield from _emit_export_line("### 角色\n", payload.format)
                for c in setup.characters:
                    yield from _emit_export_line(
                        f"- **{c.get('name', '未命名')}**：{c.get('description', '')}\n",
                        payload.format,
                    )
            if setup.world_building:
                yield from _emit_export_line(
                    f"### 世界观\n\n{json.dumps(setup.world_building, ensure_ascii=False, indent=2)}\n",
                    payload.format,
                )

    if payload.include_outline:
        outline_started = False
        for ch in _iter_outline_chapters(db, project_id=project_id):
            if not outline_started:
                yield from _emit_export_line("## 大纲\n", payload.format)
                outline_started = True
            ch_title = ch.get('title') or f"第{ch.get('chapter_index')}章"
            yield from _emit_export_line(f"### {ch_title}\n", payload.format)
            yield from _emit_export_line(f"{ch.get('summary', '')}\n", payload.format)

    has_chapters = False
    for ch in _iter_export_chapters(db, project_id=project_id, payload=payload):
        if not has_chapters:
            yield from _emit_export_line("## 正文\n", payload.format)
            has_chapters = True
        yield from _emit_export_line(f"### {ch.title or f'第{ch.chapter_index}章'}\n", payload.format)
        yield from _emit_export_line(f"{ch.content or ''}\n", payload.format)


def _iter_export_chapters(db: Session, *, project_id: str, payload: ExportRequest):
    chapters_query = db.query(ChapterContent).filter(ChapterContent.project_id == project_id)
    if payload.chapter_range and len(payload.chapter_range) >= 2:
        start, end = payload.chapter_range[:2]
        chapters_query = chapters_query.filter(
            ChapterContent.chapter_index >= start,
            ChapterContent.chapter_index <= end,
        )
    return (
        chapters_query.with_entities(
            ChapterContent.chapter_index,
            ChapterContent.title,
            ChapterContent.content,
        )
        .order_by(ChapterContent.chapter_index)
        .yield_per(EXPORT_CHAPTER_BATCH_SIZE)
    )


def _iter_outline_chapters(db: Session, *, project_id: str) -> Iterator[dict]:
    rows = (
        db.execute(
            text(
                """
                SELECT chapter.value AS value
                FROM outlines, json_each(outlines.chapters) AS chapter
                WHERE outlines.id = (
                    SELECT id
                    FROM outlines
                    WHERE project_id = :project_id
                    ORDER BY updated_at DESC
                    LIMIT 1
                )
                ORDER BY CAST(chapter.key AS INTEGER)
                """
            ),
            {"project_id": project_id},
        )
        .mappings()
        .yield_per(EXPORT_CHAPTER_BATCH_SIZE)
    )
    for row in rows:
        value = _decode_json_value(row["value"])
        if isinstance(value, dict):
            yield value


def _emit_export_line(line: str, export_format: str) -> Iterator[str]:
    yield _format_export_line(line, export_format)
    yield "\n"


def _format_export_line(line: str, export_format: str) -> str:
    if export_format != "txt":
        return line
    return line.replace("# ", "").replace("## ", "").replace("### ", "").replace("**", "").replace("- ", "")


def _decode_json_value(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


@router.get("/chapters")
def list_chapters(
    project_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(CHAPTER_SUMMARY_DEFAULT_LIMIT, ge=1, le=CHAPTER_SUMMARY_MAX_LIMIT),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    filters = [ChapterContent.project_id == project_id]
    total = db.query(func.count(ChapterContent.id)).filter(*filters).scalar() or 0
    latest_chapter_index = db.query(func.max(ChapterContent.chapter_index)).filter(*filters).scalar()
    chapters = (
        db.query(
            ChapterContent.id,
            ChapterContent.chapter_index,
            ChapterContent.title,
            ChapterContent.word_count,
            ChapterContent.status,
        )
        .filter(*filters)
        .order_by(ChapterContent.chapter_index)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(chapters) < total,
        "latest_chapter_index": latest_chapter_index,
        "chapters": [
            {
                "id": ch.id,
                "chapter_index": ch.chapter_index,
                "title": ch.title or f"第{ch.chapter_index}章",
                "word_count": ch.word_count or 0,
                "status": ch.status or "generated",
            }
            for ch in chapters
        ]
    }

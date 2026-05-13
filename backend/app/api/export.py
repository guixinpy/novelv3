import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChapterContent, Outline, Project, Setup

router = APIRouter(prefix="/api/v1/projects/{project_id}", tags=["export"])

CHAPTER_SUMMARY_DEFAULT_LIMIT = 200
CHAPTER_SUMMARY_MAX_LIMIT = 500


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

    lines = [f"# {project.name}\n"]

    if payload.include_setup:
        setup = db.query(Setup).filter(Setup.project_id == project_id).first()
        if setup:
            lines.append("## 设定\n")
            if setup.characters:
                lines.append("### 角色\n")
                for c in setup.characters:
                    lines.append(f"- **{c.get('name', '未命名')}**：{c.get('description', '')}\n")
            if setup.world_building:
                lines.append(f"### 世界观\n\n{json.dumps(setup.world_building, ensure_ascii=False, indent=2)}\n")

    if payload.include_outline:
        outline = db.query(Outline).filter(Outline.project_id == project_id).first()
        if outline and outline.chapters:
            lines.append("## 大纲\n")
            for ch in outline.chapters:
                ch_title = ch.get('title') or f"第{ch.get('chapter_index')}章"
                lines.append(f"### {ch_title}\n")
                lines.append(f"{ch.get('summary', '')}\n")

    chapters_query = db.query(ChapterContent).filter(ChapterContent.project_id == project_id)
    if payload.chapter_range and len(payload.chapter_range) >= 2:
        start, end = payload.chapter_range[:2]
        chapters_query = chapters_query.filter(
            ChapterContent.chapter_index >= start,
            ChapterContent.chapter_index <= end,
        )
    chapters = chapters_query.order_by(ChapterContent.chapter_index).all()

    if chapters:
        lines.append("## 正文\n")
        for ch in chapters:
            lines.append(f"### {ch.title or f'第{ch.chapter_index}章'}\n")
            lines.append(f"{ch.content or ''}\n")

    text = "\n".join(lines)

    if payload.format == "txt":
        text = text.replace("# ", "").replace("## ", "").replace("### ", "").replace("**", "").replace("- ", "")

    media = "text/markdown" if payload.format == "markdown" else "text/plain"
    ext = "md" if payload.format == "markdown" else "txt"
    from urllib.parse import quote
    filename_encoded = quote(f"{project.name}.{ext}")

    return PlainTextResponse(
        content=text,
        media_type=media,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}"},
    )


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

    query = db.query(ChapterContent).filter(
        ChapterContent.project_id == project_id,
    )
    total = query.count()
    latest_chapter_index = query.with_entities(func.max(ChapterContent.chapter_index)).scalar()
    chapters = query.order_by(ChapterContent.chapter_index).offset(offset).limit(limit).all()

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

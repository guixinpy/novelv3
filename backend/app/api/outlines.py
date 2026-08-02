"""大纲 CRUD API（v1 绞杀：generate/expand-window 端点已删除，保留读取与章节修订）。"""
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deprecation import add_deprecation_header
from domain.memory.narrative_plan_window import get_evolution_plan_window
from app.db import get_db
from app.models import Outline
from app.schemas import OutlineOut

router = APIRouter(prefix="/api/v1/projects/{project_id}/outline", tags=["outlines"])


@router.get("", response_model=OutlineOut)
def get_outline(
    project_id: str,
    mode: str = Query("window", pattern="^(full|window)$"),
    chapter_offset: int = Query(0, ge=0),
    chapter_limit: int = Query(100, ge=1, le=500),
    plotline_offset: int = Query(0, ge=0),
    plotline_limit: int = Query(20, ge=1, le=500),
    foreshadowing_offset: int = Query(0, ge=0),
    foreshadowing_limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    response: Response = None,
):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/plan")
    if mode == "window":
        outline = get_evolution_plan_window(
            db=db,
            project_id=project_id,
            chapter_offset=chapter_offset,
            chapter_limit=chapter_limit,
            plotline_offset=plotline_offset,
            plotline_limit=plotline_limit,
            foreshadowing_offset=foreshadowing_offset,
            foreshadowing_limit=foreshadowing_limit,
        )["outline"]
        if not outline:
            raise HTTPException(status_code=404, detail="Outline not found")
        return outline
    outline = db.query(Outline).filter(Outline.project_id == project_id).first()
    if not outline:
        raise HTTPException(status_code=404, detail="Outline not found")
    return outline


class ChapterOutlineUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    scenes: list[str] | None = None
    characters: list[str] | None = None
    purpose: str | None = None


@router.patch("/chapters/{chapter_index}")
def update_chapter_outline(
    project_id: str,
    chapter_index: int = Path(..., ge=1),
    payload: ChapterOutlineUpdate = Body(...),
    db: Session = Depends(get_db),
    response: Response = None,
):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/plan/outline/chapters/{chapter_index}")
    outline_id = db.query(Outline.id).filter(Outline.project_id == project_id).scalar()
    if not outline_id:
        raise HTTPException(status_code=404, detail="Outline not found")

    chapter_key = db.execute(
        text(
            """
            SELECT item.key AS chapter_key
            FROM outlines, json_each(outlines.chapters) AS item
            WHERE outlines.id = :outline_id
            AND CAST(json_extract(item.value, '$.chapter_index') AS INTEGER) = :chapter_index
            LIMIT 1
            """
        ),
        {"outline_id": outline_id, "chapter_index": chapter_index},
    ).scalar()
    if chapter_key is None:
        raise HTTPException(status_code=404, detail="Chapter not found in outline")

    params = {
        "outline_id": outline_id,
        "chapter_key": str(chapter_key),
        "updated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" "),
    }
    updates: list[str] = []
    for field in ("title", "summary", "purpose"):
        value = getattr(payload, field)
        if value is not None:
            params[field] = value
            updates.extend([f"'$[' || :chapter_key || '].{field}'", f":{field}"])
    for field in ("scenes", "characters"):
        value = getattr(payload, field)
        if value is not None:
            param_name = f"{field}_json"
            params[param_name] = json.dumps(value, ensure_ascii=False)
            updates.extend([f"'$[' || :chapter_key || '].{field}'", f"json(:{param_name})"])

    if updates:
        db.execute(
            text(
                f"""
                UPDATE outlines
                SET chapters = json_set(chapters, {', '.join(updates)}),
                    updated_at = :updated_at
                WHERE id = :outline_id
                """
            ),
            params,
        )
    db.commit()
    return {"updated": True, "chapter_index": chapter_index}

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models import Outline, Storyline


def get_evolution_plan_window(
    *,
    db: Session,
    project_id: str,
    chapter_offset: int = 0,
    chapter_limit: int = 100,
    plotline_offset: int = 0,
    plotline_limit: int = 20,
    milestone_offset: int = 0,
    milestone_limit: int = 80,
    foreshadowing_offset: int = 0,
    foreshadowing_limit: int = 100,
) -> dict[str, Any]:
    outline = (
        db.query(
            Outline.id,
            Outline.project_id,
            Outline.status,
            Outline.total_chapters,
            Outline.created_at,
            Outline.updated_at,
            func.coalesce(func.json_array_length(Outline.chapters), 0).label("chapters_total"),
            func.coalesce(func.json_array_length(Outline.plotlines), 0).label("plotlines_total"),
            func.coalesce(func.json_array_length(Outline.foreshadowing), 0).label("foreshadowing_total"),
        )
        .filter(Outline.project_id == project_id)
        .order_by(Outline.updated_at.desc())
        .first()
    )
    storyline = (
        db.query(
            Storyline.id,
            Storyline.project_id,
            Storyline.status,
            Storyline.created_at,
            Storyline.updated_at,
            func.coalesce(func.json_array_length(Storyline.plotlines), 0).label("plotlines_total"),
            func.coalesce(func.json_array_length(Storyline.foreshadowing), 0).label("foreshadowing_total"),
        )
        .filter(Storyline.project_id == project_id)
        .order_by(Storyline.updated_at.desc())
        .first()
    )
    return {
        "outline": _windowed_outline(
            db=db,
            outline=outline,
            chapter_offset=chapter_offset,
            chapter_limit=chapter_limit,
            plotline_offset=plotline_offset,
            plotline_limit=plotline_limit,
            foreshadowing_offset=foreshadowing_offset,
            foreshadowing_limit=foreshadowing_limit,
        ),
        "storyline": _windowed_storyline(
            db=db,
            storyline=storyline,
            plotline_offset=plotline_offset,
            plotline_limit=plotline_limit,
            milestone_offset=milestone_offset,
            milestone_limit=milestone_limit,
            foreshadowing_offset=foreshadowing_offset,
            foreshadowing_limit=foreshadowing_limit,
        ),
    }


def _windowed_outline(
    *,
    db: Session,
    outline: Any,
    chapter_offset: int,
    chapter_limit: int,
    plotline_offset: int,
    plotline_limit: int,
    foreshadowing_offset: int,
    foreshadowing_limit: int,
) -> dict[str, Any] | None:
    if outline is None:
        return None
    chapters_total = int(outline.chapters_total or 0)
    plotlines_total = int(outline.plotlines_total or 0)
    foreshadowing_total = int(outline.foreshadowing_total or 0)
    chapters = _json_array_window(db, "outlines", "chapters", outline.id, chapter_offset, chapter_limit)
    plotlines = _json_array_window(db, "outlines", "plotlines", outline.id, plotline_offset, plotline_limit)
    foreshadowing = _json_array_window(
        db,
        "outlines",
        "foreshadowing",
        outline.id,
        foreshadowing_offset,
        foreshadowing_limit,
    )
    return {
        "id": outline.id,
        "project_id": outline.project_id,
        "status": outline.status,
        "total_chapters": outline.total_chapters,
        "created_at": outline.created_at,
        "updated_at": outline.updated_at,
        "chapters": chapters,
        "plotlines": plotlines,
        "foreshadowing": foreshadowing,
        "chapters_total": chapters_total,
        "chapters_offset": chapter_offset,
        "chapters_limit": chapter_limit,
        "chapters_has_more": chapter_offset + len(chapters) < chapters_total,
        "plotlines_total": plotlines_total,
        "plotlines_offset": plotline_offset,
        "plotlines_limit": plotline_limit,
        "plotlines_has_more": plotline_offset + len(plotlines) < plotlines_total,
        "foreshadowing_total": foreshadowing_total,
        "foreshadowing_offset": foreshadowing_offset,
        "foreshadowing_limit": foreshadowing_limit,
        "foreshadowing_has_more": foreshadowing_offset + len(foreshadowing) < foreshadowing_total,
    }


def _windowed_storyline(
    *,
    db: Session,
    storyline: Any,
    plotline_offset: int,
    plotline_limit: int,
    milestone_offset: int,
    milestone_limit: int,
    foreshadowing_offset: int,
    foreshadowing_limit: int,
) -> dict[str, Any] | None:
    if storyline is None:
        return None
    plotlines_total = int(storyline.plotlines_total or 0)
    foreshadowing_total = int(storyline.foreshadowing_total or 0)
    plotlines = _json_array_window(db, "storylines", "plotlines", storyline.id, plotline_offset, plotline_limit)
    plotlines = _window_plotline_milestones(plotlines, milestone_offset, milestone_limit)
    foreshadowing = _json_array_window(
        db,
        "storylines",
        "foreshadowing",
        storyline.id,
        foreshadowing_offset,
        foreshadowing_limit,
    )
    return {
        "id": storyline.id,
        "project_id": storyline.project_id,
        "status": storyline.status,
        "created_at": storyline.created_at,
        "updated_at": storyline.updated_at,
        "plotlines": plotlines,
        "foreshadowing": foreshadowing,
        "plotlines_total": plotlines_total,
        "plotlines_offset": plotline_offset,
        "plotlines_limit": plotline_limit,
        "plotlines_has_more": plotline_offset + len(plotlines) < plotlines_total,
        "foreshadowing_total": foreshadowing_total,
        "foreshadowing_offset": foreshadowing_offset,
        "foreshadowing_limit": foreshadowing_limit,
        "foreshadowing_has_more": foreshadowing_offset + len(foreshadowing) < foreshadowing_total,
    }


def _window_plotline_milestones(plotlines: list[Any], offset: int, limit: int) -> list[Any]:
    windowed: list[Any] = []
    for plotline in plotlines:
        if not isinstance(plotline, dict):
            windowed.append(plotline)
            continue
        milestones = plotline.get("milestones")
        if not isinstance(milestones, list):
            windowed.append(plotline)
            continue
        total = len(milestones)
        next_plotline = dict(plotline)
        next_plotline["milestones"] = milestones[offset:offset + limit]
        next_plotline["milestones_total"] = total
        next_plotline["milestones_offset"] = offset
        next_plotline["milestones_limit"] = limit
        next_plotline["milestones_has_more"] = offset + len(next_plotline["milestones"]) < total
        windowed.append(next_plotline)
    return windowed


def _json_array_window(
    db: Session,
    table_name: str,
    column_name: str,
    row_id: str,
    offset: int,
    limit: int,
) -> list[Any]:
    rows = (
        db.execute(
            text(
                f"""
                SELECT item.value AS value
                FROM {table_name}, json_each({table_name}.{column_name}) AS item
                WHERE {table_name}.id = :row_id
                ORDER BY CAST(item.key AS INTEGER)
                LIMIT :limit OFFSET :offset
                """
            ),
            {"row_id": row_id, "limit": limit, "offset": offset},
        )
        .mappings()
        .all()
    )
    return [_decode_json_value(row["value"]) for row in rows]


def _decode_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value

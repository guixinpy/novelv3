from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


async def expand_outline_window_tool(
    db: Session,
    project_id: str,
    *,
    start_chapter: int,
    end_chapter: int,
    command_args: str | None = None,
) -> dict[str, Any]:
    from app.api import outlines as outline_api

    outline = await outline_api.expand_outline_window(
        project_id,
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        db=db,
        command_args=command_args,
    )
    merge = getattr(outline, "outline_expansion_result", {}) or {}
    return {
        "status": "completed",
        "start_chapter": start_chapter,
        "end_chapter": end_chapter,
        "outline_id": outline.id,
        "total_chapters": outline.total_chapters,
        "added_chapter_count": int(merge.get("added_chapter_count") or 0),
        "merge": merge,
        "trace_id": getattr(outline, "last_expansion_trace_id", None),
        "should_generate_next_chapter": False,
        "recommended_next_tools": ["preflight_writing"],
    }

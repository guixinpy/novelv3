from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.chapter_expansion import expand_chapter_to_target


async def expand_chapter_to_target_tool(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    min_word_count: int | None = None,
    extra_instruction: str = "",
) -> dict[str, Any]:
    return await expand_chapter_to_target(
        db,
        project_id,
        chapter_index,
        min_word_count=min_word_count,
        extra_instruction=extra_instruction,
    )

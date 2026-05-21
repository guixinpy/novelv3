from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.chapter_compression import compress_chapter_to_target


async def compress_chapter_to_target_tool(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    target_max_word_count: int | None = None,
    extra_instruction: str = "",
    forbidden_terms: list[str] | None = None,
) -> dict[str, Any]:
    return await compress_chapter_to_target(
        db,
        project_id,
        chapter_index,
        target_max_word_count=target_max_word_count,
        extra_instruction=extra_instruction,
        forbidden_terms=forbidden_terms or [],
    )

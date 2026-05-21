from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.chapter_revision_apply import apply_planner_revision_patch


def apply_planner_revision_patch_tool(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    revision_id: str | None = None,
) -> dict[str, Any]:
    return apply_planner_revision_patch(db, project_id, chapter_index, revision_id=revision_id)

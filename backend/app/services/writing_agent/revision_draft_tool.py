from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.chapter_revision_drafts import create_revision_draft_from_plan
from app.core.chapter_revision_planner import plan_chapter_revision


def create_revision_draft_tool(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
) -> dict[str, Any]:
    plan = plan_chapter_revision(db, project_id, chapter_index)
    return create_revision_draft_from_plan(db, project_id, chapter_index, plan)

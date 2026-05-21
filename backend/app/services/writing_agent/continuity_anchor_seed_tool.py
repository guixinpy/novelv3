from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.continuity_anchor_proposals import seed_continuity_anchor_proposals


def seed_continuity_anchor_proposals_tool(db: Session, project_id: str) -> dict[str, Any]:
    return seed_continuity_anchor_proposals(db, project_id)

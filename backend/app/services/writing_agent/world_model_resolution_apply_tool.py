from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def apply_world_model_proposal_resolution_tool(
    db: Session,
    project_id: str,
    *,
    decisions: object,
    confirm_apply: bool,
) -> dict[str, Any]:
    from app.core.world_proposal_resolution_apply import apply_world_model_proposal_resolution

    return apply_world_model_proposal_resolution(
        db,
        project_id,
        decisions if isinstance(decisions, list) else [],
        confirm_apply=confirm_apply,
    )


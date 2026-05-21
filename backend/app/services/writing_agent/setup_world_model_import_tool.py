from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.athena_longform import import_setup_to_world_model


def import_setup_world_model_tool(db: Session, project_id: str) -> dict[str, Any]:
    result = import_setup_to_world_model(db=db, project_id=project_id)
    return {
        **result,
        "should_generate_next_chapter": False,
        "recommended_next_tools": ["preflight_writing", "inspect_agent_world_model_route"],
    }

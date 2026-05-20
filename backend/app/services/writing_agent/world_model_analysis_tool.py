from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import WritingAgentStep

CHAPTER_TOOL_NAME = "generate_chapter"
STEP_SUCCESS = "success"


def analyze_chapter_world_model_tool(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    run_id: str | None = None,
) -> dict[str, Any]:
    existing_analysis = _same_run_completed_chapter_analysis(
        db,
        run_id=run_id,
        project_id=project_id,
        chapter_index=chapter_index,
    )
    if existing_analysis is not None:
        analysis = existing_analysis["analysis"]
        return {
            "status": "skipped",
            "reason": "chapter_already_analyzed_in_run",
            "chapter_index": chapter_index,
            "source_step_id": existing_analysis["source_step_id"],
            "proposal_bundle_id": analysis.get("proposal_bundle_id"),
            "created": analysis.get("created", {"proposal_items": 0}),
            "updated": analysis.get("updated", {"proposal_items": 0}),
        }

    from app.core.athena_longform import analyze_chapter_to_world_proposals

    return analyze_chapter_to_world_proposals(db=db, project_id=project_id, chapter_index=chapter_index)


def _same_run_completed_chapter_analysis(
    db: Session,
    *,
    run_id: str | None,
    project_id: str,
    chapter_index: int,
) -> dict[str, Any] | None:
    if not run_id:
        return None
    steps = (
        db.query(WritingAgentStep)
        .filter(
            WritingAgentStep.run_id == run_id,
            WritingAgentStep.project_id == project_id,
            WritingAgentStep.tool_name == CHAPTER_TOOL_NAME,
            WritingAgentStep.status == STEP_SUCCESS,
            WritingAgentStep.chapter_index == chapter_index,
        )
        .order_by(WritingAgentStep.step_index.desc(), WritingAgentStep.id.desc())
        .all()
    )
    for step in steps:
        output = step.output if isinstance(step.output, dict) else {}
        analysis = output.get("athena_analysis")
        if isinstance(analysis, dict) and analysis.get("status") == "completed":
            return {"source_step_id": step.id, "analysis": analysis}
    return None


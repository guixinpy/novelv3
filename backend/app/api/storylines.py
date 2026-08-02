from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api.deprecation import add_deprecation_header
from domain.memory.narrative_plan_window import get_evolution_plan_window
from app.db import get_db
from app.models import Storyline
from app.schemas import StorylineOut

router = APIRouter(prefix="/api/v1/projects/{project_id}/storyline", tags=["storylines"])


@router.get("", response_model=StorylineOut)
def get_storyline(
    project_id: str,
    mode: str = Query("window", pattern="^(full|window)$"),
    plotline_offset: int = Query(0, ge=0),
    plotline_limit: int = Query(20, ge=1, le=500),
    milestone_offset: int = Query(0, ge=0),
    milestone_limit: int = Query(80, ge=1, le=500),
    foreshadowing_offset: int = Query(0, ge=0),
    foreshadowing_limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    response: Response = None,
):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/plan")
    if mode == "window":
        storyline = get_evolution_plan_window(
            db=db,
            project_id=project_id,
            plotline_offset=plotline_offset,
            plotline_limit=plotline_limit,
            milestone_offset=milestone_offset,
            milestone_limit=milestone_limit,
            foreshadowing_offset=foreshadowing_offset,
            foreshadowing_limit=foreshadowing_limit,
        )["storyline"]
        if not storyline:
            raise HTTPException(status_code=404, detail="Storyline not found")
        return storyline
    storyline = db.query(Storyline).filter(Storyline.project_id == project_id).first()
    if not storyline:
        raise HTTPException(status_code=404, detail="Storyline not found")
    return storyline

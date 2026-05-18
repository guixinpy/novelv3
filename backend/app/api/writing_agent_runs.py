from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.writing_agent import (
    PaginatedWritingAgentRuns,
    WritingAgentRunCreate,
    WritingAgentRunDetail,
    WritingAgentRunListItem,
)
from app.services.writing_agent.run_service import WritingAgentRunService, detail_payload

router = APIRouter(prefix="/api/v1/projects/{project_id}/agent-runs", tags=["writing-agent"])


@router.post("", response_model=WritingAgentRunDetail)
async def create_agent_run(project_id: str, payload: WritingAgentRunCreate, db: Session = Depends(get_db)):
    service = WritingAgentRunService(db)
    run = service.create_run(project_id, payload)
    await service.execute_run(run.id, payload.tools)
    return detail_payload(service.get_run_detail(project_id, run.id))


@router.get("", response_model=PaginatedWritingAgentRuns)
def list_agent_runs(
    project_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return WritingAgentRunService(db).list_runs(project_id, offset=offset, limit=limit)


@router.get("/{run_id}", response_model=WritingAgentRunDetail)
def get_agent_run(project_id: str, run_id: str, db: Session = Depends(get_db)):
    return detail_payload(WritingAgentRunService(db).get_run_detail(project_id, run_id))


@router.post("/{run_id}/cancel", response_model=WritingAgentRunListItem)
def cancel_agent_run(project_id: str, run_id: str, db: Session = Depends(get_db)):
    return WritingAgentRunService(db).cancel_run(project_id, run_id)

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AIModelCallTrace, Project
from app.schemas.model_call_trace import ModelCallTraceDetail, PaginatedModelCallTraces

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/model-call-traces",
    tags=["model-call-traces"],
)

TRACE_LIST_COLUMNS = (
    AIModelCallTrace.id,
    AIModelCallTrace.project_id,
    AIModelCallTrace.trace_type,
    AIModelCallTrace.status,
    AIModelCallTrace.model,
    AIModelCallTrace.prompt_tokens,
    AIModelCallTrace.completion_tokens,
    AIModelCallTrace.latency_ms,
    AIModelCallTrace.error_message,
    AIModelCallTrace.dialog_id,
    AIModelCallTrace.request_message_id,
    AIModelCallTrace.response_message_id,
    AIModelCallTrace.chapter_id,
    AIModelCallTrace.chapter_index,
    AIModelCallTrace.created_at,
    AIModelCallTrace.updated_at,
)


def _require_project(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("", response_model=PaginatedModelCallTraces)
def list_model_call_traces(
    project_id: str,
    trace_type: str | None = None,
    chapter_index: int | None = None,
    dialog_id: str | None = None,
    limit: int = Query(default=30),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    _require_project(db, project_id)
    clamped_limit = min(max(limit, 1), 100)

    query = db.query(AIModelCallTrace).filter(AIModelCallTrace.project_id == project_id)
    if trace_type:
        query = query.filter(AIModelCallTrace.trace_type == trace_type)
    if chapter_index is not None:
        query = query.filter(AIModelCallTrace.chapter_index == chapter_index)
    if dialog_id:
        query = query.filter(AIModelCallTrace.dialog_id == dialog_id)

    total = query.with_entities(func.count(AIModelCallTrace.id)).order_by(None).scalar() or 0
    rows = (
        query.with_entities(*TRACE_LIST_COLUMNS)
        .order_by(AIModelCallTrace.created_at.desc(), AIModelCallTrace.id.desc())
        .offset(offset)
        .limit(clamped_limit)
        .all()
    )
    items = [dict(row._mapping) for row in rows]
    return PaginatedModelCallTraces(total=total, items=items)


@router.get("/{trace_id}", response_model=ModelCallTraceDetail)
def get_model_call_trace(
    project_id: str,
    trace_id: str,
    db: Session = Depends(get_db),
):
    _require_project(db, project_id)
    trace = (
        db.query(AIModelCallTrace)
        .filter(
            AIModelCallTrace.project_id == project_id,
            AIModelCallTrace.id == trace_id,
        )
        .first()
    )
    if not trace:
        raise HTTPException(status_code=404, detail="Model call trace not found")
    return trace

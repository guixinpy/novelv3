from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.athena_retrieval import (
    get_retrieval_diagnostics,
    index_chapter_retrieval,
    reindex_project_retrieval,
    search_retrieval,
)
from app.db import get_db
from app.schemas.athena_retrieval import (
    AthenaRetrievalDiagnostics,
    AthenaRetrievalIndexResult,
    AthenaRetrievalSearchResponse,
)

router = APIRouter()


@router.post("/retrieval/reindex", response_model=AthenaRetrievalIndexResult)
def reindex_athena_retrieval(project_id: str, db: Session = Depends(get_db)):
    return reindex_project_retrieval(db=db, project_id=project_id)


@router.post("/retrieval/chapters/{chapter_index}/index", response_model=AthenaRetrievalIndexResult)
def index_athena_retrieval_chapter(project_id: str, chapter_index: int = Path(..., ge=1), db: Session = Depends(get_db)):
    return index_chapter_retrieval(db=db, project_id=project_id, chapter_index=chapter_index)


@router.get("/retrieval/search", response_model=AthenaRetrievalSearchResponse)
def search_athena_retrieval(
    project_id: str,
    q: str = Query(..., min_length=1),
    limit: int = Query(8, ge=1, le=30),
    source_type: str | None = None,
    chapter_index: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    return search_retrieval(
        db=db,
        project_id=project_id,
        query=q,
        limit=limit,
        source_type=source_type,
        max_chapter_index=chapter_index,
    )


@router.get("/retrieval/diagnostics", response_model=AthenaRetrievalDiagnostics)
def get_athena_retrieval_diagnostics(project_id: str, db: Session = Depends(get_db)):
    return get_retrieval_diagnostics(db=db, project_id=project_id)

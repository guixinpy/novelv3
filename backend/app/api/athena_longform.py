from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.longform_memory import (
    build_longform_context_package,
    get_longform_memory_diagnostics,
    rebuild_longform_memory,
)
from app.db import get_db
from app.schemas.longform_memory import (
    LongformContextPackage,
    LongformMemoryDiagnostics,
    LongformMemoryRebuildResult,
)

router = APIRouter()


@router.post("/longform/memory/rebuild", response_model=LongformMemoryRebuildResult)
def rebuild_athena_longform_memory(
    project_id: str,
    arc_size: int = Query(20, ge=1, le=100),
    volume_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return rebuild_longform_memory(
        db=db,
        project_id=project_id,
        arc_size=arc_size,
        volume_size=volume_size,
    )


@router.get("/longform/memory/diagnostics", response_model=LongformMemoryDiagnostics)
def get_athena_longform_memory_diagnostics(project_id: str, db: Session = Depends(get_db)):
    return get_longform_memory_diagnostics(db=db, project_id=project_id)


@router.get("/longform/context/chapters/{chapter_index}", response_model=LongformContextPackage)
def get_athena_longform_context(
    project_id: str,
    chapter_index: int,
    q: str | None = Query(None, min_length=1),
    db: Session = Depends(get_db),
):
    return build_longform_context_package(
        db=db,
        project_id=project_id,
        chapter_index=chapter_index,
        user_query=q,
    )

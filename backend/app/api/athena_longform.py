from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.longform_memory import (
    build_longform_context_package,
    get_longform_maintenance_diagnostics,
    get_longform_memory_diagnostics,
    rebuild_longform_memory,
    repair_longform_maintenance,
)
from app.db import get_db
from app.schemas.longform_memory import (
    LongformContextPackage,
    LongformMaintenanceDiagnostics,
    LongformMaintenanceRepairResult,
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


@router.get("/longform/maintenance/diagnostics", response_model=LongformMaintenanceDiagnostics)
def get_athena_longform_maintenance_diagnostics(
    project_id: str,
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return get_longform_maintenance_diagnostics(db=db, project_id=project_id, limit=limit)


@router.post("/longform/maintenance/repair", response_model=LongformMaintenanceRepairResult)
def repair_athena_longform_maintenance(
    project_id: str,
    limit: int = Query(20, ge=1, le=200),
    repair_limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return repair_longform_maintenance(db=db, project_id=project_id, limit=limit, repair_limit=repair_limit)


@router.get("/longform/context/chapters/{chapter_index}", response_model=LongformContextPackage)
def get_athena_longform_context(
    project_id: str,
    chapter_index: int = Path(..., ge=1),
    q: str | None = Query(None, min_length=1),
    db: Session = Depends(get_db),
):
    return build_longform_context_package(
        db=db,
        project_id=project_id,
        chapter_index=chapter_index,
        user_query=q,
    )

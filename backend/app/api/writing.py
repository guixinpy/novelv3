from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.core.chapter_target import chapter_index_exceeds_target, effective_chapter_target
from app.core.writing_scheduler import WritingScheduler
from app.db import get_db
from app.models import AIModelCallTrace, BackgroundTask, Project
from app.schemas import WritingControlOut, WritingStateOut
from app.services.tasks.background_task_service import ACTIVE_TASK_STATUSES, BackgroundTaskService
from app.services.tasks.local_task_runner import LocalTaskRunner
from app.services.writing.writing_state_service import WritingStateService

router = APIRouter(prefix="/api/v1/projects/{project_id}/writing", tags=["writing"])
scheduler = WritingScheduler()
GENERATION_DIAGNOSTIC_INDEX_LIMIT = 200
GENERATION_DIAGNOSTIC_WARNING_LIMIT = 50


@router.post("/start", response_model=WritingControlOut, response_model_exclude_none=True)
async def start_writing(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    state = scheduler.start(project_id, db)
    if chapter_index_exceeds_target(db, project, state.current_chapter):
        return WritingStateService(db).finish_project(project_id)
    task = _queue_generate_chapter_task(db, project_id, state.current_chapter)
    return _control_out(state, task)


@router.post("/pause", response_model=WritingStateOut, response_model_exclude_none=True)
def pause_writing(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return scheduler.pause(project_id, db)


@router.post("/resume", response_model=WritingControlOut, response_model_exclude_none=True)
async def resume_writing(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    state = scheduler.resume(project_id, db)
    if state.status == "running":
        if chapter_index_exceeds_target(db, project, state.current_chapter):
            return WritingStateService(db).finish_project(project_id)
        task = _queue_generate_chapter_task(db, project_id, state.current_chapter)
        return _control_out(state, task)
    return state


@router.get("/state", response_model=WritingStateOut, response_model_exclude_none=True)
def get_writing_state(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return scheduler.state(project_id, db)


def build_retry_chapter_work(project_id: str, chapter_index: int):
    async def _regen(rdb: Session, running_task: BackgroundTask):
        from app.api.chapters import generate_chapter as _gen_chapter

        try:
            chapter = await _gen_chapter(project_id, chapter_index, rdb)
        except Exception as exc:
            WritingStateService(rdb).mark_error(project_id, str(exc))
            raise

        WritingStateService(rdb).complete_chapter(project_id, chapter_index)
        generated_index = chapter.get("chapter_index") if isinstance(chapter, dict) else chapter.chapter_index
        return {"chapter_index": generated_index}

    return _regen


def build_generate_chapter_work(project_id: str, chapter_index: int):
    async def _generate(rdb: Session, running_task: BackgroundTask):
        from app.api.chapters import generate_chapter as _gen_chapter

        progress_service = BackgroundTaskService(rdb)
        chapter_range = (running_task.payload or {}).get("chapter_range")
        if isinstance(chapter_range, dict):
            start = int(chapter_range.get("start") or chapter_index)
            end = int(chapter_range.get("end") or chapter_index)
            chapter_indexes = range(start, end + 1)
        else:
            chapter_indexes = range(chapter_index, chapter_index + 1)

        generated_index = chapter_index
        try:
            for next_chapter_index in chapter_indexes:
                current_state = WritingStateService(rdb).state(project_id, include_task_id=False)
                if current_state.status in {"paused", "failed", "completed"}:
                    break

                WritingStateService(rdb).run_chapter(project_id, next_chapter_index, include_task_id=False)
                chapter = await _gen_chapter(project_id, next_chapter_index, rdb)
                generated_index = chapter.get("chapter_index") if isinstance(chapter, dict) else chapter.chapter_index

                if isinstance(chapter_range, dict):
                    progress_service.mark_range_progress(running_task.id, completed_chapter_index=int(generated_index))
                _record_generation_diagnostics(
                    rdb,
                    task_id=running_task.id,
                    project_id=project_id,
                    chapter=chapter,
                )
        except Exception as exc:
            WritingStateService(rdb).mark_error(project_id, str(exc))
            raise

        result = dict(progress_service.get(running_task.id).result or {})
        result["chapter_index"] = generated_index
        return result

    return _generate


def _record_generation_diagnostics(
    db: Session,
    *,
    task_id: str,
    project_id: str,
    chapter,
) -> None:
    chapter_index = _generated_chapter_index(chapter)
    trace_id = _generated_chapter_trace_id(chapter)
    if chapter_index is None or not trace_id:
        return
    trace_metadata = _generation_trace_metadata(db, project_id=project_id, trace_id=trace_id)
    if not trace_metadata:
        return

    task = BackgroundTaskService(db).get(task_id)
    result = dict(task.result or {})
    diagnostics = _update_generation_diagnostics(
        dict(result.get("generation_diagnostics") or {}),
        chapter_index=chapter_index,
        trace_metadata=trace_metadata,
    )
    result["generation_diagnostics"] = diagnostics
    result["generation_diagnostic_recommendations"] = _generation_diagnostic_recommendations(diagnostics)
    task.result = result
    db.commit()


def _generated_chapter_index(chapter) -> int | None:
    value = chapter.get("chapter_index") if isinstance(chapter, dict) else getattr(chapter, "chapter_index", None)
    if value is None:
        return None
    return int(value)


def _generated_chapter_trace_id(chapter) -> str | None:
    value = (
        chapter.get("last_generation_trace_id")
        if isinstance(chapter, dict)
        else getattr(chapter, "last_generation_trace_id", None)
    )
    return str(value) if value else None


def _generation_trace_metadata(db: Session, *, project_id: str, trace_id: str) -> dict:
    row = (
        db.query(AIModelCallTrace.trace_metadata)
        .filter(AIModelCallTrace.project_id == project_id, AIModelCallTrace.id == trace_id)
        .first()
    )
    metadata = row[0] if row else None
    return metadata if isinstance(metadata, dict) else {}


def _update_generation_diagnostics(diagnostics: dict, *, chapter_index: int, trace_metadata: dict) -> dict:
    next_diagnostics = {
        "word_target": _update_generation_word_target_diagnostics(
            dict(diagnostics.get("word_target") or {}),
            chapter_index=chapter_index,
            trace_metadata=trace_metadata,
        ),
        "post_generation_warning_count": int(diagnostics.get("post_generation_warning_count") or 0),
        "post_generation_warnings": list(diagnostics.get("post_generation_warnings") or []),
    }
    warnings = trace_metadata.get("post_generation_warnings")
    if isinstance(warnings, list):
        for warning in warnings:
            if not isinstance(warning, dict):
                continue
            next_diagnostics["post_generation_warning_count"] += 1
            if len(next_diagnostics["post_generation_warnings"]) >= GENERATION_DIAGNOSTIC_WARNING_LIMIT:
                continue
            next_diagnostics["post_generation_warnings"].append(
                {
                    "chapter_index": chapter_index,
                    "stage": str(warning.get("stage") or "unknown"),
                    "error_type": str(warning.get("error_type") or "Error"),
                    "message": str(warning.get("message") or ""),
                }
            )
    return next_diagnostics


def _generation_diagnostic_recommendations(diagnostics: dict) -> list[dict]:
    recommendations: list[dict] = []
    word_target = diagnostics.get("word_target") if isinstance(diagnostics.get("word_target"), dict) else {}

    under_count = int(word_target.get("under_count") or 0)
    if under_count > 0:
        recommendations.append(
            {
                "kind": "word_target_under",
                "severity": "warning",
                "title": "存在偏短章节",
                "message": f"{under_count} 章低于目标字数，建议补足场景推进、人物反应或悬念细节。",
                "chapter_indexes": list(word_target.get("under_chapter_indexes") or []),
            }
        )

    over_count = int(word_target.get("over_count") or 0)
    if over_count > 0:
        recommendations.append(
            {
                "kind": "word_target_over",
                "severity": "warning",
                "title": "存在偏长章节",
                "message": f"{over_count} 章高于目标字数，建议压缩重复描写或拆分节奏过重的场景。",
                "chapter_indexes": list(word_target.get("over_chapter_indexes") or []),
            }
        )

    warning_count = int(diagnostics.get("post_generation_warning_count") or 0)
    if warning_count > 0:
        warning_indexes = _unique_warning_chapter_indexes(diagnostics.get("post_generation_warnings"))
        recommendations.append(
            {
                "kind": "post_generation_warning",
                "severity": "warning",
                "title": "生成后维护出现警告",
                "message": f"{warning_count} 条生成后维护警告，建议先修复长篇记忆或检索同步后再继续批量写作。",
                "chapter_indexes": warning_indexes,
            }
        )

    return recommendations


def _unique_warning_chapter_indexes(warnings) -> list[int]:
    if not isinstance(warnings, list):
        return []
    indexes: list[int] = []
    seen: set[int] = set()
    for warning in warnings:
        if not isinstance(warning, dict):
            continue
        value = warning.get("chapter_index")
        if value is None:
            continue
        index = int(value)
        if index in seen:
            continue
        seen.add(index)
        indexes.append(index)
    return indexes


def _update_generation_word_target_diagnostics(
    word_target: dict,
    *,
    chapter_index: int,
    trace_metadata: dict,
) -> dict:
    next_word_target = {
        "under_count": int(word_target.get("under_count") or 0),
        "within_count": int(word_target.get("within_count") or 0),
        "over_count": int(word_target.get("over_count") or 0),
        "untracked_count": int(word_target.get("untracked_count") or 0),
        "under_chapter_indexes": list(word_target.get("under_chapter_indexes") or []),
        "over_chapter_indexes": list(word_target.get("over_chapter_indexes") or []),
    }
    chapter_word_target = trace_metadata.get("chapter_word_target")
    status = "untracked"
    if isinstance(chapter_word_target, dict):
        status = str(chapter_word_target.get("status") or "untracked")
    if status == "under":
        next_word_target["under_count"] += 1
        _append_limited_index(next_word_target["under_chapter_indexes"], chapter_index)
    elif status == "within":
        next_word_target["within_count"] += 1
    elif status == "over":
        next_word_target["over_count"] += 1
        _append_limited_index(next_word_target["over_chapter_indexes"], chapter_index)
    else:
        next_word_target["untracked_count"] += 1
    return next_word_target


def _append_limited_index(indexes: list[int], chapter_index: int) -> None:
    if len(indexes) < GENERATION_DIAGNOSTIC_INDEX_LIMIT:
        indexes.append(chapter_index)


def _queue_generate_chapter_task(db: Session, project_id: str, chapter_index: int) -> BackgroundTask:
    active_tasks = (
        db.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == project_id,
            BackgroundTask.task_type == "generate_chapter",
            BackgroundTask.status.in_(ACTIVE_TASK_STATUSES),
        )
        .order_by(BackgroundTask.created_at.desc(), BackgroundTask.id.desc())
        .all()
    )
    for active_task in active_tasks:
        if _generate_task_covers_chapter(active_task, chapter_index):
            return active_task

    project = db.query(Project).filter(Project.id == project_id).first()
    target = effective_chapter_target(db, project) if project else 0
    if target >= chapter_index > 0:
        task = BackgroundTaskService(db).create_chapter_range(
            project_id=project_id,
            task_type="generate_chapter",
            start_chapter_index=chapter_index,
            end_chapter_index=target,
            payload={"chapter_index": chapter_index},
        )
    else:
        task = BackgroundTaskService(db).create(
            project_id=project_id,
            task_type="generate_chapter",
            payload={"chapter_index": chapter_index},
        )
    LocalTaskRunner().start(task.id, build_generate_chapter_work(project_id, chapter_index))
    return task


def _generate_task_covers_chapter(task: BackgroundTask, chapter_index: int) -> bool:
    payload = task.payload or {}
    chapter_range = payload.get("chapter_range")
    if isinstance(chapter_range, dict):
        start = int(chapter_range.get("start") or 0)
        end = int(chapter_range.get("end") or 0)
        return start <= int(chapter_index) <= end
    return int(payload.get("chapter_index") or 0) == int(chapter_index)


def _queue_retry_chapter_task(db: Session, project_id: str, chapter_index: int) -> BackgroundTask:
    active_task = (
        db.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == project_id,
            BackgroundTask.task_type == "retry_chapter",
            BackgroundTask.status.in_(ACTIVE_TASK_STATUSES),
            BackgroundTask.payload["chapter_index"].as_integer() == int(chapter_index),
        )
        .order_by(BackgroundTask.created_at.desc(), BackgroundTask.id.desc())
        .first()
    )
    if active_task:
        return active_task

    task = BackgroundTaskService(db).create(
        project_id=project_id,
        task_type="retry_chapter",
        payload={"chapter_index": chapter_index},
    )
    LocalTaskRunner().start(task.id, build_retry_chapter_work(project_id, chapter_index))
    return task


def _control_out(state: WritingStateOut, task: BackgroundTask) -> WritingControlOut:
    payload = state.model_dump()
    payload["task_id"] = task.id
    return WritingControlOut(**payload)


@router.post("/chapters/{chapter_index}/retry", response_model=WritingControlOut, response_model_exclude_none=True)
async def retry_chapter(project_id: str, chapter_index: int = Path(..., ge=1), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if chapter_index_exceeds_target(db, project, chapter_index):
        raise HTTPException(status_code=400, detail="Chapter index exceeds project target chapter count")

    task = _queue_retry_chapter_task(db, project_id, chapter_index)
    state = scheduler.run_chapter(project_id, chapter_index, db)
    return _control_out(state, task)

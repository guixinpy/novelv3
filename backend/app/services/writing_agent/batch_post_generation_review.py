from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import BackgroundTask, ChapterContent, Project
from app.services.tasks.background_task_service import TASK_CANCELLED, TASK_COMPLETED, TASK_FAILED
from app.services.writing_agent.batch_enqueue import BATCH_TASK_TYPE
from app.services.writing_agent.batch_execution import EXECUTE_VERSION

POST_REVIEW_VERSION = "phase63.longform_batch_post_generation_review.v1"
TERMINAL_STATUSES = {TASK_COMPLETED, TASK_FAILED, TASK_CANCELLED}
DEFAULT_LOOKBACK = 20


def review_longform_chapter_batch_execution(
    db: Session,
    project_id: str,
    *,
    task_id: str | None,
    lookback: int | None = None,
    confirm_review: bool = False,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    if not task_id:
        return {
            "status": "failed",
            "error": "task_id is required",
            "project_id": project_id,
            "review_version": POST_REVIEW_VERSION,
        }

    task = (
        db.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == project_id,
            BackgroundTask.task_type == BATCH_TASK_TYPE,
            BackgroundTask.id == task_id,
        )
        .first()
    )
    if task is None:
        return {
            "status": "not_found",
            "review_version": POST_REVIEW_VERSION,
            "project_id": project_id,
            "task_id": task_id,
            "trace": {
                "selected_tools": ["review_longform_chapter_batch_execution"],
                "rejected_tools": [
                    {"tool_name": "review_longform_chapter_batch_execution", "reason": "selected_task_not_found"}
                ],
            },
        }

    blocked_reason = _validate_review_request(db, task)
    if blocked_reason:
        return _blocked_output(task, reason=blocked_reason)

    result = task.result if isinstance(task.result, dict) else {}
    batch_execution_result = result["batch_execution_result"]
    chapter_index = int(batch_execution_result["chapter_index"])
    actual_lookback = _lookback(lookback)
    existing_result = _existing_post_review_result(result, batch_execution_result)
    if existing_result is not None:
        return {
            "status": "skipped",
            "reason": "post_generation_review_already_recorded",
            "review_version": POST_REVIEW_VERSION,
            "project_id": project_id,
            "task": _task_payload(task),
            "chapter_index": chapter_index,
            "review_gate": existing_result.get("review_gate"),
            "reviews": existing_result.get("reviews"),
            "post_generation_review_result": existing_result,
            "side_effects": _side_effects(executed=[], skipped=["all_reviews_already_recorded"]),
            "recommended_next_tools": ["inspect_longform_chapter_batch"],
            "trace": _trace(reason="post_generation_review_already_recorded"),
        }
    if confirm_review is not True:
        return _blocked_output(
            task,
            reason="review_confirmation_required",
            required_confirmation={"confirm_review": True, "task_id": task.id},
            skipped=[
                "review_chapter_quality",
                "review_chapter_continuity",
                "analyze_chapter_world_model",
                "background_task_result_post_generation_review",
            ],
        )

    quality = _run_quality_review(db, project_id, chapter_index)
    continuity = _run_continuity_review(db, project_id, chapter_index, lookback=actual_lookback)
    blocker_count = _blocker_count(quality) + _blocker_count(continuity)
    warning_count = _warning_count(quality) + _warning_count(continuity)
    if blocker_count:
        world_model = {"status": "skipped", "reason": "review_blockers_present", "chapter_index": chapter_index}
        post_review = _post_review_payload(
            task=task,
            chapter_index=chapter_index,
            batch_execution_result=batch_execution_result,
            lookback=actual_lookback,
            quality=quality,
            continuity=continuity,
            world_model=world_model,
            gate_status="needs_revision",
            blocker_count=blocker_count,
            warning_count=warning_count,
        )
        checkpoint = _persist_post_review(db, task, post_review)
        return {
            "status": "blocked",
            "review_version": POST_REVIEW_VERSION,
            "project_id": project_id,
            "task": _task_payload(task),
            "chapter_index": chapter_index,
            "reason": "post_generation_review_has_blockers",
            "review_gate": post_review["review_gate"],
            "reviews": post_review["reviews"],
            "post_generation_review_result": post_review,
            "execution_checkpoint": checkpoint,
            "side_effects": _side_effects(
                executed=[
                    "review_chapter_quality",
                    "review_chapter_continuity",
                    "background_task_result_post_generation_review",
                ],
                skipped=["analyze_chapter_world_model"],
            ),
            "recommended_next_tools": [
                "plan_chapter_revision",
                "create_revision_draft",
                "inspect_longform_chapter_batch",
            ],
            "trace": _trace(reason="post_generation_review_has_blockers"),
        }

    world_model = _run_world_model_analysis(db, project_id, chapter_index)
    post_review = _post_review_payload(
        task=task,
        chapter_index=chapter_index,
        batch_execution_result=batch_execution_result,
        lookback=actual_lookback,
        quality=quality,
        continuity=continuity,
        world_model=world_model,
        gate_status="passed",
        blocker_count=0,
        warning_count=warning_count,
    )
    checkpoint = _persist_post_review(db, task, post_review)
    return {
        "status": "completed",
            "review_version": POST_REVIEW_VERSION,
        "project_id": project_id,
        "task": _task_payload(task),
        "chapter_index": chapter_index,
        "review_gate": post_review["review_gate"],
        "reviews": post_review["reviews"],
        "post_generation_review_result": post_review,
        "execution_checkpoint": checkpoint,
        "side_effects": _side_effects(
            executed=[
                "review_chapter_quality",
                "review_chapter_continuity",
                "analyze_chapter_world_model",
                "background_task_result_post_generation_review",
            ],
            skipped=[],
        ),
        "recommended_next_tools": ["inspect_longform_chapter_batch", "prepare_longform_chapter_batch_execution"],
        "trace": _trace(),
    }


def _validate_review_request(db: Session, task: BackgroundTask) -> str | None:
    if str(task.status or "") in TERMINAL_STATUSES:
        return "task_status_is_terminal"
    result = task.result if isinstance(task.result, dict) else {}
    batch_execution_result = (
        result.get("batch_execution_result") if isinstance(result.get("batch_execution_result"), dict) else None
    )
    if batch_execution_result is None:
        return "missing_batch_execution_result"
    if batch_execution_result.get("version") != EXECUTE_VERSION:
        return "batch_execution_result_version_mismatch"
    if batch_execution_result.get("status") != "chapter_generated":
        return "batch_execution_result_not_successful"
    executed_indexes = batch_execution_result.get("executed_chapter_indexes")
    if not isinstance(executed_indexes, list) or len(executed_indexes) != 1:
        return "phase63_requires_single_chapter_execution"
    chapter_index = _optional_int(batch_execution_result.get("chapter_index"))
    if chapter_index is None or [chapter_index] != [int(value) for value in executed_indexes if _optional_int(value)]:
        return "batch_execution_result_chapter_mismatch"
    payload_chapters = _chapter_indexes(task.payload if isinstance(task.payload, dict) else {})
    if [chapter_index] != payload_chapters:
        return "task_batch_chapter_drift"
    latest_generation_checkpoint = _latest_generation_checkpoint(result)
    if latest_generation_checkpoint is None:
        return "missing_chapter_generation_checkpoint"
    for key in ("attempt_manifest_hash", "approval_contract_hash"):
        if latest_generation_checkpoint.get(key) != batch_execution_result.get(key):
            return f"chapter_generation_checkpoint_{key}_mismatch"
    if not _chapter_content_exists(db, task.project_id, chapter_index):
        return "generated_chapter_missing"
    return None


def _run_quality_review(db: Session, project_id: str, chapter_index: int) -> dict[str, Any]:
    from app.core import chapter_quality_review

    return chapter_quality_review.review_chapter_quality(db, project_id, chapter_index)


def _run_continuity_review(db: Session, project_id: str, chapter_index: int, *, lookback: int) -> dict[str, Any]:
    from app.core import chapter_continuity_review

    return chapter_continuity_review.review_chapter_continuity(db, project_id, chapter_index, lookback=lookback)


def _run_world_model_analysis(db: Session, project_id: str, chapter_index: int) -> dict[str, Any]:
    from app.core import athena_longform

    return athena_longform.analyze_chapter_to_world_proposals(db, project_id, chapter_index)


def _post_review_payload(
    *,
    task: BackgroundTask,
    chapter_index: int,
    batch_execution_result: dict[str, Any],
    lookback: int,
    quality: dict[str, Any],
    continuity: dict[str, Any],
    world_model: dict[str, Any],
    gate_status: str,
    blocker_count: int,
    warning_count: int,
) -> dict[str, Any]:
    batch_execution_result_hash = _stable_hash(batch_execution_result)
    reviewed_at = datetime.now(UTC).isoformat()
    return {
        "version": POST_REVIEW_VERSION,
        "status": gate_status,
        "reviewed_at": reviewed_at,
        "task_id": task.id,
        "chapter_index": chapter_index,
        "lookback": lookback,
        "batch_execution_result_hash": batch_execution_result_hash,
        "review_gate": {
            "status": gate_status,
            "blocker_count": blocker_count,
            "warning_count": warning_count,
            "decision": "stop_for_revision" if blocker_count else "continue_allowed",
            "recommended_actions": _recommended_actions(quality, continuity, blocker_count=blocker_count),
        },
        "reviews": {
            "quality": quality,
            "continuity": continuity,
            "world_model": world_model,
        },
    }


def _persist_post_review(db: Session, task: BackgroundTask, post_review: dict[str, Any]) -> dict[str, Any]:
    result = dict(task.result) if isinstance(task.result, dict) else {}
    history = result.get("execution_checkpoints") if isinstance(result.get("execution_checkpoints"), list) else []
    checkpoint = {
        "version": POST_REVIEW_VERSION,
        "checkpoint_type": "post_generation_review",
        "checkpointed_at": post_review["reviewed_at"],
        "task_id": task.id,
        "status": post_review["status"],
        "chapter_index": post_review["chapter_index"],
        "batch_execution_result_hash": post_review["batch_execution_result_hash"],
        "review_gate": post_review["review_gate"],
    }
    result["post_generation_review_result"] = post_review
    result["execution_checkpoints"] = [*history[-9:], checkpoint]
    task.result = result
    db.add(task)
    db.commit()
    db.refresh(task)
    return checkpoint


def _blocked_output(
    task: BackgroundTask,
    *,
    reason: str,
    required_confirmation: dict[str, Any] | None = None,
    skipped: list[str] | None = None,
) -> dict[str, Any]:
    output = {
        "status": "blocked",
        "review_version": POST_REVIEW_VERSION,
        "project_id": task.project_id,
        "task": _task_payload(task),
        "reason": reason,
        "side_effects": _side_effects(
            executed=[],
            skipped=skipped or ["review_chapter_quality", "review_chapter_continuity"],
        ),
        "recommended_next_tools": _recommended_next_tools(reason),
        "trace": _trace(reason=reason),
    }
    if required_confirmation is not None:
        output["required_confirmation"] = required_confirmation
    return output


def _recommended_next_tools(reason: str) -> list[str]:
    if reason == "missing_batch_execution_result":
        return ["execute_longform_chapter_batch", "inspect_longform_chapter_batch"]
    if reason == "generated_chapter_missing":
        return ["execute_longform_chapter_batch_preflight", "prepare_longform_chapter_batch_execution"]
    return ["inspect_longform_chapter_batch"]


def _side_effects(*, executed: list[str], skipped: list[str]) -> dict[str, Any]:
    return {
        "executed": executed,
        "skipped": skipped,
    }


def _trace(reason: str | None = None) -> dict[str, Any]:
    rejected = []
    if reason:
        rejected.append({"tool_name": "review_longform_chapter_batch_execution", "reason": reason})
    return {
        "selected_tools": ["review_longform_chapter_batch_execution"] if reason is None else [],
        "rejected_tools": rejected,
        "source": "phase62_batch_execution_result_plus_live_chapter_state",
    }


def _task_payload(task: BackgroundTask) -> dict[str, Any]:
    payload = task.payload if isinstance(task.payload, dict) else {}
    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "plan_hash": payload.get("plan_hash"),
        "chapter_range": payload.get("chapter_range") if isinstance(payload.get("chapter_range"), dict) else None,
        "queue_policy": payload.get("queue_policy") if isinstance(payload.get("queue_policy"), dict) else {},
    }


def _existing_post_review_result(result: dict[str, Any], batch_execution_result: dict[str, Any]) -> dict[str, Any] | None:
    existing = result.get("post_generation_review_result")
    if not isinstance(existing, dict):
        return None
    if existing.get("version") != POST_REVIEW_VERSION:
        return None
    if existing.get("batch_execution_result_hash") != _stable_hash(batch_execution_result):
        return None
    return existing


def _latest_generation_checkpoint(result: dict[str, Any]) -> dict[str, Any] | None:
    checkpoints = result.get("execution_checkpoints") if isinstance(result.get("execution_checkpoints"), list) else []
    for checkpoint in reversed(checkpoints):
        if isinstance(checkpoint, dict) and checkpoint.get("checkpoint_type") == "chapter_generation":
            return checkpoint
    return None


def _chapter_indexes(payload: dict[str, Any]) -> list[int]:
    batch = payload.get("batch") if isinstance(payload.get("batch"), dict) else {}
    values = batch.get("chapter_indexes") if isinstance(batch.get("chapter_indexes"), list) else []
    return [int(value) for value in values if _optional_int(value) is not None]


def _recommended_actions(quality: dict[str, Any], continuity: dict[str, Any], *, blocker_count: int) -> list[str]:
    actions: list[str] = []
    for review in (quality, continuity):
        for action in review.get("recommended_actions") or []:
            if action not in actions:
                actions.append(str(action))
    if blocker_count and "revise_chapter" not in actions:
        actions.insert(0, "revise_chapter")
    return actions


def _blocker_count(review: dict[str, Any]) -> int:
    return int(review.get("blocker_count") or 0)


def _warning_count(review: dict[str, Any]) -> int:
    if review.get("status") == "warning":
        return max(1, int(review.get("finding_count") or 0) - _blocker_count(review))
    findings = review.get("findings") if isinstance(review.get("findings"), list) else []
    return sum(1 for finding in findings if isinstance(finding, dict) and finding.get("severity") == "warning")


def _chapter_content_exists(db: Session, project_id: str, chapter_index: int) -> bool:
    return (
        db.query(ChapterContent.id)
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.chapter_index == chapter_index,
            ChapterContent.content.isnot(None),
            ChapterContent.content != "",
        )
        .first()
        is not None
    )


def _lookback(value: int | None) -> int:
    if value is None:
        return DEFAULT_LOOKBACK
    return max(int(value), 1)


def _stable_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _optional_int(value: object) -> int | None:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None

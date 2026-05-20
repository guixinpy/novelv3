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
from app.services.writing_agent.batch_post_generation_review import POST_REVIEW_VERSION

ROUTE_VERSION = "phase64.longform_batch_post_review_route.v1"
TERMINAL_STATUSES = {TASK_COMPLETED, TASK_FAILED, TASK_CANCELLED}
DEFAULT_NEXT_BATCH_SIZE = 1


def route_longform_chapter_batch_after_review(
    db: Session,
    project_id: str,
    *,
    task_id: str | None,
    expected_post_generation_review_hash: str | None = None,
    next_batch_size: int | None = None,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    if not task_id:
        return {
            "status": "failed",
            "error": "task_id is required",
            "project_id": project_id,
            "route_version": ROUTE_VERSION,
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
            "route_version": ROUTE_VERSION,
            "project_id": project_id,
            "task_id": task_id,
            "trace": {
                "selected_tools": ["route_longform_chapter_batch_after_review"],
                "rejected_tools": [
                    {"tool_name": "route_longform_chapter_batch_after_review", "reason": "selected_task_not_found"}
                ],
            },
        }

    blocked_reason = _validate_route_request(
        db,
        task,
        expected_post_generation_review_hash=expected_post_generation_review_hash,
    )
    if blocked_reason:
        return _blocked_output(task, reason=blocked_reason)

    result = task.result if isinstance(task.result, dict) else {}
    batch_execution_result = result["batch_execution_result"]
    post_review = result["post_generation_review_result"]
    post_review_hash = _stable_hash(post_review)
    batch_execution_hash = _stable_hash(batch_execution_result)
    chapter_index = int(post_review["chapter_index"])
    existing_route = _existing_route_result(result, post_review_hash)
    if existing_route is not None:
        return {
            "status": "skipped",
            "reason": "post_generation_route_already_recorded",
            "route_version": ROUTE_VERSION,
            "project_id": project_id,
            "task": _task_payload(task),
            "chapter_index": chapter_index,
            "route_decision": existing_route.get("route_decision"),
            "post_generation_route_result": existing_route,
            "recommended_next_tools": ["inspect_longform_chapter_batch"],
            "side_effects": _side_effects(executed=[], skipped=["route_already_recorded"]),
            "trace": _trace(reason="post_generation_route_already_recorded"),
        }

    if str(post_review.get("status")) == "needs_revision":
        route_result = _revision_route(
            db,
            task=task,
            project_id=project_id,
            chapter_index=chapter_index,
            post_review=post_review,
            post_review_hash=post_review_hash,
            batch_execution_hash=batch_execution_hash,
        )
    else:
        route_result = _next_batch_route(
            db,
            task=task,
            project_id=project_id,
            chapter_index=chapter_index,
            post_review=post_review,
            post_review_hash=post_review_hash,
            batch_execution_hash=batch_execution_hash,
            next_batch_size=next_batch_size,
        )

    checkpoint = _persist_route(db, task, route_result)
    return {
        "status": "completed",
        "route_version": ROUTE_VERSION,
        "project_id": project_id,
        "task": _task_payload(task),
        "chapter_index": chapter_index,
        "route_decision": route_result["route_decision"],
        "recovery_plan": route_result.get("recovery_plan"),
        "next_batch_plan": route_result.get("next_batch_plan"),
        "post_generation_route_result": route_result,
        "execution_checkpoint": checkpoint,
        "recommended_next_tools": route_result["recommended_next_tools"],
        "side_effects": route_result["side_effects"],
        "trace": route_result["trace"],
    }


def _validate_route_request(
    db: Session,
    task: BackgroundTask,
    *,
    expected_post_generation_review_hash: str | None,
) -> str | None:
    if str(task.status or "") in TERMINAL_STATUSES:
        return "task_status_is_terminal"
    result = task.result if isinstance(task.result, dict) else {}
    batch_execution_result = (
        result.get("batch_execution_result") if isinstance(result.get("batch_execution_result"), dict) else None
    )
    post_review = (
        result.get("post_generation_review_result")
        if isinstance(result.get("post_generation_review_result"), dict)
        else None
    )
    if batch_execution_result is None:
        return "missing_batch_execution_result"
    if post_review is None:
        return "missing_post_generation_review_result"
    if batch_execution_result.get("version") != EXECUTE_VERSION:
        return "batch_execution_result_version_mismatch"
    if batch_execution_result.get("status") != "chapter_generated":
        return "batch_execution_result_not_successful"
    if post_review.get("version") != POST_REVIEW_VERSION:
        return "post_generation_review_result_version_mismatch"
    post_review_hash = _stable_hash(post_review)
    if expected_post_generation_review_hash and expected_post_generation_review_hash != post_review_hash:
        return "post_generation_review_hash_mismatch"
    if post_review.get("batch_execution_result_hash") != _stable_hash(batch_execution_result):
        return "post_generation_review_batch_hash_stale"

    chapter_index = _optional_int(batch_execution_result.get("chapter_index"))
    review_chapter_index = _optional_int(post_review.get("chapter_index"))
    executed_indexes = batch_execution_result.get("executed_chapter_indexes")
    payload_chapters = _chapter_indexes(task.payload if isinstance(task.payload, dict) else {})
    if chapter_index is None or review_chapter_index is None or chapter_index != review_chapter_index:
        return "route_chapter_mismatch"
    if not isinstance(executed_indexes, list) or [chapter_index] != [
        int(value) for value in executed_indexes if _optional_int(value)
    ]:
        return "batch_execution_result_chapter_mismatch"
    if [chapter_index] != payload_chapters:
        return "task_batch_chapter_drift"
    if not _chapter_content_exists(db, task.project_id, chapter_index):
        return "generated_chapter_missing"

    status = str(post_review.get("status") or "")
    review_gate = post_review.get("review_gate") if isinstance(post_review.get("review_gate"), dict) else {}
    gate_status = str(review_gate.get("status") or "")
    blocker_count = int(review_gate.get("blocker_count") or 0)
    decision = str(review_gate.get("decision") or "")
    if status not in {"passed", "needs_revision"}:
        return "post_generation_review_status_unsupported"
    if gate_status != status:
        return "post_generation_review_gate_status_mismatch"
    if status == "passed" and (blocker_count != 0 or decision != "continue_allowed"):
        return "post_generation_review_gate_mismatch"
    if status == "needs_revision" and (blocker_count < 1 or decision != "stop_for_revision"):
        return "post_generation_review_gate_mismatch"
    return None


def _revision_route(
    db: Session,
    *,
    task: BackgroundTask,
    project_id: str,
    chapter_index: int,
    post_review: dict[str, Any],
    post_review_hash: str,
    batch_execution_hash: str,
) -> dict[str, Any]:
    from app.core import chapter_revision_planner

    revision_plan = chapter_revision_planner.plan_chapter_revision(db, project_id, chapter_index)
    route_decision = {
        "status": "needs_revision",
        "decision": "stop_for_revision",
        "should_generate_next_chapter": False,
        "chapter_index": chapter_index,
    }
    recovery_plan = {
        "status": "revision_required",
        "chapter_index": chapter_index,
        "review_gate": post_review.get("review_gate"),
        "quality_findings": _review_findings(post_review, "quality"),
        "continuity_findings": _review_findings(post_review, "continuity"),
        "revision_plan": revision_plan,
    }
    return _route_payload(
        task=task,
        chapter_index=chapter_index,
        post_review_hash=post_review_hash,
        batch_execution_hash=batch_execution_hash,
        route_decision=route_decision,
        recovery_plan=recovery_plan,
        next_batch_plan=None,
        recommended_next_tools=["plan_chapter_revision", "create_revision_draft", "inspect_longform_chapter_batch"],
        side_effects=_side_effects(
            executed=["plan_chapter_revision", "background_task_result_post_review_route"],
            skipped=["plan_longform_chapter_batch", "enqueue_longform_chapter_batch"],
        ),
        trace={
            "selected_tools": ["route_longform_chapter_batch_after_review", "plan_chapter_revision"],
            "rejected_tools": [
                {"tool_name": "plan_longform_chapter_batch", "reason": "review_requires_revision"},
                {"tool_name": "enqueue_longform_chapter_batch", "reason": "phase64_preview_only"},
            ],
        },
    )


def _next_batch_route(
    db: Session,
    *,
    task: BackgroundTask,
    project_id: str,
    chapter_index: int,
    post_review: dict[str, Any],
    post_review_hash: str,
    batch_execution_hash: str,
    next_batch_size: int | None,
) -> dict[str, Any]:
    from app.services.writing_agent import batch_planner

    resolved_batch_size = _next_batch_size(next_batch_size)
    next_chapter_index = chapter_index + 1
    next_batch_plan = batch_planner.build_longform_chapter_batch_plan(
        db,
        project_id,
        source_run_id=None,
        start_chapter=next_chapter_index,
        batch_size=resolved_batch_size,
    )
    route_decision = {
        "status": "passed",
        "decision": "continue_to_next_batch",
        "should_generate_next_chapter": True,
        "chapter_index": chapter_index,
        "next_chapter_index": next_chapter_index,
        "next_batch_size": resolved_batch_size,
    }
    recommended_next_tools = ["enqueue_longform_chapter_batch", "inspect_longform_chapter_batch"]
    if _world_model_created_items(post_review) > 0:
        recommended_next_tools.insert(0, "review_world_model_proposals")
    return _route_payload(
        task=task,
        chapter_index=chapter_index,
        post_review_hash=post_review_hash,
        batch_execution_hash=batch_execution_hash,
        route_decision=route_decision,
        recovery_plan=None,
        next_batch_plan=next_batch_plan,
        recommended_next_tools=recommended_next_tools,
        side_effects=_side_effects(
            executed=["plan_longform_chapter_batch", "background_task_result_post_review_route"],
            skipped=["plan_chapter_revision", "enqueue_longform_chapter_batch"],
        ),
        trace={
            "selected_tools": ["route_longform_chapter_batch_after_review", "plan_longform_chapter_batch"],
            "rejected_tools": [
                {"tool_name": "plan_chapter_revision", "reason": "review_passed"},
                {"tool_name": "enqueue_longform_chapter_batch", "reason": "phase64_preview_only"},
            ],
        },
    )


def _route_payload(
    *,
    task: BackgroundTask,
    chapter_index: int,
    post_review_hash: str,
    batch_execution_hash: str,
    route_decision: dict[str, Any],
    recovery_plan: dict[str, Any] | None,
    next_batch_plan: dict[str, Any] | None,
    recommended_next_tools: list[str],
    side_effects: dict[str, Any],
    trace: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "version": ROUTE_VERSION,
        "status": route_decision["status"],
        "routed_at": datetime.now(UTC).isoformat(),
        "task_id": task.id,
        "chapter_index": chapter_index,
        "post_generation_review_result_hash": post_review_hash,
        "batch_execution_result_hash": batch_execution_hash,
        "route_decision": route_decision,
        "recommended_next_tools": recommended_next_tools,
        "side_effects": side_effects,
        "trace": trace,
    }
    if recovery_plan is not None:
        payload["recovery_plan"] = recovery_plan
    if next_batch_plan is not None:
        payload["next_batch_plan"] = next_batch_plan
    return payload


def _persist_route(db: Session, task: BackgroundTask, route_result: dict[str, Any]) -> dict[str, Any]:
    result = dict(task.result) if isinstance(task.result, dict) else {}
    history = result.get("execution_checkpoints") if isinstance(result.get("execution_checkpoints"), list) else []
    checkpoint = {
        "version": ROUTE_VERSION,
        "checkpoint_type": "post_generation_route",
        "checkpointed_at": route_result["routed_at"],
        "task_id": task.id,
        "status": route_result["status"],
        "chapter_index": route_result["chapter_index"],
        "post_generation_review_result_hash": route_result["post_generation_review_result_hash"],
        "decision": route_result["route_decision"]["decision"],
    }
    result["post_generation_route_result"] = route_result
    result["execution_checkpoints"] = [*history[-9:], checkpoint]
    task.result = result
    db.add(task)
    db.commit()
    db.refresh(task)
    return checkpoint


def _blocked_output(task: BackgroundTask, *, reason: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "route_version": ROUTE_VERSION,
        "project_id": task.project_id,
        "task": _task_payload(task),
        "reason": reason,
        "side_effects": _side_effects(executed=[], skipped=["plan_chapter_revision", "plan_longform_chapter_batch"]),
        "recommended_next_tools": _recommended_next_tools(reason),
        "trace": _trace(reason=reason),
    }


def _existing_route_result(result: dict[str, Any], post_review_hash: str) -> dict[str, Any] | None:
    existing = result.get("post_generation_route_result")
    if not isinstance(existing, dict):
        return None
    if existing.get("version") != ROUTE_VERSION:
        return None
    if existing.get("post_generation_review_result_hash") != post_review_hash:
        return None
    return existing


def _recommended_next_tools(reason: str) -> list[str]:
    if reason == "missing_post_generation_review_result":
        return ["review_longform_chapter_batch_execution", "inspect_longform_chapter_batch"]
    if reason == "missing_batch_execution_result":
        return ["execute_longform_chapter_batch", "inspect_longform_chapter_batch"]
    return ["inspect_longform_chapter_batch"]


def _side_effects(*, executed: list[str], skipped: list[str]) -> dict[str, Any]:
    return {"executed": executed, "skipped": skipped}


def _trace(reason: str | None = None) -> dict[str, Any]:
    rejected = []
    if reason:
        rejected.append({"tool_name": "route_longform_chapter_batch_after_review", "reason": reason})
    return {
        "selected_tools": ["route_longform_chapter_batch_after_review"] if reason is None else [],
        "rejected_tools": rejected,
        "source": "phase62_execution_plus_phase63_review_evidence",
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


def _review_findings(post_review: dict[str, Any], name: str) -> list[Any]:
    reviews = post_review.get("reviews") if isinstance(post_review.get("reviews"), dict) else {}
    review = reviews.get(name) if isinstance(reviews.get(name), dict) else {}
    findings = review.get("findings")
    return findings if isinstance(findings, list) else []


def _world_model_created_items(post_review: dict[str, Any]) -> int:
    reviews = post_review.get("reviews") if isinstance(post_review.get("reviews"), dict) else {}
    world_model = reviews.get("world_model") if isinstance(reviews.get("world_model"), dict) else {}
    created = world_model.get("created") if isinstance(world_model.get("created"), dict) else {}
    return int(created.get("proposal_items") or 0)


def _chapter_indexes(payload: dict[str, Any]) -> list[int]:
    batch = payload.get("batch") if isinstance(payload.get("batch"), dict) else {}
    values = batch.get("chapter_indexes") if isinstance(batch.get("chapter_indexes"), list) else []
    return [int(value) for value in values if _optional_int(value) is not None]


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


def _next_batch_size(value: int | None) -> int:
    if value is None:
        return DEFAULT_NEXT_BATCH_SIZE
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

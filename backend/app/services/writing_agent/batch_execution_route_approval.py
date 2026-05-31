from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import BackgroundTask, Project
from app.services.writing_agent.agent_step_binding import build_agent_step_binding, verify_resource_binding_target
from app.services.writing_agent.approval_contract import (
    build_agent_plan_approval_contract,
    verify_agent_plan_approval_contract,
)
from app.services.writing_agent.approval_verification_event import build_approval_verification_event
from app.services.writing_agent.batch_enqueue import BATCH_TASK_TYPE
from app.services.writing_agent.batch_post_review_router import (
    ROUTE_VERSION,
    _existing_route_result,
    _next_batch_size,
    _stable_hash,
    _task_payload,
    _validate_route_request,
    _world_model_created_items,
    route_longform_chapter_batch_after_review,
)
from app.services.writing_agent.mutation_fingerprint import build_mutation_fingerprint

PREPARE_LONGFORM_CHAPTER_BATCH_AFTER_REVIEW_ROUTE_VERSION = "phase203.longform_batch_route_prepare.v1"
EXECUTE_LONGFORM_CHAPTER_BATCH_AFTER_REVIEW_ROUTE_WITH_APPROVAL_VERSION = (
    "phase203.longform_batch_route_with_approval_execute.v1"
)
APPROVAL_GATE_VERSION = "phase203.longform_batch_post_review_route_agent_plan_approval.v1"
TARGET_TYPE = "background_task_post_review_route"
SKIPPED_WRITE_EFFECT = "background_task_result_post_review_route"


def prepare_longform_chapter_batch_after_review_route(
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
    task = _find_batch_task(db, project_id, task_id)
    if task is None:
        return _not_found_output(project_id, task_id, prepare=True)

    preview = _route_preview(
        db,
        project_id,
        task,
        expected_post_generation_review_hash=expected_post_generation_review_hash,
        next_batch_size=next_batch_size,
    )
    if preview.get("status") == "skipped":
        return {
            **preview,
            "prepare_version": PREPARE_LONGFORM_CHAPTER_BATCH_AFTER_REVIEW_ROUTE_VERSION,
            "target_type": TARGET_TYPE,
            "side_effects": _side_effects(executed=[], skipped=["route_already_recorded"]),
        }
    if preview.get("status") != "ready":
        return {
            "status": "blocked",
            "prepare_version": PREPARE_LONGFORM_CHAPTER_BATCH_AFTER_REVIEW_ROUTE_VERSION,
            "project_id": project_id,
            "target_type": TARGET_TYPE,
            "task": _task_payload(task),
            "reason": str(preview.get("reason") or "route_not_ready"),
            "route_preview": preview,
            "side_effects": _side_effects(executed=[], skipped=[SKIPPED_WRITE_EFFECT]),
            "recommended_next_tools": ["inspect_longform_chapter_batch"],
            "trace": {
                "selected_tools": ["prepare_longform_chapter_batch_after_review_route"],
                "rejected_tools": [
                    {
                        "tool_name": "route_longform_chapter_batch_after_review",
                        "reason": str(preview.get("reason") or "route_not_ready"),
                    }
                ],
                "approval_gate_version": APPROVAL_GATE_VERSION,
            },
        }

    agent_plan = _direct_route_agent_plan(
        project_id,
        task_id=task.id,
        expected_post_generation_review_hash=expected_post_generation_review_hash,
        next_batch_size=next_batch_size,
    )
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    return {
        "status": "approval_required",
        "prepare_version": PREPARE_LONGFORM_CHAPTER_BATCH_AFTER_REVIEW_ROUTE_VERSION,
        "project_id": project_id,
        "target_type": TARGET_TYPE,
        "task": _task_payload(task),
        "route_preview": preview,
        "mutation_fingerprint": first_step.get("mutation_fingerprint"),
        "tool_call_id": first_step.get("tool_call_id"),
        "resource_binding": first_step.get("resource_binding"),
        "agent_plan": agent_plan,
        "agent_plan_approval_contract": approval_contract,
        "agent_plan_approval_contract_hash": approval_hash,
        "required_confirmation": {
            "confirm_execute": True,
            "approval_contract_hash": approval_hash,
        },
        "side_effects": _side_effects(executed=[], skipped=[SKIPPED_WRITE_EFFECT]),
        "recommended_next_tools": ["execute_longform_chapter_batch_after_review_route_with_approval"],
        "trace": {
            "selected_tools": ["prepare_longform_chapter_batch_after_review_route"],
            "rejected_tools": [
                {"tool_name": "route_longform_chapter_batch_after_review", "reason": "approval_required_before_write"}
            ],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def execute_longform_chapter_batch_after_review_route_with_approval(
    db: Session,
    project_id: str,
    *,
    task_id: str | None,
    expected_post_generation_review_hash: str | None = None,
    next_batch_size: int | None = None,
    confirm_execute: bool,
    approval_contract_hash: str | None,
    approval_contract: dict[str, Any] | None,
    approval_tool_metadata_provider,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    task = _find_batch_task(db, project_id, task_id)
    if task is None:
        return _not_found_output(project_id, task_id, prepare=False)
    if confirm_execute is not True:
        return _blocked_output(project_id, task_id=task.id, reason="confirmation_required")
    if not approval_contract_hash or not isinstance(approval_contract, dict):
        return _blocked_output(project_id, task_id=task.id, reason="approval_contract_required")
    if approval_tool_metadata_provider is None:
        return _blocked_output(project_id, task_id=task.id, reason="agent_plan_tool_metadata_missing")

    agent_plan = _direct_route_agent_plan(
        project_id,
        task_id=task.id,
        expected_post_generation_review_hash=expected_post_generation_review_hash,
        next_batch_size=next_batch_size,
    )
    verification = verify_agent_plan_approval_contract(
        agent_plan,
        approval_contract_hash=approval_contract_hash,
        approval_contract=approval_contract,
        project_id=project_id,
        tool_metadata_by_name=approval_tool_metadata_provider(agent_plan),
    )
    if verification.get("status") != "ready":
        return _blocked_output(
            project_id,
            task_id=task.id,
            reason=str(verification.get("reason") or "agent_plan_approval_not_ready"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
            },
        )

    binding_check = verify_resource_binding_target(
        verification,
        tool_name="route_longform_chapter_batch_after_review",
        target_type=TARGET_TYPE,
        target_id=_target_id(task.id),
    )
    if binding_check.get("status") != "ready":
        return _blocked_output(
            project_id,
            task_id=task.id,
            reason=str(binding_check.get("reason") or "resource_binding_target_mismatch"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
                "execution_resource_binding": binding_check,
            },
        )

    result = route_longform_chapter_batch_after_review(
        db,
        project_id,
        task_id=task.id,
        expected_post_generation_review_hash=expected_post_generation_review_hash,
        next_batch_size=next_batch_size,
    )
    return {
        **result,
        "execute_version": EXECUTE_LONGFORM_CHAPTER_BATCH_AFTER_REVIEW_ROUTE_WITH_APPROVAL_VERSION,
        "target_type": TARGET_TYPE,
        "agent_plan_approval_verification": verification,
        "approval_verification_event": build_approval_verification_event(verification),
        "execution_resource_binding": binding_check,
        "evidence": {
            "agent_plan_approval_verified": True,
            "legacy_action": "route_longform_chapter_batch_after_review",
            "execution_route": "static_adapter",
        },
        "trace": {
            **(result.get("trace") if isinstance(result.get("trace"), dict) else {}),
            "selected_tools": ["execute_longform_chapter_batch_after_review_route_with_approval"],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def _route_preview(
    db: Session,
    project_id: str,
    task: BackgroundTask,
    *,
    expected_post_generation_review_hash: str | None,
    next_batch_size: int | None,
) -> dict[str, Any]:
    blocked_reason = _validate_route_request(
        db,
        task,
        expected_post_generation_review_hash=expected_post_generation_review_hash,
    )
    if blocked_reason:
        return {
            "status": "blocked",
            "reason": blocked_reason,
            "route_version": ROUTE_VERSION,
            "side_effects": _side_effects(executed=[], skipped=[SKIPPED_WRITE_EFFECT]),
        }

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
            "task": _task_payload(task),
            "chapter_index": chapter_index,
            "route_decision": existing_route.get("route_decision"),
            "post_generation_route_result": existing_route,
            "recommended_next_tools": ["inspect_longform_chapter_batch"],
            "side_effects": _side_effects(executed=[], skipped=["route_already_recorded"]),
        }

    if str(post_review.get("status")) == "needs_revision":
        route_decision = {
            "status": "needs_revision",
            "decision": "stop_for_revision",
            "should_generate_next_chapter": False,
            "chapter_index": chapter_index,
        }
        return {
            "status": "ready",
            "route_version": ROUTE_VERSION,
            "task": _task_payload(task),
            "chapter_index": chapter_index,
            "post_generation_review_result_hash": post_review_hash,
            "batch_execution_result_hash": batch_execution_hash,
            "route_decision": route_decision,
            "recovery_plan": {
                "status": "revision_required",
                "chapter_index": chapter_index,
                "review_gate": post_review.get("review_gate"),
            },
            "recommended_next_tools": ["plan_chapter_revision", "create_revision_draft", "inspect_longform_chapter_batch"],
            "side_effects": _side_effects(executed=[], skipped=[SKIPPED_WRITE_EFFECT]),
        }

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
    return {
        "status": "ready",
        "route_version": ROUTE_VERSION,
        "task": _task_payload(task),
        "chapter_index": chapter_index,
        "post_generation_review_result_hash": post_review_hash,
        "batch_execution_result_hash": batch_execution_hash,
        "route_decision": route_decision,
        "next_batch_plan": next_batch_plan,
        "recommended_next_tools": recommended_next_tools,
        "side_effects": _side_effects(executed=[], skipped=[SKIPPED_WRITE_EFFECT]),
    }


def _direct_route_agent_plan(
    project_id: str,
    *,
    task_id: str,
    expected_post_generation_review_hash: str | None,
    next_batch_size: int | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"task_id": task_id}
    if expected_post_generation_review_hash:
        params["expected_post_generation_review_hash"] = expected_post_generation_review_hash
    if next_batch_size is not None:
        params["next_batch_size"] = int(next_batch_size)
    plan_id = f"direct-longform-batch-after-review-route:{task_id}"
    mutation_fingerprint = build_mutation_fingerprint(project_id, "route_longform_chapter_batch_after_review", params)
    step = {
        "step_index": 1,
        "step_id": plan_id,
        "tool_name": "route_longform_chapter_batch_after_review",
        "approval_executor_tool_name": "execute_longform_chapter_batch_after_review_route_with_approval",
        "params": params,
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": "根据生成后审查结果写入批次路由决策，进入修订恢复或下一批次预览。",
    }
    step.update(
        build_agent_step_binding(
            project_id=project_id,
            plan_id=plan_id,
            source_projection_id=None,
            step=step,
            mutation_fingerprint=mutation_fingerprint,
        )
    )
    return {
        "project_id": project_id,
        "intent_class": "direct_longform_batch_after_review_route",
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": None,
            "planner_version": PREPARE_LONGFORM_CHAPTER_BATCH_AFTER_REVIEW_ROUTE_VERSION,
        },
        "steps": [step],
    }


def _find_batch_task(db: Session, project_id: str, task_id: str | None) -> BackgroundTask | None:
    if not task_id:
        return None
    return (
        db.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == project_id,
            BackgroundTask.task_type == BATCH_TASK_TYPE,
            BackgroundTask.id == task_id,
        )
        .first()
    )


def _not_found_output(project_id: str, task_id: str | None, *, prepare: bool) -> dict[str, Any]:
    version_key = "prepare_version" if prepare else "execute_version"
    version = (
        PREPARE_LONGFORM_CHAPTER_BATCH_AFTER_REVIEW_ROUTE_VERSION
        if prepare
        else EXECUTE_LONGFORM_CHAPTER_BATCH_AFTER_REVIEW_ROUTE_WITH_APPROVAL_VERSION
    )
    return {
        "status": "not_found",
        version_key: version,
        "project_id": project_id,
        "task_id": task_id,
        "target_type": TARGET_TYPE,
        "side_effects": _side_effects(executed=[], skipped=[SKIPPED_WRITE_EFFECT]),
        "trace": {
            "selected_tools": [
                "prepare_longform_chapter_batch_after_review_route"
                if prepare
                else "execute_longform_chapter_batch_after_review_route_with_approval"
            ],
            "rejected_tools": [{"tool_name": "route_longform_chapter_batch_after_review", "reason": "task_not_found"}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def _blocked_output(
    project_id: str,
    *,
    task_id: str,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = {
        "status": "blocked",
        "execute_version": EXECUTE_LONGFORM_CHAPTER_BATCH_AFTER_REVIEW_ROUTE_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "task_id": task_id,
        "target_type": TARGET_TYPE,
        "reason": reason,
        "side_effects": _side_effects(executed=[], skipped=[SKIPPED_WRITE_EFFECT]),
        "recommended_next_tools": ["prepare_longform_chapter_batch_after_review_route"],
        "trace": {
            "selected_tools": ["execute_longform_chapter_batch_after_review_route_with_approval"],
            "rejected_tools": [{"tool_name": "route_longform_chapter_batch_after_review", "reason": reason}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }
    if extra:
        output.update(extra)
    return output


def _side_effects(*, executed: list[str], skipped: list[str]) -> dict[str, Any]:
    return {"executed": executed, "skipped": skipped}


def _target_id(task_id: str) -> str:
    return f"{TARGET_TYPE}:{task_id}"

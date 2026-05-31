from __future__ import annotations

import hashlib
import json

from app.models import BackgroundTask, ChapterContent, Project
from app.services.writing_agent.batch_enqueue import BATCH_TASK_TYPE
from app.services.writing_agent.batch_execution import EXECUTE_VERSION
from app.services.writing_agent.batch_execution_route_approval import (
    execute_longform_chapter_batch_after_review_route_with_approval,
    prepare_longform_chapter_batch_after_review_route,
)
from app.services.writing_agent.batch_post_generation_review import POST_REVIEW_VERSION


def test_prepare_longform_chapter_batch_after_review_route_returns_agent_contract_without_route_write(db_session):
    project, task, post_review_hash = _seed_reviewed_batch_task(db_session, review_status="passed")

    output = prepare_longform_chapter_batch_after_review_route(
        db_session,
        project.id,
        task_id=task.id,
        expected_post_generation_review_hash=post_review_hash,
        next_batch_size=2,
    )

    db_session.refresh(task)
    assert output["status"] == "approval_required"
    assert output["project_id"] == project.id
    assert output["target_type"] == "background_task_post_review_route"
    assert output["task"]["id"] == task.id
    assert output["route_preview"]["status"] == "ready"
    assert output["route_preview"]["route_decision"]["decision"] == "continue_to_next_batch"
    step = output["agent_plan"]["steps"][0]
    assert step["tool_name"] == "route_longform_chapter_batch_after_review"
    assert step["approval_executor_tool_name"] == "execute_longform_chapter_batch_after_review_route_with_approval"
    assert step["params"] == {
        "task_id": task.id,
        "expected_post_generation_review_hash": post_review_hash,
        "next_batch_size": 2,
    }
    assert step["mutation_fingerprint"]["status"] == "ready"
    assert step["mutation_fingerprint"]["components"]["target_type"] == "background_task_post_review_route"
    assert step["mutation_fingerprint"]["components"]["target_id"] == f"background_task_post_review_route:{task.id}"
    assert output["agent_plan_approval_contract"]["status"] == "requires_confirmation"
    assert output["required_confirmation"] == {
        "confirm_execute": True,
        "approval_contract_hash": output["agent_plan_approval_contract_hash"],
    }
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["background_task_result_post_review_route"]
    assert "post_generation_route_result" not in (task.result or {})


def test_execute_longform_chapter_batch_after_review_route_with_approval_blocks_without_confirmation(db_session):
    project, task, post_review_hash = _seed_reviewed_batch_task(db_session, review_status="passed")

    output = execute_longform_chapter_batch_after_review_route_with_approval(
        db_session,
        project.id,
        task_id=task.id,
        expected_post_generation_review_hash=post_review_hash,
        next_batch_size=2,
        confirm_execute=False,
        approval_contract_hash=None,
        approval_contract=None,
        approval_tool_metadata_provider=lambda plan: {},
    )

    db_session.refresh(task)
    assert output["status"] == "blocked"
    assert output["reason"] == "confirmation_required"
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["background_task_result_post_review_route"]
    assert "post_generation_route_result" not in (task.result or {})


def test_execute_longform_chapter_batch_after_review_route_with_approval_writes_route_after_contract_verification(
    db_session,
):
    project, task, post_review_hash = _seed_reviewed_batch_task(db_session, review_status="passed")
    prepared = prepare_longform_chapter_batch_after_review_route(
        db_session,
        project.id,
        task_id=task.id,
        expected_post_generation_review_hash=post_review_hash,
        next_batch_size=2,
    )

    output = execute_longform_chapter_batch_after_review_route_with_approval(
        db_session,
        project.id,
        task_id=task.id,
        expected_post_generation_review_hash=post_review_hash,
        next_batch_size=2,
        confirm_execute=True,
        approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
        approval_contract=prepared["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: {
            "route_longform_chapter_batch_after_review": {
                "tool_name": "route_longform_chapter_batch_after_review",
                "tool_exists": True,
                "adapter_exists": True,
                "adapter_type": "approval_wrapper",
                "handler_name": "_route_longform_chapter_batch_after_review",
                "mutability": "guarded_write",
                "requires_confirmation": True,
                "required_fields": ["task_id"],
            }
        },
    )

    db_session.refresh(task)
    assert output["status"] == "completed"
    assert output["route_decision"]["decision"] == "continue_to_next_batch"
    assert output["next_batch_plan"]["batch"]["start_chapter"] == 3
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["side_effects"]["executed"] == [
        "plan_longform_chapter_batch",
        "background_task_result_post_review_route",
    ]
    assert task.result["post_generation_route_result"]["route_decision"]["decision"] == "continue_to_next_batch"


def _seed_reviewed_batch_task(
    db_session,
    *,
    review_status: str,
) -> tuple[Project, BackgroundTask, str]:
    project = Project(name="Approved Batch Review Route", target_chapter_count=10)
    db_session.add(project)
    db_session.flush()
    task = BackgroundTask(
        project_id=project.id,
        task_type=BATCH_TASK_TYPE,
        status="pending",
        payload={
            "plan_hash": "plan-route-1",
            "chapter_range": {"start": 2, "end": 2},
            "batch": {"start_chapter": 2, "end_chapter": 2, "chapter_indexes": [2]},
            "dag": {"nodes": [{"node_id": "chapter_generation"}], "edges": []},
            "queue_policy": {"resume_strategy": "background_task_chapter_range"},
        },
    )
    db_session.add(task)
    db_session.flush()
    batch_execution_result = {
        "version": EXECUTE_VERSION,
        "status": "chapter_generated",
        "executed_at": "2026-05-31T00:00:00+00:00",
        "chapter_index": 2,
        "executed_chapter_indexes": [2],
        "attempt_manifest_hash": "attempt-route-1",
        "approval_contract_hash": "approval-route-1",
        "generation": {"status": "success", "chapter_index": 2, "trace_id": "trace-route-2"},
        "trace_id": "trace-route-2",
    }
    post_review = {
        "version": POST_REVIEW_VERSION,
        "status": review_status,
        "reviewed_at": "2026-05-31T00:01:00+00:00",
        "task_id": task.id,
        "chapter_index": 2,
        "lookback": 12,
        "batch_execution_result_hash": _stable_hash(batch_execution_result),
        "review_gate": {
            "status": review_status,
            "blocker_count": 0 if review_status == "passed" else 1,
            "warning_count": 0,
            "decision": "continue_allowed" if review_status == "passed" else "stop_for_revision",
            "recommended_actions": [] if review_status == "passed" else ["revise_chapter"],
        },
        "reviews": {
            "quality": {"status": "ready", "findings": []},
            "continuity": {"status": "ready", "findings": []},
            "world_model": {"status": "completed", "created": {"proposal_items": 0}},
        },
    }
    task.result = {
        "batch_execution_result": batch_execution_result,
        "post_generation_review_result": post_review,
        "execution_checkpoints": [
            {
                "version": EXECUTE_VERSION,
                "checkpoint_type": "chapter_generation",
                "checkpointed_at": "2026-05-31T00:00:00+00:00",
                "task_id": task.id,
                "status": "completed",
                "chapter_index": 2,
                "attempt_manifest_hash": "attempt-route-1",
                "approval_contract_hash": "approval-route-1",
            },
            {
                "version": POST_REVIEW_VERSION,
                "checkpoint_type": "post_generation_review",
                "checkpointed_at": "2026-05-31T00:01:00+00:00",
                "task_id": task.id,
                "status": review_status,
                "chapter_index": 2,
                "post_generation_review_result_hash": _stable_hash(post_review),
            },
        ],
    }
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=2,
            title="雾港线索2",
            content="林深和苏晚晴追入记忆诊所后巷，发现雾晶核心的回声正在扩大。",
            word_count=2200,
            status="generated",
        )
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(project)
    db_session.refresh(task)
    return project, task, _stable_hash(post_review)


def _stable_hash(payload: dict) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

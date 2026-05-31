from __future__ import annotations

from app.models import BackgroundTask, ChapterContent, Project
from app.services.writing_agent.batch_enqueue import BATCH_TASK_TYPE
from app.services.writing_agent.batch_execution import EXECUTE_VERSION
from app.services.writing_agent.batch_execution_review_approval import (
    execute_longform_chapter_batch_execution_review_with_approval,
    prepare_longform_chapter_batch_execution_review,
)


def test_prepare_longform_chapter_batch_execution_review_returns_agent_contract_without_review_write(db_session):
    project, task = _seed_executed_batch_task(db_session)

    output = prepare_longform_chapter_batch_execution_review(db_session, project.id, task_id=task.id, lookback=12)

    db_session.refresh(task)
    assert output["status"] == "approval_required"
    assert output["project_id"] == project.id
    assert output["target_type"] == "background_task_post_generation_review"
    assert output["task"]["id"] == task.id
    assert output["review_preview"]["status"] == "blocked"
    assert output["review_preview"]["reason"] == "review_confirmation_required"
    step = output["agent_plan"]["steps"][0]
    assert step["tool_name"] == "review_longform_chapter_batch_execution"
    assert step["approval_executor_tool_name"] == "execute_longform_chapter_batch_execution_review_with_approval"
    assert step["params"] == {"task_id": task.id, "lookback": 12}
    assert step["mutation_fingerprint"]["status"] == "ready"
    assert step["mutation_fingerprint"]["components"]["target_type"] == "background_task_post_generation_review"
    assert step["mutation_fingerprint"]["components"]["target_id"] == f"background_task_post_generation_review:{task.id}"
    assert output["agent_plan_approval_contract"]["status"] == "requires_confirmation"
    assert output["required_confirmation"] == {
        "confirm_execute": True,
        "approval_contract_hash": output["agent_plan_approval_contract_hash"],
    }
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["background_task_result_post_generation_review"]
    assert "post_generation_review_result" not in (task.result or {})


def test_execute_longform_chapter_batch_execution_review_with_approval_blocks_without_confirmation(db_session):
    project, task = _seed_executed_batch_task(db_session)

    output = execute_longform_chapter_batch_execution_review_with_approval(
        db_session,
        project.id,
        task_id=task.id,
        lookback=12,
        confirm_execute=False,
        approval_contract_hash=None,
        approval_contract=None,
        approval_tool_metadata_provider=lambda plan: {},
    )

    db_session.refresh(task)
    assert output["status"] == "blocked"
    assert output["reason"] == "confirmation_required"
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["background_task_result_post_generation_review"]
    assert "post_generation_review_result" not in (task.result or {})


def test_execute_longform_chapter_batch_execution_review_with_approval_writes_review_after_contract_verification(
    db_session,
    monkeypatch,
):
    project, task = _seed_executed_batch_task(db_session)
    prepared = prepare_longform_chapter_batch_execution_review(db_session, project.id, task_id=task.id, lookback=12)
    calls: list[tuple[str, int]] = []

    def fake_quality(db, project_id: str, chapter_index: int):
        calls.append(("quality", chapter_index))
        return {
            "status": "ready",
            "chapter_index": chapter_index,
            "finding_count": 0,
            "blocker_count": 0,
            "findings": [],
            "recommended_actions": [],
        }

    def fake_continuity(db, project_id: str, chapter_index: int, *, lookback: int):
        calls.append(("continuity", lookback))
        return {
            "status": "ready",
            "chapter_index": chapter_index,
            "finding_count": 0,
            "blocker_count": 0,
            "findings": [],
            "recommended_actions": [],
        }

    def fake_world_model(db, project_id: str, chapter_index: int):
        calls.append(("world_model", chapter_index))
        return {
            "status": "completed",
            "chapter_index": chapter_index,
            "proposal_bundle_id": "bundle-review-2",
            "created": {"proposal_items": 2},
        }

    monkeypatch.setattr("app.core.chapter_quality_review.review_chapter_quality", fake_quality)
    monkeypatch.setattr("app.core.chapter_continuity_review.review_chapter_continuity", fake_continuity)
    monkeypatch.setattr("app.core.athena_longform.analyze_chapter_to_world_proposals", fake_world_model)

    output = execute_longform_chapter_batch_execution_review_with_approval(
        db_session,
        project.id,
        task_id=task.id,
        lookback=12,
        confirm_execute=True,
        approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
        approval_contract=prepared["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: {
            "review_longform_chapter_batch_execution": {
                "tool_name": "review_longform_chapter_batch_execution",
                "tool_exists": True,
                "adapter_exists": True,
                "adapter_type": "approval_wrapper",
                "handler_name": "_review_longform_chapter_batch_execution",
                "mutability": "guarded_write",
                "requires_confirmation": True,
                "required_fields": ["task_id"],
            }
        },
    )

    db_session.refresh(task)
    assert output["status"] == "completed"
    assert output["review_gate"]["status"] == "passed"
    assert output["reviews"]["world_model"]["proposal_bundle_id"] == "bundle-review-2"
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["side_effects"]["executed"] == [
        "review_chapter_quality",
        "review_chapter_continuity",
        "analyze_chapter_world_model",
        "background_task_result_post_generation_review",
    ]
    assert calls == [("quality", 2), ("continuity", 12), ("world_model", 2)]
    assert task.result["post_generation_review_result"]["status"] == "passed"


def _seed_executed_batch_task(db_session) -> tuple[Project, BackgroundTask]:
    project = Project(name="Approved Batch Execution Review")
    db_session.add(project)
    db_session.flush()
    task = BackgroundTask(
        project_id=project.id,
        task_type=BATCH_TASK_TYPE,
        status="pending",
        payload={
            "plan_hash": "plan-execution-review-1",
            "chapter_range": {"start": 2, "end": 2},
            "batch": {"start_chapter": 2, "end_chapter": 2, "chapter_indexes": [2]},
            "dag": {"nodes": [{"node_id": "chapter_generation"}], "edges": []},
            "queue_policy": {"resume_strategy": "background_task_chapter_range"},
        },
    )
    db_session.add(task)
    db_session.flush()
    task.result = {
        "batch_execution_result": {
            "version": EXECUTE_VERSION,
            "status": "chapter_generated",
            "executed_at": "2026-05-31T00:00:00+00:00",
            "chapter_index": 2,
            "executed_chapter_indexes": [2],
            "attempt_manifest_hash": "attempt-review-1",
            "approval_contract_hash": "approval-review-1",
            "generation": {"status": "success", "chapter_index": 2, "trace_id": "trace-review-2"},
            "trace_id": "trace-review-2",
        },
        "execution_checkpoints": [
            {
                "version": EXECUTE_VERSION,
                "checkpoint_type": "chapter_generation",
                "checkpointed_at": "2026-05-31T00:00:00+00:00",
                "task_id": task.id,
                "status": "completed",
                "chapter_index": 2,
                "attempt_manifest_hash": "attempt-review-1",
                "approval_contract_hash": "approval-review-1",
                "trace_id": "trace-review-2",
            }
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
    return project, task

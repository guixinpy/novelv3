from __future__ import annotations

from app.models import BackgroundTask, Project
from app.services.writing_agent.batch_enqueue_execution import (
    execute_enqueue_longform_chapter_batch_with_approval,
    prepare_enqueue_longform_chapter_batch,
)


def test_prepare_enqueue_longform_chapter_batch_returns_agent_approval_contract(db_session):
    project = Project(name="Prepare Batch Enqueue")
    db_session.add(project)
    db_session.commit()

    output = prepare_enqueue_longform_chapter_batch(
        db_session,
        project.id,
        start_chapter=2,
        batch_size=2,
    )

    assert output["status"] == "approval_required"
    assert output["project_id"] == project.id
    assert output["target_type"] == "background_task_enqueue"
    assert output["plan_hash"]
    assert output["enqueue_preview"]["status"] == "confirmation_required"
    assert output["enqueue_preview"]["batch"]["chapter_indexes"] == [2, 3]
    step = output["agent_plan"]["steps"][0]
    assert {
        key: value
        for key, value in step.items()
        if key not in {"mutation_fingerprint", "tool_call_id", "resource_binding"}
    } == {
        "step_index": 1,
        "step_id": f"direct-enqueue-longform-chapter-batch:{project.id}:{output['plan_hash']}",
        "tool_name": "enqueue_longform_chapter_batch",
        "approval_executor_tool_name": "execute_enqueue_longform_chapter_batch_with_approval",
        "params": {"start_chapter": 2, "batch_size": 2, "plan_hash": output["plan_hash"]},
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "reason": "将长篇章节批次计划写入后台任务队列。",
    }
    assert step["mutation_fingerprint"]["status"] == "ready"
    assert step["mutation_fingerprint"]["components"]["target_type"] == "background_task_enqueue"
    assert step["mutation_fingerprint"]["components"]["target_id"] == (
        f"background_task_enqueue:{project.id}:{output['plan_hash']}"
    )
    assert output["agent_plan_approval_contract"]["status"] == "requires_confirmation"
    assert output["agent_plan_approval_contract_hash"].startswith("approval:")
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["enqueue_longform_chapter_batch"]
    assert db_session.query(BackgroundTask).filter(BackgroundTask.project_id == project.id).count() == 0


def test_execute_enqueue_longform_chapter_batch_with_approval_blocks_without_confirmation(db_session):
    project = Project(name="Blocked Batch Enqueue")
    db_session.add(project)
    db_session.commit()

    output = execute_enqueue_longform_chapter_batch_with_approval(
        db_session,
        project.id,
        start_chapter=2,
        batch_size=2,
        plan_hash="hash-1",
        confirm_execute=False,
        approval_contract_hash=None,
        approval_contract=None,
        approval_tool_metadata_provider=lambda plan: {},
    )

    assert output["status"] == "blocked"
    assert output["reason"] == "confirmation_required"
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["enqueue_longform_chapter_batch"]
    assert db_session.query(BackgroundTask).filter(BackgroundTask.project_id == project.id).count() == 0


def test_execute_enqueue_longform_chapter_batch_with_approval_runs_after_contract_verification(db_session):
    project = Project(name="Approved Batch Enqueue")
    db_session.add(project)
    db_session.commit()
    prepared = prepare_enqueue_longform_chapter_batch(
        db_session,
        project.id,
        start_chapter=2,
        batch_size=2,
    )

    output = execute_enqueue_longform_chapter_batch_with_approval(
        db_session,
        project.id,
        start_chapter=2,
        batch_size=2,
        plan_hash=prepared["plan_hash"],
        confirm_execute=True,
        approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
        approval_contract=prepared["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: {
            "enqueue_longform_chapter_batch": {
                "tool_name": "enqueue_longform_chapter_batch",
                "tool_exists": True,
                "adapter_exists": True,
                "adapter_type": "approval_wrapper",
                "handler_name": "_execute_enqueue_longform_chapter_batch_with_approval",
                "mutability": "write",
                "requires_confirmation": True,
                "required_fields": [],
            }
        },
    )

    task = db_session.query(BackgroundTask).filter(BackgroundTask.project_id == project.id).one()
    assert output["status"] == "queued"
    assert output["task"]["id"] == task.id
    assert output["task"]["chapter_range"] == {"start": 2, "end": 3}
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["side_effects"]["executed"] == ["enqueue_longform_chapter_batch"]

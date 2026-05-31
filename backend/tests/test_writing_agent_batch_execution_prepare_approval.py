from __future__ import annotations

from app.models import BackgroundTask, Project
from app.services.writing_agent.batch_enqueue import BATCH_TASK_TYPE
from app.services.writing_agent.batch_execution_prepare_approval import (
    execute_longform_chapter_batch_execution_prepare_with_approval,
    prepare_longform_chapter_batch_execution_prepare,
)


def test_prepare_longform_chapter_batch_execution_prepare_returns_agent_contract_without_manifest_write(db_session):
    project, task = _seed_ready_preflight_task(db_session)

    output = prepare_longform_chapter_batch_execution_prepare(db_session, project.id, task_id=task.id)

    db_session.refresh(task)
    assert output["status"] == "approval_required"
    assert output["project_id"] == project.id
    assert output["target_type"] == "background_task_execution_prepare"
    assert output["task"]["id"] == task.id
    assert output["execution_prepare_preview"]["status"] == "blocked"
    assert output["execution_prepare_preview"]["reason"] == "prepare_confirmation_required"
    step = output["agent_plan"]["steps"][0]
    assert step["tool_name"] == "prepare_longform_chapter_batch_execution"
    assert step["approval_executor_tool_name"] == "execute_longform_chapter_batch_execution_prepare_with_approval"
    assert step["params"] == {"task_id": task.id}
    assert step["mutation_fingerprint"]["status"] == "ready"
    assert step["mutation_fingerprint"]["components"]["target_type"] == "background_task_execution_prepare"
    assert step["mutation_fingerprint"]["components"]["target_id"] == f"background_task_execution_prepare:{task.id}"
    assert output["agent_plan_approval_contract"]["status"] == "requires_confirmation"
    assert output["required_confirmation"] == {
        "confirm_execute": True,
        "approval_contract_hash": output["agent_plan_approval_contract_hash"],
    }
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["background_task_result_execution_prepare"]
    assert "attempt_manifest" not in (task.result or {})
    assert "approval_contract" not in (task.result or {})


def test_execute_longform_chapter_batch_execution_prepare_with_approval_blocks_without_confirmation(db_session):
    project, task = _seed_ready_preflight_task(db_session)

    output = execute_longform_chapter_batch_execution_prepare_with_approval(
        db_session,
        project.id,
        task_id=task.id,
        confirm_execute=False,
        approval_contract_hash=None,
        approval_contract=None,
        approval_tool_metadata_provider=lambda plan: {},
    )

    db_session.refresh(task)
    assert output["status"] == "blocked"
    assert output["reason"] == "confirmation_required"
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["background_task_result_execution_prepare"]
    assert "attempt_manifest" not in (task.result or {})


def test_execute_longform_chapter_batch_execution_prepare_with_approval_writes_manifest_after_contract_verification(
    db_session,
):
    project, task = _seed_ready_preflight_task(db_session)
    prepared = prepare_longform_chapter_batch_execution_prepare(db_session, project.id, task_id=task.id)

    output = execute_longform_chapter_batch_execution_prepare_with_approval(
        db_session,
        project.id,
        task_id=task.id,
        confirm_execute=True,
        approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
        approval_contract=prepared["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: {
            "prepare_longform_chapter_batch_execution": {
                "tool_name": "prepare_longform_chapter_batch_execution",
                "tool_exists": True,
                "adapter_exists": True,
                "adapter_type": "approval_wrapper",
                "handler_name": "_prepare_longform_chapter_batch_execution",
                "mutability": "guarded_write",
                "requires_confirmation": True,
                "required_fields": ["task_id"],
            }
        },
    )

    db_session.refresh(task)
    assert output["status"] == "approval_required"
    assert output["attempt_manifest_hash"]
    assert output["approval_contract_hash"]
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["side_effects"]["executed"] == ["background_task_result_execution_prepare"]
    assert task.result["attempt_manifest"]["hash"] == output["attempt_manifest_hash"]
    assert task.result["approval_contract"]["hash"] == output["approval_contract_hash"]


def _seed_ready_preflight_task(db_session) -> tuple[Project, BackgroundTask]:
    project = Project(name="Approved Batch Execution Prepare")
    db_session.add(project)
    db_session.flush()
    task = BackgroundTask(
        project_id=project.id,
        task_type=BATCH_TASK_TYPE,
        status="pending",
        payload={
            "plan_hash": "plan-execution-prepare-1",
            "chapter_range": {"start": 2, "end": 2},
            "batch": {"start_chapter": 2, "end_chapter": 2, "chapter_indexes": [2]},
            "dag": {"nodes": [{"node_id": "chapter_generation"}], "edges": []},
            "queue_policy": {"resume_strategy": "background_task_chapter_range"},
        },
    )
    db_session.add(task)
    db_session.flush()
    task.result = {
        "preflight_checkpoint": {
            "version": "phase60.longform_batch_execute_preflight.v1",
            "checkpointed_at": "2026-05-30T00:00:00+00:00",
            "task_id": task.id,
            "status": "ready",
            "safe_nodes_executed": ["preflight_gate"],
            "stopped_before_node": "chapter_generation",
            "generation_started": False,
            "selected_chapter_indexes": [2],
            "ready_chapter_indexes": [2],
            "blocked_chapter_indexes": [],
            "chapter_preflights": [{"chapter_index": 2, "status": "ready"}],
        },
        "execution_checkpoints": [],
    }
    db_session.add(task)
    db_session.commit()
    db_session.refresh(project)
    db_session.refresh(task)
    return project, task

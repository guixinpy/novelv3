import pytest

from app.models import Project, WritingAgentRun
from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.agent_worker_recovery import inspect_agent_worker_orphan_recovery
from app.services.writing_agent.tool_executor import execute_writing_agent_tool
from app.services.writing_agent.tool_adapter_types import WritingAgentToolContext


def test_inspect_agent_worker_orphan_recovery_detects_missing_parent_run(db_session):
    project = Project(name="Worker Orphan Recovery")
    db_session.add(project)
    db_session.flush()
    worker_run = WritingAgentRun(
        project_id=project.id,
        goal="孤兒 memory worker",
        status="running",
        input={
            "planner": {
                "agent_profile": "memory_worker",
                "source_run_id": "missing-parent-run",
                "worker_dispatch": {"worker": "memory_worker"},
            }
        },
    )
    db_session.add(worker_run)
    db_session.commit()

    recovery = inspect_agent_worker_orphan_recovery(db_session, project.id)

    assert recovery["status"] == "needs_attention"
    assert recovery["summary"] == {
        "active_worker_runs": 1,
        "orphan_worker_runs": 1,
        "recovery_actions": 1,
    }
    assert recovery["orphan_worker_runs"] == [
        {
            "run_id": worker_run.id,
            "agent_profile": "memory_worker",
            "run_status": "running",
            "parent_run_id": "missing-parent-run",
            "parent_status": "missing",
            "background_task_id": None,
            "background_task_status": None,
            "reason_code": "worker_parent_run_missing",
        }
    ]
    assert recovery["recovery_actions"] == [
        {
            "action": "mark_worker_run_blocked",
            "run_id": worker_run.id,
            "reason_code": "worker_parent_run_missing",
            "preview_only": True,
        }
    ]
    assert recovery["recommended_tools"] == ["inspect_agent_trace_audit", "plan_recovery_tools"]


def test_inspect_agent_worker_orphan_recovery_plans_redispatch_from_failed_parent(db_session):
    project = Project(name="Worker Orphan Redispatch")
    db_session.add(project)
    db_session.flush()
    parent_run = WritingAgentRun(
        project_id=project.id,
        goal="审稿第2章",
        status="failed",
        input={"tools": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 2}}]},
    )
    db_session.add(parent_run)
    db_session.flush()
    worker_run = WritingAgentRun(
        project_id=project.id,
        goal="reviewer worker still running",
        status="running",
        input={
            "planner": {
                "agent_profile": "reviewer_worker",
                "source_run_id": parent_run.id,
                "worker_dispatch": {"worker": "reviewer_worker", "parent_run_id": parent_run.id},
            }
        },
    )
    db_session.add(worker_run)
    db_session.commit()

    recovery = inspect_agent_worker_orphan_recovery(db_session, project.id)

    assert recovery["status"] == "needs_attention"
    assert recovery["summary"] == {
        "active_worker_runs": 1,
        "orphan_worker_runs": 1,
        "recovery_actions": 2,
    }
    assert recovery["orphan_worker_runs"][0]["reason_code"] == "worker_parent_run_terminal"
    assert recovery["orphan_worker_runs"][0]["parent_status"] == "failed"
    assert recovery["recovery_actions"][1] == {
        "action": "redispatch_worker_tasks",
        "tool_name": "inspect_agent_worker_dispatch",
        "params": {
            "parent_run_id": parent_run.id,
            "tasks": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 2}}],
        },
        "preview_only": True,
    }


@pytest.mark.asyncio
async def test_inspect_agent_worker_dispatch_includes_orphan_recovery_audit(db_session):
    project = Project(name="Worker Dispatch Orphan Audit")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        WritingAgentRun(
            project_id=project.id,
            goal="孤兒 reviewer worker",
            status="pending",
            input={
                "planner": {
                    "agent_profile": "reviewer_worker",
                    "source_run_id": "missing-review-parent",
                    "worker_dispatch": {"worker": "reviewer_worker"},
                }
            },
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-worker-audit"),
        WritingAgentToolRequest(
            tool_name="inspect_agent_worker_dispatch",
            params={"tasks": [{"tool_name": "review_chapter_quality", "params": {"chapter_index": 2}}]},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["orphan_recovery"]["status"] == "needs_attention"
    assert result.output["orphan_recovery"]["summary"]["orphan_worker_runs"] == 1

import pytest

from app.models import Project
from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_adapter_types import WritingAgentToolContext
from app.services.writing_agent.tool_executor import (
    execute_writing_agent_tool,
    writing_agent_tool_adapter_metadata,
)
from app.services.writing_agent.tool_lifecycle_hooks import (
    TOOL_LIFECYCLE_HOOKS_VERSION,
    run_after_tool_call_hooks,
    run_before_tool_call_hooks,
    run_tool_error_hooks,
)
from app.services.writing_agent.tool_registry import get_agent_tool_descriptor


def test_before_tool_call_hooks_deny_child_agent_guarded_write(db_session):
    project = Project(name="Lifecycle Guarded Write")
    db_session.add(project)
    db_session.commit()
    tool = WritingAgentToolRequest(
        tool_name="execute_generate_chapter_with_approval",
        params={
            "agent_profile": "reviewer_worker",
            "chapter_index": 2,
            "confirm_execute": True,
            "approval_contract_hash": "approval:abc",
            "approval_contract": {"status": "requires_confirmation"},
        },
    )

    decision = run_before_tool_call_hooks(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-lifecycle-before"),
        tool,
        descriptor=get_agent_tool_descriptor(tool.tool_name),
        adapter_metadata=writing_agent_tool_adapter_metadata(tool.tool_name),
    )

    assert decision["version"] == TOOL_LIFECYCLE_HOOKS_VERSION
    assert decision["hook"] == "before_tool_call"
    assert decision["allow_call"] is False
    assert decision["status"] == "denied"
    assert decision["reason_code"] == "child_agent_guarded_write_denied"
    assert decision["events"] == [
        {
            "event_type": "tool_call_before",
            "tool_name": "execute_generate_chapter_with_approval",
            "agent_profile": "reviewer_worker",
            "mutability": "guarded_write",
            "requires_confirmation": True,
            "status": "denied",
            "allow_call": False,
            "reason_code": "child_agent_guarded_write_denied",
        }
    ]


def test_after_and_error_tool_hooks_emit_event_envelopes(db_session):
    project = Project(name="Lifecycle Event Envelope")
    db_session.add(project)
    db_session.commit()
    context = WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-lifecycle-events")
    tool = WritingAgentToolRequest(tool_name="review_chapter_quality", params={"chapter_index": 3})
    descriptor = get_agent_tool_descriptor(tool.tool_name)
    adapter_metadata = writing_agent_tool_adapter_metadata(tool.tool_name)

    after = run_after_tool_call_hooks(
        context,
        tool,
        {"status": "completed", "chapter_index": 3},
        descriptor=descriptor,
        adapter_metadata=adapter_metadata,
    )
    error = run_tool_error_hooks(
        context,
        tool,
        RuntimeError("adapter boom"),
        descriptor=descriptor,
        adapter_metadata=adapter_metadata,
    )

    assert after["version"] == TOOL_LIFECYCLE_HOOKS_VERSION
    assert after["hook"] == "after_tool_call"
    assert after["events"] == [
        {
            "event_type": "tool_call_after",
            "tool_name": "review_chapter_quality",
            "agent_profile": None,
            "mutability": "read",
            "requires_confirmation": False,
            "status": "completed",
            "result_status": "completed",
            "output_keys": ["chapter_index", "status"],
        }
    ]
    assert error["version"] == TOOL_LIFECYCLE_HOOKS_VERSION
    assert error["hook"] == "on_tool_error"
    assert error["events"] == [
        {
            "event_type": "tool_call_error",
            "tool_name": "review_chapter_quality",
            "agent_profile": None,
            "mutability": "read",
            "requires_confirmation": False,
            "status": "failed",
            "error_type": "RuntimeError",
            "message": "adapter boom",
        }
    ]


@pytest.mark.asyncio
async def test_tool_executor_blocks_child_agent_guarded_write_before_adapter(db_session, monkeypatch):
    project = Project(name="Lifecycle Executor Guard")
    db_session.add(project)
    db_session.commit()

    async def unexpected_execute(*args, **kwargs):
        raise AssertionError("adapter should not run when before_tool_call denies the tool")

    monkeypatch.setattr(
        "app.services.writing_agent.chapter_generation_execution.execute_generate_chapter_with_approval",
        unexpected_execute,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-lifecycle-denied"),
        WritingAgentToolRequest(
            tool_name="execute_generate_chapter_with_approval",
            params={
                "agent_profile": "reviewer_worker",
                "chapter_index": 2,
                "confirm_execute": True,
                "approval_contract_hash": "approval:abc",
                "approval_contract": {"status": "requires_confirmation"},
            },
        ),
    )

    assert result.handled is True
    assert result.output == {
        "status": "blocked",
        "error": "Tool lifecycle hook denied execution",
        "reason_code": "child_agent_guarded_write_denied",
        "tool_name": "execute_generate_chapter_with_approval",
        "agent_profile": "reviewer_worker",
        "write_performed": False,
    }
    assert result.lifecycle_hooks["before"]["allow_call"] is False


def test_agent_run_step_metadata_includes_tool_lifecycle_hooks(client, db_session):
    project = Project(name="Lifecycle Step Metadata")
    db_session.add(project)
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "查看工具生命周期元数据",
            "tools": [{"tool_name": "describe_agent_tools", "params": {}}],
        },
    )

    assert response.status_code == 200
    envelope = response.json()["steps"][0]["output"]["agent_tool_result"]
    lifecycle_hooks = envelope["tool_lifecycle_hooks"]
    assert lifecycle_hooks["version"] == TOOL_LIFECYCLE_HOOKS_VERSION
    assert lifecycle_hooks["before"]["allow_call"] is True
    assert lifecycle_hooks["after"]["events"][0]["event_type"] == "tool_call_after"
    assert lifecycle_hooks["after"]["events"][0]["tool_name"] == "describe_agent_tools"

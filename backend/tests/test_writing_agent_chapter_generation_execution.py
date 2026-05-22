from __future__ import annotations

import pytest

from app.models import Project
from app.services.writing_agent.chapter_generation_execution import (
    execute_generate_chapter_with_approval,
    prepare_generate_chapter_execution,
)


def test_prepare_generate_chapter_execution_returns_agent_approval_contract(db_session):
    project = Project(name="Prepare Direct Chapter")
    db_session.add(project)
    db_session.commit()

    output = prepare_generate_chapter_execution(db_session, project.id, chapter_index=2)

    assert output["status"] == "approval_required"
    assert output["chapter_index"] == 2
    assert output["agent_plan"]["steps"] == [
        {
            "step_index": 1,
            "step_id": f"direct-generate:{project.id}:chapter:2",
            "tool_name": "generate_chapter",
            "params": {"chapter_index": 2},
            "mutability": "write",
            "requires_confirmation": True,
            "reason": "直接生成指定章节正文。",
        }
    ]
    assert output["agent_plan_approval_contract"]["status"] == "requires_confirmation"
    assert output["agent_plan_approval_contract_hash"].startswith("approval:")
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["generate_chapter"]


@pytest.mark.asyncio
async def test_execute_generate_chapter_with_approval_blocks_without_confirmation(db_session, monkeypatch):
    project = Project(name="Direct Chapter Missing Approval")
    db_session.add(project)
    db_session.commit()
    calls: list[str] = []

    async def fake_generate(*args, **kwargs):
        calls.append("called")
        return {"status": "success"}

    monkeypatch.setattr("app.services.writing_agent.chapter_generation_tool.execute_generate_chapter_tool", fake_generate)

    output = await execute_generate_chapter_with_approval(
        db_session,
        project.id,
        chapter_index=2,
        confirm_execute=False,
        approval_contract_hash=None,
        approval_contract=None,
        approval_tool_metadata_provider=lambda plan: {},
    )

    assert output["status"] == "blocked"
    assert output["reason"] == "confirmation_required"
    assert output["side_effects"]["executed"] == []
    assert calls == []


@pytest.mark.asyncio
async def test_execute_generate_chapter_with_approval_blocks_stale_contract(db_session, monkeypatch):
    project = Project(name="Direct Chapter Stale Approval")
    db_session.add(project)
    db_session.commit()
    approval = prepare_generate_chapter_execution(db_session, project.id, chapter_index=2)
    calls: list[str] = []

    async def fake_generate(*args, **kwargs):
        calls.append("called")
        return {"status": "success"}

    monkeypatch.setattr("app.services.writing_agent.chapter_generation_tool.execute_generate_chapter_tool", fake_generate)

    output = await execute_generate_chapter_with_approval(
        db_session,
        project.id,
        chapter_index=2,
        confirm_execute=True,
        approval_contract_hash="approval:stale",
        approval_contract=approval["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: {
            "generate_chapter": {
                "tool_exists": True,
                "adapter_exists": True,
                "mutability": "write",
                "requires_confirmation": True,
                "required_fields": [],
            }
        },
    )

    assert output["status"] == "blocked"
    assert output["reason"] == "approval_contract_hash_mismatch"
    assert calls == []


@pytest.mark.asyncio
async def test_execute_generate_chapter_with_approval_runs_after_contract_verification(db_session, monkeypatch):
    project = Project(name="Direct Chapter Approved")
    db_session.add(project)
    db_session.commit()
    approval = prepare_generate_chapter_execution(db_session, project.id, chapter_index=2)
    calls: list[dict] = []

    async def fake_generate(db, project_id: str, *, chapter_index: int, command_args=None, action_params=None):
        calls.append(
            {
                "project_id": project_id,
                "chapter_index": chapter_index,
                "command_args": command_args,
                "action_params": action_params,
            }
        )
        return {"status": "success", "chapter_index": chapter_index, "trace_id": "trace-direct"}

    monkeypatch.setattr("app.services.writing_agent.chapter_generation_tool.execute_generate_chapter_tool", fake_generate)

    output = await execute_generate_chapter_with_approval(
        db_session,
        project.id,
        chapter_index=2,
        command_args="保持悬疑节奏",
        action_params={"chapter_index": 2, "approval_contract_hash": "should-not-forward"},
        confirm_execute=True,
        approval_contract_hash=approval["agent_plan_approval_contract_hash"],
        approval_contract=approval["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: {
            "generate_chapter": {
                "tool_exists": True,
                "adapter_exists": True,
                "mutability": "write",
                "requires_confirmation": True,
                "required_fields": [],
            }
        },
    )

    assert output["status"] == "success"
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert calls == [
        {
            "project_id": project.id,
            "chapter_index": 2,
            "command_args": "保持悬疑节奏",
            "action_params": {"chapter_index": 2},
        }
    ]

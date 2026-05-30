from __future__ import annotations

import pytest

from app.models import Project
from app.services.writing_agent.revision_draft_execution import (
    execute_create_revision_draft_with_approval,
    prepare_create_revision_draft_execution,
)


def test_prepare_create_revision_draft_execution_returns_agent_approval_contract(db_session):
    project = Project(name="Prepare Revision Draft")
    db_session.add(project)
    db_session.commit()

    output = prepare_create_revision_draft_execution(db_session, project.id, chapter_index=3)

    assert output["status"] == "approval_required"
    assert output["project_id"] == project.id
    assert output["chapter_index"] == 3
    step = output["agent_plan"]["steps"][0]
    assert {
        key: value
        for key, value in step.items()
        if key not in {"mutation_fingerprint", "tool_call_id", "resource_binding"}
    } == {
        "step_index": 1,
        "step_id": f"direct-create-revision-draft:{project.id}:chapter:3",
        "tool_name": "create_revision_draft",
        "approval_executor_tool_name": "execute_create_revision_draft_with_approval",
        "params": {"chapter_index": 3},
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "reason": "根据章节修订计划创建非破坏性修订草稿。",
    }
    assert step["mutation_fingerprint"]["status"] == "ready"
    assert step["mutation_fingerprint"]["components"]["target_type"] == "chapter_revision_draft"
    assert step["mutation_fingerprint"]["components"]["target_id"] == "chapter_revision_draft:3"
    assert output["agent_plan_approval_contract"]["status"] == "requires_confirmation"
    assert output["agent_plan_approval_contract_hash"].startswith("approval:")
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["create_revision_draft"]


@pytest.mark.asyncio
async def test_execute_create_revision_draft_with_approval_blocks_without_confirmation(db_session, monkeypatch):
    project = Project(name="Blocked Revision Draft")
    db_session.add(project)
    db_session.commit()
    calls: list[int] = []

    def fake_create_revision_draft_tool(db, project_id: str, *, chapter_index: int):
        calls.append(chapter_index)
        return {"status": "drafted", "revision_id": "rev-1"}

    monkeypatch.setattr(
        "app.services.writing_agent.revision_draft_execution.create_revision_draft_tool",
        fake_create_revision_draft_tool,
    )

    output = execute_create_revision_draft_with_approval(
        db_session,
        project.id,
        chapter_index=3,
        confirm_execute=False,
        approval_contract_hash=None,
        approval_contract=None,
        approval_tool_metadata_provider=lambda plan: {},
    )

    assert output["status"] == "blocked"
    assert output["reason"] == "confirmation_required"
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["create_revision_draft"]
    assert calls == []


def test_execute_create_revision_draft_with_approval_runs_after_contract_verification(db_session, monkeypatch):
    project = Project(name="Approved Revision Draft")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int]] = []

    def fake_create_revision_draft_tool(db, project_id: str, *, chapter_index: int):
        calls.append((project_id, chapter_index))
        return {
            "status": "drafted",
            "chapter_index": chapter_index,
            "revision_id": "rev-1",
        }

    monkeypatch.setattr(
        "app.services.writing_agent.revision_draft_execution.create_revision_draft_tool",
        fake_create_revision_draft_tool,
    )
    prepared = prepare_create_revision_draft_execution(db_session, project.id, chapter_index=3)

    output = execute_create_revision_draft_with_approval(
        db_session,
        project.id,
        chapter_index=3,
        confirm_execute=True,
        approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
        approval_contract=prepared["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: {
            "create_revision_draft": {
                "tool_name": "create_revision_draft",
                "tool_exists": True,
                "adapter_exists": True,
                "adapter_type": "approval_wrapper",
                "handler_name": "_execute_create_revision_draft_with_approval",
                "mutability": "write",
                "requires_confirmation": True,
                "required_fields": [],
            }
        },
    )

    assert output["status"] == "drafted"
    assert output["chapter_index"] == 3
    assert output["revision_id"] == "rev-1"
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["side_effects"]["executed"] == ["create_revision_draft"]
    assert calls == [(project.id, 3)]

from __future__ import annotations

import pytest

from app.models import Project
from app.services.writing_agent.outline_backfill_execution import (
    execute_backfill_outline_gaps_with_approval,
    prepare_backfill_outline_gaps_execution,
)


def test_prepare_backfill_outline_gaps_execution_returns_agent_approval_contract(db_session):
    project = Project(name="Prepare Outline Backfill")
    db_session.add(project)
    db_session.commit()

    output = prepare_backfill_outline_gaps_execution(db_session, project.id, before_chapter=4)

    assert output["status"] == "approval_required"
    assert output["project_id"] == project.id
    assert output["before_chapter"] == 4
    step = output["agent_plan"]["steps"][0]
    assert {
        key: value
        for key, value in step.items()
        if key not in {"mutation_fingerprint", "tool_call_id", "resource_binding"}
    } == {
        "step_index": 1,
        "step_id": f"direct-backfill-outline-gaps:{project.id}:before:4",
        "tool_name": "backfill_outline_gaps",
        "approval_executor_tool_name": "execute_backfill_outline_gaps_with_approval",
        "params": {"before_chapter": 4},
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "reason": "根据已生成正文回填缺失章节大纲。",
    }
    assert step["mutation_fingerprint"]["status"] == "ready"
    assert step["mutation_fingerprint"]["components"]["target_type"] == "outline"
    assert step["mutation_fingerprint"]["components"]["target_id"] == f"outline_backfill:{project.id}:before:4"
    assert output["agent_plan_approval_contract"]["status"] == "requires_confirmation"
    assert output["agent_plan_approval_contract_hash"].startswith("approval:")
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["backfill_outline_gaps"]


@pytest.mark.asyncio
async def test_execute_backfill_outline_gaps_with_approval_blocks_without_confirmation(db_session, monkeypatch):
    project = Project(name="Blocked Outline Backfill")
    db_session.add(project)
    db_session.commit()
    calls: list[int | None] = []

    def fake_backfill(db, project_id: str, *, before_chapter: int | None):
        calls.append(before_chapter)
        return {"status": "completed"}

    monkeypatch.setattr(
        "app.services.writing_agent.outline_backfill_execution.backfill_missing_outline_chapters_from_content",
        fake_backfill,
    )

    output = execute_backfill_outline_gaps_with_approval(
        db_session,
        project.id,
        before_chapter=4,
        confirm_execute=False,
        approval_contract_hash=None,
        approval_contract=None,
        approval_tool_metadata_provider=lambda plan: {},
    )

    assert output["status"] == "blocked"
    assert output["reason"] == "confirmation_required"
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["backfill_outline_gaps"]
    assert calls == []


def test_execute_backfill_outline_gaps_with_approval_runs_after_contract_verification(db_session, monkeypatch):
    project = Project(name="Approved Outline Backfill")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int | None]] = []

    def fake_backfill(db, project_id: str, *, before_chapter: int | None):
        calls.append((project_id, before_chapter))
        return {
            "status": "completed",
            "outline_id": "outline-1",
            "backfilled_chapter_indexes": [2],
            "missing_before": [2],
        }

    monkeypatch.setattr(
        "app.services.writing_agent.outline_backfill_execution.backfill_missing_outline_chapters_from_content",
        fake_backfill,
    )
    prepared = prepare_backfill_outline_gaps_execution(db_session, project.id, before_chapter=4)

    output = execute_backfill_outline_gaps_with_approval(
        db_session,
        project.id,
        before_chapter=4,
        confirm_execute=True,
        approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
        approval_contract=prepared["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: {
            "backfill_outline_gaps": {
                "tool_name": "backfill_outline_gaps",
                "tool_exists": True,
                "adapter_exists": True,
                "adapter_type": "approval_wrapper",
                "handler_name": "_execute_backfill_outline_gaps_with_approval",
                "mutability": "write",
                "requires_confirmation": True,
                "required_fields": [],
            }
        },
    )

    assert output["status"] == "completed"
    assert output["before_chapter"] == 4
    assert output["backfilled_chapter_indexes"] == [2]
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["side_effects"]["executed"] == ["backfill_outline_gaps"]
    assert calls == [(project.id, 4)]

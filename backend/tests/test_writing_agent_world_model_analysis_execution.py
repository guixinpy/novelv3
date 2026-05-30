from __future__ import annotations

import pytest

from app.models import Project
from app.services.writing_agent.world_model_analysis_execution import (
    execute_analyze_chapter_world_model_with_approval,
    prepare_analyze_chapter_world_model_execution,
)


def test_prepare_analyze_chapter_world_model_execution_returns_agent_approval_contract(db_session):
    project = Project(name="Prepare Chapter World Model Analysis")
    db_session.add(project)
    db_session.commit()

    output = prepare_analyze_chapter_world_model_execution(db_session, project.id, chapter_index=3)

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
        "step_id": f"direct-analyze-world-model:{project.id}:chapter:3",
        "tool_name": "analyze_chapter_world_model",
        "approval_executor_tool_name": "execute_analyze_chapter_world_model_with_approval",
        "params": {"chapter_index": 3},
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "reason": "分析指定章节并写入 Athena 世界模型提案。",
    }
    assert step["mutation_fingerprint"]["status"] == "ready"
    assert step["mutation_fingerprint"]["components"]["target_type"] == "world_model"
    assert step["mutation_fingerprint"]["components"]["target_id"] == f"world_model:{project.id}:chapter:3"
    assert output["agent_plan_approval_contract"]["status"] == "requires_confirmation"
    assert output["agent_plan_approval_contract_hash"].startswith("approval:")
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["analyze_chapter_world_model"]


@pytest.mark.asyncio
async def test_execute_analyze_chapter_world_model_with_approval_blocks_without_confirmation(db_session, monkeypatch):
    project = Project(name="Blocked Chapter World Model Analysis")
    db_session.add(project)
    db_session.commit()
    calls: list[int] = []

    def fake_analysis_tool(db, project_id: str, *, chapter_index: int, run_id=None):
        calls.append(chapter_index)
        return {"status": "completed"}

    monkeypatch.setattr(
        "app.services.writing_agent.world_model_analysis_execution.analyze_chapter_world_model_tool",
        fake_analysis_tool,
    )

    output = execute_analyze_chapter_world_model_with_approval(
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
    assert output["side_effects"]["skipped"] == ["analyze_chapter_world_model"]
    assert calls == []


def test_execute_analyze_chapter_world_model_with_approval_runs_after_contract_verification(db_session, monkeypatch):
    project = Project(name="Approved Chapter World Model Analysis")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int, str | None]] = []

    def fake_analysis_tool(db, project_id: str, *, chapter_index: int, run_id=None):
        calls.append((project_id, chapter_index, run_id))
        return {
            "status": "completed",
            "chapter_index": chapter_index,
            "proposal_bundle_id": "bundle-3",
            "created": {"proposal_items": 2},
            "updated": {"proposal_items": 0},
        }

    monkeypatch.setattr(
        "app.services.writing_agent.world_model_analysis_execution.analyze_chapter_world_model_tool",
        fake_analysis_tool,
    )
    prepared = prepare_analyze_chapter_world_model_execution(db_session, project.id, chapter_index=3)

    output = execute_analyze_chapter_world_model_with_approval(
        db_session,
        project.id,
        chapter_index=3,
        run_id="run-3",
        confirm_execute=True,
        approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
        approval_contract=prepared["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: {
            "analyze_chapter_world_model": {
                "tool_name": "analyze_chapter_world_model",
                "tool_exists": True,
                "adapter_exists": True,
                "adapter_type": "approval_wrapper",
                "handler_name": "_execute_analyze_chapter_world_model_with_approval",
                "mutability": "write",
                "requires_confirmation": True,
                "required_fields": ["chapter_index"],
            }
        },
    )

    assert output["status"] == "completed"
    assert output["chapter_index"] == 3
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["side_effects"]["executed"] == ["analyze_chapter_world_model"]
    assert calls == [(project.id, 3, "run-3")]

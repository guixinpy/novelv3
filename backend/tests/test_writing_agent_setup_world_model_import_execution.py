from __future__ import annotations

import pytest

from app.models import Project
from app.services.writing_agent.setup_world_model_import_execution import (
    execute_import_setup_world_model_with_approval,
    prepare_import_setup_world_model_execution,
)


def test_prepare_import_setup_world_model_execution_returns_agent_approval_contract(db_session):
    project = Project(name="Prepare Setup World Model Import")
    db_session.add(project)
    db_session.commit()

    output = prepare_import_setup_world_model_execution(db_session, project.id)

    assert output["status"] == "approval_required"
    assert output["project_id"] == project.id
    step = output["agent_plan"]["steps"][0]
    assert {
        key: value
        for key, value in step.items()
        if key not in {"mutation_fingerprint", "tool_call_id", "resource_binding"}
    } == {
        "step_index": 1,
        "step_id": f"direct-import-setup-world-model:{project.id}",
        "tool_name": "import_setup_world_model",
        "approval_executor_tool_name": "execute_import_setup_world_model_with_approval",
        "params": {},
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "reason": "将项目设定导入 Athena 世界模型 profile。",
    }
    assert step["mutation_fingerprint"]["status"] == "ready"
    assert step["mutation_fingerprint"]["components"]["target_type"] == "world_model"
    assert step["mutation_fingerprint"]["components"]["target_id"] == f"world_model:{project.id}"
    assert output["agent_plan_approval_contract"]["status"] == "requires_confirmation"
    assert output["agent_plan_approval_contract_hash"].startswith("approval:")
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["import_setup_world_model"]


@pytest.mark.asyncio
async def test_execute_import_setup_world_model_with_approval_blocks_without_confirmation(db_session, monkeypatch):
    project = Project(name="Blocked Setup World Model Import")
    db_session.add(project)
    db_session.commit()
    calls: list[str] = []

    def fake_import_tool(db, project_id: str):
        calls.append(project_id)
        return {"status": "completed"}

    monkeypatch.setattr(
        "app.services.writing_agent.setup_world_model_import_execution.import_setup_world_model_tool",
        fake_import_tool,
    )

    output = execute_import_setup_world_model_with_approval(
        db_session,
        project.id,
        confirm_execute=False,
        approval_contract_hash=None,
        approval_contract=None,
        approval_tool_metadata_provider=lambda plan: {},
    )

    assert output["status"] == "blocked"
    assert output["reason"] == "confirmation_required"
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["import_setup_world_model"]
    assert calls == []


def test_execute_import_setup_world_model_with_approval_runs_after_contract_verification(db_session, monkeypatch):
    project = Project(name="Approved Setup World Model Import")
    db_session.add(project)
    db_session.commit()
    calls: list[str] = []

    def fake_import_tool(db, project_id: str):
        calls.append(project_id)
        return {
            "status": "completed",
            "profile_version": 1,
            "project_profile_version_id": "profile-1",
            "created": {"profile": 1},
            "should_generate_next_chapter": False,
            "recommended_next_tools": ["preflight_writing", "inspect_agent_world_model_route"],
        }

    monkeypatch.setattr(
        "app.services.writing_agent.setup_world_model_import_execution.import_setup_world_model_tool",
        fake_import_tool,
    )
    prepared = prepare_import_setup_world_model_execution(db_session, project.id)

    output = execute_import_setup_world_model_with_approval(
        db_session,
        project.id,
        confirm_execute=True,
        approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
        approval_contract=prepared["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: {
            "import_setup_world_model": {
                "tool_name": "import_setup_world_model",
                "tool_exists": True,
                "adapter_exists": True,
                "adapter_type": "approval_wrapper",
                "handler_name": "_execute_import_setup_world_model_with_approval",
                "mutability": "write",
                "requires_confirmation": True,
                "required_fields": [],
            }
        },
    )

    assert output["status"] == "completed"
    assert output["profile_version"] == 1
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["side_effects"]["executed"] == ["import_setup_world_model"]
    assert calls == [project.id]

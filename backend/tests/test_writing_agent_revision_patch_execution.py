from __future__ import annotations

from app.models import Project
from app.services.writing_agent.revision_patch_execution import (
    execute_apply_planner_revision_patch_with_approval,
    prepare_apply_planner_revision_patch_execution,
)


def test_prepare_apply_planner_revision_patch_execution_returns_agent_approval_contract(db_session):
    project = Project(name="Prepare Revision Patch")
    db_session.add(project)
    db_session.commit()

    output = prepare_apply_planner_revision_patch_execution(
        db_session,
        project.id,
        chapter_index=3,
        revision_id="rev-3",
    )

    assert output["status"] == "approval_required"
    assert output["project_id"] == project.id
    assert output["chapter_index"] == 3
    assert output["revision_id"] == "rev-3"
    step = output["agent_plan"]["steps"][0]
    assert {
        key: value
        for key, value in step.items()
        if key not in {"mutation_fingerprint", "tool_call_id", "resource_binding"}
    } == {
        "step_index": 1,
        "step_id": f"direct-apply-planner-revision-patch:{project.id}:chapter:3:revision:rev-3",
        "tool_name": "apply_planner_revision_patch",
        "approval_executor_tool_name": "execute_apply_planner_revision_patch_with_approval",
        "params": {"chapter_index": 3, "revision_id": "rev-3"},
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "reason": "应用章节修订补丁并写入正文版本。",
    }
    assert step["mutation_fingerprint"]["status"] == "ready"
    assert step["mutation_fingerprint"]["components"]["target_type"] == "chapter_revision_patch"
    assert step["mutation_fingerprint"]["components"]["target_id"] == "chapter_revision_patch:3:rev-3"
    assert output["agent_plan_approval_contract"]["status"] == "requires_confirmation"
    assert output["agent_plan_approval_contract_hash"].startswith("approval:")
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["apply_planner_revision_patch"]


def test_execute_apply_planner_revision_patch_with_approval_blocks_without_confirmation(db_session, monkeypatch):
    project = Project(name="Blocked Revision Patch")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int, str | None]] = []

    def fake_apply_planner_revision_patch_tool(db, project_id: str, *, chapter_index: int, revision_id: str | None):
        calls.append((project_id, chapter_index, revision_id))
        return {"status": "completed", "revision_id": revision_id}

    monkeypatch.setattr(
        "app.services.writing_agent.revision_patch_execution.apply_planner_revision_patch_tool",
        fake_apply_planner_revision_patch_tool,
    )

    output = execute_apply_planner_revision_patch_with_approval(
        db_session,
        project.id,
        chapter_index=3,
        revision_id="rev-3",
        confirm_execute=False,
        approval_contract_hash=None,
        approval_contract=None,
        approval_tool_metadata_provider=lambda plan: {},
    )

    assert output["status"] == "blocked"
    assert output["reason"] == "confirmation_required"
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["apply_planner_revision_patch"]
    assert calls == []


def test_execute_apply_planner_revision_patch_with_approval_runs_after_contract_verification(
    db_session,
    monkeypatch,
):
    project = Project(name="Approved Revision Patch")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int, str | None]] = []

    def fake_apply_planner_revision_patch_tool(db, project_id: str, *, chapter_index: int, revision_id: str | None):
        calls.append((project_id, chapter_index, revision_id))
        return {
            "status": "completed",
            "chapter_index": chapter_index,
            "revision_id": revision_id,
            "result_version_id": "chapter-version-revised",
        }

    monkeypatch.setattr(
        "app.services.writing_agent.revision_patch_execution.apply_planner_revision_patch_tool",
        fake_apply_planner_revision_patch_tool,
    )
    prepared = prepare_apply_planner_revision_patch_execution(
        db_session,
        project.id,
        chapter_index=3,
        revision_id="rev-3",
    )

    output = execute_apply_planner_revision_patch_with_approval(
        db_session,
        project.id,
        chapter_index=3,
        revision_id="rev-3",
        confirm_execute=True,
        approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
        approval_contract=prepared["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: {
            "apply_planner_revision_patch": {
                "tool_name": "apply_planner_revision_patch",
                "tool_exists": True,
                "adapter_exists": True,
                "adapter_type": "approval_wrapper",
                "handler_name": "_execute_apply_planner_revision_patch_with_approval",
                "mutability": "write",
                "requires_confirmation": True,
                "required_fields": [],
            }
        },
    )

    assert output["status"] == "completed"
    assert output["chapter_index"] == 3
    assert output["revision_id"] == "rev-3"
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["side_effects"]["executed"] == ["apply_planner_revision_patch"]
    assert calls == [(project.id, 3, "rev-3")]

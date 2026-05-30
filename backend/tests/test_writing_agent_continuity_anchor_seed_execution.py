from __future__ import annotations

from app.models import Project
from app.services.writing_agent.continuity_anchor_seed_execution import (
    execute_seed_continuity_anchor_proposals_with_approval,
    prepare_seed_continuity_anchor_proposals_execution,
)


def test_prepare_seed_continuity_anchor_proposals_execution_returns_agent_approval_contract(db_session):
    project = Project(name="Prepare Continuity Anchor Seed")
    db_session.add(project)
    db_session.commit()

    output = prepare_seed_continuity_anchor_proposals_execution(db_session, project.id)

    assert output["status"] == "approval_required"
    assert output["project_id"] == project.id
    assert output["target_type"] == "world_model_continuity_anchor_seed"
    step = output["agent_plan"]["steps"][0]
    assert {
        key: value
        for key, value in step.items()
        if key not in {"mutation_fingerprint", "tool_call_id", "resource_binding"}
    } == {
        "step_index": 1,
        "step_id": f"direct-seed-continuity-anchor-proposals:{project.id}",
        "tool_name": "seed_continuity_anchor_proposals",
        "approval_executor_tool_name": "execute_seed_continuity_anchor_proposals_with_approval",
        "params": {},
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "reason": "创建缺失的稳定连续性锚点世界模型提案。",
    }
    assert step["mutation_fingerprint"]["status"] == "ready"
    assert step["mutation_fingerprint"]["components"]["target_type"] == "world_model_continuity_anchor_seed"
    assert step["mutation_fingerprint"]["components"]["target_id"] == (
        f"world_model_continuity_anchor_seed:{project.id}"
    )
    assert output["agent_plan_approval_contract"]["status"] == "requires_confirmation"
    assert output["agent_plan_approval_contract_hash"].startswith("approval:")
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["seed_continuity_anchor_proposals"]


def test_execute_seed_continuity_anchor_proposals_with_approval_blocks_without_confirmation(
    db_session,
    monkeypatch,
):
    project = Project(name="Blocked Continuity Anchor Seed")
    db_session.add(project)
    db_session.commit()
    calls: list[str] = []

    def fake_seed_tool(db, project_id: str):
        calls.append(project_id)
        return {"status": "blocked", "project_id": project_id}

    monkeypatch.setattr(
        "app.services.writing_agent.continuity_anchor_seed_execution.seed_continuity_anchor_proposals_tool",
        fake_seed_tool,
    )

    output = execute_seed_continuity_anchor_proposals_with_approval(
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
    assert output["side_effects"]["skipped"] == ["seed_continuity_anchor_proposals"]
    assert calls == []


def test_execute_seed_continuity_anchor_proposals_with_approval_runs_after_contract_verification(
    db_session,
    monkeypatch,
):
    project = Project(name="Approved Continuity Anchor Seed")
    db_session.add(project)
    db_session.commit()
    calls: list[str] = []

    def fake_seed_tool(db, project_id: str):
        calls.append(project_id)
        return {
            "status": "blocked",
            "project_id": project_id,
            "profile_version": 1,
            "proposal_bundle_id": "bundle-seed",
            "created_item_count": 2,
            "created_items": [],
            "pending_anchor_count": 2,
            "should_generate_next_chapter": False,
            "recommended_actions": ["apply_world_model_proposal_resolution"],
        }

    monkeypatch.setattr(
        "app.services.writing_agent.continuity_anchor_seed_execution.seed_continuity_anchor_proposals_tool",
        fake_seed_tool,
    )
    prepared = prepare_seed_continuity_anchor_proposals_execution(db_session, project.id)

    output = execute_seed_continuity_anchor_proposals_with_approval(
        db_session,
        project.id,
        confirm_execute=True,
        approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
        approval_contract=prepared["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: {
            "seed_continuity_anchor_proposals": {
                "tool_name": "seed_continuity_anchor_proposals",
                "tool_exists": True,
                "adapter_exists": True,
                "adapter_type": "approval_wrapper",
                "handler_name": "_execute_seed_continuity_anchor_proposals_with_approval",
                "mutability": "write",
                "requires_confirmation": True,
                "required_fields": [],
            }
        },
    )

    assert output["status"] == "blocked"
    assert output["created_item_count"] == 2
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["side_effects"]["executed"] == ["seed_continuity_anchor_proposals"]
    assert calls == [project.id]

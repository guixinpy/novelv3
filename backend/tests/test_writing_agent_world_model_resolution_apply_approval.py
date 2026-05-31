from __future__ import annotations

from app.models import Project
from app.services.writing_agent.world_model_resolution_apply_execution import (
    execute_apply_world_model_proposal_resolution_with_approval,
    prepare_apply_world_model_proposal_resolution,
)


def test_prepare_apply_world_model_proposal_resolution_returns_agent_contract_without_apply_write(
    db_session,
    monkeypatch,
):
    project = Project(name="World Apply Approval")
    db_session.add(project)
    db_session.commit()
    decisions = _decisions()
    calls: list[bool] = []

    def fake_apply(db, project_id: str, *, decisions: object, confirm_apply: bool):
        calls.append(confirm_apply)
        return {
            "status": "blocked",
            "project_id": project_id,
            "profile_version": 1,
            "before_actionable_items": 1,
            "after_actionable_items": 1,
            "applied_count": 0,
            "applied_reviews": [],
            "invalid_decision_count": 0,
            "invalid_decisions": [],
            "requires_confirmation": True,
            "can_auto_apply": False,
            "should_generate_next_chapter": False,
            "recommended_actions": ["confirm_apply_world_model_proposal_resolution"],
        }

    monkeypatch.setattr(
        "app.services.writing_agent.world_model_resolution_apply_execution."
        "apply_world_model_proposal_resolution_tool",
        fake_apply,
    )

    output = prepare_apply_world_model_proposal_resolution(db_session, project.id, decisions=decisions)

    assert output["status"] == "approval_required"
    assert output["target_type"] == "world_model_proposal_resolution"
    assert output["apply_preview"]["requires_confirmation"] is True
    step = output["agent_plan"]["steps"][0]
    assert step["tool_name"] == "apply_world_model_proposal_resolution"
    assert step["approval_executor_tool_name"] == "execute_apply_world_model_proposal_resolution_with_approval"
    assert step["params"] == {"decisions": decisions}
    assert step["mutation_fingerprint"]["status"] == "ready"
    assert step["mutation_fingerprint"]["components"]["target_type"] == "world_model_proposal_decisions"
    assert output["agent_plan_approval_contract"]["status"] == "requires_confirmation"
    assert output["required_confirmation"] == {
        "confirm_execute": True,
        "approval_contract_hash": output["agent_plan_approval_contract_hash"],
    }
    assert output["side_effects"] == {"executed": [], "skipped": ["apply_world_model_proposal_resolution"]}
    assert calls == [False]


def test_execute_apply_world_model_proposal_resolution_with_approval_blocks_without_confirmation(db_session):
    project = Project(name="World Apply Blocks")
    db_session.add(project)
    db_session.commit()

    output = execute_apply_world_model_proposal_resolution_with_approval(
        db_session,
        project.id,
        decisions=_decisions(),
        confirm_execute=False,
        approval_contract_hash=None,
        approval_contract=None,
        approval_tool_metadata_provider=lambda plan: {},
    )

    assert output["status"] == "blocked"
    assert output["reason"] == "confirmation_required"
    assert output["side_effects"] == {"executed": [], "skipped": ["apply_world_model_proposal_resolution"]}


def test_execute_apply_world_model_proposal_resolution_with_approval_applies_after_contract_verification(
    db_session,
    monkeypatch,
):
    project = Project(name="World Apply Executes")
    db_session.add(project)
    db_session.commit()
    decisions = _decisions()
    calls: list[tuple[object, bool]] = []

    def fake_apply(db, project_id: str, *, decisions: object, confirm_apply: bool):
        calls.append((decisions, confirm_apply))
        if not confirm_apply:
            return {
                "status": "blocked",
                "project_id": project_id,
                "profile_version": 1,
                "before_actionable_items": 1,
                "after_actionable_items": 1,
                "applied_count": 0,
                "applied_reviews": [],
                "invalid_decision_count": 0,
                "invalid_decisions": [],
                "requires_confirmation": True,
                "can_auto_apply": False,
                "should_generate_next_chapter": False,
                "recommended_actions": ["confirm_apply_world_model_proposal_resolution"],
            }
        return {
            "status": "ready",
            "project_id": project_id,
            "profile_version": 1,
            "before_actionable_items": 1,
            "after_actionable_items": 0,
            "applied_count": 1,
            "applied_reviews": [{"review_id": "review-1", "proposal_item_id": "proposal-1", "action": "reject"}],
            "invalid_decision_count": 0,
            "invalid_decisions": [],
            "requires_confirmation": False,
            "can_auto_apply": False,
            "should_generate_next_chapter": True,
            "recommended_actions": ["preflight_writing"],
        }

    monkeypatch.setattr(
        "app.services.writing_agent.world_model_resolution_apply_execution."
        "apply_world_model_proposal_resolution_tool",
        fake_apply,
    )
    prepared = prepare_apply_world_model_proposal_resolution(db_session, project.id, decisions=decisions)

    output = execute_apply_world_model_proposal_resolution_with_approval(
        db_session,
        project.id,
        decisions=decisions,
        confirm_execute=True,
        approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
        approval_contract=prepared["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: {
            "apply_world_model_proposal_resolution": {
                "tool_name": "apply_world_model_proposal_resolution",
                "tool_exists": True,
                "adapter_exists": True,
                "adapter_type": "approval_wrapper",
                "handler_name": "_apply_world_model_proposal_resolution",
                "mutability": "guarded_write",
                "requires_confirmation": True,
                "required_fields": [],
            }
        },
    )

    assert output["status"] == "ready"
    assert output["applied_count"] == 1
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["side_effects"] == {"executed": ["apply_world_model_proposal_resolution"], "skipped": []}
    assert calls == [(decisions, False), (decisions, True)]


def _decisions() -> list[dict]:
    return [
        {
            "proposal_item_id": "proposal-1",
            "action": "reject",
            "reason": "与已确认的主线事实冲突。",
            "evidence_refs": ["chapter:2"],
        }
    ]

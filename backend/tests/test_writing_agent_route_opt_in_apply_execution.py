import pytest

from app.core.dialog_agent_routes import build_dialog_agent_route
from app.models import Dialog, PendingAction, Project


def _static_adapter_names() -> set[str]:
    return {
        "prepare_generate_setup_execution",
        "execute_generate_setup_with_approval",
        "generate_setup",
    }


def _approval_metadata(plan):
    return {
        "apply_pending_action_route_approval_opt_in": {
            "tool_name": "apply_pending_action_route_approval_opt_in",
            "tool_exists": True,
            "adapter_exists": True,
            "adapter_type": "approval_wrapper",
            "handler_name": "_execute_apply_pending_action_route_approval_opt_in_with_approval",
            "mutability": "guarded_write",
            "requires_confirmation": True,
            "required_fields": [],
        }
    }


def _pending_setup_route(db_session):
    project = Project(name="Route Opt In Apply Execution")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route, "command_args": "雾港悬疑"},
    )
    db_session.add(pending)
    db_session.commit()
    return project, pending


def test_prepare_apply_route_opt_in_returns_route_and_agent_approval_contracts(db_session):
    from app.services.writing_agent.route_opt_in_apply_execution import (
        prepare_apply_pending_action_route_approval_opt_in,
    )

    project, pending = _pending_setup_route(db_session)

    output = prepare_apply_pending_action_route_approval_opt_in(
        db_session,
        project.id,
        pending_action_id=pending.id,
        static_adapter_tool_names_provider=_static_adapter_names,
    )

    assert output["status"] == "approval_required"
    assert output["project_id"] == project.id
    assert output["pending_action_id"] == pending.id
    assert output["target_type"] == "agent_route_approval_opt_in_apply"
    assert output["route_apply_approval_contract_hash"].startswith("approval:")
    assert output["route_apply_approval_contract"]["status"] == "requires_confirmation"
    assert output["agent_plan_approval_contract_hash"].startswith("approval:")
    step = output["agent_plan"]["steps"][0]
    assert {
        key: value
        for key, value in step.items()
        if key not in {"mutation_fingerprint", "tool_call_id", "resource_binding"}
    } == {
        "step_index": 1,
        "step_id": f"direct-apply-route-opt-in:{project.id}:pending:{pending.id}",
        "tool_name": "apply_pending_action_route_approval_opt_in",
        "approval_executor_tool_name": "execute_apply_pending_action_route_approval_opt_in_with_approval",
        "params": {"pending_action_id": pending.id},
        "mutability": "guarded_write",
        "requires_confirmation": True,
        "reason": "将 pending action route 切换到 Agent approval-chain opt-in。",
    }
    assert step["mutation_fingerprint"]["status"] == "ready"
    assert step["mutation_fingerprint"]["components"]["target_type"] == "pending_action_route_opt_in"
    assert step["mutation_fingerprint"]["components"]["target_id"] == f"pending_action_route_opt_in:{pending.id}"
    assert output["resource_binding"]["target_id"] == f"pending_action_route_opt_in:{pending.id}"
    assert output["side_effects"]["executed"] == []
    assert output["side_effects"]["skipped"] == ["apply_pending_action_route_approval_opt_in"]
    assert output["recommended_next_tools"] == ["execute_apply_pending_action_route_approval_opt_in_with_approval"]


def test_execute_apply_route_opt_in_with_approval_blocks_without_agent_confirmation(db_session):
    from app.services.writing_agent.route_opt_in_apply_execution import (
        execute_apply_pending_action_route_approval_opt_in_with_approval,
        prepare_apply_pending_action_route_approval_opt_in,
    )

    project, pending = _pending_setup_route(db_session)
    original_params = dict(pending.params)
    prepared = prepare_apply_pending_action_route_approval_opt_in(
        db_session,
        project.id,
        pending_action_id=pending.id,
        static_adapter_tool_names_provider=_static_adapter_names,
    )

    output = execute_apply_pending_action_route_approval_opt_in_with_approval(
        db_session,
        project.id,
        pending_action_id=pending.id,
        confirm_execute=False,
        route_apply_approval_contract_hash=prepared["route_apply_approval_contract_hash"],
        route_apply_approval_contract=prepared["route_apply_approval_contract"],
        agent_plan_approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
        agent_plan_approval_contract=prepared["agent_plan_approval_contract"],
        static_adapter_tool_names_provider=_static_adapter_names,
        approval_tool_metadata_provider=_approval_metadata,
    )

    db_session.refresh(pending)
    assert output["status"] == "blocked"
    assert output["reason"] == "confirmation_required"
    assert output["write_performed"] is False
    assert output["side_effects"]["executed"] == []
    assert pending.params == original_params


def test_execute_apply_route_opt_in_with_approval_runs_after_dual_contract_verification(db_session):
    from app.services.writing_agent.route_opt_in_apply_execution import (
        execute_apply_pending_action_route_approval_opt_in_with_approval,
        prepare_apply_pending_action_route_approval_opt_in,
    )

    project, pending = _pending_setup_route(db_session)
    prepared = prepare_apply_pending_action_route_approval_opt_in(
        db_session,
        project.id,
        pending_action_id=pending.id,
        static_adapter_tool_names_provider=_static_adapter_names,
    )

    output = execute_apply_pending_action_route_approval_opt_in_with_approval(
        db_session,
        project.id,
        pending_action_id=pending.id,
        confirm_execute=True,
        route_apply_approval_contract_hash=prepared["route_apply_approval_contract_hash"],
        route_apply_approval_contract=prepared["route_apply_approval_contract"],
        agent_plan_approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
        agent_plan_approval_contract=prepared["agent_plan_approval_contract"],
        static_adapter_tool_names_provider=_static_adapter_names,
        approval_tool_metadata_provider=_approval_metadata,
    )

    db_session.expire_all()
    reloaded = db_session.query(PendingAction).filter(PendingAction.id == pending.id).one()
    assert output["status"] == "success"
    assert output["write_performed"] is True
    assert output["params_diff"]["agent_route"]["after"]["use_agent_approval_chain"] is True
    assert output["route_apply_approval_verification"]["status"] == "ready"
    assert output["agent_plan_approval_verification"]["status"] == "ready"
    assert output["execution_resource_binding"]["status"] == "ready"
    assert output["evidence"]["agent_plan_approval_verified"] is True
    assert output["side_effects"]["executed"] == ["apply_pending_action_route_approval_opt_in"]
    assert reloaded.params["agent_route"]["use_agent_approval_chain"] is True
    assert reloaded.status == "pending"

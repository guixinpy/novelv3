import pytest

from app.core.dialog_agent_routes import build_dialog_agent_route
from app.models import Dialog, PendingAction, Project
from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_adapter_types import WritingAgentToolContext
from app.services.writing_agent.tool_executor import execute_writing_agent_tool


@pytest.mark.asyncio
async def test_tool_executor_handles_route_approval_opt_in_plan(db_session):
    project = Project(name="Route Approval Opt In Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-opt-in-plan"),
        WritingAgentToolRequest(
            tool_name="plan_agent_route_approval_opt_in",
            params={
                "action_type": "preview_setup",
                "source": "slash_command",
                "command_name": "setup",
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "ready"
    assert result.output["can_apply"] is True
    assert result.output["write_performed"] is False
    assert result.output["metadata_patch"] == {"use_agent_approval_chain": True}
    assert result.output["route_after"]["use_agent_approval_chain"] is True


@pytest.mark.asyncio
async def test_tool_executor_handles_pending_action_route_opt_in_plan(db_session):
    project = Project(name="Pending Route Approval Opt In Plan")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-pending-route-opt-in-plan"),
        WritingAgentToolRequest(
            tool_name="plan_agent_route_approval_opt_in",
            params={"pending_action_id": pending.id},
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "ready"
    assert result.output["can_apply"] is True
    assert result.output["write_performed"] is False
    assert result.output["metadata_patch"] == {"use_agent_approval_chain": True}
    assert result.output["trace"]["pending_action_id"] == pending.id
    assert result.output["trace"]["pending_action_type"] == "preview_setup"
    assert result.output["trace"]["pending_action_route_source"] == "pending_action"
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_blocks_missing_pending_action_route_opt_in_plan(db_session):
    project = Project(name="Missing Pending Route Approval Opt In Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-missing-pending-route-plan"),
        WritingAgentToolRequest(
            tool_name="plan_agent_route_approval_opt_in",
            params={"pending_action_id": "missing-pending-action"},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["can_apply"] is False
    assert result.output["write_performed"] is False
    assert result.output["risk"]["codes"] == ["pending_action_not_found"]
    assert result.output["trace"]["pending_action_id"] == "missing-pending-action"


@pytest.mark.asyncio
async def test_tool_executor_previews_pending_action_route_opt_in_apply_diff(db_session):
    project = Project(name="Pending Route Opt In Apply Preview")
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
    original_params = dict(pending.params)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-apply-preview"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply",
            params={"pending_action_id": pending.id},
        ),
    )

    db_session.refresh(pending)
    diff = result.output["params_diff"]["agent_route"]
    assert result.handled is True
    assert result.output["status"] == "ready"
    assert result.output["write_performed"] is False
    assert result.output["route_plan"]["status"] == "ready"
    assert result.output["params_before"] == original_params
    assert result.output["params_after"]["agent_route"]["use_agent_approval_chain"] is True
    assert diff["before"] == original_params["agent_route"]
    assert diff["after"]["use_agent_approval_chain"] is True
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_previews_pending_action_route_opt_in_apply_already_declared_no_diff(db_session):
    project = Project(name="Pending Route Opt In Apply Preview Declared")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = {
        **build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup"),
        "use_agent_approval_chain": True,
    }
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-apply-preview-declared"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply",
            params={"pending_action_id": pending.id},
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "already_declared"
    assert result.output["write_performed"] is False
    assert result.output["params_diff"] == {}
    assert result.output["params_after"] == original_params
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_blocks_missing_pending_action_route_opt_in_apply_preview(db_session):
    project = Project(name="Missing Pending Route Opt In Apply Preview")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-missing-route-apply-preview"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply",
            params={"pending_action_id": "missing-pending-action"},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["risk"]["codes"] == ["pending_action_not_found"]
    assert result.output["params_diff"] == {}


@pytest.mark.asyncio
async def test_tool_executor_blocks_pending_action_route_opt_in_apply_preview_without_agent_route(db_session):
    project = Project(name="Pending Route Opt In Apply Preview Missing Route")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "command_args": "雾港悬疑"},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-apply-preview-missing-route"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply",
            params={"pending_action_id": pending.id},
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["risk"]["codes"] == ["pending_action_agent_route_missing"]
    assert result.output["params_diff"] == {}
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_blocks_pending_action_route_opt_in_apply_preview_with_top_level_override(db_session):
    project = Project(name="Pending Route Opt In Apply Preview Override")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route, "use_agent_approval_chain": False},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-apply-preview-override"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply",
            params={"pending_action_id": pending.id},
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["risk"]["codes"] == ["pending_action_top_level_override"]
    assert result.output["params_diff"] == {}
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_previews_pending_route_opt_in_apply_contract(db_session):
    project = Project(name="Pending Route Opt In Apply Contract")
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
    original_params = dict(pending.params)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-contract"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply_contract",
            params={"pending_action_id": pending.id},
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "requires_confirmation"
    assert result.output["required_confirmation"] is True
    assert result.output["approval_contract_hash"].startswith("approval:")
    assert (
        result.output["approval_contract"]["approval"]["approval_contract_hash"]
        == result.output["approval_contract_hash"]
    )
    assert result.output["route_apply_preview"]["status"] == "ready"
    assert result.output["route_apply_preview"]["write_performed"] is False
    assert result.output["approval_contract"]["mutation_target"] == "PendingAction.params.agent_route"
    assert result.output["approval_contract"]["mutation_path"] == "params.agent_route.use_agent_approval_chain"
    assert result.output["recommended_next_tools"] == ["prepare_apply_pending_action_route_approval_opt_in"]
    assert result.output["recommended_next_tool_calls"] == [
        {
            "tool_name": "prepare_apply_pending_action_route_approval_opt_in",
            "visibility": "agent_internal",
            "requires_confirmation": False,
            "params": {
                "pending_action_id": pending.id,
            },
        }
    ]
    assert pending.params == original_params


def test_pending_route_opt_in_apply_contract_hash_is_stable_for_trace_and_unrelated_params():
    from app.services.writing_agent.slash_command_route import (
        build_pending_action_route_approval_opt_in_apply_contract,
        preview_pending_action_route_approval_opt_in_apply,
    )

    route_plan = {
        "status": "ready",
        "version": "phase196.route_approval_opt_in_plan.v1",
        "metadata_patch": {"use_agent_approval_chain": True},
        "route_before": {"agent_tool_name": "generate_setup"},
        "route_after": {"agent_tool_name": "generate_setup", "use_agent_approval_chain": True},
        "preference": {
            "preferred_prepare_tool_name": "prepare_generate_setup_execution",
            "preferred_execute_tool_name": "execute_generate_setup_with_approval",
        },
        "risk": {"codes": []},
        "trace": {"volatile": "a"},
    }
    preview_a = preview_pending_action_route_approval_opt_in_apply(
        pending_action_id="pending-1",
        pending_action_type="preview_setup",
        pending_params={"agent_route": {"agent_tool_name": "generate_setup"}, "command_args": "A"},
        route_plan=route_plan,
    )
    preview_b = preview_pending_action_route_approval_opt_in_apply(
        pending_action_id="pending-1",
        pending_action_type="preview_setup",
        pending_params={"command_args": "B", "agent_route": {"agent_tool_name": "generate_setup"}},
        route_plan={**route_plan, "trace": {"volatile": "b"}},
    )

    contract_a = build_pending_action_route_approval_opt_in_apply_contract(
        project_id="project-1",
        route_apply_preview=preview_a,
    )
    contract_b = build_pending_action_route_approval_opt_in_apply_contract(
        project_id="project-1",
        route_apply_preview=preview_b,
    )

    assert contract_a["approval_contract_hash"] == contract_b["approval_contract_hash"]


def test_pending_route_opt_in_apply_contract_hash_changes_for_target_or_route_after():
    from app.services.writing_agent.slash_command_route import (
        build_pending_action_route_approval_opt_in_apply_contract,
        preview_pending_action_route_approval_opt_in_apply,
    )

    route_plan = {
        "status": "ready",
        "version": "phase196.route_approval_opt_in_plan.v1",
        "metadata_patch": {"use_agent_approval_chain": True},
        "route_before": {"agent_tool_name": "generate_setup"},
        "route_after": {"agent_tool_name": "generate_setup", "use_agent_approval_chain": True},
        "preference": {
            "preferred_prepare_tool_name": "prepare_generate_setup_execution",
            "preferred_execute_tool_name": "execute_generate_setup_with_approval",
        },
        "risk": {"codes": []},
    }
    preview_a = preview_pending_action_route_approval_opt_in_apply(
        pending_action_id="pending-1",
        pending_action_type="preview_setup",
        pending_params={"agent_route": {"agent_tool_name": "generate_setup"}},
        route_plan=route_plan,
    )
    preview_b = preview_pending_action_route_approval_opt_in_apply(
        pending_action_id="pending-2",
        pending_action_type="preview_setup",
        pending_params={"agent_route": {"agent_tool_name": "generate_setup"}},
        route_plan=route_plan,
    )
    preview_c = preview_pending_action_route_approval_opt_in_apply(
        pending_action_id="pending-1",
        pending_action_type="preview_setup",
        pending_params={"agent_route": {"agent_tool_name": "generate_setup"}},
        route_plan={
            **route_plan,
            "route_after": {
                "agent_tool_name": "generate_setup",
                "use_agent_approval_chain": True,
                "source": "slash_command",
            },
        },
    )

    contract_a = build_pending_action_route_approval_opt_in_apply_contract(
        project_id="project-1",
        route_apply_preview=preview_a,
    )
    contract_b = build_pending_action_route_approval_opt_in_apply_contract(
        project_id="project-1",
        route_apply_preview=preview_b,
    )
    contract_c = build_pending_action_route_approval_opt_in_apply_contract(
        project_id="project-1",
        route_apply_preview=preview_c,
    )

    assert contract_a["approval_contract_hash"] != contract_b["approval_contract_hash"]
    assert contract_a["approval_contract_hash"] != contract_c["approval_contract_hash"]


@pytest.mark.asyncio
async def test_tool_executor_blocks_pending_route_opt_in_apply_contract_when_preview_blocked(db_session):
    project = Project(name="Blocked Pending Route Opt In Apply Contract")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-contract-blocked"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply_contract",
            params={"pending_action_id": "missing-pending-action"},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["required_confirmation"] is False
    assert result.output["approval_contract_hash"] is None
    assert result.output["risk"]["codes"] == ["pending_action_not_found"]
    assert result.output["recommended_next_tools"] == []
    assert result.output["recommended_next_tool_calls"] == []


@pytest.mark.asyncio
async def test_tool_executor_hides_foreign_non_pending_route_opt_in_apply_contract_params(db_session):
    own_project = Project(name="Own Route Opt In Apply Contract")
    foreign_project = Project(name="Foreign Route Opt In Apply Contract")
    db_session.add_all([own_project, foreign_project])
    db_session.commit()
    foreign_dialog = Dialog(project_id=foreign_project.id, state="pending_action")
    db_session.add(foreign_dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=foreign_dialog.id,
        type="preview_setup",
        status="resolved",
        params={
            "project_id": foreign_project.id,
            "agent_route": route,
            "command_args": "foreign-secret",
        },
    )
    db_session.add(pending)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=own_project.id, run_id="run-route-contract-foreign"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply_contract",
            params={"pending_action_id": pending.id},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["required_confirmation"] is False
    assert result.output["approval_contract_hash"] is None
    assert result.output["risk"]["codes"] == ["pending_action_not_found"]
    assert result.output["route_apply_preview"]["params_before"] == {}
    assert result.output["route_apply_preview"]["params_after"] == {}
    assert result.output["recommended_next_tools"] == []
    assert result.output["recommended_next_tool_calls"] == []
    assert "foreign-secret" not in str(result.output)


@pytest.mark.asyncio
async def test_tool_executor_does_not_require_route_opt_in_apply_contract_for_already_declared(db_session):
    project = Project(name="Noop Pending Route Opt In Apply Contract")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = {
        **build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup"),
        "use_agent_approval_chain": True,
    }
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route},
    )
    db_session.add(pending)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-contract-noop"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply_contract",
            params={"pending_action_id": pending.id},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "not_required"
    assert result.output["required_confirmation"] is False
    assert result.output["approval_contract_hash"] is None
    assert result.output["route_apply_preview"]["status"] == "already_declared"
    assert result.output["recommended_next_tools"] == []
    assert result.output["recommended_next_tool_calls"] == []

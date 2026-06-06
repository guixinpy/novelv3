from datetime import datetime

import pytest

from app.core.dialog_agent_routes import build_dialog_agent_route
from app.models import Dialog, PendingAction, Project
from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_adapter_types import WritingAgentToolContext
from app.services.writing_agent.tool_executor import execute_writing_agent_tool


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_updates_pending_params(db_session):
    project = Project(name="Apply Route Opt In Approval")
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
    contract = await _preview_route_opt_in_apply_contract(db_session, project.id, pending.id)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": contract["approval_contract_hash"],
                "approval_contract": contract["approval_contract"],
            },
        ),
    )

    db_session.expire_all()
    reloaded = db_session.query(PendingAction).filter(PendingAction.id == pending.id).first()
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["write_performed"] is False
    assert result.output["required_approval"]["prepare_tool"] == "prepare_apply_pending_action_route_approval_opt_in"
    assert result.output["required_approval"]["execute_tool"] == (
        "execute_apply_pending_action_route_approval_opt_in_with_approval"
    )
    assert reloaded.params == pending.params
    assert reloaded.status == "pending"


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_requires_confirmation(db_session):
    project = Project(name="Apply Route Opt In Approval Confirmation")
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
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-confirm"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={"pending_action_id": pending.id},
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["reason"] == "confirmation_required"
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_blocks_hash_mismatch(db_session):
    project = Project(name="Apply Route Opt In Approval Hash")
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
    contract = await _preview_route_opt_in_apply_contract(db_session, project.id, pending.id)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-hash"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": "approval:mismatch",
                "approval_contract": contract["approval_contract"],
            },
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["reason"] == "approval_contract_hash_mismatch"
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_blocks_contract_snapshot_mismatch(db_session):
    project = Project(name="Apply Route Opt In Approval Snapshot")
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
    contract = await _preview_route_opt_in_apply_contract(db_session, project.id, pending.id)
    tampered_contract = {**contract["approval_contract"], "mutation_path": "params.agent_route.tampered"}

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-snapshot"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": contract["approval_contract_hash"],
                "approval_contract": tampered_contract,
            },
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["reason"] == "approval_contract_snapshot_mismatch"
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_blocks_stale_pending_status(db_session):
    project = Project(name="Apply Route Opt In Approval Stale")
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
    contract = await _preview_route_opt_in_apply_contract(db_session, project.id, pending.id)
    pending.status = "resolved"
    db_session.add(pending)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-stale"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": contract["approval_contract_hash"],
                "approval_contract": contract["approval_contract"],
            },
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["reason"] == "pending_action_not_pending"
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_blocks_stale_pending_resolved_at(db_session):
    project = Project(name="Apply Route Opt In Approval Resolved At")
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
    contract = await _preview_route_opt_in_apply_contract(db_session, project.id, pending.id)
    pending.resolved_at = datetime.now()
    db_session.add(pending)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-resolved-at"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": contract["approval_contract_hash"],
                "approval_contract": contract["approval_contract"],
            },
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["reason"] == "pending_action_not_pending"
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_blocks_missing_hash_or_contract(db_session):
    project = Project(name="Apply Route Opt In Approval Missing Contract")
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

    missing_hash = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-missing-hash"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract": {"approval": {"approval_contract_hash": "approval:any"}},
            },
        ),
    )
    missing_contract = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-missing-contract"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": "approval:any",
            },
        ),
    )

    db_session.refresh(pending)
    assert missing_hash.handled is True
    assert missing_hash.output["reason"] == "approval_contract_hash_required"
    assert missing_contract.handled is True
    assert missing_contract.output["reason"] == "approval_contract_required"
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_blocks_stale_pending_route_after_contract(db_session):
    project = Project(name="Apply Route Opt In Approval Route Drift")
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
    contract = await _preview_route_opt_in_apply_contract(db_session, project.id, pending.id)
    drifted_route = {**route, "command_name": "setup-drift"}
    pending.params = {"project_id": project.id, "agent_route": drifted_route}
    db_session.add(pending)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-route-drift"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": contract["approval_contract_hash"],
                "approval_contract": contract["approval_contract"],
            },
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["reason"] == "approval_contract_hash_mismatch"
    assert pending.params["agent_route"]["command_name"] == "setup-drift"


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_hides_foreign_pending_params(db_session):
    own_project = Project(name="Own Apply Route Opt In")
    foreign_project = Project(name="Foreign Apply Route Opt In")
    db_session.add_all([own_project, foreign_project])
    db_session.commit()
    foreign_dialog = Dialog(project_id=foreign_project.id, state="pending_action")
    db_session.add(foreign_dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=foreign_dialog.id,
        type="preview_setup",
        params={
            "project_id": foreign_project.id,
            "agent_route": route,
            "command_args": "foreign-secret",
        },
    )
    db_session.add(pending)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=own_project.id, run_id="run-apply-route-opt-in-foreign"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": "approval:any",
                "approval_contract": {"approval": {"approval_contract_hash": "approval:any"}},
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["reason"] == "pending_action_not_found"
    assert "foreign-secret" not in str(result.output)


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_blocks_when_no_diff_required(db_session):
    project = Project(name="Apply Route Opt In Approval No Diff")
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
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-no-diff"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": "approval:any",
                "approval_contract": {"approval": {"approval_contract_hash": "approval:any"}},
            },
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["reason"] == "route_apply_contract_not_required"
    assert pending.params == original_params


async def _preview_route_opt_in_apply_contract(db_session, project_id: str, pending_action_id: str) -> dict:
    preview = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project_id, run_id="run-route-contract-helper"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply_contract",
            params={"pending_action_id": pending_action_id},
        ),
    )
    assert preview.handled is True
    assert preview.output["status"] == "requires_confirmation"
    return preview.output

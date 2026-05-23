from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.dialog_agent_routes import DIALOG_AGENT_ROUTE_APPROVAL_CHAIN_OPT_IN_KEY
from app.models import BackgroundTask, WritingAgentRun, WritingAgentStep
from app.schemas.writing_agent import WritingAgentRunCreate, WritingAgentToolRequest
from app.services.actions.action_result_service import ActionResultService
from app.services.tasks.background_task_service import BackgroundTaskService
from app.services.writing_agent.run_service import WritingAgentRunService

CONTROL_PLANE_VERSION = "phase65.agent_control_plane.v1"
DIALOG_CONTROL_PLANE_PROJECTION_VERSION = "phase191.dialog_control_plane_projection.v1"
AGENT_RUN_TASK_TYPE = "writing_agent_run"
APPROVAL_CHAIN_OPT_IN_PARAM = DIALOG_AGENT_ROUTE_APPROVAL_CHAIN_OPT_IN_KEY
CONTROL_PLANE_PARAM_KEYS = {"project_id", "agent_route", APPROVAL_CHAIN_OPT_IN_PARAM}

SUPPORTED_DIALOG_ACTION_TO_TOOL = {
    "generate_setup": "generate_setup",
    "generate_storyline": "generate_storyline",
    "generate_outline": "generate_outline",
    "generate_chapter": "prepare_generate_chapter_execution",
}
CHAPTER_APPROVAL_EXECUTE_TOOL = "execute_generate_chapter_with_approval"
APPROVED_DIALOG_CONTROL_PLANE_CHAINS = {
    "generate_setup": ("prepare_generate_setup_execution", "execute_generate_setup_with_approval"),
    "generate_storyline": ("prepare_generate_storyline_execution", "execute_generate_storyline_with_approval"),
    "generate_outline": ("prepare_generate_outline_execution", "execute_generate_outline_with_approval"),
    "generate_chapter": ("prepare_generate_chapter_execution", "execute_generate_chapter_with_approval"),
}

DialogAgentRunWork = Callable[[Session, BackgroundTask], Any]


@dataclass(frozen=True)
class DialogAgentRunDispatch:
    run: WritingAgentRun
    task: BackgroundTask
    work: DialogAgentRunWork


def supports_dialog_agent_control_plane(action_type: str | None) -> bool:
    return str(action_type or "").strip() in SUPPORTED_DIALOG_ACTION_TO_TOOL


def inspect_agent_dialog_control_plane_projection(action_type: str | None = None) -> dict[str, Any]:
    selected_action_type = str(action_type or "").strip() or None
    actions = [
        _dialog_control_plane_action_projection(candidate_action_type)
        for candidate_action_type in SUPPORTED_DIALOG_ACTION_TO_TOOL
        if selected_action_type is None or candidate_action_type == selected_action_type
    ]
    return {
        "status": "ready",
        "version": DIALOG_CONTROL_PLANE_PROJECTION_VERSION,
        "summary": {
            "action_count": len(actions),
            "recommended_migration_count": sum(
                1 for action in actions if action["migration_status"] == "recommended_not_applied"
            ),
            "already_approved_count": sum(
                1 for action in actions if action["runtime_already_uses_approval_chain"] is True
            ),
        },
        "actions": actions,
        "trace": {
            "selected_action_type": selected_action_type,
            "runtime_behavior_changed": False,
        },
    }


def prepare_dialog_agent_run_dispatch(
    db: Session,
    *,
    project_id: str,
    dialog_id: str,
    action_type: str,
    command_args: str | None,
    action_params: dict[str, Any] | None,
    request_message_id: str | None = None,
) -> DialogAgentRunDispatch:
    tool = _tool_request_for_action(action_type, command_args=command_args, action_params=action_params)
    tools = [tool]
    payload = WritingAgentRunCreate(
        goal=f"通过对话确认执行 {action_type}",
        entrypoint="dialog_pending_action",
        tools=tools,
        input={
            "control_plane": {
                "version": CONTROL_PLANE_VERSION,
                "source": "dialog_pending_action",
                "action_type": action_type,
            }
        },
    )
    run = WritingAgentRunService(db).create_run(
        project_id,
        payload,
        effective_tools=tools,
        dialog_id=dialog_id,
        request_message_id=request_message_id,
    )
    task = BackgroundTaskService(db).create(
        project_id=project_id,
        task_type=AGENT_RUN_TASK_TYPE,
        payload={
            "agent_run_id": run.id,
            "action_type": action_type,
            "dialog_id": dialog_id,
            "tools": [item.model_dump() for item in tools],
            "control_plane": {"version": CONTROL_PLANE_VERSION},
        },
    )
    run.background_task_id = task.id
    db.add(run)
    db.commit()
    db.refresh(run)
    db.refresh(task)
    return DialogAgentRunDispatch(
        run=run,
        task=task,
        work=build_dialog_agent_run_background_work(
            run_id=run.id,
            tools=[item.model_dump() for item in tools],
            dialog_id=dialog_id,
            action_type=action_type,
            command_args=command_args,
            action_params=action_params,
        ),
    )


def build_dialog_agent_run_background_work(
    *,
    run_id: str,
    tools: list[dict[str, Any]],
    dialog_id: str,
    action_type: str,
    command_args: str | None,
    action_params: dict[str, Any] | None,
) -> DialogAgentRunWork:
    async def _run(db: Session, running_task: BackgroundTask) -> dict[str, Any]:
        parsed_tools = [WritingAgentToolRequest(**tool) for tool in tools]
        run = await WritingAgentRunService(db).execute_run(run_id, parsed_tools)
        completion = _dialog_completion_result(db, run=run, background_task_id=running_task.id)
        message = ActionResultService(db).record_completion(
            action_type=action_type,
            project_id=running_task.project_id,
            dialog_id=dialog_id,
            result=completion,
            command_args=command_args,
            action_params=action_params,
            include_failure_data=True,
        )
        if message is not None:
            run.response_message_id = message.id
            db.add(run)
            db.commit()
        return completion

    return _run


def _tool_request_for_action(
    action_type: str,
    *,
    command_args: str | None,
    action_params: dict[str, Any] | None,
) -> WritingAgentToolRequest:
    params = dict(action_params or {})
    if APPROVAL_CHAIN_OPT_IN_PARAM not in params and _agent_route_requests_approval_chain(params):
        params[APPROVAL_CHAIN_OPT_IN_PARAM] = True
    tool_name = _tool_name_for_action(action_type, params)
    for key in CONTROL_PLANE_PARAM_KEYS:
        params.pop(key, None)
    return WritingAgentToolRequest(
        tool_name=tool_name,
        command_args=command_args,
        params=params,
    )


def _tool_name_for_action(action_type: str, params: dict[str, Any]) -> str:
    if action_type == "generate_chapter" and _has_chapter_approval_contract(params):
        return CHAPTER_APPROVAL_EXECUTE_TOOL
    if params.get(APPROVAL_CHAIN_OPT_IN_PARAM) is True:
        recommended_chain = APPROVED_DIALOG_CONTROL_PLANE_CHAINS.get(action_type)
        if recommended_chain:
            return recommended_chain[0]
    return SUPPORTED_DIALOG_ACTION_TO_TOOL[action_type]


def _agent_route_requests_approval_chain(params: dict[str, Any]) -> bool:
    route = params.get("agent_route")
    return isinstance(route, dict) and route.get(APPROVAL_CHAIN_OPT_IN_PARAM) is True


def _dialog_control_plane_action_projection(action_type: str) -> dict[str, Any]:
    current_runtime_tool = SUPPORTED_DIALOG_ACTION_TO_TOOL[action_type]
    recommended_chain = list(APPROVED_DIALOG_CONTROL_PLANE_CHAINS.get(action_type, (current_runtime_tool,)))
    runtime_already_uses_approval_chain = (
        action_type == "generate_chapter"
        and current_runtime_tool == recommended_chain[0]
        and CHAPTER_APPROVAL_EXECUTE_TOOL == recommended_chain[-1]
    )
    return {
        "action_type": action_type,
        "current_runtime_tool_name": current_runtime_tool,
        "current_approval_execute_tool_name": CHAPTER_APPROVAL_EXECUTE_TOOL
        if action_type == "generate_chapter"
        else None,
        "recommended_tool_chain": recommended_chain,
        "recommended_prepare_tool_name": recommended_chain[0] if len(recommended_chain) > 1 else None,
        "recommended_execute_tool_name": recommended_chain[-1] if len(recommended_chain) > 1 else None,
        "approval_gate_required": len(recommended_chain) > 1,
        "runtime_already_uses_approval_chain": runtime_already_uses_approval_chain,
        "runtime_behavior_changed": False,
        "migration_status": "already_applied"
        if runtime_already_uses_approval_chain
        else "recommended_not_applied"
        if len(recommended_chain) > 1
        else "no_change",
    }


def _has_chapter_approval_contract(params: dict[str, Any]) -> bool:
    return (
        params.get("confirm_execute") is True
        and bool(str(params.get("approval_contract_hash") or "").strip())
        and isinstance(params.get("approval_contract"), dict)
    )


def _dialog_completion_result(db: Session, *, run: WritingAgentRun, background_task_id: str) -> dict[str, Any]:
    step = (
        db.query(WritingAgentStep)
        .filter(WritingAgentStep.run_id == run.id)
        .order_by(WritingAgentStep.step_index.desc(), WritingAgentStep.id.desc())
        .first()
    )
    step_output = step.output if step is not None and isinstance(step.output, dict) else {}
    result = {key: value for key, value in step_output.items() if key != "agent_tool_result"}
    if run.status == "success":
        if result.get("status") != "approval_required":
            result["status"] = "success"
    else:
        result["status"] = run.status if run.status in {"blocked", "failed", "cancelled"} else "failed"
        result["error"] = run.error or result.get("error") or "Agent run did not complete successfully"
    result["agent_run_id"] = run.id
    result["background_task_id"] = background_task_id
    result["control_plane"] = {"version": CONTROL_PLANE_VERSION}
    return result

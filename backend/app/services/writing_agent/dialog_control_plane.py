from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models import BackgroundTask, WritingAgentRun, WritingAgentStep
from app.schemas.writing_agent import WritingAgentRunCreate, WritingAgentToolRequest
from app.services.actions.action_result_service import ActionResultService
from app.services.tasks.background_task_service import BackgroundTaskService
from app.services.writing_agent.run_service import WritingAgentRunService

CONTROL_PLANE_VERSION = "phase65.agent_control_plane.v1"
AGENT_RUN_TASK_TYPE = "writing_agent_run"

SUPPORTED_DIALOG_ACTION_TO_TOOL = {
    "generate_setup": "generate_setup",
    "generate_storyline": "generate_storyline",
    "generate_outline": "generate_outline",
    "generate_chapter": "generate_chapter",
}

DialogAgentRunWork = Callable[[Session, BackgroundTask], Any]


@dataclass(frozen=True)
class DialogAgentRunDispatch:
    run: WritingAgentRun
    task: BackgroundTask
    work: DialogAgentRunWork


def supports_dialog_agent_control_plane(action_type: str | None) -> bool:
    return str(action_type or "").strip() in SUPPORTED_DIALOG_ACTION_TO_TOOL


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
    tool_name = SUPPORTED_DIALOG_ACTION_TO_TOOL[action_type]
    params = dict(action_params or {})
    params.pop("project_id", None)
    return WritingAgentToolRequest(tool_name=tool_name, command_args=command_args, params=params)


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
        result["status"] = "success"
    else:
        result["status"] = run.status if run.status in {"blocked", "failed", "cancelled"} else "failed"
        result["error"] = run.error or result.get("error") or "Agent run did not complete successfully"
    result["agent_run_id"] = run.id
    result["background_task_id"] = background_task_id
    result["control_plane"] = {"version": CONTROL_PLANE_VERSION}
    return result

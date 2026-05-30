from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models import WritingAgentRun
from app.schemas.writing_agent import WritingAgentRunCreate, WritingAgentToolRequest
from app.services.writing_agent.run_service import WritingAgentRunService


@dataclass(frozen=True)
class AgentApiToolRunResult:
    run: WritingAgentRun
    control_plane: dict[str, Any]


async def execute_agent_api_tool(
    db: Session,
    *,
    project_id: str,
    entrypoint: str,
    version: str,
    source: str,
    action_type: str,
    tool_name: str,
    goal: str,
    command_args: str | None = None,
    params: dict[str, Any] | None = None,
    extra_control_plane: dict[str, Any] | None = None,
) -> AgentApiToolRunResult:
    control_plane = {
        "version": version,
        "source": source,
        "action_type": action_type,
        **(extra_control_plane or {}),
    }
    tool = _api_tool_request(
        db,
        project_id=project_id,
        tool_name=tool_name,
        command_args=command_args,
        params=params,
    )
    service = WritingAgentRunService(db)
    run = service.create_run(
        project_id,
        WritingAgentRunCreate(
            goal=goal,
            entrypoint=entrypoint,
            tools=[tool],
            input={"control_plane": control_plane},
        ),
        effective_tools=[tool],
    )
    run = await service.execute_run(run.id, [tool])
    return AgentApiToolRunResult(run=run, control_plane=control_plane)


def _api_tool_request(
    db: Session,
    *,
    project_id: str,
    tool_name: str,
    command_args: str | None,
    params: dict[str, Any] | None,
) -> WritingAgentToolRequest:
    base_params = dict(params or {})
    prepared = _prepare_approved_generation_tool(db, project_id, tool_name=tool_name, command_args=command_args)
    if prepared is None or prepared.get("status") != "approval_required":
        return WritingAgentToolRequest(tool_name=tool_name, command_args=command_args, params=base_params)
    return WritingAgentToolRequest(
        tool_name=str(prepared["execute_tool"]),
        command_args=command_args,
        params={
            **base_params,
            "confirm_execute": True,
            "approval_contract_hash": prepared["approval_contract_hash"],
            "approval_contract": prepared["approval_contract"],
        },
    )


def _prepare_approved_generation_tool(
    db: Session,
    project_id: str,
    *,
    tool_name: str,
    command_args: str | None,
) -> dict[str, Any] | None:
    if tool_name == "generate_setup":
        from app.services.writing_agent.setup_generation_execution import prepare_generate_setup_execution

        return _prepared_tool(
            "execute_generate_setup_with_approval",
            prepare_generate_setup_execution(db, project_id, command_args=command_args),
        )
    if tool_name == "generate_storyline":
        from app.services.writing_agent.storyline_generation_execution import prepare_generate_storyline_execution

        return _prepared_tool(
            "execute_generate_storyline_with_approval",
            prepare_generate_storyline_execution(db, project_id, command_args=command_args),
        )
    if tool_name == "generate_outline":
        from app.services.writing_agent.outline_generation_execution import prepare_generate_outline_execution

        return _prepared_tool(
            "execute_generate_outline_with_approval",
            prepare_generate_outline_execution(db, project_id, command_args=command_args),
        )
    return None


def _prepared_tool(execute_tool: str, prepared: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": prepared.get("status"),
        "execute_tool": execute_tool,
        "approval_contract_hash": prepared.get("agent_plan_approval_contract_hash"),
        "approval_contract": prepared.get("agent_plan_approval_contract"),
    }

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
    tool = WritingAgentToolRequest(
        tool_name=tool_name,
        command_args=command_args,
        params=params or {},
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

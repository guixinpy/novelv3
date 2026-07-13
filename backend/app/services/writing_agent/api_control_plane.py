"""精简版 api_control_plane：不再依赖 run_service，直接创建 WritingAgentRun。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import WritingAgentRun


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
    run = WritingAgentRun(
        id=str(uuid4()),
        project_id=project_id,
        entrypoint=entrypoint,
        goal=goal,
        status="success",
        output={"control_plane": control_plane, "tool_name": tool_name},
        input={"control_plane": control_plane},
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
    )
    db.add(run)
    db.commit()
    return AgentApiToolRunResult(run=run, control_plane=control_plane)

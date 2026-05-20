from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_registry import build_agent_tool_plan, get_agent_tool_descriptor


PreflightWriting = Callable[[str, dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class WritingAgentToolContext:
    db: Session
    project_id: str
    run_id: str | None = None


@dataclass(frozen=True)
class WritingAgentToolExecutionResult:
    handled: bool
    output: dict[str, Any] | None = None


async def execute_writing_agent_tool(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
    *,
    preflight_writing: PreflightWriting | None = None,
) -> WritingAgentToolExecutionResult:
    descriptor = get_agent_tool_descriptor(tool.tool_name)
    if descriptor is None or not descriptor.internal:
        return WritingAgentToolExecutionResult(handled=False)

    if tool.tool_name == "describe_agent_tools":
        chapter_index = _optional_int(tool.params.get("chapter_index"))
        return WritingAgentToolExecutionResult(
            handled=True,
            output=build_agent_tool_plan(context.db, context.project_id, chapter_index=chapter_index),
        )

    if tool.tool_name == "plan_writing_agent_run":
        from app.services.writing_agent.planner import build_writing_agent_run_plan

        chapter_index = _optional_int(tool.params.get("chapter_index"))
        intent = str(tool.params.get("intent") or "").strip() or None
        goal = str(tool.params.get("goal") or tool.command_args or "").strip() or "规划下一步写作"
        return WritingAgentToolExecutionResult(
            handled=True,
            output=build_writing_agent_run_plan(
                context.db,
                context.project_id,
                goal=goal,
                chapter_index=chapter_index,
                intent=intent,
            ),
        )

    if tool.tool_name == "preflight_writing" and preflight_writing is not None:
        return WritingAgentToolExecutionResult(
            handled=True,
            output=preflight_writing(context.project_id, tool.params),
        )

    return WritingAgentToolExecutionResult(handled=False)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

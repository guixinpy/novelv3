from __future__ import annotations

from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_adapter_types import WritingAgentToolAdapter, WritingAgentToolContext


def _plan_chapter_conflict_recovery(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.chapter_conflict_recovery_planner import plan_chapter_conflict_recovery

    return plan_chapter_conflict_recovery(
        context.db,
        context.project_id,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
    )


def _inspect_agent_job_projection(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.agent_job_projection import inspect_agent_job_projection

    return inspect_agent_job_projection(
        context.db,
        context.project_id,
        task_id=str(tool.params.get("task_id") or "").strip() or None,
        task_type=str(tool.params.get("task_type") or "").strip() or None,
        status=str(tool.params.get("status") or "").strip() or None,
        limit=_optional_int(tool.params.get("limit")),
        chapter_index=_optional_int(tool.params.get("chapter_index")),
    )


def _inspect_agent_event_projection(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.agent_event_projection import inspect_agent_event_projection

    return inspect_agent_event_projection(
        context.db,
        context.project_id,
        task_id=str(tool.params.get("task_id") or "").strip() or None,
        run_id=str(tool.params.get("run_id") or "").strip() or None,
        limit=_optional_int(tool.params.get("limit")),
    )


AGENT_TASK_QUEUE_TOOL_ADAPTERS: dict[str, WritingAgentToolAdapter] = {
    "plan_chapter_conflict_recovery": WritingAgentToolAdapter(
        "plan_chapter_conflict_recovery",
        _plan_chapter_conflict_recovery,
        category="task_queue",
        mutability="read",
    ),
    "inspect_agent_job_projection": WritingAgentToolAdapter(
        "inspect_agent_job_projection",
        _inspect_agent_job_projection,
        category="task_queue",
        mutability="read",
    ),
    "inspect_agent_event_projection": WritingAgentToolAdapter(
        "inspect_agent_event_projection",
        _inspect_agent_event_projection,
        category="task_queue",
        mutability="read",
    ),
}


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

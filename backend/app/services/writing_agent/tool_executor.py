from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_registry import build_agent_tool_plan, get_agent_tool_descriptor


PreflightWriting = Callable[[str, dict[str, Any]], dict[str, Any]]
StaticToolAdapter = Callable[["WritingAgentToolContext", WritingAgentToolRequest], dict[str, Any]]


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

    adapter = _STATIC_TOOL_ADAPTERS.get(tool.tool_name)
    if adapter is not None:
        return WritingAgentToolExecutionResult(handled=True, output=adapter(context, tool))

    if tool.tool_name == "preflight_writing" and preflight_writing is not None:
        return WritingAgentToolExecutionResult(
            handled=True,
            output=preflight_writing(context.project_id, tool.params),
        )

    return WritingAgentToolExecutionResult(handled=False)


def static_writing_agent_tool_adapter_names() -> set[str]:
    return set(_STATIC_TOOL_ADAPTERS)


def _describe_agent_tools(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    chapter_index = _optional_int(tool.params.get("chapter_index"))
    return build_agent_tool_plan(context.db, context.project_id, chapter_index=chapter_index)


def _plan_writing_agent_run(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.planner import build_writing_agent_run_plan

    chapter_index = _optional_int(tool.params.get("chapter_index"))
    intent = str(tool.params.get("intent") or "").strip() or None
    goal = str(tool.params.get("goal") or tool.command_args or "").strip() or "规划下一步写作"
    return build_writing_agent_run_plan(
        context.db,
        context.project_id,
        goal=goal,
        chapter_index=chapter_index,
        intent=intent,
    )


def _review_chapter_quality(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.core.chapter_quality_review import review_chapter_quality

    return review_chapter_quality(context.db, context.project_id, _chapter_index(tool))


def _review_chapter_continuity(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.core.chapter_continuity_review import review_chapter_continuity

    lookback = _optional_int(tool.params.get("lookback")) or 20
    return review_chapter_continuity(context.db, context.project_id, _chapter_index(tool), lookback=lookback)


def _plan_chapter_revision(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.core.chapter_revision_planner import plan_chapter_revision

    return plan_chapter_revision(context.db, context.project_id, _chapter_index(tool))


def _review_world_model_proposals(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.core.world_proposal_agent_report import build_world_proposal_agent_report

    return build_world_proposal_agent_report(
        context.db,
        context.project_id,
        offset=_optional_int(tool.params.get("offset")) or 0,
        limit=_optional_int(tool.params.get("limit")) or 50,
    )


def _plan_world_model_proposal_resolution(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.core.world_proposal_resolution_plan import build_world_proposal_resolution_plan

    return build_world_proposal_resolution_plan(
        context.db,
        context.project_id,
        offset=_optional_int(tool.params.get("offset")) or 0,
        limit=_optional_int(tool.params.get("limit")) or 50,
    )


def _preview_world_model_proposal_resolution(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.core.world_proposal_resolution_preview import preview_world_model_proposal_resolution

    decisions = tool.params.get("decisions")
    return preview_world_model_proposal_resolution(
        context.db,
        context.project_id,
        decisions if isinstance(decisions, list) else [],
    )


def _draft_world_model_proposal_resolution_decisions(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.core.world_proposal_resolution_draft import draft_world_model_proposal_resolution_decisions

    predicate_policies = tool.params.get("predicate_policies")
    return draft_world_model_proposal_resolution_decisions(
        context.db,
        context.project_id,
        limit=_optional_int(tool.params.get("limit")) or 50,
        predicate_policies=predicate_policies if isinstance(predicate_policies, dict) else None,
        include_unclassified=tool.params.get("include_unclassified") is True,
    )


_STATIC_TOOL_ADAPTERS: dict[str, StaticToolAdapter] = {
    "describe_agent_tools": _describe_agent_tools,
    "plan_writing_agent_run": _plan_writing_agent_run,
    "review_chapter_quality": _review_chapter_quality,
    "review_chapter_continuity": _review_chapter_continuity,
    "plan_chapter_revision": _plan_chapter_revision,
    "review_world_model_proposals": _review_world_model_proposals,
    "plan_world_model_proposal_resolution": _plan_world_model_proposal_resolution,
    "preview_world_model_proposal_resolution": _preview_world_model_proposal_resolution,
    "draft_world_model_proposal_resolution_decisions": _draft_world_model_proposal_resolution_decisions,
}


def _chapter_index(tool: WritingAgentToolRequest) -> int:
    return int(tool.params.get("chapter_index") or 1)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

from __future__ import annotations

from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_adapter_types import WritingAgentToolAdapter, WritingAgentToolContext


def _import_setup_world_model(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.setup_world_model_import_tool import import_setup_world_model_tool

    return import_setup_world_model_tool(context.db, context.project_id)


def _analyze_chapter_world_model(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.world_model_analysis_tool import analyze_chapter_world_model_tool

    chapter_index = int(tool.params.get("chapter_index") or 1)
    return analyze_chapter_world_model_tool(
        context.db,
        context.project_id,
        chapter_index=chapter_index,
        run_id=context.run_id,
    )


def _review_world_model_proposals(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.core.world_proposal_agent_report import build_world_proposal_agent_report

    return build_world_proposal_agent_report(
        context.db,
        context.project_id,
        offset=_optional_int(tool.params.get("offset")) or 0,
        limit=_optional_int(tool.params.get("limit")) or 50,
    )


def _inspect_agent_world_model_route(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.agent_world_model_route import inspect_agent_world_model_route

    return inspect_agent_world_model_route(
        context.db,
        context.project_id,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
        subject_ref=str(tool.params.get("subject_ref") or "").strip() or None,
        limit=_optional_int(tool.params.get("limit")),
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


def _apply_world_model_proposal_resolution(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.world_model_resolution_apply_tool import apply_world_model_proposal_resolution_tool

    return apply_world_model_proposal_resolution_tool(
        context.db,
        context.project_id,
        decisions=tool.params.get("decisions"),
        confirm_apply=tool.params.get("confirm_apply") is True,
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


def _draft_high_value_world_proposal_resolution_decisions(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.core.high_value_world_proposal_resolution_draft import (
        draft_high_value_world_proposal_resolution_decisions,
    )

    return draft_high_value_world_proposal_resolution_decisions(
        context.db,
        context.project_id,
        limit=_optional_int(tool.params.get("limit")) or 50,
    )


def _seed_continuity_anchor_proposals(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.continuity_anchor_seed_tool import seed_continuity_anchor_proposals_tool

    return seed_continuity_anchor_proposals_tool(context.db, context.project_id)


WORLD_MODEL_AGENT_TOOL_ADAPTERS: dict[str, WritingAgentToolAdapter] = {
    "import_setup_world_model": WritingAgentToolAdapter(
        "import_setup_world_model",
        _import_setup_world_model,
        category="athena_world_model",
        mutability="write",
    ),
    "analyze_chapter_world_model": WritingAgentToolAdapter(
        "analyze_chapter_world_model",
        _analyze_chapter_world_model,
        category="athena_world_model",
        mutability="write",
    ),
    "review_world_model_proposals": WritingAgentToolAdapter(
        "review_world_model_proposals",
        _review_world_model_proposals,
        category="athena_world_model",
        mutability="read",
    ),
    "inspect_agent_world_model_route": WritingAgentToolAdapter(
        "inspect_agent_world_model_route",
        _inspect_agent_world_model_route,
        category="athena_world_model",
        mutability="read",
    ),
    "plan_world_model_proposal_resolution": WritingAgentToolAdapter(
        "plan_world_model_proposal_resolution",
        _plan_world_model_proposal_resolution,
        category="athena_world_model",
        mutability="read",
    ),
    "preview_world_model_proposal_resolution": WritingAgentToolAdapter(
        "preview_world_model_proposal_resolution",
        _preview_world_model_proposal_resolution,
        category="athena_world_model",
        mutability="read",
    ),
    "apply_world_model_proposal_resolution": WritingAgentToolAdapter(
        "apply_world_model_proposal_resolution",
        _apply_world_model_proposal_resolution,
        category="athena_world_model",
        mutability="write",
    ),
    "draft_world_model_proposal_resolution_decisions": WritingAgentToolAdapter(
        "draft_world_model_proposal_resolution_decisions",
        _draft_world_model_proposal_resolution_decisions,
        category="athena_world_model",
        mutability="read",
    ),
    "draft_high_value_world_proposal_resolution_decisions": WritingAgentToolAdapter(
        "draft_high_value_world_proposal_resolution_decisions",
        _draft_high_value_world_proposal_resolution_decisions,
        category="athena_world_model",
        mutability="read",
    ),
    "seed_continuity_anchor_proposals": WritingAgentToolAdapter(
        "seed_continuity_anchor_proposals",
        _seed_continuity_anchor_proposals,
        category="maintenance",
        mutability="write",
    ),
}


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

from __future__ import annotations

from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.approval_tool_metadata import build_approval_tool_metadata_by_name
from app.services.writing_agent.direct_generation_write_guard import approval_required_redirect
from app.services.writing_agent.tool_adapter_types import WritingAgentToolAdapter, WritingAgentToolContext


def _import_setup_world_model(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    return approval_required_redirect(
        project_id=context.project_id,
        tool_name="import_setup_world_model",
        target_type="world_model",
        prepare_tool="prepare_import_setup_world_model_execution",
        execute_tool="execute_import_setup_world_model_with_approval",
    )


def _prepare_import_setup_world_model_execution(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.setup_world_model_import_execution import (
        prepare_import_setup_world_model_execution,
    )

    return prepare_import_setup_world_model_execution(context.db, context.project_id)


def _execute_import_setup_world_model_with_approval(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.setup_world_model_import_execution import (
        execute_import_setup_world_model_with_approval,
    )

    approval_contract = tool.params.get("approval_contract")
    return execute_import_setup_world_model_with_approval(
        context.db,
        context.project_id,
        confirm_execute=tool.params.get("confirm_execute") is True,
        approval_contract_hash=str(tool.params.get("approval_contract_hash") or "").strip() or None,
        approval_contract=approval_contract if isinstance(approval_contract, dict) else None,
        approval_tool_metadata_provider=_world_model_approval_tool_metadata_by_name,
    )


def _analyze_chapter_world_model(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    chapter_index = int(tool.params.get("chapter_index") or 1)
    return approval_required_redirect(
        project_id=context.project_id,
        tool_name="analyze_chapter_world_model",
        target_type="world_model",
        prepare_tool="prepare_analyze_chapter_world_model_execution",
        execute_tool="execute_analyze_chapter_world_model_with_approval",
        extra={"chapter_index": chapter_index},
    )


def _prepare_analyze_chapter_world_model_execution(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.world_model_analysis_execution import (
        prepare_analyze_chapter_world_model_execution,
    )

    chapter_index = int(tool.params.get("chapter_index") or 1)
    return prepare_analyze_chapter_world_model_execution(
        context.db,
        context.project_id,
        chapter_index=chapter_index,
    )


def _execute_analyze_chapter_world_model_with_approval(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.world_model_analysis_execution import (
        execute_analyze_chapter_world_model_with_approval,
    )

    chapter_index = int(tool.params.get("chapter_index") or 1)
    approval_contract = tool.params.get("approval_contract")
    return execute_analyze_chapter_world_model_with_approval(
        context.db,
        context.project_id,
        chapter_index=chapter_index,
        run_id=context.run_id,
        confirm_execute=tool.params.get("confirm_execute") is True,
        approval_contract_hash=str(tool.params.get("approval_contract_hash") or "").strip() or None,
        approval_contract=approval_contract if isinstance(approval_contract, dict) else None,
        approval_tool_metadata_provider=_world_model_approval_tool_metadata_by_name,
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


async def _inspect_agent_world_model_semantic_check(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.world_model_semantic_check import inspect_agent_world_model_semantic_check

    return await inspect_agent_world_model_semantic_check(
        context.db,
        context.project_id,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
        subject_ref=str(tool.params.get("subject_ref") or "").strip() or None,
        max_facts=_optional_int(tool.params.get("max_facts")),
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
    return approval_required_redirect(
        project_id=context.project_id,
        tool_name="apply_world_model_proposal_resolution",
        target_type="world_model_proposal_resolution",
        prepare_tool="prepare_apply_world_model_proposal_resolution",
        execute_tool="execute_apply_world_model_proposal_resolution_with_approval",
        extra={"decisions": tool.params.get("decisions") if isinstance(tool.params.get("decisions"), list) else []},
    )


def _prepare_apply_world_model_proposal_resolution(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.world_model_resolution_apply_execution import (
        prepare_apply_world_model_proposal_resolution,
    )

    return prepare_apply_world_model_proposal_resolution(
        context.db,
        context.project_id,
        decisions=tool.params.get("decisions"),
    )


def _execute_apply_world_model_proposal_resolution_with_approval(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.world_model_resolution_apply_execution import (
        execute_apply_world_model_proposal_resolution_with_approval,
    )

    approval_contract = tool.params.get("approval_contract")
    return execute_apply_world_model_proposal_resolution_with_approval(
        context.db,
        context.project_id,
        decisions=tool.params.get("decisions"),
        confirm_execute=tool.params.get("confirm_execute") is True,
        approval_contract_hash=str(tool.params.get("approval_contract_hash") or "").strip() or None,
        approval_contract=approval_contract if isinstance(approval_contract, dict) else None,
        approval_tool_metadata_provider=_world_model_approval_tool_metadata_by_name,
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
    return approval_required_redirect(
        project_id=context.project_id,
        tool_name="seed_continuity_anchor_proposals",
        target_type="world_model_continuity_anchor_seed",
        prepare_tool="prepare_seed_continuity_anchor_proposals_execution",
        execute_tool="execute_seed_continuity_anchor_proposals_with_approval",
    )


def _prepare_seed_continuity_anchor_proposals_execution(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.continuity_anchor_seed_execution import (
        prepare_seed_continuity_anchor_proposals_execution,
    )

    return prepare_seed_continuity_anchor_proposals_execution(context.db, context.project_id)


def _execute_seed_continuity_anchor_proposals_with_approval(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.continuity_anchor_seed_execution import (
        execute_seed_continuity_anchor_proposals_with_approval,
    )

    approval_contract = tool.params.get("approval_contract")
    return execute_seed_continuity_anchor_proposals_with_approval(
        context.db,
        context.project_id,
        confirm_execute=tool.params.get("confirm_execute") is True,
        approval_contract_hash=str(tool.params.get("approval_contract_hash") or "").strip() or None,
        approval_contract=approval_contract if isinstance(approval_contract, dict) else None,
        approval_tool_metadata_provider=_world_model_approval_tool_metadata_by_name,
    )


WORLD_MODEL_AGENT_TOOL_ADAPTERS: dict[str, WritingAgentToolAdapter] = {
    "import_setup_world_model": WritingAgentToolAdapter(
        "import_setup_world_model",
        _import_setup_world_model,
        category="athena_world_model",
        mutability="guarded_write",
        write_policy="approval_required_redirect",
    ),
    "prepare_import_setup_world_model_execution": WritingAgentToolAdapter(
        "prepare_import_setup_world_model_execution",
        _prepare_import_setup_world_model_execution,
        category="athena_world_model",
        mutability="read",
    ),
    "execute_import_setup_world_model_with_approval": WritingAgentToolAdapter(
        "execute_import_setup_world_model_with_approval",
        _execute_import_setup_world_model_with_approval,
        category="athena_world_model",
        mutability="write",
    ),
    "analyze_chapter_world_model": WritingAgentToolAdapter(
        "analyze_chapter_world_model",
        _analyze_chapter_world_model,
        category="athena_world_model",
        mutability="guarded_write",
        write_policy="approval_required_redirect",
    ),
    "prepare_analyze_chapter_world_model_execution": WritingAgentToolAdapter(
        "prepare_analyze_chapter_world_model_execution",
        _prepare_analyze_chapter_world_model_execution,
        category="athena_world_model",
        mutability="read",
    ),
    "execute_analyze_chapter_world_model_with_approval": WritingAgentToolAdapter(
        "execute_analyze_chapter_world_model_with_approval",
        _execute_analyze_chapter_world_model_with_approval,
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
    "inspect_agent_world_model_semantic_check": WritingAgentToolAdapter(
        "inspect_agent_world_model_semantic_check",
        _inspect_agent_world_model_semantic_check,
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
        mutability="guarded_write",
        write_policy="approval_required_redirect",
    ),
    "prepare_apply_world_model_proposal_resolution": WritingAgentToolAdapter(
        "prepare_apply_world_model_proposal_resolution",
        _prepare_apply_world_model_proposal_resolution,
        category="athena_world_model",
        mutability="read",
    ),
    "execute_apply_world_model_proposal_resolution_with_approval": WritingAgentToolAdapter(
        "execute_apply_world_model_proposal_resolution_with_approval",
        _execute_apply_world_model_proposal_resolution_with_approval,
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
        mutability="guarded_write",
        write_policy="approval_required_redirect",
    ),
    "prepare_seed_continuity_anchor_proposals_execution": WritingAgentToolAdapter(
        "prepare_seed_continuity_anchor_proposals_execution",
        _prepare_seed_continuity_anchor_proposals_execution,
        category="maintenance",
        mutability="read",
    ),
    "execute_seed_continuity_anchor_proposals_with_approval": WritingAgentToolAdapter(
        "execute_seed_continuity_anchor_proposals_with_approval",
        _execute_seed_continuity_anchor_proposals_with_approval,
        category="maintenance",
        mutability="write",
    ),
}


def _world_model_approval_tool_metadata_by_name(plan: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    return build_approval_tool_metadata_by_name(
        plan,
        adapter_metadata_by_name={
            name: adapter.to_metadata()
            for name, adapter in WORLD_MODEL_AGENT_TOOL_ADAPTERS.items()
        },
    )


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

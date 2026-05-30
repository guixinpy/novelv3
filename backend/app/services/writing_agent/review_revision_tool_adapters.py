from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.direct_generation_write_guard import approval_required_redirect
from app.services.writing_agent.tool_adapter_types import WritingAgentToolAdapter, WritingAgentToolContext

ApprovalToolMetadataProvider = Callable[[dict[str, Any] | None], dict[str, dict[str, Any]]]


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


def _create_revision_draft(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    chapter_index = _chapter_index(tool)
    return approval_required_redirect(
        project_id=context.project_id,
        tool_name="create_revision_draft",
        target_type="chapter_revision_draft",
        prepare_tool="prepare_create_revision_draft_execution",
        execute_tool="execute_create_revision_draft_with_approval",
        extra={"chapter_index": chapter_index},
    )


def _prepare_create_revision_draft_execution(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.revision_draft_execution import prepare_create_revision_draft_execution

    return prepare_create_revision_draft_execution(
        context.db,
        context.project_id,
        chapter_index=_chapter_index(tool),
    )


def _execute_create_revision_draft_with_approval(
    approval_tool_metadata_provider: ApprovalToolMetadataProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], Any]:
    def execute_create_revision_draft_with_approval_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.services.writing_agent.revision_draft_execution import execute_create_revision_draft_with_approval

        approval_contract = tool.params.get("approval_contract")
        return execute_create_revision_draft_with_approval(
            context.db,
            context.project_id,
            chapter_index=_chapter_index(tool),
            confirm_execute=tool.params.get("confirm_execute") is True,
            approval_contract_hash=str(tool.params.get("approval_contract_hash") or "").strip() or None,
            approval_contract=approval_contract if isinstance(approval_contract, dict) else None,
            approval_tool_metadata_provider=approval_tool_metadata_provider,
        )

    execute_create_revision_draft_with_approval_adapter.__name__ = "_execute_create_revision_draft_with_approval"
    return execute_create_revision_draft_with_approval_adapter


def _apply_planner_revision_patch(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.revision_patch_tool import apply_planner_revision_patch_tool

    revision_id = str(tool.params.get("revision_id") or "").strip() or None
    return apply_planner_revision_patch_tool(
        context.db,
        context.project_id,
        chapter_index=_chapter_index(tool),
        revision_id=revision_id,
    )


async def _expand_chapter_to_target(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.chapter_expansion_tool import expand_chapter_to_target_tool

    return await expand_chapter_to_target_tool(
        context.db,
        context.project_id,
        chapter_index=_chapter_index(tool),
        min_word_count=_optional_int(tool.params.get("min_word_count")),
        extra_instruction=str(tool.params.get("extra_instruction") or ""),
    )


async def _compress_chapter_to_target(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.chapter_compression_tool import compress_chapter_to_target_tool

    forbidden_terms = [str(item).strip() for item in (tool.params.get("forbidden_terms") or []) if str(item).strip()]
    return await compress_chapter_to_target_tool(
        context.db,
        context.project_id,
        chapter_index=_chapter_index(tool),
        target_max_word_count=_optional_int(tool.params.get("target_max_word_count")),
        extra_instruction=str(tool.params.get("extra_instruction") or ""),
        forbidden_terms=forbidden_terms,
    )


def build_review_revision_agent_tool_adapters(
    approval_tool_metadata_provider: ApprovalToolMetadataProvider,
) -> dict[str, WritingAgentToolAdapter]:
    return {
        "review_chapter_quality": WritingAgentToolAdapter(
            "review_chapter_quality",
            _review_chapter_quality,
            category="review",
            mutability="read",
        ),
        "review_chapter_continuity": WritingAgentToolAdapter(
            "review_chapter_continuity",
            _review_chapter_continuity,
            category="review",
            mutability="read",
        ),
        "plan_chapter_revision": WritingAgentToolAdapter(
            "plan_chapter_revision",
            _plan_chapter_revision,
            category="review",
            mutability="read",
        ),
        "create_revision_draft": WritingAgentToolAdapter(
            "create_revision_draft",
            _create_revision_draft,
            category="revision",
            mutability="guarded_write",
            write_policy="approval_required_redirect",
        ),
        "prepare_create_revision_draft_execution": WritingAgentToolAdapter(
            "prepare_create_revision_draft_execution",
            _prepare_create_revision_draft_execution,
            category="revision",
            mutability="read",
        ),
        "execute_create_revision_draft_with_approval": WritingAgentToolAdapter(
            "execute_create_revision_draft_with_approval",
            _execute_create_revision_draft_with_approval(approval_tool_metadata_provider),
            category="revision",
            mutability="write",
        ),
        "apply_planner_revision_patch": WritingAgentToolAdapter(
            "apply_planner_revision_patch",
            _apply_planner_revision_patch,
            category="revision",
            mutability="write",
        ),
        "expand_chapter_to_target": WritingAgentToolAdapter(
            "expand_chapter_to_target",
            _expand_chapter_to_target,
            category="revision",
            mutability="write",
        ),
        "compress_chapter_to_target": WritingAgentToolAdapter(
            "compress_chapter_to_target",
            _compress_chapter_to_target,
            category="revision",
            mutability="write",
        ),
    }


REVIEW_REVISION_AGENT_TOOL_ADAPTERS = build_review_revision_agent_tool_adapters(
    approval_tool_metadata_provider=lambda plan: {}
)


def _chapter_index(tool: WritingAgentToolRequest) -> int:
    return int(tool.params.get("chapter_index") or 1)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

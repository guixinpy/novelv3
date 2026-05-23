from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_adapter_types import WritingAgentToolAdapter, WritingAgentToolContext


ApprovalToolMetadataProvider = Callable[[dict[str, Any] | None], dict[str, dict[str, Any]]]


def build_agent_generation_tool_adapters(
    *,
    approval_tool_metadata_provider: ApprovalToolMetadataProvider,
) -> dict[str, WritingAgentToolAdapter]:
    return {
        "generate_chapter": WritingAgentToolAdapter(
            "generate_chapter",
            _generate_chapter,
            category="generation",
            mutability="write",
        ),
        "prepare_generate_chapter_execution": WritingAgentToolAdapter(
            "prepare_generate_chapter_execution",
            _prepare_generate_chapter_execution,
            category="generation",
            mutability="read",
        ),
        "execute_generate_chapter_with_approval": WritingAgentToolAdapter(
            "execute_generate_chapter_with_approval",
            _execute_generate_chapter_with_approval(approval_tool_metadata_provider),
            category="generation",
            mutability="write",
        ),
        "expand_outline_window": WritingAgentToolAdapter(
            "expand_outline_window",
            _expand_outline_window,
            category="generation",
            mutability="write",
        ),
        "backfill_outline_gaps": WritingAgentToolAdapter(
            "backfill_outline_gaps",
            _backfill_outline_gaps,
            category="maintenance",
            mutability="write",
        ),
    }


async def _generate_chapter(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.chapter_generation_tool import execute_generate_chapter_tool

    chapter_index = int(tool.params.get("chapter_index") or 1)
    return await execute_generate_chapter_tool(
        context.db,
        context.project_id,
        chapter_index=chapter_index,
        command_args=tool.command_args,
        action_params=tool.params,
    )


def _prepare_generate_chapter_execution(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.chapter_generation_execution import prepare_generate_chapter_execution

    return prepare_generate_chapter_execution(
        context.db,
        context.project_id,
        chapter_index=int(tool.params.get("chapter_index") or 1),
    )


def _execute_generate_chapter_with_approval(
    approval_tool_metadata_provider: ApprovalToolMetadataProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], Any]:
    async def execute_generate_chapter_with_approval_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.services.writing_agent.chapter_generation_execution import execute_generate_chapter_with_approval

        chapter_index = int(tool.params.get("chapter_index") or 1)
        command_args = str(tool.params.get("command_args") or tool.command_args or "").strip() or None
        approval_contract = tool.params.get("approval_contract")
        return await execute_generate_chapter_with_approval(
            context.db,
            context.project_id,
            chapter_index=chapter_index,
            command_args=command_args,
            action_params=tool.params,
            confirm_execute=tool.params.get("confirm_execute") is True,
            approval_contract_hash=str(tool.params.get("approval_contract_hash") or "").strip() or None,
            approval_contract=approval_contract if isinstance(approval_contract, dict) else None,
            approval_tool_metadata_provider=approval_tool_metadata_provider,
        )

    execute_generate_chapter_with_approval_adapter.__name__ = "_execute_generate_chapter_with_approval"
    return execute_generate_chapter_with_approval_adapter


async def _expand_outline_window(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.outline_window_tool import expand_outline_window_tool

    start_chapter = int(tool.params.get("start_chapter") or tool.params.get("chapter_index") or 1)
    end_chapter = int(tool.params.get("end_chapter") or start_chapter)
    command_args = str(tool.params.get("command_args") or tool.command_args or "").strip() or None
    return await expand_outline_window_tool(
        context.db,
        context.project_id,
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        command_args=command_args,
    )


def _backfill_outline_gaps(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.core.outline_lookup import backfill_missing_outline_chapters_from_content

    before_chapter = tool.params.get("before_chapter") or tool.params.get("chapter_index")
    return backfill_missing_outline_chapters_from_content(
        context.db,
        context.project_id,
        before_chapter=int(before_chapter) if before_chapter else None,
    )

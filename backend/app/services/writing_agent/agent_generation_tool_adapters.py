from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.direct_generation_write_guard import approval_required_redirect
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
            mutability="guarded_write",
            write_policy="approval_required_redirect",
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
            mutability="guarded_write",
            write_policy="approval_required_redirect",
        ),
        "prepare_backfill_outline_gaps_execution": WritingAgentToolAdapter(
            "prepare_backfill_outline_gaps_execution",
            _prepare_backfill_outline_gaps_execution,
            category="maintenance",
            mutability="read",
        ),
        "execute_backfill_outline_gaps_with_approval": WritingAgentToolAdapter(
            "execute_backfill_outline_gaps_with_approval",
            _execute_backfill_outline_gaps_with_approval(approval_tool_metadata_provider),
            category="maintenance",
            mutability="write",
        ),
    }


def _generate_chapter(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    chapter_index = int(tool.params.get("chapter_index") or 1)
    command_args = str(tool.params.get("command_args") or tool.command_args or "").strip() or None
    return approval_required_redirect(
        project_id=context.project_id,
        tool_name="generate_chapter",
        target_type="chapter",
        prepare_tool="prepare_generate_chapter_execution",
        execute_tool="execute_generate_chapter_with_approval",
        command_args=command_args,
        extra={"chapter_index": chapter_index},
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
    if tool.params.get("confirm_execute") is not True:
        return _blocked_confirmation_required(
            context.project_id,
            "expand_outline_window",
            target_type="outline",
            extra={"start_chapter": start_chapter, "end_chapter": end_chapter},
        )
    return await expand_outline_window_tool(
        context.db,
        context.project_id,
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        command_args=command_args,
    )


def _backfill_outline_gaps(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    before_chapter = _optional_int(tool.params.get("before_chapter") or tool.params.get("chapter_index"))
    return approval_required_redirect(
        project_id=context.project_id,
        tool_name="backfill_outline_gaps",
        target_type="outline",
        prepare_tool="prepare_backfill_outline_gaps_execution",
        execute_tool="execute_backfill_outline_gaps_with_approval",
        extra={"before_chapter": before_chapter},
    )


def _prepare_backfill_outline_gaps_execution(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.outline_backfill_execution import prepare_backfill_outline_gaps_execution

    before_chapter = _optional_int(tool.params.get("before_chapter") or tool.params.get("chapter_index"))
    return prepare_backfill_outline_gaps_execution(
        context.db,
        context.project_id,
        before_chapter=before_chapter,
    )


def _execute_backfill_outline_gaps_with_approval(
    approval_tool_metadata_provider: ApprovalToolMetadataProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], Any]:
    def execute_backfill_outline_gaps_with_approval_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.services.writing_agent.outline_backfill_execution import (
            execute_backfill_outline_gaps_with_approval,
        )

        before_chapter = _optional_int(tool.params.get("before_chapter") or tool.params.get("chapter_index"))
        approval_contract = tool.params.get("approval_contract")
        return execute_backfill_outline_gaps_with_approval(
            context.db,
            context.project_id,
            before_chapter=before_chapter,
            confirm_execute=tool.params.get("confirm_execute") is True,
            approval_contract_hash=str(tool.params.get("approval_contract_hash") or "").strip() or None,
            approval_contract=approval_contract if isinstance(approval_contract, dict) else None,
            approval_tool_metadata_provider=approval_tool_metadata_provider,
        )

    execute_backfill_outline_gaps_with_approval_adapter.__name__ = "_execute_backfill_outline_gaps_with_approval"
    return execute_backfill_outline_gaps_with_approval_adapter


def _optional_int(value: object) -> int | None:
    try:
        parsed = int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None
    return parsed if parsed and parsed > 0 else None


def _blocked_confirmation_required(
    project_id: str,
    tool_name: str,
    *,
    target_type: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": "confirmation_required",
        "project_id": project_id,
        "target_type": target_type,
        **(extra or {}),
        "required_confirmation": {"confirm_execute": True},
        "side_effects": {"executed": [], "skipped": [tool_name]},
        "trace": {
            "selected_tools": [],
            "rejected_tools": [{"tool_name": tool_name, "reason": "confirmation_required"}],
            "source": "direct_agent_write_guard",
        },
    }

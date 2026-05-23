from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_adapter_types import WritingAgentToolAdapter, WritingAgentToolContext


ApprovalToolMetadataProvider = Callable[[dict[str, Any] | None], dict[str, dict[str, Any]]]


def build_outline_generation_agent_tool_adapters(
    *,
    approval_tool_metadata_provider: ApprovalToolMetadataProvider,
) -> dict[str, WritingAgentToolAdapter]:
    return {
        "preview_generate_outline_execution": WritingAgentToolAdapter(
            "preview_generate_outline_execution",
            _preview_generate_outline_execution,
            category="generation",
            mutability="read",
        ),
        "prepare_generate_outline_execution": WritingAgentToolAdapter(
            "prepare_generate_outline_execution",
            _prepare_generate_outline_execution,
            category="generation",
            mutability="read",
        ),
        "execute_generate_outline_with_approval": WritingAgentToolAdapter(
            "execute_generate_outline_with_approval",
            _execute_generate_outline_with_approval(approval_tool_metadata_provider),
            category="generation",
            mutability="write",
        ),
    }


def _preview_generate_outline_execution(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.outline_generation_execution import preview_generate_outline_execution

    command_args = str(tool.params.get("command_args") or tool.command_args or "").strip() or None
    return preview_generate_outline_execution(context.db, context.project_id, command_args=command_args)


def _prepare_generate_outline_execution(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.outline_generation_execution import prepare_generate_outline_execution

    command_args = str(tool.params.get("command_args") or tool.command_args or "").strip() or None
    return prepare_generate_outline_execution(context.db, context.project_id, command_args=command_args)


def _execute_generate_outline_with_approval(
    approval_tool_metadata_provider: ApprovalToolMetadataProvider,
) -> Callable[[WritingAgentToolContext, WritingAgentToolRequest], Any]:
    async def execute_generate_outline_with_approval_adapter(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.services.writing_agent.outline_generation_execution import execute_generate_outline_with_approval

        command_args = str(tool.params.get("command_args") or tool.command_args or "").strip() or None
        approval_contract = tool.params.get("approval_contract")
        return await execute_generate_outline_with_approval(
            context.db,
            context.project_id,
            command_args=command_args,
            action_params=tool.params,
            confirm_execute=tool.params.get("confirm_execute") is True,
            approval_contract_hash=str(tool.params.get("approval_contract_hash") or "").strip() or None,
            approval_contract=approval_contract if isinstance(approval_contract, dict) else None,
            approval_tool_metadata_provider=approval_tool_metadata_provider,
        )

    execute_generate_outline_with_approval_adapter.__name__ = "_execute_generate_outline_with_approval"
    return execute_generate_outline_with_approval_adapter

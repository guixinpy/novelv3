from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.direct_generation_write_guard import approval_required_redirect
from app.services.writing_agent.tool_adapter_types import WritingAgentToolAdapter, WritingAgentToolContext


ApprovalToolMetadataProvider = Callable[[dict[str, Any] | None], dict[str, dict[str, Any]]]


def build_longform_agent_tool_adapters(
    *,
    approval_tool_metadata_provider: ApprovalToolMetadataProvider,
) -> dict[str, WritingAgentToolAdapter]:
    return {
        "plan_longform_chapter_batch": WritingAgentToolAdapter(
            "plan_longform_chapter_batch",
            _plan_longform_chapter_batch,
            category="task_queue",
            mutability="read",
        ),
        "enqueue_longform_chapter_batch": WritingAgentToolAdapter(
            "enqueue_longform_chapter_batch",
            _enqueue_longform_chapter_batch,
            category="task_queue",
            mutability="guarded_write",
            write_policy="approval_required_redirect",
        ),
        "prepare_enqueue_longform_chapter_batch": WritingAgentToolAdapter(
            "prepare_enqueue_longform_chapter_batch",
            _prepare_enqueue_longform_chapter_batch,
            category="task_queue",
            mutability="read",
        ),
        "execute_enqueue_longform_chapter_batch_with_approval": WritingAgentToolAdapter(
            "execute_enqueue_longform_chapter_batch_with_approval",
            _execute_enqueue_longform_chapter_batch_with_approval(approval_tool_metadata_provider),
            category="task_queue",
            mutability="write",
        ),
        "inspect_longform_chapter_batch": WritingAgentToolAdapter(
            "inspect_longform_chapter_batch",
            _inspect_longform_chapter_batch,
            category="task_queue",
            mutability="read",
        ),
        "execute_longform_chapter_batch_preflight": WritingAgentToolAdapter(
            "execute_longform_chapter_batch_preflight",
            _execute_longform_chapter_batch_preflight,
            category="task_queue",
            mutability="write",
        ),
        "prepare_longform_chapter_batch_execution": WritingAgentToolAdapter(
            "prepare_longform_chapter_batch_execution",
            _prepare_longform_chapter_batch_execution,
            category="task_queue",
            mutability="write",
        ),
        "execute_longform_chapter_batch": WritingAgentToolAdapter(
            "execute_longform_chapter_batch",
            _execute_longform_chapter_batch_with(approval_tool_metadata_provider),
            category="task_queue",
            mutability="write",
        ),
        "review_longform_chapter_batch_execution": WritingAgentToolAdapter(
            "review_longform_chapter_batch_execution",
            _review_longform_chapter_batch_execution,
            category="task_queue",
            mutability="write",
        ),
        "route_longform_chapter_batch_after_review": WritingAgentToolAdapter(
            "route_longform_chapter_batch_after_review",
            _route_longform_chapter_batch_after_review,
            category="task_queue",
            mutability="write",
        ),
    }


def _plan_longform_chapter_batch(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.batch_planner import build_longform_chapter_batch_plan

    source_run_id = str(tool.params.get("source_run_id") or "").strip() or None
    return build_longform_chapter_batch_plan(
        context.db,
        context.project_id,
        source_run_id=source_run_id,
        start_chapter=_optional_int(tool.params.get("start_chapter")),
        batch_size=_optional_int(tool.params.get("batch_size")),
    )


def _enqueue_longform_chapter_batch(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    source_run_id = str(tool.params.get("source_run_id") or "").strip() or None
    return approval_required_redirect(
        project_id=context.project_id,
        tool_name="enqueue_longform_chapter_batch",
        target_type="background_task_enqueue",
        prepare_tool="prepare_enqueue_longform_chapter_batch",
        execute_tool="execute_enqueue_longform_chapter_batch_with_approval",
        extra={
            "source_run_id": source_run_id,
            "start_chapter": _optional_int(tool.params.get("start_chapter")),
            "batch_size": _optional_int(tool.params.get("batch_size")),
        },
    )


def _prepare_enqueue_longform_chapter_batch(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.batch_enqueue_execution import prepare_enqueue_longform_chapter_batch

    source_run_id = str(tool.params.get("source_run_id") or "").strip() or None
    return prepare_enqueue_longform_chapter_batch(
        context.db,
        context.project_id,
        source_run_id=source_run_id,
        start_chapter=_optional_int(tool.params.get("start_chapter")),
        batch_size=_optional_int(tool.params.get("batch_size")),
    )


def _execute_enqueue_longform_chapter_batch_with_approval(
    approval_tool_metadata_provider: ApprovalToolMetadataProvider,
):
    def _execute_enqueue_longform_chapter_batch_with_approval(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.services.writing_agent.batch_enqueue_execution import (
            execute_enqueue_longform_chapter_batch_with_approval,
        )

        source_run_id = str(tool.params.get("source_run_id") or "").strip() or None
        approval_contract = tool.params.get("approval_contract")
        return execute_enqueue_longform_chapter_batch_with_approval(
            context.db,
            context.project_id,
            source_run_id=source_run_id,
            start_chapter=_optional_int(tool.params.get("start_chapter")),
            batch_size=_optional_int(tool.params.get("batch_size")),
            plan_hash=str(tool.params.get("plan_hash") or "").strip() or None,
            confirm_execute=tool.params.get("confirm_execute") is True,
            approval_contract_hash=str(tool.params.get("approval_contract_hash") or "").strip() or None,
            approval_contract=approval_contract if isinstance(approval_contract, dict) else None,
            approval_tool_metadata_provider=approval_tool_metadata_provider,
        )

    return _execute_enqueue_longform_chapter_batch_with_approval


def _inspect_longform_chapter_batch(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.batch_queue_inspector import inspect_longform_chapter_batch_queue

    return inspect_longform_chapter_batch_queue(
        context.db,
        context.project_id,
        task_id=str(tool.params.get("task_id") or "").strip() or None,
        plan_hash=str(tool.params.get("plan_hash") or "").strip() or None,
        limit=_optional_int(tool.params.get("limit")),
    )


def _execute_longform_chapter_batch_preflight(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.batch_preflight import execute_longform_chapter_batch_preflight

    return execute_longform_chapter_batch_preflight(
        context.db,
        context.project_id,
        task_id=str(tool.params.get("task_id") or "").strip() or None,
        max_chapters=_optional_int(tool.params.get("max_chapters")),
        confirm_checkpoint=tool.params.get("confirm_checkpoint") is True,
    )


def _prepare_longform_chapter_batch_execution(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.batch_execution_prepare import prepare_longform_chapter_batch_execution

    return prepare_longform_chapter_batch_execution(
        context.db,
        context.project_id,
        task_id=str(tool.params.get("task_id") or "").strip() or None,
        confirm_prepare=tool.params.get("confirm_prepare") is True,
    )


def _execute_longform_chapter_batch_with(
    approval_tool_metadata_provider: ApprovalToolMetadataProvider,
):
    async def _execute_longform_chapter_batch(
        context: WritingAgentToolContext,
        tool: WritingAgentToolRequest,
    ) -> dict[str, Any]:
        from app.services.writing_agent.batch_execution import execute_longform_chapter_batch

        return await execute_longform_chapter_batch(
            context.db,
            context.project_id,
            task_id=str(tool.params.get("task_id") or "").strip() or None,
            confirm_execute=tool.params.get("confirm_execute") is True,
            attempt_manifest_hash=str(tool.params.get("attempt_manifest_hash") or "").strip() or None,
            approval_contract_hash=str(tool.params.get("approval_contract_hash") or "").strip() or None,
            approval_tool_metadata_provider=approval_tool_metadata_provider,
        )

    return _execute_longform_chapter_batch


def _review_longform_chapter_batch_execution(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.batch_post_generation_review import review_longform_chapter_batch_execution

    return review_longform_chapter_batch_execution(
        context.db,
        context.project_id,
        task_id=str(tool.params.get("task_id") or "").strip() or None,
        lookback=_optional_int(tool.params.get("lookback")),
        confirm_review=tool.params.get("confirm_review") is True,
    )


def _route_longform_chapter_batch_after_review(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.batch_post_review_router import route_longform_chapter_batch_after_review

    return route_longform_chapter_batch_after_review(
        context.db,
        context.project_id,
        task_id=str(tool.params.get("task_id") or "").strip() or None,
        expected_post_generation_review_hash=str(tool.params.get("expected_post_generation_review_hash") or "").strip()
        or None,
        next_batch_size=_optional_int(tool.params.get("next_batch_size")),
    )


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

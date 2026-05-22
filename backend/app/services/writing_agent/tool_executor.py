from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import inspect
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_registry import build_agent_tool_plan, get_agent_tool_descriptor, internal_tool_names


PreflightWriting = Callable[[str, dict[str, Any]], dict[str, Any]]
StaticToolAdapterOutput = dict[str, Any] | Awaitable[dict[str, Any]]
StaticToolAdapterHandler = Callable[["WritingAgentToolContext", WritingAgentToolRequest], StaticToolAdapterOutput]


@dataclass(frozen=True)
class WritingAgentToolContext:
    db: Session
    project_id: str
    run_id: str | None = None


@dataclass(frozen=True)
class WritingAgentToolExecutionResult:
    handled: bool
    output: dict[str, Any] | None = None


@dataclass(frozen=True)
class WritingAgentToolAdapter:
    tool_name: str
    handler: StaticToolAdapterHandler
    category: str
    mutability: str
    adapter_type: str = "static"

    def to_metadata(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "adapter_type": self.adapter_type,
            "category": self.category,
            "mutability": self.mutability,
            "handler_name": self.handler.__name__,
        }


async def execute_writing_agent_tool(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
    *,
    preflight_writing: PreflightWriting | None = None,
) -> WritingAgentToolExecutionResult:
    descriptor = get_agent_tool_descriptor(tool.tool_name)
    if descriptor is None:
        return WritingAgentToolExecutionResult(handled=False)

    adapter = _STATIC_TOOL_ADAPTERS.get(tool.tool_name)
    if adapter is not None:
        output = adapter.handler(context, tool)
        if inspect.isawaitable(output):
            output = await output
        return WritingAgentToolExecutionResult(handled=True, output=output)

    if tool.tool_name == "preflight_writing" and preflight_writing is not None:
        return WritingAgentToolExecutionResult(
            handled=True,
            output=preflight_writing(context.project_id, tool.params),
        )

    if not descriptor.internal:
        return WritingAgentToolExecutionResult(handled=False)

    return WritingAgentToolExecutionResult(handled=False)


def static_writing_agent_tool_adapter_names() -> set[str]:
    return set(_STATIC_TOOL_ADAPTERS)


def writing_agent_tool_adapter_metadata(tool_name: str) -> dict[str, Any] | None:
    adapter = _STATIC_TOOL_ADAPTERS.get(tool_name)
    if adapter is not None:
        return adapter.to_metadata()
    if tool_name == "preflight_writing":
        return {
            "tool_name": "preflight_writing",
            "adapter_type": "injected",
            "category": "preflight",
            "mutability": "read",
            "handler_name": "preflight_writing",
        }
    return None


def unhandled_internal_writing_agent_tool_names() -> set[str]:
    handled = static_writing_agent_tool_adapter_names() | {"preflight_writing"}
    return internal_tool_names() - handled


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))


def _describe_agent_tools(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    chapter_index = _optional_int(tool.params.get("chapter_index"))
    return build_agent_tool_plan(context.db, context.project_id, chapter_index=chapter_index)


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


def _plan_recovery_tools(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.recovery_planner import build_recovery_tool_plan

    run_id = str(tool.params.get("run_id") or "").strip() or None
    return build_recovery_tool_plan(context.db, context.project_id, run_id)


def _plan_recommended_followups(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.recommended_followup_planner import build_recommended_followup_tool_plan

    run_id = str(tool.params.get("run_id") or "").strip() or None
    return build_recommended_followup_tool_plan(context.db, context.project_id, run_id)


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
    from app.services.writing_agent.batch_enqueue import build_longform_chapter_batch_enqueue

    source_run_id = str(tool.params.get("source_run_id") or "").strip() or None
    return build_longform_chapter_batch_enqueue(
        context.db,
        context.project_id,
        source_run_id=source_run_id,
        start_chapter=_optional_int(tool.params.get("start_chapter")),
        batch_size=_optional_int(tool.params.get("batch_size")),
        confirm_enqueue=tool.params.get("confirm_enqueue") is True,
        plan_hash=str(tool.params.get("plan_hash") or "").strip() or None,
    )


def _inspect_longform_chapter_batch(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.batch_queue_inspector import inspect_longform_chapter_batch_queue

    return inspect_longform_chapter_batch_queue(
        context.db,
        context.project_id,
        task_id=str(tool.params.get("task_id") or "").strip() or None,
        plan_hash=str(tool.params.get("plan_hash") or "").strip() or None,
        limit=_optional_int(tool.params.get("limit")),
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
    )


def _inspect_agent_tool_contracts(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.tool_contracts import build_agent_tool_contract_snapshot

    adapter_metadata = {name: adapter.to_metadata() for name, adapter in _STATIC_TOOL_ADAPTERS.items()}
    adapter_metadata["preflight_writing"] = {
        "tool_name": "preflight_writing",
        "adapter_type": "injected",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "preflight_writing",
    }
    return build_agent_tool_contract_snapshot(
        adapter_metadata_by_name=adapter_metadata,
        include_gap_details=tool.params.get("include_gap_details") is not False,
    )


def _inspect_agent_slash_command_route(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.slash_command_route import inspect_agent_slash_command_route
    from app.services.actions.action_execution_service import SUPPORTED_ACTION_EXECUTION_TYPES

    return inspect_agent_slash_command_route(
        command_name=str(tool.params.get("command_name") or "").strip() or None,
        static_adapter_tool_names=set(_STATIC_TOOL_ADAPTERS),
        action_execution_tool_names=set(SUPPORTED_ACTION_EXECUTION_TYPES),
    )


def _inspect_agent_dialog_route_projection(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.actions.action_execution_service import SUPPORTED_ACTION_EXECUTION_TYPES
    from app.services.writing_agent.slash_command_route import inspect_agent_dialog_route_projection

    return inspect_agent_dialog_route_projection(
        source=str(tool.params.get("source") or "").strip() or None,
        static_adapter_tool_names=set(_STATIC_TOOL_ADAPTERS),
        action_execution_tool_names=set(SUPPORTED_ACTION_EXECUTION_TYPES),
    )


def _inspect_agent_intent_projection(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.core.intent_router import IntentRouter
    from app.schemas import ProjectDiagnosisOut
    from app.services.workspace.bootstrap import build_project_diagnosis

    text = str(tool.params.get("text") or tool.command_args or "").strip()
    if "missing_items" in tool.params or "completed_items" in tool.params or "suggested_next_step" in tool.params:
        diagnosis = ProjectDiagnosisOut(
            missing_items=_string_list(tool.params.get("missing_items")),
            completed_items=_string_list(tool.params.get("completed_items")),
            suggested_next_step=str(tool.params.get("suggested_next_step") or "").strip() or None,
        )
    else:
        diagnosis = build_project_diagnosis(context.db, context.project_id)
    return IntentRouter().project(
        text,
        str(tool.params.get("dialog_state") or "chatting"),
        str(tool.params.get("pending_action_id") or "").strip() or None,
        diagnosis,
    ).to_dict()


def _analyze_chapter_world_model(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.world_model_analysis_tool import analyze_chapter_world_model_tool

    chapter_index = int(tool.params.get("chapter_index") or 1)
    return analyze_chapter_world_model_tool(
        context.db,
        context.project_id,
        chapter_index=chapter_index,
        run_id=context.run_id,
    )


def _import_setup_world_model(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.setup_world_model_import_tool import import_setup_world_model_tool

    return import_setup_world_model_tool(context.db, context.project_id)


def _seed_continuity_anchor_proposals(
    context: WritingAgentToolContext,
    tool: WritingAgentToolRequest,
) -> dict[str, Any]:
    from app.services.writing_agent.continuity_anchor_seed_tool import seed_continuity_anchor_proposals_tool

    return seed_continuity_anchor_proposals_tool(context.db, context.project_id)


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


def _inspect_agent_knowledge_base_route(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.agent_knowledge_base_route import inspect_agent_knowledge_base_route

    return inspect_agent_knowledge_base_route(
        context.db,
        context.project_id,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
        query=str(tool.params.get("query") or "").strip() or None,
        limit=_optional_int(tool.params.get("limit")),
    )


def _record_agent_knowledge_base_candidate(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.agent_knowledge_base_candidates import record_agent_knowledge_base_candidate

    source_refs = tool.params.get("source_refs")
    tags = tool.params.get("tags")
    return record_agent_knowledge_base_candidate(
        context.db,
        context.project_id,
        memory_type=str(tool.params.get("memory_type") or "").strip(),
        title=str(tool.params.get("title") or "").strip(),
        summary=str(tool.params.get("summary") or "").strip(),
        source_refs=_string_list(source_refs),
        confidence=_optional_float(tool.params.get("confidence")),
        status=str(tool.params.get("status") or "").strip() or None,
        tags=_string_list(tags),
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
    )


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
    )


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


def _inspect_agent_trace_audit(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.agent_trace_audit import inspect_agent_trace_audit

    return inspect_agent_trace_audit(
        context.db,
        context.project_id,
        run_id=str(tool.params.get("run_id") or "").strip() or None,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
        task_id=str(tool.params.get("task_id") or "").strip() or None,
        limit=_optional_int(tool.params.get("limit")),
    )


def _inspect_agent_memory_route(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.agent_memory_route import inspect_agent_memory_route

    return inspect_agent_memory_route(
        context.db,
        context.project_id,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
        query=str(tool.params.get("query") or tool.command_args or "").strip() or None,
        include_context_summary=tool.params.get("include_context_summary") is True,
    )


def _summarize_longform_context(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.longform_context_summary import summarize_longform_context

    return summarize_longform_context(
        context.db,
        context.project_id,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
        query=str(tool.params.get("query") or tool.command_args or "").strip() or None,
        max_chars=_optional_int(tool.params.get("max_chars")),
        include_prompt_context=tool.params.get("include_prompt_context") is True,
    )


def _repair_longform_maintenance(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.core.longform_memory import repair_longform_maintenance

    return _json_safe_output(
        repair_longform_maintenance(
            context.db,
            context.project_id,
            limit=_optional_int(tool.params.get("limit")) or 20,
            repair_limit=_optional_int(tool.params.get("repair_limit")) or 100,
        )
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


def _create_revision_draft(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.revision_draft_tool import create_revision_draft_tool

    return create_revision_draft_tool(
        context.db,
        context.project_id,
        chapter_index=_chapter_index(tool),
    )


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


def _backfill_outline_gaps(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.core.outline_lookup import backfill_missing_outline_chapters_from_content

    before_chapter = tool.params.get("before_chapter") or tool.params.get("chapter_index")
    return backfill_missing_outline_chapters_from_content(
        context.db,
        context.project_id,
        before_chapter=int(before_chapter) if before_chapter else None,
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


_STATIC_TOOL_ADAPTERS: dict[str, WritingAgentToolAdapter] = {
    "describe_agent_tools": WritingAgentToolAdapter(
        "describe_agent_tools",
        _describe_agent_tools,
        category="preflight",
        mutability="read",
    ),
    "generate_chapter": WritingAgentToolAdapter(
        "generate_chapter",
        _generate_chapter,
        category="generation",
        mutability="write",
    ),
    "plan_writing_agent_run": WritingAgentToolAdapter(
        "plan_writing_agent_run",
        _plan_writing_agent_run,
        category="preflight",
        mutability="read",
    ),
    "plan_recovery_tools": WritingAgentToolAdapter(
        "plan_recovery_tools",
        _plan_recovery_tools,
        category="preflight",
        mutability="read",
    ),
    "plan_recommended_followups": WritingAgentToolAdapter(
        "plan_recommended_followups",
        _plan_recommended_followups,
        category="preflight",
        mutability="read",
    ),
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
        mutability="write",
    ),
    "inspect_longform_chapter_batch": WritingAgentToolAdapter(
        "inspect_longform_chapter_batch",
        _inspect_longform_chapter_batch,
        category="task_queue",
        mutability="read",
    ),
    "inspect_agent_job_projection": WritingAgentToolAdapter(
        "inspect_agent_job_projection",
        _inspect_agent_job_projection,
        category="task_queue",
        mutability="read",
    ),
    "inspect_agent_tool_contracts": WritingAgentToolAdapter(
        "inspect_agent_tool_contracts",
        _inspect_agent_tool_contracts,
        category="preflight",
        mutability="read",
    ),
    "inspect_agent_slash_command_route": WritingAgentToolAdapter(
        "inspect_agent_slash_command_route",
        _inspect_agent_slash_command_route,
        category="preflight",
        mutability="read",
    ),
    "inspect_agent_dialog_route_projection": WritingAgentToolAdapter(
        "inspect_agent_dialog_route_projection",
        _inspect_agent_dialog_route_projection,
        category="preflight",
        mutability="read",
    ),
    "inspect_agent_intent_projection": WritingAgentToolAdapter(
        "inspect_agent_intent_projection",
        _inspect_agent_intent_projection,
        category="preflight",
        mutability="read",
    ),
    "import_setup_world_model": WritingAgentToolAdapter(
        "import_setup_world_model",
        _import_setup_world_model,
        category="athena_world_model",
        mutability="write",
    ),
    "seed_continuity_anchor_proposals": WritingAgentToolAdapter(
        "seed_continuity_anchor_proposals",
        _seed_continuity_anchor_proposals,
        category="maintenance",
        mutability="write",
    ),
    "analyze_chapter_world_model": WritingAgentToolAdapter(
        "analyze_chapter_world_model",
        _analyze_chapter_world_model,
        category="athena_world_model",
        mutability="write",
    ),
    "expand_outline_window": WritingAgentToolAdapter(
        "expand_outline_window",
        _expand_outline_window,
        category="generation",
        mutability="write",
    ),
    "inspect_agent_knowledge_base_route": WritingAgentToolAdapter(
        "inspect_agent_knowledge_base_route",
        _inspect_agent_knowledge_base_route,
        category="knowledge_base",
        mutability="read",
    ),
    "record_agent_knowledge_base_candidate": WritingAgentToolAdapter(
        "record_agent_knowledge_base_candidate",
        _record_agent_knowledge_base_candidate,
        category="knowledge_base",
        mutability="write",
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
        _execute_longform_chapter_batch,
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
    "inspect_agent_trace_audit": WritingAgentToolAdapter(
        "inspect_agent_trace_audit",
        _inspect_agent_trace_audit,
        category="trace",
        mutability="read",
    ),
    "inspect_agent_memory_route": WritingAgentToolAdapter(
        "inspect_agent_memory_route",
        _inspect_agent_memory_route,
        category="longform_memory",
        mutability="read",
    ),
    "summarize_longform_context": WritingAgentToolAdapter(
        "summarize_longform_context",
        _summarize_longform_context,
        category="longform_memory",
        mutability="read",
    ),
    "repair_longform_maintenance": WritingAgentToolAdapter(
        "repair_longform_maintenance",
        _repair_longform_maintenance,
        category="maintenance",
        mutability="write",
    ),
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
    "backfill_outline_gaps": WritingAgentToolAdapter(
        "backfill_outline_gaps",
        _backfill_outline_gaps,
        category="maintenance",
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


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    cleaned = str(value).strip()
    return [cleaned] if cleaned else []

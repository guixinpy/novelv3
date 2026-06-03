from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import AIModelCallTrace, DialogMessage, Project, WritingAgentRun, WritingAgentStep
from app.services.writing_agent.agent_step_binding import summarize_resource_binding
from app.services.writing_agent.command_contract_projection import (
    command_contracts_from_run_input,
    command_contracts_needs_attention,
)
from app.services.writing_agent.control_plane_readiness_projection import (
    control_plane_readiness_from_run_input,
    control_plane_readiness_needs_attention,
)

AGENT_TRACE_AUDIT_VERSION = "phase73.agent_trace_audit.v1"
DEFAULT_AUDIT_LIMIT = 20
MAX_AUDIT_LIMIT = 100
TRACE_EXPECTED_TOOL_NAMES = {
    "generate_chapter",
    "expand_chapter",
    "preflight_writing",
    "summarize_longform_context",
    "generate_setup",
    "generate_storyline",
    "generate_outline",
    "backfill_outline",
    "expand_outline_window",
    "draft_revision",
    "apply_revision_patch",
    "review_chapter",
    "batch_post_generation_review",
}


def inspect_agent_trace_audit(
    db: Session,
    project_id: str,
    *,
    run_id: str | None = None,
    chapter_index: int | None = None,
    task_id: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    _require_project(db, project_id)
    clamped_limit = _clamp_limit(limit)
    run = _select_run(db, project_id, run_id=run_id, chapter_index=chapter_index, task_id=task_id)
    if run is None:
        return _json_safe_output(
            {
                "status": "completed",
                "project_id": project_id,
                "audit": {
                    "status": "no_run",
                    "reason": "no_matching_agent_run",
                    "message": "未找到匹配的 Writing Agent run。",
                },
                "run": None,
                "steps": [],
                "traces": [],
                "approval_events": [],
                "context": {"total_blocks": 0, "blocks": []},
                "failure": None,
                "recommended_actions": [{"tool_name": "inspect_agent_memory_route", "reason_code": "no_matching_run"}],
                "trace": _audit_trace_metadata(),
                "control_plane_readiness": None,
            }
        )

    steps = _steps_for_run(db, project_id, run.id, limit=clamped_limit)
    trace_ids = [step.trace_id for step in steps if step.trace_id]
    traces = _traces_by_id(db, project_id, trace_ids)
    trace_items = [_trace_summary(traces[trace_id]) for trace_id in trace_ids if trace_id in traces]
    approval_events = _approval_events_for_run(db, run)
    dialog_events = _dialog_events_for_run(db, run)
    dialog_route_events = _dialog_route_events_for_run(db, project_id, run)
    event_chain = _event_chain(
        run,
        steps=steps,
        trace_items=trace_items,
        approval_events=approval_events,
        dialog_events=dialog_events,
        dialog_route_events=dialog_route_events,
    )
    context = _context_summary([traces[trace_id] for trace_id in trace_ids if trace_id in traces])
    failure = _failure_summary(run, steps)
    profile_policy_audit = _profile_policy_audit_summary(_profile_policy_audit_from_steps(steps))
    control_plane_readiness = control_plane_readiness_from_run_input(run.input)
    command_contracts = command_contracts_from_run_input(run.input)
    intent_chain = _intent_chain_summary(run, steps)
    end_to_end_chain = _end_to_end_chain_summary(
        intent_chain,
        steps=steps,
        trace_items=trace_items,
        dialog_events=dialog_events,
    )
    anomaly_summary = _trace_anomaly_summary(
        run,
        steps=steps,
        trace_items=trace_items,
        context=context,
        intent_chain=intent_chain,
        end_to_end_chain=end_to_end_chain,
    )
    recommended_actions = _recommended_actions(
        steps,
        failure=failure,
        control_plane_readiness=control_plane_readiness,
        command_contracts=command_contracts,
    )
    audit = {
        "status": _audit_status(run.status),
        "reason": _audit_reason(run.status, failure=failure),
        "step_count": len(steps),
        "trace_count": len(trace_items),
        "dialog_route_event_count": len(dialog_route_events),
        "approval_event_count": len(approval_events),
        "event_chain_count": len(event_chain),
        "context_block_count": context["total_blocks"],
        "intent_chain_status": intent_chain["status"],
        "planned_tool_count": intent_chain["planned_tool_count"],
        "matched_planned_tool_count": intent_chain["matched_tool_count"],
        "end_to_end_chain_status": end_to_end_chain["status"],
        "anomaly_status": anomaly_summary["status"],
        "anomaly_issue_count": anomaly_summary["issue_count"],
    }
    if profile_policy_audit is not None:
        profile_policy_summary = (
            profile_policy_audit.get("summary") if isinstance(profile_policy_audit.get("summary"), dict) else {}
        )
        audit["profile_policy_status"] = profile_policy_audit.get("status")
        audit["profile_policy_issue_count"] = profile_policy_summary.get("issues", 0)
    if control_plane_readiness is not None:
        control_plane_summary = (
            control_plane_readiness.get("summary")
            if isinstance(control_plane_readiness.get("summary"), dict)
            else {}
        )
        audit["control_plane_status"] = control_plane_readiness.get("status")
        audit["control_plane_gap_count"] = control_plane_summary.get("total_gap_count", 0)
    if command_contracts is not None:
        command_contract_summary = (
            command_contracts.get("summary")
            if isinstance(command_contracts.get("summary"), dict)
            else {}
        )
        audit["command_contract_gap_count"] = command_contract_summary.get("gap_count", 0)
        audit["command_contract_available_commands"] = command_contract_summary.get("available_commands", 0)
    return _json_safe_output(
        {
            "status": "completed",
            "project_id": project_id,
            "audit": audit,
            "run": _run_summary(run),
            "steps": [_step_summary(step) for step in steps],
            "traces": trace_items,
            "dialog_events": dialog_events,
            "dialog_route_events": dialog_route_events,
            "approval_events": approval_events,
            "event_chain": event_chain,
            "context": context,
            "intent_chain": intent_chain,
            "end_to_end_chain": end_to_end_chain,
            "anomaly_summary": anomaly_summary,
            "failure": failure,
            "recommended_actions": recommended_actions,
            "profile_policy_audit": profile_policy_audit,
            "control_plane_readiness": control_plane_readiness,
            "command_contracts": command_contracts,
            "trace": _audit_trace_metadata(),
        }
    )


def _require_project(db: Session, project_id: str) -> None:
    if db.query(Project.id).filter(Project.id == project_id).first() is None:
        raise HTTPException(status_code=404, detail="Project not found")


def _select_run(
    db: Session,
    project_id: str,
    *,
    run_id: str | None,
    chapter_index: int | None,
    task_id: str | None,
) -> WritingAgentRun | None:
    if run_id:
        run = (
            db.query(WritingAgentRun)
            .filter(WritingAgentRun.project_id == project_id, WritingAgentRun.id == run_id)
            .first()
        )
        if run is None:
            raise HTTPException(status_code=404, detail="Writing agent run not found")
        return run
    if task_id:
        run = (
            db.query(WritingAgentRun)
            .filter(WritingAgentRun.project_id == project_id, WritingAgentRun.background_task_id == task_id)
            .order_by(WritingAgentRun.created_at.desc(), WritingAgentRun.id.desc())
            .first()
        )
        if run is not None:
            return run
    if chapter_index:
        step = (
            db.query(WritingAgentStep)
            .filter(WritingAgentStep.project_id == project_id, WritingAgentStep.chapter_index == chapter_index)
            .order_by(WritingAgentStep.created_at.desc(), WritingAgentStep.id.desc())
            .first()
        )
        if step is not None:
            return (
                db.query(WritingAgentRun)
                .filter(WritingAgentRun.project_id == project_id, WritingAgentRun.id == step.run_id)
                .first()
            )
    return (
        db.query(WritingAgentRun)
        .filter(WritingAgentRun.project_id == project_id)
        .order_by(WritingAgentRun.created_at.desc(), WritingAgentRun.id.desc())
        .first()
    )


def _steps_for_run(db: Session, project_id: str, run_id: str, *, limit: int) -> list[WritingAgentStep]:
    return (
        db.query(WritingAgentStep)
        .filter(WritingAgentStep.project_id == project_id, WritingAgentStep.run_id == run_id)
        .order_by(WritingAgentStep.step_index.asc(), WritingAgentStep.id.asc())
        .limit(limit)
        .all()
    )


def _traces_by_id(db: Session, project_id: str, trace_ids: list[str]) -> dict[str, AIModelCallTrace]:
    if not trace_ids:
        return {}
    rows = (
        db.query(AIModelCallTrace)
        .filter(AIModelCallTrace.project_id == project_id, AIModelCallTrace.id.in_(sorted(set(trace_ids))))
        .all()
    )
    return {trace.id: trace for trace in rows}


def _run_summary(run: WritingAgentRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "goal": run.goal,
        "status": run.status,
        "entrypoint": run.entrypoint,
        "background_task_id": run.background_task_id,
        "dialog_id": run.dialog_id,
        "input_keys": sorted((run.input or {}).keys()) if isinstance(run.input, dict) else [],
        "output_keys": sorted((run.output or {}).keys()) if isinstance(run.output, dict) else [],
        "error": run.error,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }


def _step_summary(step: WritingAgentStep) -> dict[str, Any]:
    output = step.output if isinstance(step.output, dict) else {}
    envelope = output.get("agent_tool_result") if isinstance(output.get("agent_tool_result"), dict) else {}
    return {
        "id": step.id,
        "step_index": step.step_index,
        "tool_name": step.tool_name,
        "status": step.status,
        "trace_id": step.trace_id,
        "background_task_id": step.background_task_id,
        "target_type": step.target_type,
        "target_id": step.target_id,
        "chapter_index": step.chapter_index,
        "tool_call_id": step.tool_call_id,
        "resource_binding": summarize_resource_binding(step.resource_binding),
        "error": step.error,
        "output_keys": sorted(output.keys()),
        "result_status": envelope.get("result_status") or output.get("status"),
        "is_error": envelope.get("is_error") if "is_error" in envelope else step.status in {"failed", "blocked"},
    }


def _trace_summary(trace: AIModelCallTrace) -> dict[str, Any]:
    context_blocks = trace.context_blocks if isinstance(trace.context_blocks, list) else []
    metadata = trace.trace_metadata if isinstance(trace.trace_metadata, dict) else {}
    return {
        "id": trace.id,
        "trace_type": trace.trace_type,
        "status": trace.status,
        "model": trace.model,
        "prompt_tokens": trace.prompt_tokens,
        "completion_tokens": trace.completion_tokens,
        "latency_ms": trace.latency_ms,
        "error_message": trace.error_message,
        "chapter_index": trace.chapter_index,
        "context_block_count": len(context_blocks),
        "context_char_count": sum(len(str(block.get("content") or "")) for block in context_blocks if isinstance(block, dict)),
        "metadata_keys": sorted(metadata.keys()),
    }


def _dialog_events_for_run(db: Session, run: WritingAgentRun) -> dict[str, Any]:
    return {
        "approval_message": _dialog_message_summary(db, run.request_message_id),
        "result_message": _dialog_message_summary(db, run.response_message_id),
    }


def _dialog_message_summary(db: Session, message_id: str | None) -> dict[str, Any] | None:
    if not message_id:
        return None
    message = db.query(DialogMessage).filter(DialogMessage.id == message_id).first()
    if message is None:
        return None
    action_result = message.action_result if isinstance(message.action_result, dict) else {}
    return {
        "id": message.id,
        "role": message.role,
        "action_type": action_result.get("type"),
        "action_status": action_result.get("status"),
    }


def _dialog_route_events_for_run(db: Session, project_id: str, run: WritingAgentRun) -> list[dict[str, Any]]:
    if not run.dialog_id:
        return []
    traces = (
        db.query(AIModelCallTrace)
        .filter(
            AIModelCallTrace.project_id == project_id,
            AIModelCallTrace.dialog_id == run.dialog_id,
            AIModelCallTrace.trace_type == "dialog_route_decision",
        )
        .order_by(AIModelCallTrace.created_at.asc(), AIModelCallTrace.id.asc())
        .all()
    )
    events: list[dict[str, Any]] = []
    for trace in traces:
        metadata = trace.trace_metadata if isinstance(trace.trace_metadata, dict) else {}
        agent_run_id = str(metadata.get("agent_run_id") or "").strip()
        request_matches = bool(run.request_message_id and trace.request_message_id == run.request_message_id)
        response_matches = bool(run.response_message_id and trace.response_message_id == run.response_message_id)
        if agent_run_id != run.id and not request_matches and not response_matches:
            continue
        event = _dialog_route_event_summary(trace)
        if event is not None:
            events.append(event)
    return events


def _dialog_route_event_summary(trace: AIModelCallTrace) -> dict[str, Any] | None:
    metadata = trace.trace_metadata if isinstance(trace.trace_metadata, dict) else {}
    decision = metadata.get("dialog_route_decision") if isinstance(metadata.get("dialog_route_decision"), dict) else {}
    selected_route = str(decision.get("selected_route") or "").strip()
    reason_code = str(decision.get("reason_code") or "").strip()
    if not selected_route and not reason_code:
        return None
    event: dict[str, Any] = {
        "trace_id": trace.id,
        "trace_type": trace.trace_type,
        "status": trace.status,
        "model": trace.model,
        "selected_route": selected_route,
        "selected_route_label": _dialog_route_label(selected_route),
        "reason_code": reason_code,
        "reason_label": _dialog_route_reason_label(reason_code),
        "request_message_id": trace.request_message_id,
        "response_message_id": trace.response_message_id,
    }
    action_type = str(metadata.get("action_type") or "").strip()
    if action_type:
        event["action_type"] = action_type
    source_run_id = str(metadata.get("source_run_id") or decision.get("source_run_id") or "").strip()
    if source_run_id:
        event["source_run_id"] = source_run_id
    return event


def _dialog_route_label(route: str) -> str:
    return {
        "recover_blocked_run": "恢复阻塞运行",
        "recommended_followups": "执行推荐后继",
        "chapter_generation": "生成下一章节",
    }.get(route, route)


def _dialog_route_reason_label(reason_code: str) -> str:
    return {
        "recoverable_run_found": "发现可恢复的阻塞运行",
        "recommended_followups_found": "发现可执行的推荐后继",
        "no_recovery_or_followup": "未发现恢复或后继，回落到章节生成",
    }.get(reason_code, reason_code)


def _approval_events_for_run(db: Session, run: WritingAgentRun) -> list[dict[str, Any]]:
    if not run.dialog_id:
        return []
    messages = (
        db.query(DialogMessage)
        .filter(
            DialogMessage.dialog_id == run.dialog_id,
            DialogMessage.role == "system",
            DialogMessage.action_result.isnot(None),
        )
        .order_by(DialogMessage.created_at.asc(), DialogMessage.id.asc())
        .all()
    )
    events: list[dict[str, Any]] = []
    for message in messages:
        action_result = message.action_result if isinstance(message.action_result, dict) else {}
        data = action_result.get("data") if isinstance(action_result.get("data"), dict) else {}
        if str(data.get("agent_run_id") or "") != run.id:
            continue
        decision = data.get("approval_decision") if isinstance(data.get("approval_decision"), dict) else None
        if decision is None:
            continue
        events.append(_approval_event_summary(message, decision))
    return events


def _event_chain(
    run: WritingAgentRun,
    *,
    steps: list[WritingAgentStep],
    trace_items: list[dict[str, Any]],
    approval_events: list[dict[str, Any]],
    dialog_events: dict[str, Any],
    dialog_route_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    for event in dialog_route_events:
        chain_event = {
            "event_type": "dialog_route_decision",
            "trace_id": event.get("trace_id"),
            "action_type": event.get("action_type"),
            "selected_route": event.get("selected_route"),
            "selected_route_label": event.get("selected_route_label"),
            "reason_code": event.get("reason_code"),
            "reason_label": event.get("reason_label"),
            "request_message_id": event.get("request_message_id"),
            "response_message_id": event.get("response_message_id"),
        }
        source_run_id = str(event.get("source_run_id") or "").strip()
        if source_run_id:
            chain_event["source_run_id"] = source_run_id
        chain.append(chain_event)

    for event in approval_events:
        chain_event = {
            "event_type": "approval_decision",
            "message_id": event.get("message_id"),
            "action_type": event.get("action_type"),
            "decision": event.get("decision"),
            "decision_label": event.get("decision_label"),
        }
        if event.get("chapter_index") is not None:
            chain_event["chapter_index"] = event.get("chapter_index")
        chapter_index_source = str(event.get("chapter_index_source") or "").strip()
        if chapter_index_source:
            chain_event["chapter_index_source"] = chapter_index_source
            chain_event["chapter_index_source_label"] = event.get("chapter_index_source_label")
        if event.get("chapter_target_conflict") is not None:
            chain_event["chapter_target_conflict"] = event.get("chapter_target_conflict")
        chain.append(chain_event)

    chain.append(
        {
            "event_type": "run_dispatched",
            "run_id": run.id,
            "status": run.status,
            "entrypoint": run.entrypoint,
            "background_task_id": run.background_task_id,
        }
    )

    for step in steps:
        output = step.output if isinstance(step.output, dict) else {}
        chain.append(
            {
                "event_type": "tool_step",
                "step_id": step.id,
                "step_index": step.step_index,
                "tool_name": step.tool_name,
                "status": step.status,
                "trace_id": step.trace_id,
                "target_type": step.target_type,
                "target_id": step.target_id,
                "chapter_index": step.chapter_index,
                "tool_call_id": step.tool_call_id,
                "resource_binding": summarize_resource_binding(step.resource_binding),
            }
        )
        verification_event = _verification_event_summary(output.get("approval_verification_event"))
        if verification_event is not None:
            chain.append(verification_event)

    for trace in trace_items:
        chain.append(
            {
                "event_type": "trace_attached",
                "trace_id": trace.get("id"),
                "trace_type": trace.get("trace_type"),
                "status": trace.get("status"),
                "chapter_index": trace.get("chapter_index"),
                "context_block_count": trace.get("context_block_count"),
            }
        )

    result_message = dialog_events.get("result_message") if isinstance(dialog_events.get("result_message"), dict) else None
    if result_message:
        chain.append(
            {
                "event_type": "result_message",
                "message_id": result_message.get("id"),
                "action_type": result_message.get("action_type"),
                "action_status": result_message.get("action_status"),
            }
        )

    return chain


def _verification_event_summary(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    event_type = str(value.get("event_type") or "").strip()
    if event_type not in {"contract_verified", "contract_blocked"}:
        return None
    return {
        "event_type": event_type,
        "status": str(value.get("status") or ""),
        "reason": str(value.get("reason") or ""),
        "approval_contract_bound": bool(value.get("approval_contract_bound")),
        "approval_contract_version": value.get("approval_contract_version"),
        "write_step_count": value.get("write_step_count"),
        "tool_contract_drift_count": value.get("tool_contract_drift_count"),
        "tool_call_ids": _string_list(value.get("tool_call_ids")),
        "resource_bindings": _resource_binding_summaries(value.get("resource_bindings")),
    }


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item or "").strip()]


def _resource_binding_summaries(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    summaries: list[dict[str, Any]] = []
    for item in value:
        summary = summarize_resource_binding(item)
        if summary:
            summaries.append(summary)
    return summaries


def _approval_event_summary(message: DialogMessage, decision: dict[str, Any]) -> dict[str, Any]:
    decision_value = str(decision.get("decision") or "").strip()
    event = {
        "kind": str(decision.get("kind") or "pending_action_decision"),
        "message_id": message.id,
        "action_type": str(decision.get("action_type") or ""),
        "pending_action_type": str(decision.get("pending_action_type") or ""),
        "decision": decision_value,
        "decision_label": _decision_label(decision_value),
        "approval_mode": str(decision.get("approval_mode") or ""),
        "approval_contract_bound": bool(str(decision.get("approval_contract_hash") or "").strip()),
        "approval_contract_version": decision.get("approval_contract_version"),
        "resolved_at": decision.get("resolved_at"),
    }
    chapter_index = _optional_int(decision.get("chapter_index"))
    if chapter_index is not None:
        event["chapter_index"] = chapter_index
    chapter_index_source = str(decision.get("chapter_index_source") or "").strip()
    if chapter_index_source:
        event["chapter_index_source"] = chapter_index_source
        event["chapter_index_source_label"] = _chapter_source_label(chapter_index_source)
    chapter_target_conflict = _chapter_target_conflict_summary(decision.get("chapter_target_conflict"))
    if chapter_target_conflict is not None:
        event["chapter_target_conflict"] = chapter_target_conflict
    return event


def _chapter_target_conflict_summary(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or value.get("status") != "reserved":
        return None
    chapter_index = _optional_int(value.get("chapter_index"))
    if chapter_index is None:
        return None
    return {
        "status": "reserved",
        "chapter_index": chapter_index,
        "reason": str(value.get("reason") or "pending_or_running_generation"),
        "source": str(value.get("source") or "").strip(),
        "source_label": str(value.get("source_label") or "").strip(),
    }


def _decision_label(decision: str) -> str:
    if decision == "confirm":
        return "已确认"
    if decision == "cancel":
        return "已取消"
    if decision == "revise":
        return "要求修改"
    return decision


def _chapter_source_label(source: str) -> str:
    if source == "explicit_user":
        return "用户指定"
    if source == "inferred_next_unwritten":
        return "系统推断"
    if source == "router_default":
        return "默认目标"
    return source


def _optional_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _context_summary(traces: list[AIModelCallTrace]) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    for trace in traces:
        raw_blocks = trace.context_blocks if isinstance(trace.context_blocks, list) else []
        for index, block in enumerate(raw_blocks):
            if not isinstance(block, dict):
                continue
            sources = block.get("sources") if isinstance(block.get("sources"), list) else []
            content = str(block.get("content") or "")
            blocks.append(
                {
                    "trace_id": trace.id,
                    "key": str(block.get("key") or f"block-{index}"),
                    "kind": str(block.get("kind") or "unknown"),
                    "title": str(block.get("title") or block.get("key") or f"block-{index}"),
                    "char_count": len(content),
                    "source_count": len(sources),
                    "truncated": bool(block.get("truncated")),
                }
            )
    return {"total_blocks": len(blocks), "blocks": blocks}


def _intent_chain_summary(run: WritingAgentRun, steps: list[WritingAgentStep]) -> dict[str, Any]:
    planner = _planner_from_run(run)
    if planner is None:
        return {
            "status": "missing",
            "reason": "planner_not_recorded",
            "planned_tool_count": 0,
            "executed_tool_count": 0,
            "matched_tool_count": 0,
            "planned_tools": [],
        }

    planned_tool_names = _planned_tool_names(planner)
    step_by_tool_name: dict[str, WritingAgentStep] = {}
    for step in steps:
        if step.tool_name not in step_by_tool_name:
            step_by_tool_name[step.tool_name] = step

    planned_tools = []
    matched_tool_count = 0
    for tool_name in planned_tool_names:
        matched_step = step_by_tool_name.get(tool_name)
        if matched_step is not None:
            matched_tool_count += 1
        planned_tools.append(
            {
                "tool_name": tool_name,
                "status": "executed" if matched_step is not None else "pending",
                "step_index": matched_step.step_index if matched_step is not None else None,
            }
        )

    intent_projection = (
        planner.get("intent_projection") if isinstance(planner.get("intent_projection"), dict) else {}
    )
    candidate = (
        intent_projection.get("candidate") if isinstance(intent_projection.get("candidate"), dict) else {}
    )
    planner_summary = planner.get("planner") if isinstance(planner.get("planner"), dict) else {}
    rule_id = str(intent_projection.get("rule_id") or planner_summary.get("mapped_from_rule_id") or "").strip()
    intent_class = str(planner_summary.get("intent_class") or candidate.get("type") or "").strip()
    mapped_from_action_type = str(
        planner_summary.get("mapped_from_action_type") or candidate.get("type") or ""
    ).strip()
    chapter_index = _optional_int(planner_summary.get("chapter_index") or candidate.get("chapter_index"))
    params = candidate.get("params") if isinstance(candidate.get("params"), dict) else {}
    if chapter_index is None:
        chapter_index = _optional_int(params.get("chapter_index"))

    summary: dict[str, Any] = {
        "status": "available" if rule_id or intent_class or planned_tools else "missing",
        "source": "run_input_planner",
        "rule_id": rule_id,
        "intent_class": intent_class,
        "mapped_from_action_type": mapped_from_action_type,
        "chapter_index": chapter_index,
        "planned_tool_count": len(planned_tools),
        "executed_tool_count": matched_tool_count,
        "matched_tool_count": matched_tool_count,
        "planned_tools": planned_tools,
    }
    if summary["status"] == "missing":
        summary["reason"] = "intent_plan_not_recorded"
    return summary


def _end_to_end_chain_summary(
    intent_chain: dict[str, Any],
    *,
    steps: list[WritingAgentStep],
    trace_items: list[dict[str, Any]],
    dialog_events: dict[str, Any],
) -> dict[str, Any]:
    planned_tool_count = _non_negative_int(intent_chain.get("planned_tool_count"))
    executed_tool_count = _non_negative_int(intent_chain.get("executed_tool_count"))
    matched_tool_count = _non_negative_int(intent_chain.get("matched_tool_count"))
    tool_step_count = len(steps)
    model_trace_count = len(trace_items)
    result_message = (
        dialog_events.get("result_message") if isinstance(dialog_events.get("result_message"), dict) else None
    )
    result_summary = _result_message_chain_summary(result_message)
    coverage = {
        "intent": intent_chain.get("status") == "available",
        "planned_tools": planned_tool_count > 0,
        "executed_tools": tool_step_count > 0,
        "model_traces": model_trace_count > 0,
        "result_message": result_summary is not None,
    }
    if all(coverage.values()):
        status = "complete"
    elif any(coverage.values()):
        status = "partial"
    else:
        status = "missing"

    return {
        "status": status,
        "coverage": coverage,
        "intent_chain_status": str(intent_chain.get("status") or "missing"),
        "planned_tool_count": planned_tool_count,
        "executed_tool_count": executed_tool_count,
        "matched_tool_count": matched_tool_count,
        "tool_step_count": tool_step_count,
        "model_trace_count": model_trace_count,
        "result_message": result_summary,
        "segments": _end_to_end_chain_segments(
            intent_chain,
            planned_tool_count=planned_tool_count,
            executed_tool_count=executed_tool_count,
            model_trace_count=model_trace_count,
            result_summary=result_summary,
        ),
    }


def _result_message_chain_summary(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    action_type = str(value.get("action_type") or "").strip()
    action_status = str(value.get("action_status") or "").strip()
    if not action_type and not action_status:
        return None
    return {
        "status": "available",
        "action_type": action_type,
        "action_status": action_status,
    }


def _end_to_end_chain_segments(
    intent_chain: dict[str, Any],
    *,
    planned_tool_count: int,
    executed_tool_count: int,
    model_trace_count: int,
    result_summary: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    intent_status = "available" if intent_chain.get("status") == "available" else "missing"
    result_segment = {
        "stage": "result_message",
        "status": "available" if result_summary is not None else "missing",
    }
    if result_summary is not None:
        result_segment["action_type"] = result_summary["action_type"]
        result_segment["action_status"] = result_summary["action_status"]
    return [
        {
            "stage": "intent",
            "status": intent_status,
            "rule_id": str(intent_chain.get("rule_id") or ""),
            "intent_class": str(intent_chain.get("intent_class") or ""),
            "chapter_index": intent_chain.get("chapter_index"),
        },
        {
            "stage": "planned_tools",
            "status": "available" if planned_tool_count > 0 else "missing",
            "count": planned_tool_count,
        },
        {
            "stage": "executed_tools",
            "status": "available" if executed_tool_count > 0 else "missing",
            "count": executed_tool_count,
        },
        {
            "stage": "model_traces",
            "status": "available" if model_trace_count > 0 else "missing",
            "count": model_trace_count,
        },
        result_segment,
    ]


def _trace_anomaly_summary(
    run: WritingAgentRun,
    *,
    steps: list[WritingAgentStep],
    trace_items: list[dict[str, Any]],
    context: dict[str, Any],
    intent_chain: dict[str, Any],
    end_to_end_chain: dict[str, Any],
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []

    failed_steps = [step for step in steps if step.status in {"blocked", "failed"}]
    for step in failed_steps:
        issues.append(
            {
                "code": "failed_tool_step",
                "severity": "critical",
                "tool_name": step.tool_name,
                "status": step.status,
                "step_index": step.step_index,
                "chapter_index": step.chapter_index,
            }
        )

    failed_traces = [
        trace
        for trace in trace_items
        if str(trace.get("status") or "").strip().lower() in {"blocked", "failed", "error"}
    ]
    for trace in failed_traces:
        issues.append(
            {
                "code": "failed_model_trace",
                "severity": "critical",
                "trace_type": str(trace.get("trace_type") or ""),
                "status": str(trace.get("status") or ""),
                "chapter_index": trace.get("chapter_index"),
                "error_recorded": bool(str(trace.get("error_message") or "").strip()),
            }
        )

    missing_trace_steps = [step for step in steps if _step_expected_trace(step) and not step.trace_id]
    for step in missing_trace_steps:
        issues.append(
            {
                "code": "missing_trace_binding",
                "severity": "warning",
                "tool_name": step.tool_name,
                "status": step.status,
                "step_index": step.step_index,
                "chapter_index": step.chapter_index,
            }
        )

    unmatched_planned_tools = [
        tool
        for tool in _safe_planned_tools(intent_chain)
        if str(tool.get("status") or "").strip() not in {"executed", "completed", "success"}
    ]
    for tool in unmatched_planned_tools:
        issues.append(
            {
                "code": "planned_tool_not_executed",
                "severity": "warning",
                "tool_name": str(tool.get("tool_name") or ""),
            }
        )

    result_missing = bool(run.dialog_id and not _record_has_result_message(end_to_end_chain))
    if result_missing:
        issues.append(
            {
                "code": "missing_result_message",
                "severity": "warning",
                "stage": "result_message",
            }
        )

    truncated_context_blocks = [
        block for block in _record_list(context.get("blocks")) if block.get("truncated") is True
    ]
    for block in truncated_context_blocks:
        issues.append(
            {
                "code": "truncated_context_block",
                "severity": "info",
                "kind": str(block.get("kind") or ""),
                "title": str(block.get("title") or ""),
                "char_count": _non_negative_int(block.get("char_count")),
                "source_count": _non_negative_int(block.get("source_count")),
            }
        )

    severity_counts = {
        "critical": sum(1 for issue in issues if issue.get("severity") == "critical"),
        "warning": sum(1 for issue in issues if issue.get("severity") == "warning"),
        "info": sum(1 for issue in issues if issue.get("severity") == "info"),
    }
    if severity_counts["critical"] > 0:
        status = "failed"
    elif severity_counts["warning"] > 0:
        status = "needs_attention"
    elif severity_counts["info"] > 0:
        status = "informational"
    else:
        status = "clear"

    return {
        "status": status,
        "issue_count": len(issues),
        "severity_counts": severity_counts,
        "failed_step_count": len(failed_steps),
        "failed_trace_count": len(failed_traces),
        "missing_trace_binding_count": len(missing_trace_steps),
        "unmatched_planned_tool_count": len(unmatched_planned_tools),
        "missing_result_message": result_missing,
        "truncated_context_block_count": len(truncated_context_blocks),
        "issues": issues,
    }


def _step_expected_trace(step: WritingAgentStep) -> bool:
    return str(step.tool_name or "").strip() in TRACE_EXPECTED_TOOL_NAMES


def _safe_planned_tools(intent_chain: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        tool
        for tool in _record_list(intent_chain.get("planned_tools"))
        if str(tool.get("tool_name") or "").strip()
    ]


def _record_has_result_message(end_to_end_chain: dict[str, Any]) -> bool:
    coverage = end_to_end_chain.get("coverage") if isinstance(end_to_end_chain.get("coverage"), dict) else {}
    if coverage.get("result_message") is True:
        return True
    return isinstance(end_to_end_chain.get("result_message"), dict)


def _record_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _planner_from_run(run: WritingAgentRun) -> dict[str, Any] | None:
    run_input = run.input if isinstance(run.input, dict) else {}
    planner = run_input.get("planner")
    return planner if isinstance(planner, dict) else None


def _planned_tool_names(planner: dict[str, Any]) -> list[str]:
    raw_tools = planner.get("tools") if isinstance(planner.get("tools"), list) else None
    plan = planner.get("plan") if isinstance(planner.get("plan"), dict) else {}
    if raw_tools is None:
        raw_tools = plan.get("tools") if isinstance(plan.get("tools"), list) else None
    if raw_tools is None:
        raw_tools = plan.get("steps") if isinstance(plan.get("steps"), list) else []

    tool_names: list[str] = []
    for item in raw_tools:
        if isinstance(item, str):
            tool_name = item.strip()
        elif isinstance(item, dict):
            tool_name = str(item.get("tool_name") or item.get("name") or "").strip()
        else:
            tool_name = ""
        if tool_name:
            tool_names.append(tool_name)
    return tool_names


def _failure_summary(run: WritingAgentRun, steps: list[WritingAgentStep]) -> dict[str, Any] | None:
    if run.status not in {"blocked", "failed"}:
        return None
    failed_step = next((step for step in reversed(steps) if step.status in {"blocked", "failed"}), None)
    output = failed_step.output if failed_step is not None and isinstance(failed_step.output, dict) else {}
    return {
        "status": run.status,
        "tool_name": failed_step.tool_name if failed_step is not None else None,
        "step_index": failed_step.step_index if failed_step is not None else None,
        "reason_code": output.get("reason") or output.get("error"),
        "message": run.error or output.get("error") or failed_step.error if failed_step is not None else run.error,
    }


def _recommended_actions(
    steps: list[WritingAgentStep],
    *,
    failure: dict[str, Any] | None,
    control_plane_readiness: dict[str, Any] | None,
    command_contracts: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if failure is None:
        actions: list[dict[str, Any]] = []
        if control_plane_readiness_needs_attention(control_plane_readiness):
            actions.append(
                {
                    "tool_name": "inspect_agent_control_plane_readiness",
                    "reason_code": "agent_control_plane_degraded",
                }
            )
        if command_contracts_needs_attention(command_contracts):
            actions.append(
                {
                    "tool_name": "inspect_agent_command_contracts",
                    "reason_code": "agent_command_contracts_have_gaps",
                }
            )
        return actions
    for step in reversed(steps):
        output = step.output if isinstance(step.output, dict) else {}
        envelope = output.get("agent_tool_result") if isinstance(output.get("agent_tool_result"), dict) else {}
        recovery = envelope.get("recovery") if isinstance(envelope.get("recovery"), dict) else {}
        next_tool = str(recovery.get("next_tool") or "").strip()
        if recovery.get("status") == "recommended" and next_tool:
            return [
                {
                    "tool_name": next_tool,
                    "reason_code": recovery.get("reason_code"),
                    "source_step_index": step.step_index,
                }
            ]
    return [{"tool_name": "plan_recovery_tools", "reason_code": failure.get("reason_code") or "agent_run_blocked"}]


def _profile_policy_audit_from_steps(steps: list[WritingAgentStep]) -> dict[str, Any] | None:
    for step in reversed(steps):
        if step.tool_name != "describe_agent_tools":
            continue
        output = step.output if isinstance(step.output, dict) else {}
        projection = (
            output.get("agent_profile_tool_projection")
            if isinstance(output.get("agent_profile_tool_projection"), dict)
            else {}
        )
        audit = projection.get("consistency_audit")
        if isinstance(audit, dict):
            return dict(audit)
    return None


def _profile_policy_audit_summary(audit: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(audit, dict):
        return None
    summary = audit.get("summary") if isinstance(audit.get("summary"), dict) else {}
    issues = audit.get("issues") if isinstance(audit.get("issues"), list) else []
    return {
        "version": str(audit.get("version") or ""),
        "status": str(audit.get("status") or ""),
        "summary": {
            "issues": _non_negative_int(summary.get("issues")),
            "delegate_edges": _non_negative_int(summary.get("delegate_edges")),
        },
        "issues": [_profile_policy_issue_summary(issue) for issue in issues if isinstance(issue, dict)],
    }


def _profile_policy_issue_summary(issue: dict[str, Any]) -> dict[str, Any]:
    summary = {
        "code": str(issue.get("code") or ""),
        "severity": str(issue.get("severity") or ""),
        "profile": str(issue.get("profile") or ""),
    }
    target = str(issue.get("target") or "").strip()
    if target:
        summary["target"] = target
    return summary


def _non_negative_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)


def _audit_status(status: str) -> str:
    return {
        "success": "completed",
        "blocked": "blocked",
        "failed": "failed",
        "running": "running",
        "pending": "pending",
        "cancelled": "cancelled",
    }.get(status, status)


def _audit_reason(status: str, *, failure: dict[str, Any] | None) -> str:
    if failure is not None:
        return str(failure.get("reason_code") or status)
    return {
        "success": "run_completed",
        "running": "run_in_progress",
        "pending": "run_pending",
        "cancelled": "run_cancelled",
    }.get(status, "run_state")


def _audit_trace_metadata() -> dict[str, Any]:
    return {
        "source": "inspect_agent_trace_audit",
        "version": AGENT_TRACE_AUDIT_VERSION,
        "mutability": "read",
    }


def _clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_AUDIT_LIMIT
    return min(max(int(limit), 1), MAX_AUDIT_LIMIT)


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import AIModelCallTrace, DialogMessage, Project, WritingAgentRun, WritingAgentStep
from app.services.writing_agent.agent_step_binding import summarize_resource_binding

AGENT_TRACE_AUDIT_VERSION = "phase73.agent_trace_audit.v1"
DEFAULT_AUDIT_LIMIT = 20
MAX_AUDIT_LIMIT = 100


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
            }
        )

    steps = _steps_for_run(db, project_id, run.id, limit=clamped_limit)
    trace_ids = [step.trace_id for step in steps if step.trace_id]
    traces = _traces_by_id(db, project_id, trace_ids)
    trace_items = [_trace_summary(traces[trace_id]) for trace_id in trace_ids if trace_id in traces]
    approval_events = _approval_events_for_run(db, run)
    dialog_events = _dialog_events_for_run(db, run)
    event_chain = _event_chain(
        run,
        steps=steps,
        trace_items=trace_items,
        approval_events=approval_events,
        dialog_events=dialog_events,
    )
    context = _context_summary([traces[trace_id] for trace_id in trace_ids if trace_id in traces])
    failure = _failure_summary(run, steps)
    recommended_actions = _recommended_actions(steps, failure=failure)
    return _json_safe_output(
        {
            "status": "completed",
            "project_id": project_id,
            "audit": {
                "status": _audit_status(run.status),
                "reason": _audit_reason(run.status, failure=failure),
                "step_count": len(steps),
                "trace_count": len(trace_items),
                "approval_event_count": len(approval_events),
                "event_chain_count": len(event_chain),
                "context_block_count": context["total_blocks"],
            },
            "run": _run_summary(run),
            "steps": [_step_summary(step) for step in steps],
            "traces": trace_items,
            "dialog_events": dialog_events,
            "approval_events": approval_events,
            "event_chain": event_chain,
            "context": context,
            "failure": failure,
            "recommended_actions": recommended_actions,
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
) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
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


def _recommended_actions(steps: list[WritingAgentStep], *, failure: dict[str, Any] | None) -> list[dict[str, Any]]:
    if failure is None:
        return []
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

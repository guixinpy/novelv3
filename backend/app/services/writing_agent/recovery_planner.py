from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import BackgroundTask, ChapterContent, WritingAgentRun, WritingAgentStep
from app.services.writing_agent.agent_step_binding import summarize_resource_binding
from app.services.writing_agent.batch_enqueue import BATCH_TASK_TYPE
from app.services.writing_agent.batch_execution import execution_checkpoints_for_resume
from app.services.writing_agent.recovery_policy import (
    CHECKPOINT_RESUME_PREVIEW_VERSION,
    build_checkpoint_resume_policy,
)
from app.services.writing_agent.tool_executor import writing_agent_tool_adapter_metadata_by_name
from app.services.writing_agent.tool_registry import allowed_tool_names, build_agent_tool_plan

RECOVERY_PREVIEW_VERSION = "phase50.recovery_preview.v1"
MAINTENANCE_REPAIR_PREPARE_TOOL = "prepare_repair_longform_maintenance"
LEGACY_MAINTENANCE_REPAIR_TOOL = "repair_longform_maintenance"
SAFE_RECOVERY_EXECUTE_TOOLS = {"expand_outline_window", "backfill_outline_gaps"}


def build_recovery_tool_plan(db: Session, project_id: str, run_id: str | None) -> dict[str, Any]:
    if not run_id:
        return {
            "status": "failed",
            "error": "run_id is required",
            "source_run_id": None,
            "tools": [],
            "trace": {"selected_tools": [], "rejected_tools": [{"reason": "missing_run_id"}]},
        }

    run = (
        db.query(WritingAgentRun)
        .filter(WritingAgentRun.project_id == project_id, WritingAgentRun.id == run_id)
        .first()
    )
    if run is None:
        return {
            "status": "failed",
            "error": "Writing agent run not found",
            "source_run_id": run_id,
            "tools": [],
            "trace": {"selected_tools": [], "rejected_tools": [{"reason": "missing_run"}]},
        }

    step, recovery = _latest_recommended_recovery(db, project_id=project_id, run_id=run_id)
    if step is None or recovery is None:
        return {
            "status": "ready",
            "source_run_id": run_id,
            "source_run_status": run.status,
            "source_step": None,
            "recovery": {"status": "none"},
            "tools": [],
            "trace": {"selected_tools": [], "rejected_tools": [{"reason": "no_recommended_recovery"}]},
        }
    recovery = _normalize_recovery(recovery)

    tools = _tool_requests_from_recovery(recovery)
    selected_tools = [str(tool.get("tool_name") or "") for tool in tools]
    hash_payload = {
        "preview_version": RECOVERY_PREVIEW_VERSION,
        "project_id": project_id,
        "source_run_id": run_id,
        "source_step_id": step.id,
        "source_step_index": step.step_index,
        "source_tool_call_id": step.tool_call_id,
        "source_resource_binding": summarize_resource_binding(step.resource_binding),
        "source_tool": recovery.get("source_tool"),
        "reason_code": recovery.get("reason_code"),
        "affected_chapter_indexes": recovery.get("affected_chapter_indexes"),
        "tools": tools,
    }
    plan_hash = _plan_hash(hash_payload)
    safe_auto_execute = bool(tools) and all(tool.get("tool_name") in SAFE_RECOVERY_EXECUTE_TOOLS for tool in tools)
    guardrails = _recovery_guardrails(db, project_id, tools=tools, recovery=recovery, plan_hash=plan_hash)
    can_execute = bool(tools) and guardrails["status"] == "ready"
    execution_status = "ready" if can_execute else _first_blocker_code(guardrails)
    return {
        "status": "completed" if tools else "ready",
        "preview_version": RECOVERY_PREVIEW_VERSION,
        "preview_only": True,
        "mode": "preview",
        "can_execute": can_execute,
        "requires_confirmation": True,
        "approval_required": True,
        "plan_hash": plan_hash,
        "hash_payload": hash_payload,
        "source_run_id": run_id,
        "source_run_status": run.status,
        "source_step_id": step.id,
        "reason_code": recovery.get("reason_code"),
        "source_step": {
            "id": step.id,
            "step_index": step.step_index,
            "tool_name": step.tool_name,
            "status": step.status,
            "tool_call_id": step.tool_call_id,
            "resource_binding": summarize_resource_binding(step.resource_binding),
        },
        "recovery": recovery,
        "tools": tools,
        "guardrails": guardrails,
        "execution_policy": {
            "mode": "preview",
            "status": execution_status,
            "requires_confirmation": True,
            "requires_plan_hash": True,
            "safe_auto_execute": safe_auto_execute,
        },
        "trace": {
            "selected_tools": selected_tools,
            "rejected_tools": [] if tools else [{"reason": "recovery_without_next_tool"}],
        },
    }


def build_checkpoint_resume_preview(
    db: Session,
    project_id: str,
    *,
    task_id: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    run = _resume_run(db, project_id=project_id, run_id=run_id)
    if run_id and run is None:
        return _checkpoint_resume_failed(project_id, task_id=task_id, run_id=run_id, reason="missing_run")

    task = _resume_task(db, project_id=project_id, task_id=task_id, run=run)
    if task is None:
        return _checkpoint_resume_failed(project_id, task_id=task_id, run_id=run_id, reason="missing_task")

    chapter_range = _resume_chapter_range(task)
    if chapter_range is None:
        return _checkpoint_resume_failed(project_id, task_id=task.id, run_id=run_id, reason="missing_chapter_range")

    chapter_indexes = list(range(chapter_range["start"], chapter_range["end"] + 1))
    chapter_set = set(chapter_indexes)
    progress = _task_progress(task)
    checkpoints = execution_checkpoints_for_resume(task)
    step_evidence = _resume_step_evidence(
        db,
        project_id=project_id,
        task_id=task.id,
        run_id=run.id if run is not None else run_id,
        chapter_indexes=chapter_set,
    )
    chapter_records = _chapter_record_indexes(db, project_id=project_id, chapter_indexes=chapter_indexes)

    completed = sorted(
        (
            set(_progress_completed_indexes(progress, chapter_range=chapter_range))
            | set(chapter_records)
            | {item["chapter_index"] for item in checkpoints if item.get("status") == "completed"}
            | {
                item["chapter_index"]
                for item in step_evidence
                if item.get("status") == "success" and item.get("output_status") in {"completed", "success"}
            }
        )
        & chapter_set
    )
    blocked = sorted(
        (
            {item["chapter_index"] for item in checkpoints if item.get("status") in {"blocked", "failed"}}
            | {
                item["chapter_index"]
                for item in step_evidence
                if item.get("status") in {"blocked", "failed"} or item.get("output_status") in {"blocked", "failed"}
            }
        )
        - set(completed)
    )
    pending = [chapter_index for chapter_index in chapter_indexes if chapter_index not in set(completed)]
    resume = build_checkpoint_resume_policy(
        task_id=task.id,
        chapter_range=chapter_range,
        completed_chapter_indexes=completed,
        blocked_chapter_indexes=blocked,
        pending_chapter_indexes=pending,
    )
    return {
        "status": resume["status"],
        "preview_version": CHECKPOINT_RESUME_PREVIEW_VERSION,
        "preview_only": True,
        "mode": "preview",
        "project_id": project_id,
        "task_id": task.id,
        "task_status": task.status,
        "source_run_id": run.id if run is not None else run_id,
        "source_run_status": run.status if run is not None else None,
        "chapter_range": chapter_range,
        "completed_chapter_indexes": completed,
        "skipped_chapter_indexes": completed,
        "blocked_chapter_indexes": blocked,
        "pending_chapter_indexes": pending,
        "resume": resume,
        "checkpoint_evidence": {
            "background_task_progress": progress,
            "execution_checkpoints": checkpoints,
            "chapter_records": chapter_records,
            "writing_agent_steps": step_evidence,
        },
        "trace": {
            "selected_sources": ["background_task", "chapter_records", "writing_agent_steps"],
            "resume_reason": "blocked_chapter" if blocked else "first_pending_chapter",
        },
    }


def _latest_recommended_recovery(
    db: Session,
    *,
    project_id: str,
    run_id: str,
) -> tuple[WritingAgentStep | None, dict[str, Any] | None]:
    steps = (
        db.query(WritingAgentStep)
        .filter(
            WritingAgentStep.project_id == project_id,
            WritingAgentStep.run_id == run_id,
            WritingAgentStep.status.in_(("blocked", "failed", "success")),
        )
        .order_by(WritingAgentStep.step_index.desc(), WritingAgentStep.id.desc())
        .all()
    )
    for step in steps:
        output = step.output if isinstance(step.output, dict) else {}
        envelope = output.get("agent_tool_result") if isinstance(output.get("agent_tool_result"), dict) else {}
        recovery = envelope.get("recovery") if isinstance(envelope.get("recovery"), dict) else None
        if recovery and recovery.get("status") == "recommended":
            return step, recovery
    return None, None


def _checkpoint_resume_failed(
    project_id: str,
    *,
    task_id: str | None,
    run_id: str | None,
    reason: str,
) -> dict[str, Any]:
    return {
        "status": "failed",
        "preview_version": CHECKPOINT_RESUME_PREVIEW_VERSION,
        "project_id": project_id,
        "task_id": task_id,
        "source_run_id": run_id,
        "reason": reason,
        "completed_chapter_indexes": [],
        "skipped_chapter_indexes": [],
        "blocked_chapter_indexes": [],
        "pending_chapter_indexes": [],
        "resume": {"status": "failed", "can_resume": False, "next_chapter_index": None},
        "checkpoint_evidence": {},
        "trace": {"selected_sources": [], "rejected_sources": [{"reason": reason}]},
    }


def _resume_run(db: Session, *, project_id: str, run_id: str | None) -> WritingAgentRun | None:
    if not run_id:
        return None
    return (
        db.query(WritingAgentRun)
        .filter(WritingAgentRun.project_id == project_id, WritingAgentRun.id == run_id)
        .first()
    )


def _resume_task(
    db: Session,
    *,
    project_id: str,
    task_id: str | None,
    run: WritingAgentRun | None,
) -> BackgroundTask | None:
    resolved_task_id = str(task_id or "").strip()
    if not resolved_task_id and run is not None:
        resolved_task_id = str(run.background_task_id or "").strip()
        run_input = run.input if isinstance(run.input, dict) else {}
        resolved_task_id = resolved_task_id or str(run_input.get("task_id") or "").strip()
    query = db.query(BackgroundTask).filter(
        BackgroundTask.project_id == project_id,
        BackgroundTask.task_type == BATCH_TASK_TYPE,
    )
    if resolved_task_id:
        return query.filter(BackgroundTask.id == resolved_task_id).first()
    return query.order_by(BackgroundTask.created_at.desc(), BackgroundTask.id.desc()).first()


def _resume_chapter_range(task: BackgroundTask) -> dict[str, int] | None:
    payload = task.payload if isinstance(task.payload, dict) else {}
    result = task.result if isinstance(task.result, dict) else {}
    progress = result.get("progress") if isinstance(result.get("progress"), dict) else {}
    for source in (payload, progress):
        chapter_range = source.get("chapter_range") if isinstance(source, dict) else None
        if not isinstance(chapter_range, dict):
            continue
        start = _positive_int(chapter_range.get("start"))
        end = _positive_int(chapter_range.get("end"))
        if start is not None and end is not None and start <= end:
            return {"start": start, "end": end}
    chapter_indexes = _payload_chapter_indexes(payload)
    if chapter_indexes:
        return {"start": min(chapter_indexes), "end": max(chapter_indexes)}
    return None


def _task_progress(task: BackgroundTask) -> dict[str, Any]:
    result = task.result if isinstance(task.result, dict) else {}
    progress = result.get("progress") if isinstance(result.get("progress"), dict) else {}
    return dict(progress)


def _progress_completed_indexes(progress: dict[str, Any], *, chapter_range: dict[str, int]) -> list[int]:
    completed = set(_int_list(progress.get("completed_chapter_indexes")))
    completed_until = _positive_int(progress.get("completed_until_chapter_index"))
    if completed_until is not None:
        completed.update(range(chapter_range["start"], min(completed_until, chapter_range["end"]) + 1))
    return sorted(index for index in completed if chapter_range["start"] <= index <= chapter_range["end"])


def _resume_step_evidence(
    db: Session,
    *,
    project_id: str,
    task_id: str,
    run_id: str | None,
    chapter_indexes: set[int],
) -> list[dict[str, Any]]:
    query = db.query(WritingAgentStep).filter(WritingAgentStep.project_id == project_id)
    if run_id:
        query = query.filter(WritingAgentStep.run_id == run_id)
    else:
        query = query.filter(WritingAgentStep.background_task_id == task_id)
    rows = query.order_by(WritingAgentStep.step_index.asc(), WritingAgentStep.id.asc()).all()
    evidence: list[dict[str, Any]] = []
    for step in rows:
        if step.background_task_id and step.background_task_id != task_id:
            continue
        output = step.output if isinstance(step.output, dict) else {}
        chapter_index = _positive_int(step.chapter_index) or _positive_int(output.get("chapter_index"))
        if chapter_index is None or chapter_index not in chapter_indexes:
            continue
        output_task = output.get("task") if isinstance(output.get("task"), dict) else {}
        if not step.background_task_id and output_task.get("id") not in (None, task_id):
            continue
        evidence.append(
            {
                "id": step.id,
                "run_id": step.run_id,
                "step_index": step.step_index,
                "tool_name": step.tool_name,
                "status": step.status,
                "output_status": str(output.get("status") or ""),
                "chapter_index": chapter_index,
                "reason": output.get("reason") or step.error,
                "trace_id": step.trace_id,
            }
        )
    return evidence


def _chapter_record_indexes(
    db: Session,
    *,
    project_id: str,
    chapter_indexes: list[int],
) -> list[int]:
    if not chapter_indexes:
        return []
    rows = (
        db.query(ChapterContent.chapter_index)
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.chapter_index.in_(chapter_indexes),
            ChapterContent.content.isnot(None),
            ChapterContent.content != "",
        )
        .order_by(ChapterContent.chapter_index.asc())
        .all()
    )
    return [int(row.chapter_index) for row in rows]


def _payload_chapter_indexes(payload: dict[str, Any]) -> list[int]:
    batch = payload.get("batch") if isinstance(payload.get("batch"), dict) else {}
    return _int_list(batch.get("chapter_indexes"))


def _int_list(value: object) -> list[int]:
    if not isinstance(value, list):
        return []
    indexes = {_positive_int(item) for item in value}
    return sorted(index for index in indexes if index is not None)


def _positive_int(value: object) -> int | None:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _tool_request_from_recovery(recovery: dict[str, Any]) -> dict[str, Any] | None:
    next_tool = str(recovery.get("next_tool") or "").strip()
    if not next_tool:
        return None
    params = recovery.get("next_params") if isinstance(recovery.get("next_params"), dict) else {}
    request: dict[str, Any] = {
        "tool_name": next_tool,
        "params": params,
        "planner": {
            "reason": str(recovery.get("message") or "根据上一轮阻塞结果规划恢复工具。"),
            "on_missing": "ask_user" if recovery.get("requires_user_input") else "stop",
            "on_failure": "stop",
            "expected_output": "恢复阻塞前置条件。",
            "post_generation": False,
            "planner_version": "phase48.recovery_planner.v1",
        },
    }
    next_command_args = recovery.get("next_command_args")
    if next_command_args:
        request["command_args"] = str(next_command_args)
    return request


def _normalize_recovery(recovery: dict[str, Any]) -> dict[str, Any]:
    if str(recovery.get("next_tool") or "").strip() != LEGACY_MAINTENANCE_REPAIR_TOOL:
        return recovery
    normalized = dict(recovery)
    continuation_tools = recovery.get("continuation_tools") if isinstance(recovery.get("continuation_tools"), list) else []
    next_params = dict(recovery.get("next_params") if isinstance(recovery.get("next_params"), dict) else {})
    if continuation_tools and "post_approval_continuation_tools" not in next_params:
        next_params["post_approval_continuation_tools"] = continuation_tools
        normalized["post_approval_continuation_tools"] = continuation_tools
    normalized["legacy_next_tool"] = LEGACY_MAINTENANCE_REPAIR_TOOL
    normalized["next_tool"] = MAINTENANCE_REPAIR_PREPARE_TOOL
    normalized["next_params"] = next_params
    normalized["continuation_tools"] = []
    return normalized


def _tool_requests_from_recovery(recovery: dict[str, Any]) -> list[dict[str, Any]]:
    first = _tool_request_from_recovery(recovery)
    if first is None:
        return []
    requests = [first]
    continuation_tools = recovery.get("continuation_tools")
    if not isinstance(continuation_tools, list):
        return requests
    for index, item in enumerate(continuation_tools, start=1):
        if not isinstance(item, dict):
            continue
        request = _tool_request_from_continuation(item, index=index)
        if request is not None:
            requests.append(request)
    return requests


def _tool_request_from_continuation(item: dict[str, Any], *, index: int) -> dict[str, Any] | None:
    tool_name = str(item.get("tool_name") or "").strip()
    if not tool_name:
        return None
    request: dict[str, Any] = {
        "tool_name": tool_name,
        "params": item.get("params") if isinstance(item.get("params"), dict) else {},
        "planner": {
            "step_index": index + 1,
            "reason": str(item.get("reason") or "恢复前置条件后继续执行下一步工具。"),
            "on_missing": str(item.get("on_missing") or "stop"),
            "on_failure": str(item.get("on_failure") or "stop"),
            "expected_output": str(item.get("expected_output") or "恢复链后续工具输出。"),
            "post_generation": bool(item.get("post_generation") is True),
            "planner_version": "phase55.recovery_chain.v1",
        },
    }
    command_args = item.get("command_args")
    if command_args:
        request["command_args"] = str(command_args)
    return request


def _plan_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _recovery_guardrails(
    db: Session,
    project_id: str,
    *,
    tools: list[dict[str, Any]],
    recovery: dict[str, Any],
    plan_hash: str,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    if not tools:
        blockers.append({"code": "recovery_without_next_tool", "message": "恢复建议缺少可执行工具。"})
        return {"status": "blocked", "checks": checks, "blockers": blockers}

    if recovery.get("requires_user_input") is True:
        blockers.append(
            {
                "code": "requires_user_input",
                "tool_name": str(tools[0].get("tool_name") or ""),
                "fields": recovery.get("user_input_fields") if isinstance(recovery.get("user_input_fields"), list) else [],
                "message": "恢复工具需要用户补充输入，不能自动执行。",
            }
        )

    allowed_tools = allowed_tool_names()
    for index, tool in enumerate(tools, start=1):
        tool_name = str(tool.get("tool_name") or "").strip()
        allowed = tool_name in allowed_tools
        checks.append(
            {
                "code": "tool_allowed",
                "status": "passed" if allowed else "blocked",
                "tool_name": tool_name,
                "position": index,
            }
        )
        if not allowed:
            blockers.append(
                {"code": "tool_not_allowed", "tool_name": tool_name, "position": index, "message": "恢复工具未注册。"}
            )
        elif not _tool_visible_now(db, project_id, tool):
            blockers.append(
                {"code": "tool_not_visible", "tool_name": tool_name, "position": index, "message": "恢复工具当前不可见。"}
            )

    failed_attempt = _failed_recovery_attempt(db, project_id, plan_hash)
    checks.append(
        {
            "code": "repeat_failed_recovery",
            "status": "blocked" if failed_attempt else "passed",
            "plan_hash": plan_hash,
        }
    )
    if failed_attempt:
        blockers.append(
            {
                "code": "repeat_failed_recovery",
                "run_id": failed_attempt.id,
                "message": "同一恢复计划已有失败执行记录，不能盲目重复执行。",
            }
        )

    return {"status": "blocked" if blockers else "ready", "checks": checks, "blockers": blockers}


def _tool_visible_now(db: Session, project_id: str, tool: dict[str, Any]) -> bool:
    tool_name = str(tool.get("tool_name") or "").strip()
    chapter_index = _chapter_index_from_tool(tool)
    plan = build_agent_tool_plan(
        db,
        project_id,
        chapter_index=chapter_index,
        adapter_metadata_by_name=writing_agent_tool_adapter_metadata_by_name(),
    )
    return tool_name in {str(item.get("name")) for item in plan.get("visible_tools", []) if isinstance(item, dict)}


def _chapter_index_from_tool(tool: dict[str, Any]) -> int | None:
    params = tool.get("params") if isinstance(tool.get("params"), dict) else {}
    for key in ("chapter_index", "start_chapter", "before_chapter"):
        try:
            value = int(params.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value
    return None


def _failed_recovery_attempt(db: Session, project_id: str, plan_hash: str) -> WritingAgentRun | None:
    if not plan_hash:
        return None
    rows = (
        db.query(WritingAgentRun)
        .filter(WritingAgentRun.project_id == project_id, WritingAgentRun.status == "failed")
        .order_by(WritingAgentRun.created_at.desc(), WritingAgentRun.id.desc())
        .all()
    )
    for row in rows:
        run_input = row.input if isinstance(row.input, dict) else {}
        planner = run_input.get("planner") if isinstance(run_input.get("planner"), dict) else {}
        if planner.get("mode") == "execute" and planner.get("plan_hash") == plan_hash:
            return row
    return None


def _first_blocker_code(guardrails: dict[str, Any]) -> str:
    blockers = guardrails.get("blockers") if isinstance(guardrails.get("blockers"), list) else []
    if blockers and isinstance(blockers[0], dict):
        return str(blockers[0].get("code") or "not_executable")
    return "not_executable"

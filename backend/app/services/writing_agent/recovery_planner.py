from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import WritingAgentRun, WritingAgentStep
from app.services.writing_agent.tool_registry import allowed_tool_names, build_agent_tool_plan

RECOVERY_PREVIEW_VERSION = "phase50.recovery_preview.v1"
SAFE_RECOVERY_EXECUTE_TOOLS = {"expand_outline_window", "backfill_outline_gaps", "repair_longform_maintenance"}


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

    tool = _tool_request_from_recovery(recovery)
    selected_tools = [tool["tool_name"]] if tool else []
    hash_payload = {
        "preview_version": RECOVERY_PREVIEW_VERSION,
        "source_run_id": run_id,
        "source_step_id": step.id,
        "source_step_index": step.step_index,
        "reason_code": recovery.get("reason_code"),
        "tools": [tool] if tool else [],
    }
    plan_hash = _plan_hash(hash_payload)
    safe_auto_execute = tool["tool_name"] in SAFE_RECOVERY_EXECUTE_TOOLS if tool else False
    guardrails = _recovery_guardrails(db, project_id, tool=tool, recovery=recovery, plan_hash=plan_hash)
    can_execute = tool is not None and guardrails["status"] == "ready"
    execution_status = "ready" if can_execute else _first_blocker_code(guardrails)
    return {
        "status": "completed" if tool else "ready",
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
        },
        "recovery": recovery,
        "tools": [tool] if tool else [],
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
            "rejected_tools": [] if tool else [{"reason": "recovery_without_next_tool"}],
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


def _tool_request_from_recovery(recovery: dict[str, Any]) -> dict[str, Any] | None:
    next_tool = str(recovery.get("next_tool") or "").strip()
    if not next_tool:
        return None
    request: dict[str, Any] = {
        "tool_name": next_tool,
        "params": recovery.get("next_params") if isinstance(recovery.get("next_params"), dict) else {},
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


def _plan_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _recovery_guardrails(
    db: Session,
    project_id: str,
    *,
    tool: dict[str, Any] | None,
    recovery: dict[str, Any],
    plan_hash: str,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    if tool is None:
        blockers.append({"code": "recovery_without_next_tool", "message": "恢复建议缺少可执行工具。"})
        return {"status": "blocked", "checks": checks, "blockers": blockers}

    tool_name = str(tool.get("tool_name") or "").strip()
    if recovery.get("requires_user_input") is True:
        blockers.append(
            {
                "code": "requires_user_input",
                "tool_name": tool_name,
                "fields": recovery.get("user_input_fields") if isinstance(recovery.get("user_input_fields"), list) else [],
                "message": "恢复工具需要用户补充输入，不能自动执行。",
            }
        )

    allowed = tool_name in allowed_tool_names()
    checks.append({"code": "tool_allowed", "status": "passed" if allowed else "blocked", "tool_name": tool_name})
    if not allowed:
        blockers.append({"code": "tool_not_allowed", "tool_name": tool_name, "message": "恢复工具未注册。"})
    elif not _tool_visible_now(db, project_id, tool):
        blockers.append({"code": "tool_not_visible", "tool_name": tool_name, "message": "恢复工具当前不可见。"})

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
    plan = build_agent_tool_plan(db, project_id, chapter_index=chapter_index)
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

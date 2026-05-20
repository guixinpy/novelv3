from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import WritingAgentRun, WritingAgentStep


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
    return {
        "status": "completed" if tool else "ready",
        "source_run_id": run_id,
        "source_run_status": run.status,
        "source_step": {
            "id": step.id,
            "step_index": step.step_index,
            "tool_name": step.tool_name,
            "status": step.status,
        },
        "recovery": recovery,
        "tools": [tool] if tool else [],
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
            WritingAgentStep.status.in_(("blocked", "failed")),
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

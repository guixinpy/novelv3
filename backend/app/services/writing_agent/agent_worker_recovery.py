from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import BackgroundTask, WritingAgentRun
from app.services.writing_agent.agent_definitions import load_agent_definition

AGENT_WORKER_ORPHAN_RECOVERY_VERSION = "phase236.agent_worker_orphan_recovery.v1"
ACTIVE_WORKER_RUN_STATUSES = ("pending", "running")
FAILED_PARENT_STATUSES = ("failed", "cancelled")
FAILED_TASK_STATUSES = ("failed", "cancelled")
DEFAULT_ORPHAN_SCAN_LIMIT = 20


def inspect_agent_worker_orphan_recovery(
    db: Session,
    project_id: str,
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    active_worker_runs = _active_worker_runs(db, project_id, limit=_scan_limit(limit))
    orphan_runs = [_orphan_candidate(db, run) for run in active_worker_runs]
    orphan_runs = [candidate for candidate in orphan_runs if candidate is not None]
    recovery_actions = [action for candidate in orphan_runs for action in _recovery_actions(candidate)]
    return {
        "version": AGENT_WORKER_ORPHAN_RECOVERY_VERSION,
        "status": "needs_attention" if orphan_runs else "clear",
        "summary": {
            "active_worker_runs": len(active_worker_runs),
            "orphan_worker_runs": len(orphan_runs),
            "recovery_actions": len(recovery_actions),
        },
        "orphan_worker_runs": orphan_runs,
        "recovery_actions": recovery_actions,
        "recommended_tools": ["inspect_agent_trace_audit", "plan_recovery_tools"] if orphan_runs else [],
    }


def _active_worker_runs(db: Session, project_id: str, *, limit: int) -> list[WritingAgentRun]:
    rows = (
        db.query(WritingAgentRun)
        .filter(WritingAgentRun.project_id == project_id, WritingAgentRun.status.in_(ACTIVE_WORKER_RUN_STATUSES))
        .order_by(WritingAgentRun.created_at.desc(), WritingAgentRun.id.desc())
        .limit(limit)
        .all()
    )
    return [run for run in rows if _agent_profile_is_worker(_agent_profile(run))]


def _orphan_candidate(db: Session, run: WritingAgentRun) -> dict[str, Any] | None:
    agent_profile = _agent_profile(run)
    parent_run_id = _parent_run_id(run)
    background_task_id = str(run.background_task_id or "").strip() or None
    parent_status = None
    background_task_status = None
    reason_code = ""

    redispatch_tasks: list[dict[str, Any]] = []
    if parent_run_id:
        parent = _run_by_id(db, project_id=run.project_id, run_id=parent_run_id)
        parent_status = str(parent.status) if parent is not None else "missing"
        if parent is None:
            reason_code = "worker_parent_run_missing"
        elif parent.status in FAILED_PARENT_STATUSES:
            reason_code = "worker_parent_run_terminal"
            redispatch_tasks = _parent_tool_requests(parent)
    else:
        reason_code = "worker_parent_run_unlinked"

    if not reason_code and background_task_id:
        background_task = _background_task_by_id(db, project_id=run.project_id, task_id=background_task_id)
        background_task_status = str(background_task.status) if background_task is not None else "missing"
        if background_task is None:
            reason_code = "worker_background_task_missing"
        elif background_task.status in FAILED_TASK_STATUSES:
            reason_code = "worker_background_task_terminal"

    if not reason_code:
        return None

    candidate: dict[str, Any] = {
        "run_id": run.id,
        "agent_profile": agent_profile,
        "run_status": str(run.status),
        "parent_run_id": parent_run_id,
        "parent_status": parent_status,
        "background_task_id": background_task_id,
        "background_task_status": background_task_status,
        "reason_code": reason_code,
    }
    if redispatch_tasks:
        candidate["redispatch_tasks"] = redispatch_tasks
    return candidate


def _recovery_actions(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    actions = [
        {
            "action": "mark_worker_run_blocked",
            "run_id": candidate["run_id"],
            "reason_code": candidate["reason_code"],
            "preview_only": True,
        }
    ]
    redispatch_tasks = candidate.get("redispatch_tasks") if isinstance(candidate.get("redispatch_tasks"), list) else []
    if candidate.get("parent_run_id") and redispatch_tasks:
        actions.append(
            {
                "action": "redispatch_worker_tasks",
                "tool_name": "inspect_agent_worker_dispatch",
                "params": {
                    "parent_run_id": candidate["parent_run_id"],
                    "tasks": redispatch_tasks,
                },
                "preview_only": True,
            }
        )
    return actions


def _run_by_id(db: Session, *, project_id: str, run_id: str) -> WritingAgentRun | None:
    return (
        db.query(WritingAgentRun)
        .filter(WritingAgentRun.project_id == project_id, WritingAgentRun.id == run_id)
        .first()
    )


def _background_task_by_id(db: Session, *, project_id: str, task_id: str) -> BackgroundTask | None:
    return (
        db.query(BackgroundTask)
        .filter(BackgroundTask.project_id == project_id, BackgroundTask.id == task_id)
        .first()
    )


def _agent_profile(run: WritingAgentRun) -> str:
    run_input = run.input if isinstance(run.input, dict) else {}
    planner = run_input.get("planner") if isinstance(run_input.get("planner"), dict) else {}
    return str(planner.get("agent_profile") or run_input.get("agent_profile") or "").strip()


def _parent_run_id(run: WritingAgentRun) -> str | None:
    run_input = run.input if isinstance(run.input, dict) else {}
    planner = run_input.get("planner") if isinstance(run_input.get("planner"), dict) else {}
    worker_dispatch = planner.get("worker_dispatch") if isinstance(planner.get("worker_dispatch"), dict) else {}
    value = (
        planner.get("source_run_id")
        or planner.get("parent_run_id")
        or worker_dispatch.get("parent_run_id")
        or run_input.get("source_run_id")
        or run_input.get("parent_run_id")
    )
    return str(value or "").strip() or None


def _parent_tool_requests(run: WritingAgentRun) -> list[dict[str, Any]]:
    run_input = run.input if isinstance(run.input, dict) else {}
    tools = run_input.get("tools") if isinstance(run_input.get("tools"), list) else []
    requests: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        tool_name = str(tool.get("tool_name") or "").strip()
        if not tool_name:
            continue
        requests.append(
            {
                "tool_name": tool_name,
                "params": tool.get("params") if isinstance(tool.get("params"), dict) else {},
            }
        )
    return requests


def _agent_profile_is_worker(agent_profile: str) -> bool:
    if not agent_profile:
        return False
    definition = load_agent_definition(agent_profile)
    return definition.get("status") == "ready" and definition.get("role") == "worker"


def _scan_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_ORPHAN_SCAN_LIMIT
    return min(max(int(limit), 1), 100)

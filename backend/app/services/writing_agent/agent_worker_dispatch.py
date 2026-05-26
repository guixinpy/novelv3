from __future__ import annotations

from typing import Any

from app.services.writing_agent.agent_definitions import load_agent_definition

AGENT_WORKER_DISPATCH_VERSION = "phase230.agent_worker_dispatch.v1"


def preview_agent_worker_dispatch(
    worker_name: str,
    tasks: list[dict[str, Any]],
    *,
    parent_run_id: str | None = None,
) -> dict[str, Any]:
    definition = load_agent_definition(worker_name)
    if definition.get("status") != "ready":
        return {
            "version": AGENT_WORKER_DISPATCH_VERSION,
            "status": "blocked",
            "worker": _worker_summary(definition),
            "summary": {"planned_tasks": 0, "blocked_tasks": 0, "issues": 1},
            "task_envelopes": [],
            "issues": [
                {
                    "code": str(definition.get("reason_code") or "agent_definition_not_ready"),
                    "severity": "error",
                    "worker": str(worker_name or "").strip(),
                }
            ],
        }

    task_envelopes = [
        _task_envelope(definition, task, parent_run_id=parent_run_id)
        for task in tasks
        if isinstance(task, dict)
    ]
    issues = [issue for envelope in task_envelopes for issue in envelope.pop("_issues", [])]
    blocked_tasks = sum(1 for envelope in task_envelopes if envelope["status"] == "blocked")
    planned_tasks = len(task_envelopes) - blocked_tasks
    return {
        "version": AGENT_WORKER_DISPATCH_VERSION,
        "status": "ready" if not issues else "blocked",
        "worker": _worker_summary(definition),
        "summary": {
            "planned_tasks": planned_tasks,
            "blocked_tasks": blocked_tasks,
            "issues": len(issues),
        },
        "task_envelopes": task_envelopes,
        "issues": issues,
    }


def _task_envelope(
    definition: dict[str, Any],
    task: dict[str, Any],
    *,
    parent_run_id: str | None,
) -> dict[str, Any]:
    worker_name = str(definition["name"])
    tool_name = str(task.get("tool_name") or "").strip()
    issue_codes: list[str] = []
    issues: list[dict[str, Any]] = []

    if tool_name not in set(definition["allowed_tools"]):
        issue_codes.append("tool_not_allowed_for_worker")
        issues.append(_issue("tool_not_allowed_for_worker", worker_name=worker_name, tool_name=tool_name))
    if _has_child_dispatch(task) and definition["can_dispatch_children"] is not True:
        issue_codes.append("child_dispatch_not_allowed")
        issues.append(_issue("child_dispatch_not_allowed", worker_name=worker_name, tool_name=tool_name))

    envelope = {
        "status": "planned" if not issue_codes else "blocked",
        "worker": worker_name,
        "role": definition["role"],
        "tool_name": tool_name,
        "params": task.get("params") if isinstance(task.get("params"), dict) else {},
        "parent_run_id": parent_run_id,
        "dispatch_mode": "preview_only",
        "will_execute": False,
        "child_dispatch_allowed": definition["can_dispatch_children"] is True,
    }
    if issue_codes:
        envelope["issue_codes"] = issue_codes
    envelope["_issues"] = issues
    return envelope


def _worker_summary(definition: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": str(definition.get("name") or ""),
        "role": str(definition.get("role") or "unknown"),
        "can_dispatch_children": definition.get("can_dispatch_children") is True,
        "allowed_tools": list(definition.get("allowed_tools") or []),
    }


def _issue(code: str, *, worker_name: str, tool_name: str) -> dict[str, Any]:
    return {
        "code": code,
        "severity": "error",
        "tool_name": tool_name,
        "worker": worker_name,
    }


def _has_child_dispatch(task: dict[str, Any]) -> bool:
    children = task.get("children")
    delegate_to = task.get("delegate_to") or task.get("delegate_to_worker")
    return bool(children or delegate_to)

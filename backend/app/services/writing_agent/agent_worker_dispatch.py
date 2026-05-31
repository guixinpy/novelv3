from __future__ import annotations

from typing import Any

from app.services.writing_agent.agent_definitions import inspect_agent_definition_registry, load_agent_definition

AGENT_WORKER_DISPATCH_VERSION = "phase230.agent_worker_dispatch.v1"
TOOL_WORKER_ROUTES = {
    "generate_setup": "drafting_worker",
    "generate_storyline": "drafting_worker",
    "generate_outline": "drafting_worker",
    "generate_chapter": "drafting_worker",
    "prepare_generate_chapter_execution": "drafting_worker",
    "execute_generate_chapter_with_approval": "drafting_worker",
    "review_chapter_quality": "reviewer_worker",
    "review_chapter_continuity": "reviewer_worker",
    "search_agent_retrieval_context": "retrieval_worker",
    "summarize_longform_context": "memory_worker",
    "inspect_agent_context_compression_projection": "memory_worker",
    "inspect_agent_memory_activation_plan": "memory_worker",
    "plan_post_chapter_memory_capture": "memory_worker",
    "prepare_record_agent_knowledge_base_candidate": "memory_worker",
    "record_agent_knowledge_base_candidate": "memory_worker",
    "execute_record_agent_knowledge_base_candidate_with_approval": "memory_worker",
    "inspect_agent_memory_route": "memory_worker",
    "inspect_agent_knowledge_base_route": "memory_worker",
    "inspect_agent_world_model_route": "world_model_worker",
    "prepare_analyze_chapter_world_model_execution": "world_model_worker",
    "analyze_chapter_world_model": "world_model_worker",
    "execute_analyze_chapter_world_model_with_approval": "world_model_worker",
    "review_world_model_proposals": "world_model_worker",
    "plan_world_model_proposal_resolution": "world_model_worker",
    "preview_world_model_proposal_resolution": "world_model_worker",
    "draft_world_model_proposal_resolution_decisions": "world_model_worker",
    "draft_high_value_world_proposal_resolution_decisions": "world_model_worker",
    "plan_chapter_revision": "revision_worker",
    "create_revision_draft": "revision_worker",
    "apply_planner_revision_patch": "revision_worker",
    "execute_apply_planner_revision_patch_with_approval": "revision_worker",
    "plan_recovery_tools": "recovery_worker",
    "repair_longform_maintenance": "recovery_worker",
}


def preview_agent_worker_dispatch(
    worker_name: str,
    tasks: list[dict[str, Any]],
    *,
    parent_run_id: str | None = None,
    include_definition_registry: bool = True,
) -> dict[str, Any]:
    definition = load_agent_definition(worker_name)
    if definition.get("status") != "ready":
        output = {
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
        return _with_definition_registry(output, include_definition_registry=include_definition_registry)

    task_envelopes = [
        _task_envelope(definition, task, parent_run_id=parent_run_id)
        for task in tasks
        if isinstance(task, dict)
    ]
    issues = [issue for envelope in task_envelopes for issue in envelope.pop("_issues", [])]
    blocked_tasks = sum(1 for envelope in task_envelopes if envelope["status"] == "blocked")
    planned_tasks = len(task_envelopes) - blocked_tasks
    output = {
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
    return _with_definition_registry(output, include_definition_registry=include_definition_registry)


def agent_worker_profile_for_tool(tool_name: str) -> str | None:
    return TOOL_WORKER_ROUTES.get(str(tool_name or "").strip()) or None


def preview_agent_worker_dispatches(
    tasks: list[dict[str, Any]],
    *,
    parent_run_id: str | None = None,
) -> dict[str, Any]:
    grouped_tasks: dict[str, list[dict[str, Any]]] = {}
    for task in tasks:
        if not isinstance(task, dict):
            continue
        worker_name = agent_worker_profile_for_tool(str(task.get("tool_name") or ""))
        if not worker_name:
            continue
        grouped_tasks.setdefault(worker_name, []).append(task)

    worker_dispatches = [
        preview_agent_worker_dispatch(
            worker_name,
            worker_tasks,
            parent_run_id=parent_run_id,
            include_definition_registry=False,
        )
        for worker_name, worker_tasks in grouped_tasks.items()
    ]
    issues = [issue for dispatch in worker_dispatches for issue in dispatch.get("issues", [])]
    planned_tasks = sum(int(dispatch.get("summary", {}).get("planned_tasks") or 0) for dispatch in worker_dispatches)
    blocked_tasks = sum(int(dispatch.get("summary", {}).get("blocked_tasks") or 0) for dispatch in worker_dispatches)
    return {
        "version": AGENT_WORKER_DISPATCH_VERSION,
        "status": "ready" if not issues else "blocked",
        "summary": {
            "workers": len(worker_dispatches),
            "planned_tasks": planned_tasks,
            "blocked_tasks": blocked_tasks,
            "issues": len(issues),
        },
        "definition_registry": inspect_agent_definition_registry(),
        "worker_dispatches": worker_dispatches,
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


def _with_definition_registry(
    output: dict[str, Any],
    *,
    include_definition_registry: bool,
) -> dict[str, Any]:
    if include_definition_registry:
        output["definition_registry"] = inspect_agent_definition_registry()
    return output


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

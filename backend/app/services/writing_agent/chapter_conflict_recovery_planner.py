from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.writing_agent.agent_job_projection import inspect_agent_job_projection

CHAPTER_CONFLICT_RECOVERY_VERSION = "phase141.chapter_conflict_recovery.v1"


def plan_chapter_conflict_recovery(db: Session, project_id: str, *, chapter_index: int | None) -> dict[str, Any]:
    target = _positive_int(chapter_index)
    if target is None:
        return {
            "status": "failed",
            "version": CHAPTER_CONFLICT_RECOVERY_VERSION,
            "chapter_index": None,
            "error": "chapter_index is required",
            "tools": [],
            "trace": {"selected_tools": [], "rejected_tools": [{"reason": "missing_chapter_index"}]},
        }

    projection = inspect_agent_job_projection(db, project_id, chapter_index=target)
    reservation = projection.get("chapter_reservation") if isinstance(projection.get("chapter_reservation"), dict) else {}
    conflict = _conflict_summary(reservation, target)
    if conflict["status"] != "reserved":
        tool = _generate_chapter_tool(target)
        return {
            "status": "completed",
            "version": CHAPTER_CONFLICT_RECOVERY_VERSION,
            "chapter_index": target,
            "conflict": conflict,
            "recovery": {
                "status": "none",
                "reason_code": "chapter_target_available",
                "next_tool": "generate_chapter",
                "next_params": {"chapter_index": target},
                "should_continue_current_run": True,
                "requires_user_input": False,
            },
            "tools": [tool],
            "recovery_options": [],
            "trace": {"selected_tools": ["generate_chapter"], "rejected_tools": []},
        }

    tools = [_inspect_chapter_tool(target)]
    recovery_options: list[dict[str, Any]] = []
    for task in conflict["tasks"]:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("task_id") or "").strip()
        if not task_id:
            continue
        tools.append(_inspect_task_tool(task_id))
        recovery_options.append(
            {
                "action": "inspect_occupying_task",
                "tool_name": "inspect_agent_job_projection",
                "params": {"task_id": task_id},
                "safe_auto_execute": True,
            }
        )
    recovery_options.append(
        {
            "action": "wait_for_occupying_task",
            "safe_auto_execute": False,
            "reason": "目标章节已有 pending/running 生成任务，继续写入前应等待或人工确认处理。",
        }
    )
    next_params = tools[1]["params"] if len(tools) > 1 else {"chapter_index": target}
    return {
        "status": "completed",
        "version": CHAPTER_CONFLICT_RECOVERY_VERSION,
        "chapter_index": target,
        "conflict": conflict,
        "recovery": {
            "status": "recommended",
            "reason_code": "chapter_target_reserved",
            "next_tool": "inspect_agent_job_projection",
            "next_params": next_params,
            "should_continue_current_run": False,
            "requires_user_input": False,
        },
        "tools": tools,
        "recovery_options": recovery_options,
        "trace": {"selected_tools": [str(tool["tool_name"]) for tool in tools], "rejected_tools": []},
    }


def _conflict_summary(reservation: dict[str, Any], chapter_index: int) -> dict[str, Any]:
    return {
        "chapter_index": chapter_index,
        "status": str(reservation.get("status") or "available"),
        "active_task_count": int(reservation.get("active_task_count") or 0),
        "tasks": reservation.get("tasks") if isinstance(reservation.get("tasks"), list) else [],
    }


def _generate_chapter_tool(chapter_index: int) -> dict[str, Any]:
    return {
        "tool_name": "generate_chapter",
        "params": {"chapter_index": chapter_index},
        "planner": {
            "reason": "目标章节未被后台任务占用，可以继续生成。",
            "on_missing": "stop",
            "on_failure": "stop",
            "expected_output": "生成目标章节正文。",
            "post_generation": True,
            "planner_version": CHAPTER_CONFLICT_RECOVERY_VERSION,
        },
    }


def _inspect_chapter_tool(chapter_index: int) -> dict[str, Any]:
    return {
        "tool_name": "inspect_agent_job_projection",
        "params": {"chapter_index": chapter_index},
        "planner": {
            "reason": "先查看目标章节的占用投影。",
            "on_missing": "stop",
            "on_failure": "stop",
            "expected_output": "返回目标章节的后台任务占用信息。",
            "post_generation": False,
            "planner_version": CHAPTER_CONFLICT_RECOVERY_VERSION,
        },
    }


def _inspect_task_tool(task_id: str) -> dict[str, Any]:
    return {
        "tool_name": "inspect_agent_job_projection",
        "params": {"task_id": task_id},
        "planner": {
            "reason": "查看占用该章节的具体后台任务。",
            "on_missing": "stop",
            "on_failure": "stop",
            "expected_output": "返回占用任务详情、恢复建议和关联 Agent run。",
            "post_generation": False,
            "planner_version": CHAPTER_CONFLICT_RECOVERY_VERSION,
        },
    }


def _positive_int(value: object) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None

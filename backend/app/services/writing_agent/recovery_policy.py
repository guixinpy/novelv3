from __future__ import annotations

from typing import Any


RECOVERY_POLICY_VERSION = "phase47.recovery_policy.v1"


def build_writing_agent_recovery(
    *,
    tool_name: str,
    step_status: str,
    output: dict[str, Any],
    planner: dict[str, Any] | None = None,
) -> dict[str, Any]:
    planner = planner or {}
    if step_status not in {"blocked", "failed"} and output.get("status") not in {"blocked", "failed"}:
        return _none(tool_name)
    if tool_name == "preflight_writing":
        return _preflight_recovery(output, planner)
    return _none(tool_name)


def _preflight_recovery(output: dict[str, Any], planner: dict[str, Any]) -> dict[str, Any]:
    issue = _first_blocker_issue(output)
    if issue is None:
        return _none("preflight_writing")

    code = str(issue.get("code") or "unknown_blocker")
    chapter_index = _optional_int(output.get("chapter_index"))
    base = {
        "policy_version": RECOVERY_POLICY_VERSION,
        "status": "recommended",
        "source_tool": "preflight_writing",
        "reason_code": code,
        "should_continue_current_run": False,
        "next_command_args": None,
        "user_input_fields": [],
        "affected_chapter_indexes": [],
        "planner_on_missing": planner.get("on_missing"),
        "planner_on_failure": planner.get("on_failure"),
    }

    if code == "missing_setup":
        return {
            **base,
            "action": "ask_user",
            "next_tool": "generate_setup",
            "next_params": {},
            "requires_user_input": True,
            "user_input_fields": ["command_args"],
            "message": str(issue.get("message") or "项目缺少基础设定，建议先生成设定。"),
        }
    if code == "missing_outline_chapter" and chapter_index is not None:
        return {
            **base,
            "action": "run_tool",
            "next_tool": "expand_outline_window",
            "next_params": {"start_chapter": chapter_index, "end_chapter": chapter_index},
            "requires_user_input": False,
            "message": str(issue.get("message") or f"第{chapter_index}章缺少章节大纲，建议先补齐目标章节大纲。"),
        }
    if code == "missing_historical_outline_chapters":
        suggested_tool = str(issue.get("suggested_tool") or "backfill_outline_gaps")
        suggested_params = issue.get("suggested_params") if isinstance(issue.get("suggested_params"), dict) else {}
        return {
            **base,
            "action": "run_tool",
            "next_tool": suggested_tool,
            "next_params": suggested_params,
            "requires_user_input": False,
            "message": str(issue.get("message") or "历史章节缺少大纲，建议先回填大纲缺口。"),
        }
    if code == "missing_previous_chapter" and chapter_index is not None and chapter_index > 1:
        return {
            **base,
            "action": "run_tool",
            "next_tool": "generate_chapter",
            "next_params": {"chapter_index": chapter_index - 1},
            "requires_user_input": False,
            "message": str(issue.get("message") or f"第{chapter_index - 1}章尚未生成，建议先生成前一章。"),
        }
    if code == "repeated_chapter_length_drift":
        return {
            **base,
            "action": "review_policy",
            "next_tool": "review_chapter_quality",
            "next_params": {"chapter_index": chapter_index} if chapter_index else {},
            "requires_user_input": True,
            "message": str(issue.get("message") or "章节字数策略连续偏离，建议先复核项目目标。"),
        }

    return {
        **base,
        "action": "ask_user",
        "next_tool": None,
        "next_params": {},
        "requires_user_input": True,
        "message": str(issue.get("message") or "Agent 运行被阻塞，需要用户确认下一步。"),
    }


def _first_blocker_issue(output: dict[str, Any]) -> dict[str, Any] | None:
    issues = output.get("issues")
    if not isinstance(issues, list):
        return None
    for issue in issues:
        if isinstance(issue, dict) and issue.get("severity") == "blocker":
            return issue
    return None


def _none(tool_name: str) -> dict[str, Any]:
    return {
        "policy_version": RECOVERY_POLICY_VERSION,
        "status": "none",
        "source_tool": tool_name,
    }


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

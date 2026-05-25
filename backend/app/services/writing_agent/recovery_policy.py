from __future__ import annotations

from typing import Any


RECOVERY_POLICY_VERSION = "phase47.recovery_policy.v1"
BINDING_RECOVERY_REASONS = {"resource_binding_missing", "resource_binding_target_mismatch"}


def build_writing_agent_recovery(
    *,
    tool_name: str,
    step_status: str,
    output: dict[str, Any],
    planner: dict[str, Any] | None = None,
) -> dict[str, Any]:
    planner = planner or {}
    if tool_name == "summarize_longform_context" and output.get("should_generate_next_chapter") is False:
        return _longform_context_recovery(output, planner)
    if step_status not in {"blocked", "failed"} and output.get("status") not in {"blocked", "failed"}:
        return _none(tool_name)
    binding_recovery = _binding_recovery(tool_name, output, planner)
    if binding_recovery.get("status") == "recommended":
        return binding_recovery
    if tool_name == "preflight_writing":
        return _preflight_recovery(output, planner)
    return _none(tool_name)


def _longform_context_recovery(output: dict[str, Any], planner: dict[str, Any]) -> dict[str, Any]:
    recommended_actions = output.get("recommended_actions")
    provenance = output.get("memory_provenance") if isinstance(output.get("memory_provenance"), dict) else {}
    provenance_recovery = provenance.get("recovery") if isinstance(provenance.get("recovery"), dict) else {}
    provenance_next_tools = (
        provenance_recovery.get("next_tools") if isinstance(provenance_recovery.get("next_tools"), list) else []
    )
    has_legacy_repair = isinstance(recommended_actions, list) and "repair_longform_maintenance" in recommended_actions
    has_provenance_repair = "repair_longform_maintenance" in provenance_next_tools
    if not has_legacy_repair and not has_provenance_repair:
        return _none("summarize_longform_context")
    decision = output.get("decision") if isinstance(output.get("decision"), dict) else {}
    chapter_index = _optional_positive_int(output.get("chapter_index"))
    continuation_tools = []
    if chapter_index is not None:
        continuation_tools = [
            {
                "tool_name": "summarize_longform_context",
                "params": {
                    "chapter_index": chapter_index,
                    "query": f"恢复长篇维护后，重新汇总第{chapter_index}章写作上下文。",
                },
                "reason": f"修复长篇维护后重新检查第{chapter_index}章上下文是否可写。",
                "expected_output": "恢复后的长篇上下文摘要。",
            },
            {
                "tool_name": "preflight_writing",
                "params": {"chapter_index": chapter_index},
                "reason": f"上下文恢复后重新执行第{chapter_index}章生成前检查。",
                "expected_output": "章节可写性检查。",
            },
            {
                "tool_name": "generate_chapter",
                "params": {"chapter_index": chapter_index},
                "reason": f"硬阻塞清除后继续生成第{chapter_index}章正文。",
                "expected_output": "章节正文。",
            },
        ]
    return {
        "policy_version": RECOVERY_POLICY_VERSION,
        "status": "recommended",
        "source_tool": "summarize_longform_context",
        "reason_code": str(provenance_recovery.get("reason") or decision.get("reason") or "longform_context_blocked"),
        "action": "run_tool",
        "next_tool": "repair_longform_maintenance",
        "next_params": {},
        "continuation_tools": continuation_tools,
        "next_command_args": None,
        "requires_user_input": False,
        "user_input_fields": [],
        "affected_chapter_indexes": [chapter_index] if chapter_index is not None else [],
        "should_continue_current_run": False,
        "planner_on_missing": planner.get("on_missing"),
        "planner_on_failure": planner.get("on_failure"),
        "memory_provenance_status": provenance.get("status"),
        "memory_provenance_recovery_status": provenance_recovery.get("status"),
        "memory_source_count": provenance.get("source_count"),
        "message": str(decision.get("message") or "长篇上下文维护未就绪，建议先修复长篇记忆和检索索引。"),
    }


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


def _binding_recovery(tool_name: str, output: dict[str, Any], planner: dict[str, Any]) -> dict[str, Any]:
    reason = str(output.get("reason") or output.get("error") or "").strip()
    if reason not in BINDING_RECOVERY_REASONS:
        return _none(tool_name)

    chapter_index = _optional_positive_int(output.get("chapter_index"))
    base = {
        "policy_version": RECOVERY_POLICY_VERSION,
        "status": "recommended",
        "source_tool": tool_name,
        "reason_code": reason,
        "action": "run_tool",
        "next_command_args": None,
        "requires_user_input": False,
        "user_input_fields": [],
        "affected_chapter_indexes": [chapter_index] if chapter_index is not None else [],
        "should_continue_current_run": False,
        "planner_on_missing": planner.get("on_missing"),
        "planner_on_failure": planner.get("on_failure"),
        "message": "资源绑定已过期或不匹配，建议重新生成执行前审批快照后再继续。",
    }

    if tool_name == "execute_longform_chapter_batch":
        task = output.get("task") if isinstance(output.get("task"), dict) else {}
        task_id = str(task.get("id") or "").strip()
        if task_id:
            return {
                **base,
                "next_tool": "prepare_longform_chapter_batch_execution",
                "next_params": {"task_id": task_id},
            }

    if tool_name == "execute_generate_chapter_with_approval" and chapter_index is not None:
        return {
            **base,
            "next_tool": "prepare_generate_chapter_execution",
            "next_params": {"chapter_index": chapter_index},
        }

    return {
        **base,
        "action": "ask_user",
        "next_tool": None,
        "next_params": {},
        "requires_user_input": True,
        "message": "资源绑定已过期或不匹配，但缺少可定位的恢复参数，需要用户确认下一步。",
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


def _optional_positive_int(value: object) -> int | None:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

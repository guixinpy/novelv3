from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ChapterContent
from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_registry import build_agent_tool_plan

PLANNER_VERSION = "phase53.context_gate.v1"


def build_writing_agent_run_plan(
    db: Session,
    project_id: str,
    *,
    goal: str,
    chapter_index: int | None = None,
    intent: str | None = None,
) -> dict[str, Any]:
    resolved_chapter_index = _infer_chapter_index(db, project_id, chapter_index)
    intent_class = _classify_intent(goal, intent, resolved_chapter_index)
    tool_plan = build_agent_tool_plan(db, project_id, chapter_index=resolved_chapter_index)
    diagnostics = tool_plan.get("diagnostics", [])
    trace: dict[str, Any] = {
        "planner_version": PLANNER_VERSION,
        "intent_class": intent_class,
        "selected_tools": [],
        "rejected_tools": [],
        "missing_dependencies": [],
        "risk_flags": [],
    }
    steps: list[dict[str, Any]] = []

    _append_step(
        steps,
        trace,
        "describe_agent_tools",
        {"chapter_index": resolved_chapter_index},
        reason="读取当前项目和章节下可见工具、隐藏工具与依赖诊断。",
        on_missing="stop",
        on_failure="stop",
        expected_output="Agent 工具能力投影。",
    )

    if intent_class == "setup_project":
        _build_setup_plan(steps, trace, diagnostics, tool_plan, goal)
    elif intent_class == "review_chapter":
        _build_review_plan(steps, trace, diagnostics, resolved_chapter_index)
    elif intent_class == "continue_next_chapter":
        _build_continue_chapter_plan(steps, trace, diagnostics, tool_plan, resolved_chapter_index)
    else:
        trace["rejected_tools"].append({"tool_name": "*", "reason": "未识别到可安全自动执行的写作意图。"})

    _collect_missing_dependencies(trace, diagnostics)
    status = "blocked" if trace["risk_flags"] else "completed"
    return {
        "status": status,
        "planner_version": PLANNER_VERSION,
        "intent_class": intent_class,
        "goal": goal,
        "chapter_index": resolved_chapter_index,
        "steps": steps,
        "tools": [_tool_request_from_step(step) for step in steps],
        "trace": trace,
    }


def tools_from_plan(plan: dict[str, Any]) -> list[WritingAgentToolRequest]:
    return [WritingAgentToolRequest(**tool) for tool in plan.get("tools", []) if isinstance(tool, dict)]


def _build_setup_plan(
    steps: list[dict[str, Any]],
    trace: dict[str, Any],
    diagnostics: list[dict[str, Any]],
    tool_plan: dict[str, Any],
    goal: str,
) -> None:
    setup_missing = _has_diagnostic(diagnostics, "generate_storyline", "missing_setup")
    if setup_missing or _tool_visible(tool_plan, "generate_setup"):
        _append_step(
            steps,
            trace,
            "generate_setup",
            {},
            reason="项目需要先生成基础设定，后续故事线、大纲和章节才能稳定推进。",
            command_args=goal,
            on_missing="ask_user",
            on_failure="stop",
            expected_output="项目基础设定。",
        )
    else:
        trace["rejected_tools"].append({"tool_name": "generate_setup", "reason": "项目已有设定，避免重复覆盖基础设定。"})


def _build_review_plan(
    steps: list[dict[str, Any]],
    trace: dict[str, Any],
    diagnostics: list[dict[str, Any]],
    chapter_index: int,
) -> None:
    if _has_diagnostic(diagnostics, "review_chapter_quality", "missing_generated_chapter"):
        trace["risk_flags"].append("missing_generated_chapter")
        trace["rejected_tools"].append({"tool_name": "review_chapter_quality", "reason": f"第{chapter_index}章尚未生成。"})
        return
    for tool_name, reason in (
        ("review_chapter_quality", "审查章节正文质量、完整度和字数弹性。"),
        ("review_chapter_continuity", "审查章节与前文、人物状态和伏笔连续性。"),
        ("plan_chapter_revision", "把审稿结果转成可执行修订计划。"),
    ):
        _append_step(
            steps,
            trace,
            tool_name,
            {"chapter_index": chapter_index},
            reason=reason,
            on_missing="record_issue",
            on_failure="record_issue",
            expected_output="审稿或修订计划报告。",
        )


def _build_continue_chapter_plan(
    steps: list[dict[str, Any]],
    trace: dict[str, Any],
    diagnostics: list[dict[str, Any]],
    tool_plan: dict[str, Any],
    chapter_index: int,
) -> None:
    if _has_diagnostic(diagnostics, "generate_chapter", "missing_setup"):
        trace["risk_flags"].append("missing_setup")
        trace["rejected_tools"].append({"tool_name": "generate_chapter", "reason": "项目缺少设定，不能稳定生成章节。"})
        return
    missing_previous = _has_diagnostic(diagnostics, "generate_chapter", "missing_previous_chapter")
    if missing_previous:
        trace["risk_flags"].append("missing_previous_chapter")
        trace["rejected_tools"].append({"tool_name": "generate_chapter", "reason": f"第{chapter_index - 1}章尚未生成。"})
        return

    needs_outline_expansion = _has_diagnostic(diagnostics, "generate_chapter", "missing_outline_chapter")
    if needs_outline_expansion and _tool_visible(tool_plan, "expand_outline_window"):
        _append_step(
            steps,
            trace,
            "expand_outline_window",
            {"start_chapter": chapter_index, "end_chapter": chapter_index},
            reason=f"第{chapter_index}章缺少大纲，先由 Agent 补齐章节窗口。",
            on_missing="fallback_tool",
            on_failure="stop",
            expected_output="补齐目标章节大纲。",
        )
    elif needs_outline_expansion:
        trace["risk_flags"].append("missing_outline_chapter")
        trace["rejected_tools"].append({"tool_name": "generate_chapter", "reason": f"第{chapter_index}章缺少大纲且无法自动扩展。"})
        return

    _append_step(
        steps,
        trace,
        "summarize_longform_context",
        {
            "chapter_index": chapter_index,
            "query": f"续写第{chapter_index}章前汇总长篇上下文。",
        },
        reason="生成前读取长篇记忆、检索证据和上下文诊断。",
        on_missing="record_issue",
        on_failure="record_issue",
        expected_output="长篇上下文摘要。",
    )
    _append_step(
        steps,
        trace,
        "preflight_writing",
        {"chapter_index": chapter_index},
        reason=f"检查第{chapter_index}章生成前依赖。",
        on_missing="fallback_tool",
        on_failure="stop",
        expected_output="章节可写性检查。",
    )
    _append_step(
        steps,
        trace,
        "generate_chapter",
        {"chapter_index": chapter_index},
        reason=f"依赖满足后生成第{chapter_index}章正文。",
        on_missing="stop",
        on_failure="stop",
        expected_output="章节正文。",
    )
    for tool_name, reason, on_failure in (
        ("review_chapter_quality", "生成后审查正文质量和弹性字数。", "record_issue"),
        ("review_chapter_continuity", "生成后审查连续性和关键伏笔。", "record_issue"),
        ("analyze_chapter_world_model", "生成后抽取世界模型候选事实，进入提案机制。", "record_issue"),
    ):
        _append_step(
            steps,
            trace,
            tool_name,
            {"chapter_index": chapter_index},
            reason=reason,
            on_missing="defer",
            on_failure=on_failure,
            expected_output="生成后质量或世界模型报告。",
            post_generation=True,
        )


def _append_step(
    steps: list[dict[str, Any]],
    trace: dict[str, Any],
    tool_name: str,
    params: dict[str, Any],
    *,
    reason: str,
    on_missing: str,
    on_failure: str,
    expected_output: str,
    command_args: str | None = None,
    post_generation: bool = False,
) -> None:
    step = {
        "step_index": len(steps) + 1,
        "tool_name": tool_name,
        "params": params,
        "reason": reason,
        "on_missing": on_missing,
        "on_failure": on_failure,
        "expected_output": expected_output,
        "post_generation": post_generation,
    }
    if command_args:
        step["command_args"] = command_args
    steps.append(step)
    trace["selected_tools"].append(tool_name)


def _tool_request_from_step(step: dict[str, Any]) -> dict[str, Any]:
    request = {
        "tool_name": step["tool_name"],
        "params": step.get("params") or {},
        "planner": {
            "step_index": step["step_index"],
            "reason": step["reason"],
            "on_missing": step["on_missing"],
            "on_failure": step["on_failure"],
            "expected_output": step["expected_output"],
            "post_generation": step["post_generation"],
            "planner_version": PLANNER_VERSION,
        },
    }
    if step.get("command_args"):
        request["command_args"] = step["command_args"]
    return request


def _collect_missing_dependencies(trace: dict[str, Any], diagnostics: list[dict[str, Any]]) -> None:
    for diagnostic in diagnostics:
        if diagnostic.get("severity") != "blocker":
            continue
        trace["missing_dependencies"].append(
            {
                "tool_name": diagnostic.get("tool_name"),
                "code": diagnostic.get("code"),
                "message": diagnostic.get("message"),
            }
        )


def _infer_chapter_index(db: Session, project_id: str, explicit_chapter_index: int | None) -> int:
    if explicit_chapter_index and explicit_chapter_index > 0:
        return explicit_chapter_index
    latest = (
        db.query(func.max(ChapterContent.chapter_index))
        .filter(ChapterContent.project_id == project_id, ChapterContent.content != "")
        .scalar()
    )
    return int(latest or 0) + 1


def _classify_intent(goal: str, explicit_intent: str | None, chapter_index: int) -> str:
    if explicit_intent:
        return explicit_intent
    text = str(goal or "")
    if any(token in text for token in ("设定", "开书", "创建", "新书")):
        return "setup_project"
    if any(token in text for token in ("审稿", "检查", "复查", "问题")):
        return "review_chapter"
    if chapter_index >= 1 and any(token in text for token in ("继续", "下一章", "写", "生成", "章节")):
        return "continue_next_chapter"
    return "inspect_tools"


def _has_diagnostic(diagnostics: list[dict[str, Any]], tool_name: str, code: str) -> bool:
    return any(item.get("tool_name") == tool_name and item.get("code") == code for item in diagnostics)


def _tool_visible(tool_plan: dict[str, Any], tool_name: str) -> bool:
    return any(tool.get("name") == tool_name for tool in tool_plan.get("visible_tools", []))

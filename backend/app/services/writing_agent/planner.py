from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ChapterContent, WritingAgentRun, WritingAgentStep
from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.approval_contract import build_agent_plan_approval_contract
from app.services.writing_agent.reference_pattern_projection import (
    REFERENCE_PATTERN_PROJECTION_VERSION,
    build_reference_pattern_projection,
)
from app.services.writing_agent.tool_contracts import agent_tool_execution_metadata
from app.services.writing_agent.tool_executor import (
    static_writing_agent_tool_adapter_names,
    writing_agent_tool_adapter_metadata,
    writing_agent_tool_adapter_metadata_by_name,
)
from app.services.writing_agent.tool_registry import build_agent_tool_plan, get_agent_tool_descriptor

PLANNER_VERSION = "phase53.context_gate.v1"
CHAPTER_GENERATION_ROUTE_LEGACY = "legacy_generate_chapter"
CHAPTER_GENERATION_ROUTE_APPROVED_PREPARE = "approved_prepare"
_SUPPORTED_CHAPTER_GENERATION_ROUTES = {
    CHAPTER_GENERATION_ROUTE_LEGACY,
    CHAPTER_GENERATION_ROUTE_APPROVED_PREPARE,
}


def build_writing_agent_run_plan(
    db: Session,
    project_id: str,
    *,
    goal: str,
    chapter_index: int | None = None,
    intent: str | None = None,
    source_projection_id: str | None = None,
    source_plan_id: str | None = None,
    chapter_generation_route: str | None = None,
) -> dict[str, Any]:
    resolved_chapter_index = _infer_chapter_index(db, project_id, chapter_index)
    intent_class = _classify_intent(goal, intent, resolved_chapter_index)
    agent_profile = _agent_profile_for_intent(intent_class)
    resolved_chapter_generation_route = _normalize_chapter_generation_route(chapter_generation_route)
    plan_id = source_plan_id or _plan_id(project_id, goal, intent_class, resolved_chapter_index)
    tool_plan = build_agent_tool_plan(
        db,
        project_id,
        chapter_index=resolved_chapter_index,
        adapter_metadata_by_name=writing_agent_tool_adapter_metadata_by_name(),
    )
    diagnostics = tool_plan.get("diagnostics", [])
    health_projection = _planner_health_projection(
        db,
        project_id,
        chapter_index=resolved_chapter_index,
        tool_plan=tool_plan,
    )
    trace: dict[str, Any] = {
        "plan_id": plan_id,
        "source_projection_id": source_projection_id,
        "planner_version": PLANNER_VERSION,
        "reference_pattern_version": REFERENCE_PATTERN_PROJECTION_VERSION,
        "reference_patterns": build_reference_pattern_projection(),
        "intent_class": intent_class,
        "tool_policy_projection": tool_plan.get("tool_policy_projection"),
        "agent_profile": agent_profile,
        "agent_profile_tool_projection": _profile_projection_from_tool_plan(tool_plan, agent_profile),
        "agent_health_projection": health_projection,
        "selected_tools": [],
        "rejected_tools": [],
        "missing_dependencies": [],
        "risk_flags": [],
        "chapter_generation_route": resolved_chapter_generation_route,
    }
    steps: list[dict[str, Any]] = []

    _append_step(
        steps,
        trace,
        "describe_agent_tools",
        {"chapter_index": resolved_chapter_index, "agent_profile": agent_profile},
        reason="读取当前项目和章节下可见工具、隐藏工具与依赖诊断。",
        on_missing="stop",
        on_failure="stop",
        expected_output="Agent 工具能力投影。",
    )

    if intent_class == "setup_project":
        _build_setup_plan(steps, trace, diagnostics, tool_plan, goal)
    elif intent_class == "build_storyline":
        _build_storyline_plan(steps, trace, diagnostics, goal)
    elif intent_class == "build_outline":
        _build_outline_plan(steps, trace, diagnostics, goal)
    elif intent_class == "review_chapter":
        _build_review_plan(steps, trace, diagnostics, resolved_chapter_index)
    elif intent_class == "continue_next_chapter":
        _build_continue_chapter_plan(
            steps,
            trace,
            diagnostics,
            tool_plan,
            resolved_chapter_index,
            chapter_generation_route=resolved_chapter_generation_route,
        )
    elif intent_class == "recover_blocked_run":
        _build_recover_blocked_run_plan(steps, trace, db, project_id)
    else:
        trace["rejected_tools"].append({"tool_name": "*", "reason": "未识别到可安全自动执行的写作意图。"})

    _collect_missing_dependencies(trace, diagnostics)
    status = "blocked" if trace["risk_flags"] else "completed"
    plan = {
        "status": status,
        "planner_version": PLANNER_VERSION,
        "project_id": project_id,
        "intent_class": intent_class,
        "goal": goal,
        "chapter_index": resolved_chapter_index,
        "steps": steps,
        "tools": [_tool_request_from_step(step) for step in steps],
        "trace": trace,
    }
    plan["approval_contract"] = build_agent_plan_approval_contract(plan)
    return plan


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
            "prepare_generate_setup_execution",
            {},
            reason="项目需要先生成基础设定，先准备设定生成审批合约，不直接写入设定。",
            command_args=goal,
            on_missing="ask_user",
            on_failure="stop",
            expected_output="设定生成审批合约。",
        )
    else:
        trace["rejected_tools"].append({"tool_name": "generate_setup", "reason": "项目已有设定，避免重复覆盖基础设定。"})


def _build_storyline_plan(
    steps: list[dict[str, Any]],
    trace: dict[str, Any],
    diagnostics: list[dict[str, Any]],
    goal: str,
) -> None:
    if _has_diagnostic(diagnostics, "prepare_generate_storyline_execution", "missing_setup"):
        trace["risk_flags"].append("missing_setup")
        trace["rejected_tools"].append(
            {"tool_name": "prepare_generate_storyline_execution", "reason": "项目缺少设定，不能稳定生成故事线。"}
        )
        return
    _append_step(
        steps,
        trace,
        "prepare_generate_storyline_execution",
        {},
        reason="基于现有设定准备故事线生成审批合约，不直接写入故事线。",
        command_args=goal,
        on_missing="stop",
        on_failure="stop",
        expected_output="故事线生成审批合约。",
    )


def _build_outline_plan(
    steps: list[dict[str, Any]],
    trace: dict[str, Any],
    diagnostics: list[dict[str, Any]],
    goal: str,
) -> None:
    if _has_diagnostic(diagnostics, "prepare_generate_outline_execution", "missing_setup"):
        trace["risk_flags"].append("missing_setup")
        trace["rejected_tools"].append(
            {"tool_name": "prepare_generate_outline_execution", "reason": "项目缺少设定，不能稳定生成大纲。"}
        )
        return
    if _has_diagnostic(diagnostics, "prepare_generate_outline_execution", "missing_storyline"):
        trace["risk_flags"].append("missing_storyline")
        trace["rejected_tools"].append(
            {"tool_name": "prepare_generate_outline_execution", "reason": "项目缺少故事线，不能稳定生成大纲。"}
        )
        return
    _append_step(
        steps,
        trace,
        "prepare_generate_outline_execution",
        {},
        reason="基于设定和故事线准备章节大纲生成审批合约，不直接写入大纲。",
        command_args=goal,
        on_missing="stop",
        on_failure="stop",
        expected_output="章节大纲生成审批合约。",
    )


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


def _build_recover_blocked_run_plan(
    steps: list[dict[str, Any]],
    trace: dict[str, Any],
    db: Session,
    project_id: str,
) -> None:
    run_id = latest_recoverable_run_id(db, project_id)
    if not run_id:
        trace["risk_flags"].append("missing_recoverable_run")
        trace["rejected_tools"].append({"tool_name": "plan_recovery_tools", "reason": "没有找到可恢复的阻塞或失败运行。"})
        return

    _append_step(
        steps,
        trace,
        "plan_recovery_tools",
        {"run_id": run_id},
        reason="预览上一轮阻塞或失败运行的恢复工具链，不直接执行恢复。",
        on_missing="stop",
        on_failure="stop",
        expected_output="恢复工具链预览。",
    )


def _build_continue_chapter_plan(
    steps: list[dict[str, Any]],
    trace: dict[str, Any],
    diagnostics: list[dict[str, Any]],
    tool_plan: dict[str, Any],
    chapter_index: int,
    *,
    chapter_generation_route: str,
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
        "inspect_agent_knowledge_base_route",
        {
            "chapter_index": chapter_index,
            "query": f"生成第{chapter_index}章前读取作者偏好、项目策略和写法经验。",
        },
        reason="读取知识库创作记忆，避免仅依赖用户临时提示约束长篇写作。",
        on_missing="record_issue",
        on_failure="record_issue",
        expected_output="作者偏好、项目策略、学习规则和写法参考投影。",
    )
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
    if chapter_generation_route == CHAPTER_GENERATION_ROUTE_APPROVED_PREPARE:
        _append_step(
            steps,
            trace,
            "prepare_generate_chapter_execution",
            {"chapter_index": chapter_index},
            reason=f"为第{chapter_index}章生成创建审批合约，不直接写入正文。",
            on_missing="stop",
            on_failure="stop",
            expected_output="章节生成审批合约。",
        )
        return

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
    step_metadata = _step_metadata(trace, step)
    step.update(step_metadata)
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
            "step_id": step["step_id"],
            "plan_id": step["plan_id"],
            "source_projection_id": step["source_projection_id"],
            "mutability": step["mutability"],
            "requires_confirmation": step["requires_confirmation"],
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


def _step_metadata(trace: dict[str, Any], step: dict[str, Any]) -> dict[str, Any]:
    plan_id = str(trace.get("plan_id") or "")
    tool_name = str(step["tool_name"])
    descriptor = get_agent_tool_descriptor(tool_name)
    execution_metadata = agent_tool_execution_metadata(
        descriptor,
        adapter_metadata=writing_agent_tool_adapter_metadata(tool_name),
    )
    return {
        "step_id": _step_id(plan_id, int(step["step_index"]), tool_name, step.get("params") or {}),
        "plan_id": plan_id,
        "source_projection_id": trace.get("source_projection_id"),
        "mutability": execution_metadata["mutability"],
        "requires_confirmation": execution_metadata["requires_confirmation"],
    }


def _planner_health_projection(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    tool_plan: dict[str, Any],
) -> dict[str, Any]:
    from app.services.actions.action_execution_service import SUPPORTED_ACTION_EXECUTION_TYPES
    from app.services.writing_agent.agent_health_projection import inspect_agent_health_projection

    output = inspect_agent_health_projection(
        db,
        project_id,
        chapter_index=chapter_index,
        adapter_metadata_by_name=writing_agent_tool_adapter_metadata_by_name(),
        static_adapter_tool_names=static_writing_agent_tool_adapter_names(),
        action_execution_tool_names=set(SUPPORTED_ACTION_EXECUTION_TYPES),
        tool_plan=tool_plan,
    )
    diagnostics = output.get("diagnostics") if isinstance(output.get("diagnostics"), list) else []
    return {
        "version": output.get("version"),
        "status": output.get("status"),
        "diagnostic_count": len(diagnostics),
        "diagnostics": diagnostics,
        "command_contracts": output.get("command_contracts")
        if isinstance(output.get("command_contracts"), dict)
        else {},
        "control_plane_readiness": output.get("control_plane_readiness")
        if isinstance(output.get("control_plane_readiness"), dict)
        else {},
        "recommended_tools": output.get("recommended_tools") if isinstance(output.get("recommended_tools"), list) else [],
    }


def _plan_id(project_id: str, goal: str, intent_class: str, chapter_index: int) -> str:
    source = json.dumps(
        {
            "project_id": project_id,
            "goal": goal,
            "intent_class": intent_class,
            "chapter_index": chapter_index,
            "planner_version": PLANNER_VERSION,
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return f"plan:{hashlib.sha256(source.encode('utf-8')).hexdigest()[:16]}"


def _step_id(plan_id: str, step_index: int, tool_name: str, params: dict[str, Any]) -> str:
    source = json.dumps(
        {
            "plan_id": plan_id,
            "step_index": step_index,
            "tool_name": tool_name,
            "params": params,
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return f"step:{hashlib.sha256(source.encode('utf-8')).hexdigest()[:16]}"


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
    if "恢复" in text or any(token in text for token in ("上一轮阻塞", "上次阻塞", "上一轮失败", "上次失败")):
        return "recover_blocked_run"
    if any(token in text for token in ("设定", "开书", "创建", "新书")):
        return "setup_project"
    if "故事线" in text or "主枝干" in text:
        return "build_storyline"
    if "大纲" in text:
        return "build_outline"
    if any(token in text for token in ("审稿", "检查", "复查", "问题")):
        return "review_chapter"
    if chapter_index >= 1 and any(token in text for token in ("继续", "下一章", "写", "生成", "章节")):
        return "continue_next_chapter"
    return "inspect_tools"


def _agent_profile_for_intent(intent_class: str) -> str:
    if intent_class == "continue_next_chapter":
        return "drafting_worker"
    if intent_class == "review_chapter":
        return "reviewer_worker"
    if intent_class == "recover_blocked_run":
        return "recovery_worker"
    if intent_class == "setup_project":
        return "drafting_worker"
    return "orchestrator"


def _profile_projection_from_tool_plan(tool_plan: dict[str, Any], profile: str) -> dict[str, Any] | None:
    projection = tool_plan.get("agent_profile_tool_projection")
    if not isinstance(projection, dict):
        return None
    profiles = projection.get("profiles")
    if not isinstance(profiles, dict):
        return None
    selected = profiles.get(profile)
    return selected if isinstance(selected, dict) else None


def _normalize_chapter_generation_route(route: str | None) -> str:
    cleaned = str(route or "").strip() or CHAPTER_GENERATION_ROUTE_APPROVED_PREPARE
    if cleaned in _SUPPORTED_CHAPTER_GENERATION_ROUTES:
        return cleaned
    return CHAPTER_GENERATION_ROUTE_APPROVED_PREPARE


def _has_diagnostic(diagnostics: list[dict[str, Any]], tool_name: str, code: str) -> bool:
    return any(item.get("tool_name") == tool_name and item.get("code") == code for item in diagnostics)


def _tool_visible(tool_plan: dict[str, Any], tool_name: str) -> bool:
    return any(tool.get("name") == tool_name for tool in tool_plan.get("visible_tools", []))


def latest_recoverable_run_id(db: Session, project_id: str) -> str | None:
    runs = (
        db.query(WritingAgentRun)
        .filter(WritingAgentRun.project_id == project_id, WritingAgentRun.status.in_(("blocked", "failed")))
        .order_by(WritingAgentRun.updated_at.desc(), WritingAgentRun.id.desc())
        .limit(20)
        .all()
    )
    for run in runs:
        steps = (
            db.query(WritingAgentStep)
            .filter(WritingAgentStep.project_id == project_id, WritingAgentStep.run_id == run.id)
            .order_by(WritingAgentStep.step_index.desc(), WritingAgentStep.id.desc())
            .all()
        )
        for step in steps:
            output = step.output if isinstance(step.output, dict) else {}
            envelope = output.get("agent_tool_result") if isinstance(output.get("agent_tool_result"), dict) else {}
            recovery = envelope.get("recovery") if isinstance(envelope.get("recovery"), dict) else {}
            if recovery.get("status") == "recommended":
                return str(run.id)
    return None

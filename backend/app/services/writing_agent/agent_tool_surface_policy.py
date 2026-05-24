from __future__ import annotations

from collections import Counter
from typing import Any

TOOL_SURFACE_POLICY_VERSION = "phase206.agent_tool_surface_policy.v1"
AGENT_PROFILE_TOOL_POLICY_VERSION = "phase207.agent_profile_tool_policy.v1"

AGENT_TOOL_PROFILE_RULES: dict[str, dict[str, object]] = {
    "orchestrator": {
        "description": "顶层路由与计划编排，只保留只读的核心路由、Trace 和记忆检查工具。",
        "allowed_categories": frozenset({"preflight", "trace", "knowledge_base", "longform_memory"}),
        "allowed_mutabilities": frozenset({"read"}),
    },
    "drafting_worker": {
        "description": "章节生成工作者，可访问写作生成、知识库、长篇记忆、审稿和世界模型分析工具。",
        "allowed_categories": frozenset({"preflight", "generation", "knowledge_base", "longform_memory", "review"}),
        "allowed_mutabilities": frozenset({"read", "write", "guarded_write"}),
        "allowed_tools": frozenset({"analyze_chapter_world_model"}),
        "denied_tools": frozenset({"apply_pending_action_route_approval_opt_in"}),
    },
    "reviewer_worker": {
        "description": "审稿和修订工作者，默认不直接生成新章节。",
        "allowed_categories": frozenset({"preflight", "knowledge_base", "longform_memory", "review", "revision", "trace"}),
        "allowed_mutabilities": frozenset({"read", "write", "guarded_write"}),
        "denied_tools": frozenset({"apply_pending_action_route_approval_opt_in"}),
    },
    "world_model_worker": {
        "description": "世界模型维护工作者，聚焦 Athena 世界模型、知识库和 Trace。",
        "allowed_categories": frozenset({"preflight", "athena_world_model", "knowledge_base", "trace"}),
        "allowed_mutabilities": frozenset({"read", "write", "guarded_write"}),
    },
    "recovery_worker": {
        "description": "恢复和维护工作者，聚焦任务队列、维护、长篇记忆和 Trace。",
        "allowed_categories": frozenset({"preflight", "task_queue", "maintenance", "longform_memory", "trace"}),
        "allowed_mutabilities": frozenset({"read", "write", "guarded_write"}),
        "denied_tools": frozenset({"apply_pending_action_route_approval_opt_in"}),
    },
}


def build_agent_tool_surface_policy_projection(
    visible_tools: list[dict[str, Any]],
    hidden_tools: list[dict[str, Any]],
) -> dict[str, Any]:
    tools = [
        *_tool_rows(visible_tools, visibility_state="visible"),
        *_tool_rows(hidden_tools, visibility_state="hidden"),
    ]
    mutability_counts = Counter(tool["mutability"] for tool in tools)
    visibility_counts = Counter(tool["visibility_state"] for tool in tools)
    return {
        "version": TOOL_SURFACE_POLICY_VERSION,
        "summary": {
            "total_tools": len(tools),
            "visible_tools": visibility_counts["visible"],
            "hidden_tools": visibility_counts["hidden"],
            "read_tools": mutability_counts["read"],
            "write_tools": mutability_counts["write"],
            "guarded_write_tools": mutability_counts["guarded_write"],
            "unclassified_tools": mutability_counts["unclassified"],
        },
        "parallel_read_tools": _names(
            tool for tool in tools if tool["visibility_state"] == "visible" and tool["parallel_safe"]
        ),
        "approval_required_tools": _names(tool for tool in tools if tool["mutability"] in {"write", "guarded_write"}),
        "explicit_confirmation_tools": _names(tool for tool in tools if tool["requires_confirmation"]),
        "write_tools": _names(tool for tool in tools if tool["mutability"] == "write"),
        "guarded_write_tools": _names(tool for tool in tools if tool["mutability"] == "guarded_write"),
        "unclassified_tools": _names(tool for tool in tools if tool["mutability"] == "unclassified"),
        "agent_only_tools": _names(tool for tool in tools if tool["tool_scope"] == "agent_only"),
        "legacy_action_bridge_tools": _names(tool for tool in tools if tool["tool_scope"] == "agent_and_legacy_action"),
        "policy_rules": [
            {
                "code": "read_tools_are_parallel_safe",
                "description": "可见 read 工具可作为默认并行候选。",
            },
            {
                "code": "guarded_writes_require_confirmation",
                "description": "guarded_write 工具需要确认或审批契约后才能执行。",
            },
            {
                "code": "unclassified_tools_require_review",
                "description": "unclassified 工具不能自动进入执行计划，需先补齐工具契约。",
            },
        ],
    }


def build_agent_profile_tool_projection(
    visible_tools: list[dict[str, Any]],
    hidden_tools: list[dict[str, Any]],
) -> dict[str, Any]:
    tools = [
        *_tool_rows(visible_tools, visibility_state="visible"),
        *_tool_rows(hidden_tools, visibility_state="hidden"),
    ]
    profiles = {
        profile: _profile_projection(profile, rule, tools)
        for profile, rule in AGENT_TOOL_PROFILE_RULES.items()
    }
    return {
        "version": AGENT_PROFILE_TOOL_POLICY_VERSION,
        "profiles": profiles,
        "policy_rules": [
            {
                "code": "profiles_filter_visibility_only",
                "description": "profile 投影只过滤模型可见工具面，不直接改变执行器行为。",
            },
            {
                "code": "orchestrator_is_read_only",
                "description": "orchestrator 默认只保留 read 工具，将写操作交给 worker profile。",
            },
            {
                "code": "workers_receive_bounded_capabilities",
                "description": "worker profile 按写作域能力分组接收有限工具面。",
            },
        ],
    }


def _tool_rows(tools: list[dict[str, Any]], *, visibility_state: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tool in tools:
        surface = tool.get("agent_tool_surface") if isinstance(tool.get("agent_tool_surface"), dict) else {}
        rows.append(
            {
                "name": str(tool.get("name") or ""),
                "category": str(tool.get("category") or "unknown"),
                "visibility_state": visibility_state,
                "tool_scope": str(surface.get("tool_scope") or "unknown"),
                "mutability": str(surface.get("mutability") or "unclassified"),
                "requires_confirmation": surface.get("requires_confirmation") is True,
                "parallel_safe": surface.get("parallel_safe") is True,
            }
        )
    return rows


def _profile_projection(profile: str, rule: dict[str, object], tools: list[dict[str, Any]]) -> dict[str, Any]:
    allowed_categories = rule["allowed_categories"]
    allowed_mutabilities = rule["allowed_mutabilities"]
    allowed_visible = [tool for tool in tools if tool["visibility_state"] == "visible" and _tool_allowed(tool, rule)]
    blocked_visible = [tool for tool in tools if tool["visibility_state"] == "visible" and tool not in allowed_visible]
    allowed_hidden = [tool for tool in tools if tool["visibility_state"] == "hidden" and _tool_allowed(tool, rule)]
    return {
        "profile": profile,
        "description": str(rule["description"]),
        "allowed_categories": sorted(str(category) for category in allowed_categories),
        "allowed_mutabilities": sorted(str(mutability) for mutability in allowed_mutabilities),
        "allowed_tool_overrides": sorted(str(tool_name) for tool_name in rule.get("allowed_tools", frozenset())),
        "denied_tools": sorted(str(tool_name) for tool_name in rule.get("denied_tools", frozenset())),
        "allowed_visible_tools": _names(allowed_visible),
        "allowed_hidden_tools": _names(allowed_hidden),
        "blocked_visible_tools": _names(blocked_visible),
        "summary": {
            "allowed_visible_tools": len(allowed_visible),
            "allowed_hidden_tools": len(allowed_hidden),
            "blocked_visible_tools": len(blocked_visible),
        },
    }


def _tool_allowed(tool: dict[str, Any], rule: dict[str, object]) -> bool:
    denied_tools = rule.get("denied_tools", frozenset())
    if tool["name"] in denied_tools:
        return False
    allowed_tools = rule.get("allowed_tools", frozenset())
    if tool["name"] in allowed_tools:
        return True
    allowed_categories = rule["allowed_categories"]
    allowed_mutabilities = rule["allowed_mutabilities"]
    if tool["category"] not in allowed_categories:
        return False
    if tool["mutability"] not in allowed_mutabilities:
        return False
    return True


def _names(tools: Any) -> list[str]:
    return sorted(tool["name"] for tool in tools if tool.get("name"))

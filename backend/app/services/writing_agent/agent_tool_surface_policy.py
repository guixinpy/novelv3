from __future__ import annotations

from collections import Counter
from typing import Any

TOOL_SURFACE_POLICY_VERSION = "phase206.agent_tool_surface_policy.v1"


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


def _tool_rows(tools: list[dict[str, Any]], *, visibility_state: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tool in tools:
        surface = tool.get("agent_tool_surface") if isinstance(tool.get("agent_tool_surface"), dict) else {}
        rows.append(
            {
                "name": str(tool.get("name") or ""),
                "visibility_state": visibility_state,
                "tool_scope": str(surface.get("tool_scope") or "unknown"),
                "mutability": str(surface.get("mutability") or "unclassified"),
                "requires_confirmation": surface.get("requires_confirmation") is True,
                "parallel_safe": surface.get("parallel_safe") is True,
            }
        )
    return rows


def _names(tools: Any) -> list[str]:
    return sorted(tool["name"] for tool in tools if tool.get("name"))

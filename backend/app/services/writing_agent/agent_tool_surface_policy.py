from __future__ import annotations

from collections import Counter
from typing import Any

TOOL_SURFACE_POLICY_VERSION = "phase206.agent_tool_surface_policy.v1"
AGENT_PROFILE_TOOL_POLICY_VERSION = "phase207.agent_profile_tool_policy.v1"
AGENT_PROFILE_DEFINITION_VERSION = "phase212.agent_profile_definition.v1"
AGENT_PROFILE_POLICY_AUDIT_VERSION = "phase215.agent_profile_policy_audit.v1"

AGENT_PROFILE_DEFINITIONS: dict[str, dict[str, object]] = {
    "orchestrator": {
        "display_name": "编排主控",
        "role": "orchestrator",
        "tier": "reasoning",
        "delegation_allowed": True,
        "delegate_to_profiles": ("drafting_worker", "reviewer_worker", "world_model_worker", "recovery_worker"),
    },
    "drafting_worker": {
        "display_name": "创作执行者",
        "role": "worker",
        "tier": "worker",
        "delegation_allowed": False,
        "delegate_to_profiles": (),
    },
    "reviewer_worker": {
        "display_name": "审稿执行者",
        "role": "worker",
        "tier": "worker",
        "delegation_allowed": False,
        "delegate_to_profiles": (),
    },
    "world_model_worker": {
        "display_name": "世界模型执行者",
        "role": "worker",
        "tier": "worker",
        "delegation_allowed": False,
        "delegate_to_profiles": (),
    },
    "recovery_worker": {
        "display_name": "恢复维护者",
        "role": "worker",
        "tier": "worker",
        "delegation_allowed": False,
        "delegate_to_profiles": (),
    },
}

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
    profile_definitions = build_agent_profile_definitions_projection()
    return {
        "version": AGENT_PROFILE_TOOL_POLICY_VERSION,
        "profile_definitions": profile_definitions,
        "profiles": profiles,
        "consistency_audit": build_agent_profile_policy_audit(profile_definitions, profiles),
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


def build_agent_profile_definitions_projection() -> dict[str, Any]:
    return {
        "version": AGENT_PROFILE_DEFINITION_VERSION,
        "profiles": {
            profile: build_agent_profile_definition(profile)
            for profile in sorted(AGENT_PROFILE_DEFINITIONS)
        },
    }


def build_agent_profile_definition(profile: str | None, *, source: str | None = None) -> dict[str, Any] | None:
    profile_id = str(profile or "").strip()
    if not profile_id:
        return None

    definition = AGENT_PROFILE_DEFINITIONS.get(profile_id)
    if definition is None:
        return {
            "version": AGENT_PROFILE_DEFINITION_VERSION,
            "status": "unknown_profile",
            "profile": profile_id,
            "display_name": profile_id,
            "role": "unknown",
            "tier": "unknown",
            "delegation_allowed": False,
            "delegate_to_profiles": [],
            "source": source,
            "description": "",
        }

    rule = AGENT_TOOL_PROFILE_RULES.get(profile_id, {})
    return {
        "version": AGENT_PROFILE_DEFINITION_VERSION,
        "status": "known",
        "profile": profile_id,
        "display_name": str(definition["display_name"]),
        "role": str(definition["role"]),
        "tier": str(definition["tier"]),
        "delegation_allowed": definition["delegation_allowed"] is True,
        "delegate_to_profiles": [str(item) for item in definition.get("delegate_to_profiles", ())],
        "source": source,
        "description": str(rule.get("description") or ""),
    }


def build_agent_profile_policy_audit(
    profile_definitions_projection: dict[str, Any],
    profiles_projection: dict[str, Any],
) -> dict[str, Any]:
    definitions = profile_definitions_projection.get("profiles")
    if not isinstance(definitions, dict):
        definitions = {}
    profiles = profiles_projection if isinstance(profiles_projection, dict) else {}
    definition_profiles = {str(profile) for profile, definition in definitions.items() if isinstance(definition, dict)}
    tool_rule_profiles = {str(profile) for profile, profile_projection in profiles.items() if isinstance(profile_projection, dict)}
    issues: list[dict[str, Any]] = []
    delegate_edges: list[dict[str, str]] = []

    for profile in sorted(definition_profiles - tool_rule_profiles):
        issues.append(
            {
                "code": "profile_definition_missing_tool_rule",
                "severity": "error",
                "profile": profile,
            }
        )

    for profile in sorted(tool_rule_profiles - definition_profiles):
        issues.append(
            {
                "code": "profile_tool_rule_missing_definition",
                "severity": "error",
                "profile": profile,
            }
        )

    for profile in sorted(definition_profiles):
        definition = definitions.get(profile)
        if not isinstance(definition, dict):
            continue
        delegate_targets = _delegate_target_names(definition.get("delegate_to_profiles"))
        if definition.get("delegation_allowed") is not True and delegate_targets:
            issues.append(
                {
                    "code": "non_delegating_profile_has_delegate_targets",
                    "severity": "error",
                    "profile": profile,
                    "targets": delegate_targets,
                }
            )
        for target in delegate_targets:
            delegate_edges.append({"source": profile, "target": target})
            if target not in definition_profiles:
                issues.append(
                    {
                        "code": "delegate_target_missing_definition",
                        "severity": "error",
                        "profile": profile,
                        "target": target,
                    }
                )
            if target not in tool_rule_profiles:
                issues.append(
                    {
                        "code": "delegate_target_missing_tool_rule",
                        "severity": "error",
                        "profile": profile,
                        "target": target,
                    }
                )
            target_definition = definitions.get(target)
            if isinstance(target_definition, dict) and target_definition.get("delegation_allowed") is True:
                issues.append(
                    {
                        "code": "delegated_profile_can_delegate",
                        "severity": "warning",
                        "profile": profile,
                        "target": target,
                    }
                )

    return {
        "version": AGENT_PROFILE_POLICY_AUDIT_VERSION,
        "status": "passed" if not issues else "needs_attention",
        "summary": {
            "profile_definitions": len(definition_profiles),
            "profile_tool_rules": len(tool_rule_profiles),
            "delegate_edges": len(delegate_edges),
            "issues": len(issues),
        },
        "delegate_edges": delegate_edges,
        "issues": issues,
        "rules": [
            _audit_rule(
                "profile_definitions_have_tool_rules",
                issues,
                {"profile_definition_missing_tool_rule"},
            ),
            _audit_rule(
                "profile_tool_rules_have_definitions",
                issues,
                {"profile_tool_rule_missing_definition"},
            ),
            _audit_rule(
                "delegate_targets_have_definitions",
                issues,
                {"delegate_target_missing_definition"},
            ),
            _audit_rule(
                "delegate_targets_have_tool_rules",
                issues,
                {"delegate_target_missing_tool_rule"},
            ),
            _audit_rule(
                "non_delegating_profiles_have_no_delegate_targets",
                issues,
                {"non_delegating_profile_has_delegate_targets"},
            ),
            _audit_rule(
                "delegated_profiles_are_leaf_profiles",
                issues,
                {"delegated_profile_can_delegate"},
            ),
        ],
    }


def apply_agent_profile_tool_scope(plan: dict[str, Any], agent_profile: str | None) -> dict[str, Any]:
    profile = str(agent_profile or "").strip()
    if not profile:
        return {**plan, "agent_profile_scope": {"status": "not_requested", "agent_profile": None}}

    profile_projection = _profile_projection_from_plan(plan, profile)
    if profile_projection is None:
        return {
            **plan,
            "visible_tools": [],
            "hidden_tools": [],
            "toolsets": {},
            "tool_policy_projection": build_agent_tool_surface_policy_projection([], []),
            "agent_profile_tool_projection": build_agent_profile_tool_projection([], []),
            "agent_profile_scope": {
                "status": "unknown_profile",
                "agent_profile": profile,
                "available_profiles": _available_profiles(plan),
            },
        }

    allowed_visible = set(profile_projection.get("allowed_visible_tools") or [])
    allowed_hidden = set(profile_projection.get("allowed_hidden_tools") or [])
    blocked_visible = set(profile_projection.get("blocked_visible_tools") or [])
    scoped_visible = [tool for tool in plan.get("visible_tools", []) if tool.get("name") in allowed_visible]
    profile_filtered = [tool for tool in plan.get("visible_tools", []) if tool.get("name") in blocked_visible]
    scoped_hidden = [
        *[tool for tool in plan.get("hidden_tools", []) if tool.get("name") in allowed_hidden],
    ]
    return {
        **plan,
        "visible_tools": scoped_visible,
        "hidden_tools": scoped_hidden,
        "toolsets": _group_tools_by_category(scoped_visible),
        "tool_policy_projection": build_agent_tool_surface_policy_projection(scoped_visible, scoped_hidden),
        "agent_profile_tool_projection": build_agent_profile_tool_projection(scoped_visible, scoped_hidden),
        "agent_profile_scope": {
            "status": "applied",
            "agent_profile": profile,
            "allowed_visible_tool_count": len(scoped_visible),
            "profile_filtered_visible_tool_count": len(profile_filtered),
            "profile_filtered_visible_tools": _names(profile_filtered),
            "allowed_hidden_tool_count": len(scoped_hidden),
        },
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


def _profile_projection_from_plan(plan: dict[str, Any], profile: str) -> dict[str, Any] | None:
    projection = plan.get("agent_profile_tool_projection")
    if not isinstance(projection, dict):
        return None
    profiles = projection.get("profiles")
    if not isinstance(profiles, dict):
        return None
    selected = profiles.get(profile)
    return selected if isinstance(selected, dict) else None


def _available_profiles(plan: dict[str, Any]) -> list[str]:
    projection = plan.get("agent_profile_tool_projection")
    if not isinstance(projection, dict):
        return []
    profiles = projection.get("profiles")
    if not isinstance(profiles, dict):
        return []
    return sorted(str(profile) for profile in profiles)


def _group_tools_by_category(tools: list[dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for tool in tools:
        grouped.setdefault(str(tool.get("category") or "unknown"), []).append(str(tool.get("name") or ""))
    return grouped


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


def _delegate_target_names(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [target for target in (str(item).strip() for item in value) if target]


def _audit_rule(code: str, issues: list[dict[str, Any]], issue_codes: set[str]) -> dict[str, str]:
    status = "failed" if any(issue.get("code") in issue_codes for issue in issues) else "passed"
    return {"code": code, "status": status}


def _names(tools: Any) -> list[str]:
    return sorted(tool["name"] for tool in tools if tool.get("name"))

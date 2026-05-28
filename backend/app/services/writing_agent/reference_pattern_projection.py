from __future__ import annotations

from typing import Any

REFERENCE_PATTERN_PROJECTION_VERSION = "phase107.reference_pattern_projection.v1"


def build_reference_pattern_projection() -> list[dict[str, Any]]:
    return [
        {
            "source": "hermes-agent",
            "source_path": "references/agent-projects/hermes-agent/AGENTS.md",
            "source_lines": ["499-508", "717-746", "820-853"],
            "applied_patterns": [
                "tool_lifecycle_hooks",
                "bounded_delegation_roles",
                "durable_worker_queue_boundary",
            ],
            "decision": "Keep dialog planning explicit, hook-ready, and clear about durable queue boundaries.",
        },
        {
            "source": "openhuman",
            "source_path": "references/agent-projects/openhuman/docs/agent-subagent-tool-flow.md",
            "source_lines": ["31-41", "61-68", "244-258"],
            "applied_patterns": [
                "agent_definition_visible_tool_split",
                "stateful_parent_turn_with_memory",
                "compact_subagent_result_contract",
            ],
            "decision": "Separate planner-visible tools from runtime execution and preserve compact worker outputs.",
        },
        {
            "source": "openclaw",
            "source_path": "references/agent-projects/openclaw/AGENTS.md",
            "source_lines": ["44-49", "121-127", "171-175"],
            "applied_patterns": [
                "schema_and_audit_discipline",
                "behavior_tests_over_string_greps",
                "source_class_provenance_for_memory",
            ],
            "decision": "Prefer behavior tests, deterministic schemas, and provenance-bearing memory/tool traces.",
        },
    ]

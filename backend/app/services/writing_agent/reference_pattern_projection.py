from __future__ import annotations

from typing import Any

REFERENCE_PATTERN_PROJECTION_VERSION = "phase107.reference_pattern_projection.v1"
REFERENCE_ALIGNMENT_INSPECTION_VERSION = "phase232.reference_alignment_inspection.v1"


def _decision(
    decision_id: str,
    module_path: str,
    rationale: str,
    evidence_tools: list[str],
) -> dict[str, Any]:
    return {
        "decision_id": decision_id,
        "module_path": module_path,
        "rationale": rationale,
        "status": "implemented",
        "evidence_tools": evidence_tools,
    }


def _capability(
    area: str,
    current_decision: str,
    module_paths: list[str],
    evidence_tools: list[str],
) -> dict[str, Any]:
    return {
        "area": area,
        "current_decision": current_decision,
        "module_paths": module_paths,
        "evidence_tools": evidence_tools,
    }


_SOURCE_REFS = [
    "references/agent-projects/hermes-agent",
    "references/agent-projects/openhuman",
    "references/agent-projects/openclaw",
]

_PATTERNS: list[dict[str, Any]] = [
    {
        "pattern_id": "tool_registry_visible_surface",
        "source": "hermes-agent",
        "source_path": "references/agent-projects/hermes-agent/AGENTS.md",
        "source_lines": ["263-301", "698-712"],
        "applied_patterns": [
            "tool_lifecycle_hooks",
            "registry_backed_tool_discovery",
            "toolset_visibility_boundary",
        ],
        "decision": "Keep Writing Agent tools registered through descriptors/adapters, with visibility decided by toolsets and profiles.",
        "novelv3_decisions": [
            _decision(
                "central_tool_descriptor_registry",
                "backend/app/services/writing_agent/tool_registry.py",
                "Agent capabilities are discovered from typed descriptors instead of hidden feature branches.",
                ["describe_agent_tools", "inspect_agent_tool_contracts"],
            ),
            _decision(
                "static_adapter_execution_boundary",
                "backend/app/services/writing_agent/tool_executor.py",
                "Agent execution enters a unified adapter boundary before reaching domain services.",
                ["inspect_agent_tool_contracts", "inspect_agent_health_projection"],
            ),
        ],
        "capability_areas": ["Hermes/dialog", "frontend"],
        "recommended_next_tools": ["inspect_agent_tool_contracts", "inspect_agent_health_projection"],
    },
    {
        "pattern_id": "subagent_worker_boundary",
        "source": "hermes-agent",
        "source_path": "references/agent-projects/hermes-agent/AGENTS.md",
        "source_lines": ["717-746", "820-853"],
        "applied_patterns": [
            "bounded_delegation_roles",
            "durable_worker_queue_boundary",
            "worker_spin_loop_guard",
        ],
        "decision": "Model review, memory, world-model and recovery work as named workers, with durable queue handoffs for long tasks.",
        "novelv3_decisions": [
            _decision(
                "profile_bounded_worker_projection",
                "backend/app/services/writing_agent/agent_tool_surface_policy.py",
                "Worker profiles constrain which writing tools can be called by drafting, review, world-model and recovery roles.",
                ["describe_agent_tools", "inspect_agent_health_projection"],
            ),
            _decision(
                "yaml_worker_definition_registry",
                "backend/app/services/writing_agent/agent_definitions.py",
                "Worker profile boundaries are backed by YAML AgentDefinition files and audited as leaf workers before dispatch.",
                ["inspect_agent_worker_dispatch", "inspect_agent_health_projection"],
            ),
            _decision(
                "longform_batch_queue_boundary",
                "backend/app/services/writing_agent/longform_tool_adapters.py",
                "Multi-chapter writing is represented as task queue work rather than hidden synchronous recursion.",
                ["inspect_longform_chapter_batch", "inspect_agent_job_projection"],
            ),
            _decision(
                "story_asset_worker_chain",
                "backend/app/services/writing_agent/agent_worker_dispatch.py",
                "Setup, storyline and outline generation now expose preview/prepare/execute tools through the drafting worker boundary.",
                [
                    "preview_generate_setup_execution",
                    "prepare_generate_setup_execution",
                    "execute_generate_setup_with_approval",
                    "preview_generate_storyline_execution",
                    "prepare_generate_storyline_execution",
                    "execute_generate_storyline_with_approval",
                    "preview_generate_outline_execution",
                    "prepare_generate_outline_execution",
                    "execute_generate_outline_with_approval",
                    "inspect_agent_worker_dispatch",
                ],
            ),
        ],
        "capability_areas": ["story_assets", "review", "task_queue"],
        "recommended_next_tools": [
            "inspect_agent_worker_dispatch",
            "inspect_agent_job_projection",
            "plan_recovery_tools",
        ],
    },
    {
        "pattern_id": "long_memory_context_resume",
        "source": "openhuman",
        "source_path": "references/agent-projects/openhuman/docs/agent-subagent-tool-flow.md",
        "source_lines": ["61-68", "264-289", "562-564"],
        "applied_patterns": [
            "stateful_parent_turn_with_memory",
            "memory_context_injection",
            "transcript_resume_boundary",
        ],
        "decision": "Treat memory activation, context compression, transcript trace and continuation as separate Agent-readable state.",
        "novelv3_decisions": [
            _decision(
                "longform_memory_activation_plan",
                "backend/app/services/writing_agent/agent_memory_trace_tool_adapters.py",
                "Before generation, Agent can inspect what long-memory context will be activated for the chapter.",
                ["inspect_agent_memory_activation_plan", "summarize_longform_context"],
            ),
            _decision(
                "knowledge_base_route_projection",
                "backend/app/services/writing_agent/agent_knowledge_base_route.py",
                "Author preferences, project strategy and reference patterns are surfaced through a knowledge-base route.",
                ["inspect_agent_knowledge_base_route"],
            ),
        ],
        "capability_areas": ["long_memory", "retrieval", "knowledge_base"],
        "recommended_next_tools": ["inspect_agent_memory_activation_plan", "inspect_agent_knowledge_base_route"],
    },
    {
        "pattern_id": "permission_audit_gate",
        "source": "openhuman",
        "source_path": "references/agent-projects/openhuman/docs/agent-subagent-tool-flow.md",
        "source_lines": ["312-325", "548-558"],
        "applied_patterns": [
            "visible_tool_filtering",
            "approval_gated_execution",
            "structured_blocked_tool_result",
        ],
        "decision": "High-risk writes must pass explicit preview/approval/execute gates and report blocked calls as structured results.",
        "novelv3_decisions": [
            _decision(
                "agent_plan_approval_contracts",
                "backend/app/services/writing_agent/approval_contract.py",
                "Write plans carry stable approval hashes so stale or mismatched executions fail closed.",
                ["preview_agent_plan_approval_contract", "verify_agent_plan_approval_contract"],
            ),
            _decision(
                "write_gate_coverage_projection",
                "backend/app/services/writing_agent/write_gate_coverage.py",
                "Agent can inspect remaining write-gate gaps before selecting the next hardening target.",
                ["inspect_agent_write_gate_coverage"],
            ),
        ],
        "capability_areas": ["trace", "frontend"],
        "recommended_next_tools": ["inspect_agent_write_gate_coverage", "inspect_agent_trace_audit"],
    },
    {
        "pattern_id": "schema_provenance_behavior_tests",
        "source": "openclaw",
        "source_path": "references/agent-projects/openclaw/AGENTS.md",
        "source_lines": ["44-49", "121-127", "171-175"],
        "applied_patterns": [
            "schema_and_audit_discipline",
            "behavior_tests_over_string_greps",
            "source_class_provenance_for_memory",
        ],
        "decision": "Prefer deterministic schemas, behavior tests and provenance-bearing memory/tool traces for every Agent capability.",
        "novelv3_decisions": [
            _decision(
                "world_model_provenance_contract",
                "backend/app/services/writing_agent/memory_provenance_contract.py",
                "World-model and memory routes preserve source/provenance fields for later Agent audit.",
                ["inspect_agent_world_model_route", "inspect_agent_trace_audit"],
            ),
            _decision(
                "behavior_contract_tests",
                "backend/tests/test_writing_agent_tool_executor.py",
                "Agent tool behavior is locked with executor and registry tests instead of documentation-only checks.",
                ["inspect_agent_tool_contracts"],
            ),
        ],
        "capability_areas": ["Athena/world_model", "trace"],
        "recommended_next_tools": ["inspect_agent_world_model_route", "inspect_agent_trace_audit"],
    },
]

_CAPABILITY_ALIGNMENT: list[dict[str, Any]] = [
    _capability(
        "Hermes/dialog",
        "Dialog intent and slash-command routes enter Writing Agent plan tools.",
        ["backend/app/services/writing_agent/dialog_intent_planner.py", "backend/app/services/writing_agent/slash_command_route.py"],
        ["plan_dialog_intent_agent_run", "inspect_agent_dialog_route_projection"],
    ),
    _capability(
        "Athena/world_model",
        "World-model imports, analysis and proposal resolution are exposed as auditable Agent tools.",
        ["backend/app/services/writing_agent/world_model_tool_adapters.py"],
        ["inspect_agent_world_model_route", "review_world_model_proposals"],
    ),
    _capability(
        "story_assets",
        "Setup, storyline and outline generation can be previewed, prepared for approval and executed through drafting worker tools.",
        [
            "backend/app/services/writing_agent/setup_generation_tool_adapters.py",
            "backend/app/services/writing_agent/storyline_generation_tool_adapters.py",
            "backend/app/services/writing_agent/outline_generation_tool_adapters.py",
            "backend/app/services/writing_agent/agent_worker_dispatch.py",
        ],
        [
            "preview_generate_setup_execution",
            "prepare_generate_setup_execution",
            "execute_generate_setup_with_approval",
            "preview_generate_storyline_execution",
            "prepare_generate_storyline_execution",
            "execute_generate_storyline_with_approval",
            "preview_generate_outline_execution",
            "prepare_generate_outline_execution",
            "execute_generate_outline_with_approval",
            "inspect_agent_worker_dispatch",
        ],
    ),
    _capability(
        "retrieval",
        "Chapter generation, review and revision can retrieve indexed evidence before drafting or changing canon.",
        ["backend/app/services/writing_agent/agent_memory_trace_tool_adapters.py"],
        ["search_agent_retrieval_context", "summarize_longform_context", "inspect_agent_memory_activation_plan"],
    ),
    _capability(
        "knowledge_base",
        "Author preferences, learned rules and reference patterns are projected through the knowledge-base route.",
        ["backend/app/services/writing_agent/agent_knowledge_base_route.py"],
        ["inspect_agent_knowledge_base_route"],
    ),
    _capability(
        "review",
        "Review and revision tools are callable by reviewer workers with guarded write follow-ups.",
        ["backend/app/services/writing_agent/review_revision_tool_adapters.py"],
        ["review_chapter_quality", "plan_chapter_revision"],
    ),
    _capability(
        "task_queue",
        "Longform batch work is observable through queue/job tools and bounded recovery routes.",
        ["backend/app/services/writing_agent/longform_tool_adapters.py"],
        ["inspect_agent_job_projection", "inspect_longform_chapter_batch"],
    ),
    _capability(
        "trace",
        "Trace, approval, mutation fingerprints and write gates expose audit evidence for Agent decisions.",
        ["backend/app/services/writing_agent/write_gate_coverage.py", "backend/app/services/writing_agent/mutation_fingerprint.py"],
        ["inspect_agent_trace_audit", "inspect_agent_write_gate_coverage"],
    ),
    _capability(
        "frontend",
        "Frontend actions are moving toward visible Agent routes and approval-chain drawer execution.",
        ["frontend/src", "backend/app/services/writing_agent/slash_command_route.py"],
        ["inspect_agent_dialog_control_plane_projection", "inspect_agent_route_preference_projection"],
    ),
    _capability(
        "long_memory",
        "Long-memory activation, context compression and knowledge capture are explicit Agent-readable surfaces.",
        ["backend/app/services/writing_agent/agent_memory_trace_tool_adapters.py", "backend/app/services/writing_agent/knowledge_base_tool_adapters.py"],
        ["inspect_agent_memory_activation_plan", "record_agent_knowledge_base_candidate"],
    ),
]


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


def inspect_reference_pattern_alignment(
    *,
    adapter_metadata_by_name: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    adapter_metadata_by_name = adapter_metadata_by_name or {}
    patterns = [_copy_pattern(pattern) for pattern in _PATTERNS]
    capability_alignment = [_copy_capability(item, adapter_metadata_by_name) for item in _CAPABILITY_ALIGNMENT]
    recommended_next_tools = _dedupe(
        [
            tool_name
            for pattern in patterns
            for tool_name in list(pattern["recommended_next_tools"])
        ]
    )
    decision_count = sum(len(pattern["novelv3_decisions"]) for pattern in patterns)
    return {
        "status": "completed",
        "version": REFERENCE_ALIGNMENT_INSPECTION_VERSION,
        "source_refs": list(_SOURCE_REFS),
        "summary": {
            "source_count": len(_SOURCE_REFS),
            "pattern_count": len(patterns),
            "decision_count": decision_count,
            "capability_area_count": len(capability_alignment),
            "adapter_backed_tool_count": len(adapter_metadata_by_name),
        },
        "patterns": patterns,
        "capability_alignment": capability_alignment,
        "recommended_next_tools": recommended_next_tools,
        "trace": {
            "reference_pattern_version": REFERENCE_PATTERN_PROJECTION_VERSION,
            "source_project_count": len(_SOURCE_REFS),
            "adapter_backed_tool_count": len(adapter_metadata_by_name),
        },
    }


def _copy_pattern(pattern: dict[str, Any]) -> dict[str, Any]:
    return {
        "pattern_id": str(pattern["pattern_id"]),
        "source": str(pattern["source"]),
        "source_path": str(pattern["source_path"]),
        "source_lines": list(pattern["source_lines"]),
        "applied_patterns": list(pattern["applied_patterns"]),
        "decision": str(pattern["decision"]),
        "novelv3_decisions": [dict(decision) for decision in list(pattern["novelv3_decisions"])],
        "capability_areas": list(pattern["capability_areas"]),
        "recommended_next_tools": list(pattern["recommended_next_tools"]),
    }


def _copy_capability(
    item: dict[str, Any],
    adapter_metadata_by_name: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    evidence_tools = list(item["evidence_tools"])
    adapter_backed_tools = [tool for tool in evidence_tools if tool in adapter_metadata_by_name]
    return {
        "area": str(item["area"]),
        "current_decision": str(item["current_decision"]),
        "module_paths": list(item["module_paths"]),
        "evidence_tools": evidence_tools,
        "adapter_backed_tools": adapter_backed_tools,
        "status": "implemented" if adapter_backed_tools else "descriptor_only",
    }


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result

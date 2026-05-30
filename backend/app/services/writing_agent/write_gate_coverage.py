from __future__ import annotations

from typing import Any

from app.services.writing_agent.tool_contracts import agent_tool_execution_metadata
from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor, CONFIRM_PARAM_NAMES, HASH_PARAM_NAMES
from app.services.writing_agent.tool_registry import list_agent_tool_descriptors

WRITE_MUTABILITY = {"write", "guarded_write"}
AGENT_PLAN_GATED_TOOLS = {
    "execute_generate_setup_with_approval": {
        "gate_version": "phase186.setup_agent_plan_approval.v1",
        "gate_type": "stateless_agent_plan_approval",
        "covered_tools": ["generate_setup"],
    },
    "execute_generate_storyline_with_approval": {
        "gate_version": "phase187.storyline_agent_plan_approval.v1",
        "gate_type": "stateless_agent_plan_approval",
        "covered_tools": ["generate_storyline"],
    },
    "execute_generate_outline_with_approval": {
        "gate_version": "phase188.outline_agent_plan_approval.v1",
        "gate_type": "stateless_agent_plan_approval",
        "covered_tools": ["generate_outline"],
    },
    "execute_generate_chapter_with_approval": {
        "gate_version": "phase114.direct_generate_agent_plan_approval.v1",
        "gate_type": "stateless_agent_plan_approval",
        "covered_tools": ["generate_chapter"],
    },
    "execute_import_setup_world_model_with_approval": {
        "gate_version": "phase191.setup_world_model_import_agent_plan_approval.v1",
        "gate_type": "stateless_agent_plan_approval",
        "covered_tools": ["import_setup_world_model"],
    },
    "execute_analyze_chapter_world_model_with_approval": {
        "gate_version": "phase192.world_model_analysis_agent_plan_approval.v1",
        "gate_type": "stateless_agent_plan_approval",
        "covered_tools": ["analyze_chapter_world_model"],
    },
    "execute_backfill_outline_gaps_with_approval": {
        "gate_version": "phase193.outline_backfill_agent_plan_approval.v1",
        "gate_type": "stateless_agent_plan_approval",
        "covered_tools": ["backfill_outline_gaps"],
    },
    "execute_record_agent_knowledge_base_candidate_with_approval": {
        "gate_version": "phase189.knowledge_base_candidate_agent_plan_approval.v1",
        "gate_type": "stateless_agent_plan_approval",
        "covered_tools": ["record_agent_knowledge_base_candidate"],
    },
    "execute_repair_longform_maintenance_with_approval": {
        "gate_version": "phase190.longform_maintenance_agent_plan_approval.v1",
        "gate_type": "stateless_agent_plan_approval",
        "covered_tools": ["repair_longform_maintenance"],
    },
    "execute_create_revision_draft_with_approval": {
        "gate_version": "phase194.revision_draft_agent_plan_approval.v1",
        "gate_type": "stateless_agent_plan_approval",
        "covered_tools": ["create_revision_draft"],
    },
    "execute_apply_planner_revision_patch_with_approval": {
        "gate_version": "phase195.revision_patch_agent_plan_approval.v1",
        "gate_type": "stateless_agent_plan_approval",
        "covered_tools": ["apply_planner_revision_patch"],
    },
    "execute_longform_chapter_batch": {
        "gate_version": "phase111.agent_plan_approval_execution_gate.v1",
        "gate_type": "persisted_agent_plan_approval",
        "covered_tools": ["generate_chapter"],
    }
}


def inspect_agent_write_gate_coverage(
    *,
    adapter_metadata_by_name: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    adapter_metadata_by_name = adapter_metadata_by_name or {}
    write_tools = [
        _write_tool_projection(descriptor, adapter_metadata_by_name.get(descriptor.name))
        for descriptor in list_agent_tool_descriptors()
        if _is_write_tool(descriptor, adapter_metadata_by_name.get(descriptor.name))
    ]
    write_tools.sort(key=lambda tool: (_risk_rank(tool["risk_level"]), tool["sort_key"], tool["tool_name"]))
    recommended_next_targets = [
        _recommended_target(tool)
        for tool in write_tools
        if tool["agent_plan_gate_status"] != "enforced"
    ][:8]

    return {
        "status": "completed",
        "version": "phase113.write_gate_coverage.v1",
        "summary": _summary(write_tools),
        "write_tools": write_tools,
        "recommended_next_targets": recommended_next_targets,
        "trace": {
            "source": "inspect_agent_write_gate_coverage",
            "coverage_basis": "tool_descriptor_plus_adapter_metadata",
        },
    }


def _is_write_tool(descriptor: AgentToolDescriptor, adapter_metadata: dict[str, Any] | None) -> bool:
    metadata = agent_tool_execution_metadata(descriptor, adapter_metadata)
    return str(metadata["mutability"]) in WRITE_MUTABILITY


def _write_tool_projection(descriptor: AgentToolDescriptor, adapter_metadata: dict[str, Any] | None) -> dict[str, Any]:
    execution_metadata = agent_tool_execution_metadata(descriptor, adapter_metadata)
    confirmation_fields = _confirmation_fields(descriptor)
    direct_confirmation_guard = bool(confirmation_fields)
    direct_write_policy = str((adapter_metadata or {}).get("write_policy") or "")
    direct_write_blocked = direct_write_policy == "approval_required_redirect"
    gate = AGENT_PLAN_GATED_TOOLS.get(descriptor.name)
    indirect_coverage = _indirect_coverage_for_tool(descriptor.name)
    gate_status = _gate_status(descriptor.name, gate, indirect_coverage)
    risk_level = _risk_level(
        gate_status=gate_status,
        direct_confirmation_guard=direct_confirmation_guard,
        direct_write_blocked=direct_write_blocked,
    )
    return {
        "tool_name": descriptor.name,
        "category": descriptor.category,
        "target_type": descriptor.target_type,
        "sort_key": descriptor.sort_key,
        "adapter_exists": adapter_metadata is not None,
        "adapter_type": adapter_metadata.get("adapter_type") if adapter_metadata else None,
        "handler_name": adapter_metadata.get("handler_name") if adapter_metadata else None,
        "mutability": execution_metadata["mutability"],
        "requires_confirmation": execution_metadata["requires_confirmation"],
        "direct_confirmation_guard": direct_confirmation_guard,
        "direct_write_policy": direct_write_policy or None,
        "direct_write_blocked": direct_write_blocked,
        "confirmation_fields": confirmation_fields,
        "agent_plan_gate_status": gate_status,
        "gate_version": gate.get("gate_version") if gate else None,
        "gate_type": gate.get("gate_type") if gate else None,
        "indirect_coverage": indirect_coverage,
        "risk_level": risk_level,
        "recommended_action": _recommended_action(
            gate_status,
            direct_confirmation_guard,
            direct_write_blocked=direct_write_blocked,
        ),
    }


def _confirmation_fields(descriptor: AgentToolDescriptor) -> list[str]:
    properties = descriptor.input_schema.get("properties") if isinstance(descriptor.input_schema, dict) else {}
    if not isinstance(properties, dict):
        return []
    confirm_fields = [field for field in CONFIRM_PARAM_NAMES + HASH_PARAM_NAMES if field in properties]
    return sorted(confirm_fields)


def _indirect_coverage_for_tool(tool_name: str) -> list[dict[str, Any]]:
    coverage: list[dict[str, Any]] = []
    for consumer_tool, gate in AGENT_PLAN_GATED_TOOLS.items():
        if tool_name in gate.get("covered_tools", []):
            coverage.append(
                {
                    "consumer_tool": consumer_tool,
                    "gate_version": gate["gate_version"],
                    "scope": "only_when_called_through_consumer",
                }
            )
    return coverage


def _gate_status(
    tool_name: str,
    gate: dict[str, Any] | None,
    indirect_coverage: list[dict[str, Any]],
) -> str:
    if gate is not None:
        return "enforced"
    if indirect_coverage:
        return "indirect_agent_gate_available"
    return "missing_agent_plan_gate"


def _risk_level(*, gate_status: str, direct_confirmation_guard: bool, direct_write_blocked: bool) -> str:
    if gate_status == "enforced":
        return "low"
    if direct_write_blocked:
        return "low"
    if direct_confirmation_guard:
        return "medium"
    return "high"


def _recommended_action(gate_status: str, direct_confirmation_guard: bool, *, direct_write_blocked: bool) -> str:
    if gate_status == "enforced":
        return "monitor_gate_drift"
    if direct_write_blocked:
        return "route_direct_calls_to_approval_executor"
    if direct_confirmation_guard:
        return "promote_confirm_guard_to_agent_plan_approval"
    return "add_direct_agent_plan_approval_gate"


def _summary(write_tools: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "write_tool_count": len(write_tools),
        "agent_plan_gate_enforced_count": sum(
            1 for tool in write_tools if tool["agent_plan_gate_status"] == "enforced"
        ),
        "direct_confirmation_guard_count": sum(1 for tool in write_tools if tool["direct_confirmation_guard"]),
        "missing_agent_plan_gate_count": sum(
            1 for tool in write_tools if tool["agent_plan_gate_status"] != "enforced"
        ),
        "high_risk_direct_write_count": sum(1 for tool in write_tools if tool["risk_level"] == "high"),
    }


def _recommended_target(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool_name": tool["tool_name"],
        "category": tool["category"],
        "risk_level": tool["risk_level"],
        "agent_plan_gate_status": tool["agent_plan_gate_status"],
        "recommended_action": tool["recommended_action"],
    }


def _risk_rank(risk_level: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(risk_level, 3)

from __future__ import annotations

from collections import Counter
from typing import Any

from app.services.writing_agent.tool_policy import report_policy_for_tool
from app.services.writing_agent.tool_recommendations import RECOMMENDATION_OUTPUT_FIELDS
from app.services.writing_agent.tool_descriptor_types import (
    AgentToolDescriptor,
    ToolMutability,
    descriptor_mutability,
    descriptor_permission_level,
    descriptor_requires_confirmation,
)
from app.services.writing_agent.tool_registry import list_agent_tool_descriptors

REFERENCE_ALIGNMENT = {
    "patterns": [
        "tool_visibility_projection",
        "schema_backed_tool_contracts",
        "normalized_tool_results",
        "runtime_policy_projection",
        "recommendation_surface_normalization",
        "traceable_failure_recovery",
        "memory_tool_boundary",
        "permission_scope_category",
        "delegation_as_named_tools",
        "bounded_memory_context",
        "event_and_transcript_audit",
    ],
    "source_refs": [
        "references/agent-projects/openclaw",
        "references/agent-projects/hermes-agent",
        "references/agent-projects/openhuman",
    ],
}

CAPABILITY_AREA_BY_CATEGORY = {
    "preflight": "agent_core",
    "generation": "hermes_generation",
    "knowledge_base": "knowledge_base",
    "longform_memory": "longform_memory",
    "retrieval": "retrieval",
    "athena_world_model": "world_model",
    "review": "review",
    "task_queue": "task_queue",
    "trace": "trace_audit",
    "maintenance": "maintenance",
}

MEMORY_BOUNDARY_BY_CATEGORY = {
    "knowledge_base": "knowledge_base",
    "longform_memory": "longform_memory",
    "retrieval": "retrieval_index",
    "athena_world_model": "world_model",
    "trace": "trace_audit",
}
RESOURCE_SCOPE_BY_CATEGORY = {
    "preflight": "agent_plan",
    "generation": "manuscript",
    "knowledge_base": "knowledge_base",
    "longform_memory": "longform_memory",
    "retrieval": "retrieval_index",
    "athena_world_model": "world_model",
    "review": "chapter_review",
    "task_queue": "background_task",
    "trace": "trace_audit",
    "maintenance": "project_maintenance",
}


def build_agent_tool_contract_snapshot(
    *,
    adapter_metadata_by_name: dict[str, dict[str, Any]] | None = None,
    include_gap_details: bool = True,
) -> dict[str, Any]:
    adapter_metadata_by_name = adapter_metadata_by_name or {}
    descriptors = list_agent_tool_descriptors()
    tools = [
        _tool_contract(descriptor, adapter_metadata_by_name.get(descriptor.name), include_gap_details=include_gap_details)
        for descriptor in descriptors
    ]
    gaps = [gap for tool in tools for gap in tool.get("gaps", [])]
    if not include_gap_details:
        for tool in tools:
            tool.pop("gaps", None)

    summary = _summary(tools, gaps)
    return {
        "status": "completed",
        "summary": summary,
        "coverage": _coverage(tools),
        "tools": tools,
        "gaps": gaps if include_gap_details else [],
        "reference_alignment": REFERENCE_ALIGNMENT,
        "recommended_next_steps": _recommended_next_steps(gaps),
    }


def _tool_contract(
    descriptor: AgentToolDescriptor,
    adapter_metadata: dict[str, Any] | None,
    *,
    include_gap_details: bool,
) -> dict[str, Any]:
    input_schema_present = _schema_present(descriptor.input_schema)
    output_schema_present = _schema_present(descriptor.output_schema)
    mutability = _mutability(descriptor, adapter_metadata)
    gaps = _gaps(
        descriptor,
        adapter_metadata=adapter_metadata,
        input_schema_present=input_schema_present,
        output_schema_present=output_schema_present,
        mutability=mutability,
    )
    recovery_tools = _recovery_tools(descriptor, mutability)
    report_policy = report_policy_for_tool(descriptor.name)
    contract = {
        "name": descriptor.name,
        "module": descriptor.module,
        "category": descriptor.category,
        "capability_area": CAPABILITY_AREA_BY_CATEGORY.get(descriptor.category, descriptor.category),
        "target_type": descriptor.target_type,
        "internal": descriptor.internal,
        "visibility": "internal_only" if descriptor.internal else "agent_visible",
        "non_blocking_report": descriptor.non_blocking_report,
        "mutability": mutability.value,
        "permission_level": _permission_level(mutability),
        "side_effects": _side_effects(mutability),
        "requires_confirmation": _requires_confirmation(descriptor),
        "parallel_safe": _parallel_safe(mutability),
        "resource_scope": RESOURCE_SCOPE_BY_CATEGORY.get(descriptor.category, descriptor.category),
        "memory_boundary": MEMORY_BOUNDARY_BY_CATEGORY.get(descriptor.category, "none"),
        "trace_required": descriptor.internal or mutability in {ToolMutability.WRITE, ToolMutability.GUARDED_WRITE},
        "execution_route": _execution_route(descriptor, adapter_metadata),
        "result_size_policy": _result_size_policy(descriptor),
        "adapter_type": adapter_metadata.get("adapter_type") if adapter_metadata else None,
        "handler_name": adapter_metadata.get("handler_name") if adapter_metadata else None,
        "input_schema_present": input_schema_present,
        "output_schema_present": output_schema_present,
        "input_required_fields": list(descriptor.input_schema.get("required") or []),
        "availability_checks": list(descriptor.availability_checks),
        "warning_checks": list(descriptor.warning_checks),
        "preconditions": list(descriptor.availability_checks),
        "postconditions": _postconditions(descriptor, mutability),
        "recovery_tools": recovery_tools,
        "report_policy": report_policy,
        "recommendation_contract": _recommendation_contract(descriptor, report_policy, recovery_tools),
        "gap_codes": [gap["code"] for gap in gaps],
        "contract_status": "ready" if not gaps else "needs_work",
    }
    if include_gap_details:
        contract["gaps"] = gaps
    return contract


def _schema_present(schema: dict[str, Any]) -> bool:
    return isinstance(schema, dict) and schema.get("type") == "object"


def _mutability(descriptor: AgentToolDescriptor, adapter_metadata: dict[str, Any] | None) -> ToolMutability:
    return descriptor_mutability(descriptor, adapter_metadata=adapter_metadata)


def agent_tool_execution_metadata(
    descriptor: AgentToolDescriptor | None,
    adapter_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if descriptor is None:
        return {"mutability": "unclassified", "requires_confirmation": False}
    mutability = _mutability(descriptor, adapter_metadata)
    return {
        "mutability": mutability.value,
        "requires_confirmation": mutability in {ToolMutability.WRITE, ToolMutability.GUARDED_WRITE}
        or _requires_confirmation(descriptor),
    }


def _execution_route(descriptor: AgentToolDescriptor, adapter_metadata: dict[str, Any] | None) -> str:
    if adapter_metadata:
        adapter_type = str(adapter_metadata.get("adapter_type") or "adapter")
        return f"{adapter_type}_adapter"
    if descriptor.internal:
        return "unsupported_internal"
    return "legacy_action_fallback"


def _permission_level(mutability: ToolMutability) -> str:
    return descriptor_permission_level(mutability).value


def _side_effects(mutability: ToolMutability) -> list[str]:
    if mutability is ToolMutability.READ:
        return []
    if mutability is ToolMutability.GUARDED_WRITE:
        return ["database_write", "requires_confirmation"]
    if mutability is ToolMutability.WRITE:
        return ["database_write"]
    return ["unknown"]


def _requires_confirmation(descriptor: AgentToolDescriptor) -> bool:
    return descriptor_requires_confirmation(descriptor)


def _parallel_safe(mutability: ToolMutability) -> bool:
    return mutability is ToolMutability.READ


def _result_size_policy(descriptor: AgentToolDescriptor) -> str:
    if descriptor.category in {"longform_memory", "knowledge_base", "trace"}:
        return "bounded_summary"
    if descriptor.category == "generation":
        return "large_artifact"
    return "structured_summary"


def _postconditions(descriptor: AgentToolDescriptor, mutability: ToolMutability) -> list[str]:
    if mutability is ToolMutability.READ:
        return ["no_state_change", "structured_result"]
    if descriptor.category == "task_queue":
        return ["task_state_updated", "traceable_result"]
    if descriptor.category == "athena_world_model":
        return ["proposal_or_world_state_updated", "traceable_result"]
    if descriptor.category == "generation":
        return ["project_artifact_updated", "traceable_result"]
    return ["state_updated", "traceable_result"]


def _recovery_tools(descriptor: AgentToolDescriptor, mutability: ToolMutability) -> list[str]:
    if descriptor.name == "plan_recovery_tools":
        return []
    if descriptor.category == "task_queue":
        return ["inspect_agent_job_projection", "plan_recovery_tools"]
    if descriptor.category == "athena_world_model":
        return ["review_world_model_proposals", "plan_world_model_proposal_resolution"]
    if descriptor.category == "generation" or mutability is not ToolMutability.READ:
        return ["plan_recovery_tools", "inspect_agent_trace_audit"]
    return []


def _recommendation_contract(
    descriptor: AgentToolDescriptor,
    report_policy: dict[str, object],
    recovery_tools: list[str],
) -> dict[str, object]:
    properties = descriptor.output_schema.get("properties") if isinstance(descriptor.output_schema, dict) else {}
    output_fields = [
        field for field in RECOMMENDATION_OUTPUT_FIELDS if isinstance(properties, dict) and field in properties
    ]
    policy_followups = [str(tool) for tool in report_policy.get("allowed_followups") or []]
    return {
        "output_fields": output_fields,
        "canonical_output_field": output_fields[0] if output_fields else None,
        "legacy_output_fields": [field for field in output_fields if field != "recommended_next_tools"],
        "policy_followups": policy_followups,
        "recovery_followups": list(recovery_tools),
        "deterministic_followups": _dedupe(policy_followups + recovery_tools),
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


def _gaps(
    descriptor: AgentToolDescriptor,
    *,
    adapter_metadata: dict[str, Any] | None,
    input_schema_present: bool,
    output_schema_present: bool,
    mutability: ToolMutability,
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    if not input_schema_present:
        gaps.append(_gap(descriptor.name, "missing_input_schema", "blocker", "工具缺少可投影的输入 schema。"))
    if not output_schema_present:
        gaps.append(_gap(descriptor.name, "missing_output_schema", "blocker", "工具缺少可投影的输出 schema。"))
    if mutability is ToolMutability.UNCLASSIFIED:
        gaps.append(_gap(descriptor.name, "missing_mutability_classification", "warning", "工具缺少读写/保护写入分类。"))
    if adapter_metadata is None:
        severity = "blocker" if descriptor.internal else "warning"
        gaps.append(_gap(descriptor.name, "missing_agent_native_adapter", severity, "工具尚未接入 Agent-native 执行适配器。"))
    if mutability in {ToolMutability.WRITE, ToolMutability.GUARDED_WRITE} and not descriptor.availability_checks:
        gaps.append(_gap(descriptor.name, "missing_availability_checks", "warning", "写入类工具缺少可见性或依赖检查。"))
    if mutability in {ToolMutability.WRITE, ToolMutability.GUARDED_WRITE} and not _requires_confirmation(descriptor):
        gaps.append(_gap(descriptor.name, "missing_confirmation_guard", "warning", "写入类工具缺少显式确认或哈希门禁字段。"))
    if descriptor.output_schema == {"type": "object", "properties": {"status": {"type": "string"}}, "additionalProperties": True}:
        gaps.append(_gap(descriptor.name, "output_schema_too_generic", "warning", "工具输出 schema 过宽，Agent 难以判断后置状态。"))
    return gaps


def _gap(tool_name: str, code: str, severity: str, message: str) -> dict[str, Any]:
    return {"tool_name": tool_name, "code": code, "severity": severity, "message": message}


def _summary(tools: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> dict[str, Any]:
    mutability_counts = Counter(str(tool["mutability"]) for tool in tools)
    capability_counts = Counter(str(tool["capability_area"]) for tool in tools)
    return {
        "total_tools": len(tools),
        "internal_tools": sum(1 for tool in tools if tool["internal"]),
        "external_tools": sum(1 for tool in tools if not tool["internal"]),
        "adapter_backed_tools": sum(1 for tool in tools if tool["adapter_type"]),
        "tools_needing_work": sum(1 for tool in tools if tool["contract_status"] != "ready"),
        "gap_count": len(gaps),
        "mutability_counts": dict(sorted(mutability_counts.items())),
        "capability_counts": dict(sorted(capability_counts.items())),
    }


def _coverage(tools: list[dict[str, Any]]) -> dict[str, float]:
    total = len(tools) or 1
    return {
        "schema_coverage_ratio": round(
            sum(1 for tool in tools if tool["input_schema_present"] and tool["output_schema_present"]) / total,
            4,
        ),
        "adapter_coverage_ratio": round(sum(1 for tool in tools if tool["adapter_type"]) / total, 4),
        "mutability_coverage_ratio": round(sum(1 for tool in tools if tool["mutability"] != "unclassified") / total, 4),
        "trace_contract_ratio": round(sum(1 for tool in tools if tool["trace_required"]) / total, 4),
        "confirmation_contract_ratio": round(
            sum(1 for tool in tools if tool["mutability"] == "read" or tool["requires_confirmation"]) / total,
            4,
        ),
        "availability_check_ratio": round(sum(1 for tool in tools if tool["availability_checks"]) / total, 4),
    }


def _recommended_next_steps(gaps: list[dict[str, Any]]) -> list[str]:
    codes = {gap["code"] for gap in gaps}
    steps: list[str] = []
    if "missing_agent_native_adapter" in codes:
        steps.append("优先将仍走 legacy action 的核心生成、修订和世界模型写入工具迁移为 Agent-native adapter。")
    if "missing_availability_checks" in codes:
        steps.append("为写入类工具补齐可见性、依赖和确认门禁，减少 Agent 误调用。")
    if "missing_confirmation_guard" in codes:
        steps.append("为写入类工具补齐 confirm/hash 保护，区分 preview、plan 和 execute。")
    if "output_schema_too_generic" in codes:
        steps.append("收紧关键工具输出 schema，使 planner 能基于状态、目标和后置条件做判断。")
    if "missing_mutability_classification" in codes:
        steps.append("补齐工具读写分类，确保 Agent planner 能区分只读、写入和保护写入。")
    if not steps:
        steps.append("继续把模块级能力拆成更小的领域工具，并接入 Trace 与恢复策略。")
    return steps

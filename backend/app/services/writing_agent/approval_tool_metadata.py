from __future__ import annotations

from typing import Any

from app.services.writing_agent.tool_contracts import agent_tool_execution_metadata
from app.services.writing_agent.tool_registry import get_agent_tool_descriptor

_WRITE_MUTABILITY = {"write", "guarded_write"}


def build_approval_tool_metadata_by_name(
    plan: dict[str, Any] | None,
    *,
    adapter_metadata_by_name: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    if not isinstance(plan, dict):
        return {}

    steps = plan.get("steps") if isinstance(plan.get("steps"), list) else []
    adapter_metadata_by_name = adapter_metadata_by_name or {}
    metadata_by_name: dict[str, dict[str, Any]] = {}

    for step in steps:
        if not _approval_step_needs_contract_check(step):
            continue
        tool_name = str(step.get("tool_name") or "").strip() if isinstance(step, dict) else ""
        if not tool_name:
            continue

        descriptor = get_agent_tool_descriptor(tool_name)
        adapter_metadata = adapter_metadata_by_name.get(tool_name)
        if adapter_metadata is None:
            adapter_metadata = _approval_executor_adapter_metadata(step, adapter_metadata_by_name)
        execution_metadata = agent_tool_execution_metadata(descriptor, adapter_metadata)
        input_schema = descriptor.input_schema if descriptor is not None else {}
        required_fields = input_schema.get("required") if isinstance(input_schema, dict) else []
        metadata_by_name[tool_name] = {
            "tool_name": tool_name,
            "tool_exists": descriptor is not None,
            "adapter_exists": adapter_metadata is not None,
            "adapter_type": adapter_metadata.get("adapter_type") if adapter_metadata else None,
            "handler_name": adapter_metadata.get("handler_name") if adapter_metadata else None,
            "mutability": execution_metadata["mutability"],
            "requires_confirmation": execution_metadata["requires_confirmation"],
            "required_fields": list(required_fields) if isinstance(required_fields, list) else [],
        }

    return metadata_by_name


def _approval_executor_adapter_metadata(
    step: dict[str, Any],
    adapter_metadata_by_name: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    executor_tool_name = str(step.get("approval_executor_tool_name") or "").strip()
    if not executor_tool_name:
        return None
    executor_metadata = adapter_metadata_by_name.get(executor_tool_name)
    if executor_metadata is None:
        return None
    return {
        "tool_name": str(step.get("tool_name") or "").strip(),
        "adapter_type": "approval_wrapper",
        "category": executor_metadata.get("category"),
        "mutability": "write",
        "handler_name": executor_metadata.get("handler_name"),
        "approval_executor_tool_name": executor_tool_name,
    }


def _approval_step_needs_contract_check(step: object) -> bool:
    if not isinstance(step, dict):
        return False
    mutability = str(step.get("mutability") or "")
    return step.get("requires_confirmation") is True or mutability in _WRITE_MUTABILITY

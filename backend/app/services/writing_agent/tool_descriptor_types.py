from __future__ import annotations

from dataclasses import dataclass
from typing import Any


READ_TOOL_NAMES = frozenset({"preflight_writing"})
READ_PREFIXES = ("describe_", "inspect_", "plan_", "preview_", "review_", "summarize_", "verify_")
WRITE_PREFIXES = (
    "generate_",
    "expand_",
    "import_",
    "analyze_",
    "apply_",
    "record_",
    "repair_",
    "enqueue_",
    "execute_",
    "create_",
    "backfill_",
    "compress_",
)
GUARDED_WRITE_PREFIXES = ("apply_", "execute_", "enqueue_", "route_")
CONFIRM_PARAM_NAMES = (
    "confirm_apply",
    "confirm_checkpoint",
    "confirm_enqueue",
    "confirm_execute",
    "confirm_prepare",
    "confirm_review",
)
HASH_PARAM_NAMES = (
    "plan_hash",
    "attempt_manifest_hash",
    "approval_contract_hash",
    "expected_post_generation_review_hash",
)


@dataclass(frozen=True)
class AgentToolDescriptor:
    name: str
    module: str
    category: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    target_type: str | None
    internal: bool = False
    non_blocking_report: bool = False
    sort_key: int = 100
    availability_checks: tuple[str, ...] = ()
    warning_checks: tuple[str, ...] = ()

    def to_public_dict(self, adapter_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "name": self.name,
            "module": self.module,
            "category": self.category,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "target_type": self.target_type,
            "internal": self.internal,
            "non_blocking_report": self.non_blocking_report,
            "agent_tool_surface": descriptor_tool_surface(self, adapter_metadata=adapter_metadata),
        }


def descriptor_tool_surface(
    descriptor: AgentToolDescriptor,
    *,
    adapter_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mutability = descriptor_mutability(descriptor, adapter_metadata=adapter_metadata)
    return {
        "visibility": "internal_only" if descriptor.internal else "agent_visible",
        "tool_scope": "agent_only" if descriptor.internal else "agent_and_legacy_action",
        "mutability": mutability,
        "permission_level": descriptor_permission_level(mutability),
        "requires_confirmation": mutability == "guarded_write" or (
            mutability not in {"read", "write"} and descriptor_requires_confirmation(descriptor)
        ),
        "parallel_safe": mutability == "read",
    }


def descriptor_mutability(
    descriptor: AgentToolDescriptor,
    *,
    adapter_metadata: dict[str, Any] | None = None,
) -> str:
    if adapter_metadata and adapter_metadata.get("mutability"):
        adapter_mutability = str(adapter_metadata["mutability"])
        if adapter_mutability == "write" and (
            descriptor.name.startswith(GUARDED_WRITE_PREFIXES) or descriptor_requires_confirmation(descriptor)
        ):
            return "guarded_write"
        return adapter_mutability
    if descriptor.name in READ_TOOL_NAMES or descriptor.name.startswith(READ_PREFIXES):
        return "read"
    if descriptor.name.startswith(GUARDED_WRITE_PREFIXES) or descriptor_requires_confirmation(descriptor):
        return "guarded_write"
    if descriptor.name.startswith(WRITE_PREFIXES):
        return "write"
    if descriptor.non_blocking_report:
        return "read"
    return "unclassified"


def descriptor_permission_level(mutability: str) -> str:
    if mutability == "read":
        return "read"
    if mutability == "guarded_write":
        return "confirm_required"
    if mutability == "write":
        return "write"
    return "unknown"


def descriptor_requires_confirmation(descriptor: AgentToolDescriptor) -> bool:
    properties = descriptor.input_schema.get("properties") if isinstance(descriptor.input_schema, dict) else {}
    if not isinstance(properties, dict):
        return False
    return any(name in properties for name in CONFIRM_PARAM_NAMES + HASH_PARAM_NAMES)


def object_schema(properties: dict[str, Any] | None = None, required: tuple[str, ...] = ()) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": properties or {}, "additionalProperties": True}
    if required:
        schema["required"] = list(required)
    return schema

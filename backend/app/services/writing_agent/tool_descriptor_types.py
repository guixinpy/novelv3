from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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

    def to_public_dict(self) -> dict[str, Any]:
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
        }


def object_schema(properties: dict[str, Any] | None = None, required: tuple[str, ...] = ()) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": properties or {}, "additionalProperties": True}
    if required:
        schema["required"] = list(required)
    return schema

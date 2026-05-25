from __future__ import annotations

from typing import Any

from app.services.writing_agent.tool_registry import get_agent_tool_descriptor

TOOL_REQUEST_VALIDATION_VERSION = "phase221.tool_request_validation.v1"


def validate_writing_agent_tool_request(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    descriptor = get_agent_tool_descriptor(tool_name)
    if descriptor is None:
        return {
            "status": "failed",
            "version": TOOL_REQUEST_VALIDATION_VERSION,
            "tool_name": tool_name,
            "issues": [
                {
                    "code": "unknown_tool",
                    "path": "tool_name",
                    "message": f"Unknown writing agent tool: {tool_name}",
                }
            ],
        }

    schema = descriptor.input_schema if isinstance(descriptor.input_schema, dict) else {}
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    required = schema.get("required") if isinstance(schema.get("required"), list) else []
    issues: list[dict[str, str]] = []

    for name in required:
        if isinstance(name, str) and name not in params:
            issues.append(
                {
                    "code": "missing_required_param",
                    "path": name,
                    "message": f"Missing required param: {name}",
                }
            )

    for name, property_schema in properties.items():
        if not isinstance(name, str) or name not in params or not isinstance(property_schema, dict):
            continue
        value = params[name]
        expected_type = property_schema.get("type")
        if expected_type and not _matches_json_schema_type(value, expected_type):
            issues.append(
                {
                    "code": "invalid_param_type",
                    "path": name,
                    "message": f"Param {name} must be {_type_label(expected_type)}.",
                }
            )
            continue
        minimum = property_schema.get("minimum")
        if isinstance(minimum, int | float) and isinstance(value, int | float) and not isinstance(value, bool):
            if value < minimum:
                issues.append(
                    {
                        "code": "invalid_param_minimum",
                        "path": name,
                        "message": f"Param {name} must be >= {minimum}.",
                    }
                )

    return {
        "status": "failed" if issues else "passed",
        "version": TOOL_REQUEST_VALIDATION_VERSION,
        "tool_name": tool_name,
        "issues": issues,
    }


def _matches_json_schema_type(value: Any, expected_type: Any) -> bool:
    if isinstance(expected_type, list):
        return any(_matches_json_schema_type(value, item) for item in expected_type)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    return True


def _type_label(expected_type: Any) -> str:
    if isinstance(expected_type, list):
        return " or ".join(str(item) for item in expected_type)
    return str(expected_type)

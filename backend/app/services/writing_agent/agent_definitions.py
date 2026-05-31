from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

AGENT_DEFINITION_VERSION = "phase229.agent_definition.v1"
AGENT_DEFINITION_REGISTRY_AUDIT_VERSION = "phase234.agent_definition_registry_audit.v1"
AGENT_DEFINITION_DIR = Path(__file__).with_name("agent_definitions")
REQUIRED_FIELDS = ("name", "role", "max_depth", "allowed_tools", "write_policy")


def load_agent_definition(name: str, *, base_dir: Path | None = None) -> dict[str, Any]:
    definition_name = _definition_name(name)
    if not definition_name:
        return _blocked_definition(name, reason_code="missing_agent_definition_name")

    definition_dir = base_dir or AGENT_DEFINITION_DIR
    path = definition_dir / f"{definition_name}.yaml"
    if not path.exists():
        return _blocked_definition(definition_name, reason_code="agent_definition_not_found")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return _blocked_definition(definition_name, reason_code="agent_definition_invalid_yaml")

    missing_fields = [field for field in REQUIRED_FIELDS if field not in data]
    if missing_fields:
        definition = _blocked_definition(definition_name, reason_code="agent_definition_missing_fields")
        definition["missing_fields"] = missing_fields
        return definition

    allowed_tools = _string_list(data.get("allowed_tools"))
    write_policy = data.get("write_policy") if isinstance(data.get("write_policy"), dict) else {}
    max_depth = _non_negative_int(data.get("max_depth"))
    return {
        "version": AGENT_DEFINITION_VERSION,
        "status": "ready",
        "name": str(data["name"]).strip(),
        "role": str(data["role"]).strip(),
        "max_depth": max_depth,
        "allowed_tools": allowed_tools,
        "write_policy": dict(write_policy),
        "can_dispatch_children": _can_dispatch_children(max_depth, write_policy),
        "source_path": str(path),
    }


def inspect_agent_definition_registry() -> dict[str, Any]:
    from app.services.writing_agent.agent_tool_surface_policy import AGENT_PROFILE_DEFINITIONS

    worker_profiles = sorted(
        str(profile)
        for profile, definition in AGENT_PROFILE_DEFINITIONS.items()
        if isinstance(definition, dict) and definition.get("role") == "worker"
    )
    definitions = [_definition_audit_row(profile, load_agent_definition(profile)) for profile in worker_profiles]
    issues = [issue for row in definitions for issue in row.pop("_issues", [])]
    ready_worker_definitions = sum(1 for row in definitions if row["status"] == "ready")
    leaf_worker_definitions = sum(1 for row in definitions if row["can_dispatch_children"] is False)
    return {
        "version": AGENT_DEFINITION_REGISTRY_AUDIT_VERSION,
        "status": "passed" if not issues else "needs_attention",
        "summary": {
            "worker_profiles": len(worker_profiles),
            "ready_worker_definitions": ready_worker_definitions,
            "leaf_worker_definitions": leaf_worker_definitions,
            "issues": len(issues),
        },
        "worker_profiles": worker_profiles,
        "definitions": definitions,
        "issues": issues,
    }


def _blocked_definition(name: str, *, reason_code: str) -> dict[str, Any]:
    return {
        "version": AGENT_DEFINITION_VERSION,
        "status": "blocked",
        "name": str(name or "").strip(),
        "role": "unknown",
        "max_depth": 0,
        "allowed_tools": [],
        "write_policy": {},
        "can_dispatch_children": False,
        "reason_code": reason_code,
    }


def _definition_audit_row(profile: str, definition: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if definition.get("status") != "ready":
        issues.append(_definition_issue("agent_definition_not_ready", profile=profile, definition=definition))
    if definition.get("role") != "worker":
        issues.append(_definition_issue("agent_definition_not_worker", profile=profile, definition=definition))
    if definition.get("can_dispatch_children") is True:
        issues.append(_definition_issue("worker_definition_can_dispatch_children", profile=profile, definition=definition))

    return {
        "profile": profile,
        "definition_name": str(definition.get("name") or ""),
        "status": str(definition.get("status") or "unknown"),
        "role": str(definition.get("role") or "unknown"),
        "can_dispatch_children": definition.get("can_dispatch_children") is True,
        "allowed_tools": list(definition.get("allowed_tools") or []),
        "_issues": issues,
    }


def _definition_issue(code: str, *, profile: str, definition: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": code,
        "severity": "error",
        "profile": profile,
        "definition_name": str(definition.get("name") or ""),
    }


def _can_dispatch_children(max_depth: int, write_policy: dict[str, Any]) -> bool:
    return max_depth > 0 and str(write_policy.get("child_dispatch") or "").strip() == "allow"


def _definition_name(name: str) -> str:
    return str(name or "").strip().replace("\\", "").replace("/", "")


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := str(item or "").strip())]


def _non_negative_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)

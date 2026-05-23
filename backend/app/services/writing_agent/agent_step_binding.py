from __future__ import annotations

import hashlib
import json
from typing import Any

AGENT_STEP_BINDING_VERSION = "phase144.agent_step_binding.v1"


def build_agent_step_binding(
    *,
    project_id: str,
    plan_id: object,
    source_projection_id: object,
    step: dict[str, Any],
    mutation_fingerprint: dict[str, Any] | None,
) -> dict[str, Any]:
    resource_binding = _resource_binding(
        project_id=project_id,
        plan_id=plan_id,
        source_projection_id=source_projection_id,
        step=step,
        mutation_fingerprint=mutation_fingerprint,
    )
    tool_call_id = _tool_call_id(resource_binding)
    resource_binding["tool_call_id"] = tool_call_id
    return {
        "tool_call_id": tool_call_id,
        "resource_binding": resource_binding,
    }


def summarize_resource_binding(resource_binding: object) -> dict[str, Any] | None:
    if not isinstance(resource_binding, dict):
        return None
    return {
        "tool_call_id": resource_binding.get("tool_call_id"),
        "tool_name": resource_binding.get("tool_name"),
        "target_type": resource_binding.get("target_type"),
        "target_id": resource_binding.get("target_id"),
        "source_plan_id": resource_binding.get("source_plan_id"),
        "source_step_id": resource_binding.get("source_step_id"),
        "binding_source": resource_binding.get("binding_source"),
    }


def verify_resource_binding_target(
    verification: object,
    *,
    tool_name: str,
    target_type: str,
    target_id: str,
) -> dict[str, Any]:
    expected = {
        "tool_name": _clean(tool_name),
        "target_type": _clean(target_type),
        "target_id": _clean(target_id),
    }
    resource_bindings = _verification_resource_bindings(verification)
    tool_bindings = [binding for binding in resource_bindings if binding.get("tool_name") == expected["tool_name"]]
    if not tool_bindings:
        return _binding_check(
            status="blocked",
            reason="resource_binding_missing",
            expected=expected,
            resource_bindings=resource_bindings,
        )

    for binding in tool_bindings:
        if binding.get("target_type") == expected["target_type"] and binding.get("target_id") == expected["target_id"]:
            return _binding_check(
                status="ready",
                reason="resource_binding_verified",
                expected=expected,
                resource_binding=binding,
                resource_bindings=tool_bindings,
            )

    return _binding_check(
        status="blocked",
        reason="resource_binding_target_mismatch",
        expected=expected,
        resource_bindings=tool_bindings,
    )


def _verification_resource_bindings(verification: object) -> list[dict[str, Any]]:
    drift = verification.get("drift") if isinstance(verification, dict) and isinstance(verification.get("drift"), dict) else {}
    value = drift.get("resource_bindings")
    if not isinstance(value, list):
        return []
    bindings: list[dict[str, Any]] = []
    for item in value:
        summary = summarize_resource_binding(item)
        if summary:
            bindings.append(summary)
    return bindings


def _binding_check(
    *,
    status: str,
    reason: str,
    expected: dict[str, Any],
    resource_bindings: list[dict[str, Any]],
    resource_binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": status,
        "reason": reason,
        "expected": expected,
        "resource_bindings": resource_bindings,
    }
    if resource_binding is not None:
        result["tool_call_id"] = resource_binding.get("tool_call_id")
        result["resource_binding"] = resource_binding
    return result


def _resource_binding(
    *,
    project_id: str,
    plan_id: object,
    source_projection_id: object,
    step: dict[str, Any],
    mutation_fingerprint: dict[str, Any] | None,
) -> dict[str, Any]:
    components = mutation_fingerprint.get("components") if isinstance(mutation_fingerprint, dict) else {}
    return {
        "binding_version": AGENT_STEP_BINDING_VERSION,
        "binding_source": "server_derived",
        "project_id": project_id,
        "source_plan_id": _clean(plan_id),
        "source_projection_id": _clean(source_projection_id),
        "source_step_id": _clean(step.get("step_id")),
        "step_index": step.get("step_index"),
        "tool_name": _clean(step.get("tool_name")),
        "target_type": components.get("target_type") if isinstance(components, dict) else None,
        "target_id": components.get("target_id") if isinstance(components, dict) else None,
        "mutation_fingerprint": mutation_fingerprint.get("fingerprint") if isinstance(mutation_fingerprint, dict) else None,
    }


def _tool_call_id(resource_binding: dict[str, Any]) -> str:
    payload = {
        "binding_version": resource_binding.get("binding_version"),
        "project_id": resource_binding.get("project_id"),
        "source_plan_id": resource_binding.get("source_plan_id"),
        "source_step_id": resource_binding.get("source_step_id"),
        "step_index": resource_binding.get("step_index"),
        "tool_name": resource_binding.get("tool_name"),
        "target_type": resource_binding.get("target_type"),
        "target_id": resource_binding.get("target_id"),
    }
    return f"toolcall:{_sha256(payload)[:16]}"


def _sha256(value: object) -> str:
    normalized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _clean(value: object) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None

from __future__ import annotations

import hashlib
import json
from typing import Any

MUTATION_FINGERPRINT_VERSION = "phase142.mutation_fingerprint.v1"

_KNOWN_MUTATING_TOOLS = {
    "execute_generate_setup_with_approval",
    "execute_generate_storyline_with_approval",
    "execute_generate_outline_with_approval",
    "generate_setup",
    "generate_storyline",
    "generate_outline",
    "generate_chapter",
    "generate_chapter_range",
    "apply_world_model_proposal_resolution",
}


def inspect_agent_mutation_fingerprints(project_id: str, tools: object) -> dict[str, Any]:
    tool_calls = tools if isinstance(tools, list) else []
    fingerprints = [
        build_mutation_fingerprint(
            project_id,
            str(item.get("tool_name") or item.get("name") or "").strip(),
            item.get("params") if isinstance(item.get("params"), dict) else {},
        )
        for item in tool_calls
        if isinstance(item, dict)
    ]
    blocked_count = sum(1 for item in fingerprints if item["status"] == "blocked")
    ready_count = sum(1 for item in fingerprints if item["status"] == "ready")
    not_mutating_count = sum(1 for item in fingerprints if item["status"] == "not_mutating")
    return {
        "status": "blocked" if blocked_count else "completed",
        "version": MUTATION_FINGERPRINT_VERSION,
        "project_id": project_id,
        "summary": {
            "tool_count": len(fingerprints),
            "ready_count": ready_count,
            "blocked_count": blocked_count,
            "not_mutating_count": not_mutating_count,
        },
        "fingerprints": fingerprints,
        "recommended_next_tools": ["inspect_agent_tool_contracts"] if blocked_count else [],
    }


def build_mutation_fingerprint(project_id: str, tool_name: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    params = params or {}
    if tool_name not in _KNOWN_MUTATING_TOOLS:
        return _fingerprint_result(
            project_id=project_id,
            tool_name=tool_name,
            mutating=False,
            status="not_mutating",
            action=tool_name,
            target_type=None,
            target_id=None,
            diagnostics=[],
        )

    target = _target_for_tool(project_id, tool_name, params)
    if target["status"] != "ready":
        return _fingerprint_result(
            project_id=project_id,
            tool_name=tool_name,
            mutating=True,
            status="blocked",
            action=tool_name,
            target_type=target.get("target_type"),
            target_id=target.get("target_id"),
            diagnostics=target["diagnostics"],
        )

    return _fingerprint_result(
        project_id=project_id,
        tool_name=tool_name,
        mutating=True,
        status="ready",
        action=tool_name,
        target_type=target["target_type"],
        target_id=target["target_id"],
        diagnostics=[],
    )


def _target_for_tool(project_id: str, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    if tool_name in {"execute_generate_setup_with_approval", "generate_setup"}:
        project_target = _clean_string(project_id)
        if not project_target:
            return _blocked("setup", "missing_target", f"{tool_name} requires project_id")
        return _ready("setup", f"setup:{project_target}")

    if tool_name in {"execute_generate_storyline_with_approval", "generate_storyline"}:
        project_target = _clean_string(project_id)
        if not project_target:
            return _blocked("storyline", "missing_target", f"{tool_name} requires project_id")
        return _ready("storyline", f"storyline:{project_target}")

    if tool_name in {"execute_generate_outline_with_approval", "generate_outline"}:
        project_target = _clean_string(project_id)
        if not project_target:
            return _blocked("outline", "missing_target", f"{tool_name} requires project_id")
        return _ready("outline", f"outline:{project_target}")

    if tool_name == "generate_chapter":
        chapter_index = _positive_int(params.get("chapter_index"))
        if chapter_index is None:
            return _blocked("chapter", "missing_target", "generate_chapter requires a positive chapter_index")
        return _ready("chapter", f"chapter:{chapter_index}")

    if tool_name == "generate_chapter_range":
        chapter_range = params.get("chapter_range") if isinstance(params.get("chapter_range"), dict) else {}
        start = _positive_int(
            params.get("start_chapter")
            or params.get("start_chapter_index")
            or params.get("start")
            or chapter_range.get("start_chapter")
            or chapter_range.get("start")
        )
        end = _positive_int(
            params.get("end_chapter")
            or params.get("end_chapter_index")
            or params.get("end")
            or chapter_range.get("end_chapter")
            or chapter_range.get("end")
        )
        if start is None or end is None or end < start:
            return _blocked("chapter_range", "missing_target", "generate_chapter_range requires a valid start/end range")
        return _ready("chapter_range", f"chapters:{start}-{end}")

    if tool_name == "apply_world_model_proposal_resolution":
        bundle_id = _clean_string(params.get("proposal_bundle_id") or params.get("bundle_id"))
        if bundle_id:
            return _ready("world_model_proposal_bundle", f"world_model_proposal_bundle:{bundle_id}")

        plan_id = _clean_string(params.get("plan_id"))
        if plan_id:
            return _ready("world_model_proposal_plan", f"world_model_proposal_plan:{plan_id}")

        decision_target = _decision_target_id(params.get("decisions"))
        if decision_target:
            return _ready("world_model_proposal_decisions", decision_target)

        return _blocked(
            "world_model_proposal_bundle",
            "missing_target",
            "apply_world_model_proposal_resolution requires a proposal bundle, plan, or decision target",
        )

    return _blocked(None, "unsupported_tool", f"{tool_name} is not supported by mutation fingerprinting")


def _fingerprint_result(
    *,
    project_id: str,
    tool_name: str,
    mutating: bool,
    status: str,
    action: str,
    target_type: str | None,
    target_id: str | None,
    diagnostics: list[dict[str, str]],
) -> dict[str, Any]:
    components = {
        "version": MUTATION_FINGERPRINT_VERSION,
        "project_id": project_id,
        "tool_name": tool_name,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
    }
    fingerprint = _sha256(components) if status == "ready" and target_id else None
    return {
        "status": status,
        "tool_name": tool_name,
        "mutating": mutating,
        "fingerprint": fingerprint,
        "components": components,
        "diagnostics": diagnostics,
    }


def _decision_target_id(decisions: object) -> str | None:
    if not isinstance(decisions, list):
        return None
    normalized: list[dict[str, str]] = []
    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        proposal_item_id = _clean_string(decision.get("proposal_item_id"))
        action = _clean_string(decision.get("action"))
        if proposal_item_id:
            normalized.append({"proposal_item_id": proposal_item_id, "action": action or ""})
    if not normalized:
        return None
    digest = _sha256(sorted(normalized, key=lambda item: (item["proposal_item_id"], item["action"])))[:16]
    return f"world_model_proposal_decisions:{digest}"


def _sha256(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _ready(target_type: str, target_id: str) -> dict[str, Any]:
    return {"status": "ready", "target_type": target_type, "target_id": target_id, "diagnostics": []}


def _blocked(target_type: str | None, code: str, message: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "target_type": target_type,
        "target_id": None,
        "diagnostics": [{"code": code, "message": message}],
    }


def _positive_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _clean_string(value: object) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None

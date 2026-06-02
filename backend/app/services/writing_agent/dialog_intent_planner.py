from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy.orm import Session

from app.core.intent_router import IntentRouter
from app.schemas import ProjectDiagnosisOut
from app.services.workspace.bootstrap import build_project_diagnosis
from app.services.writing_agent.planner import (
    CHAPTER_GENERATION_ROUTE_APPROVED_PREPARE,
    build_writing_agent_run_plan,
)
from app.services.writing_agent.reference_pattern_projection import (
    REFERENCE_PATTERN_PROJECTION_VERSION,
    build_reference_pattern_projection,
)

DIALOG_INTENT_AGENT_PLAN_VERSION = "phase106.dialog_intent_agent_plan.v1"

_ACTION_TO_PLANNER_INTENT = {
    "preview_setup": "setup_project",
    "preview_storyline": "build_storyline",
    "preview_outline": "build_outline",
    "preview_chapter": "continue_next_chapter",
    "preview_review": "review_chapter",
    "preview_recovery": "recover_blocked_run",
}
_ACTION_TO_CHAPTER_GENERATION_ROUTE = {
    "preview_chapter": CHAPTER_GENERATION_ROUTE_APPROVED_PREPARE,
}
_ACTION_TO_DIRECT_READ_TOOL = {
    "inspect_agent_health": "inspect_agent_health_projection",
    "inspect_control_plane_readiness": "inspect_agent_control_plane_readiness",
    "inspect_memory_tree": "inspect_agent_memory_tree",
    "inspect_context_compression": "inspect_agent_context_compression_projection",
    "inspect_worker_dispatch": "inspect_agent_worker_dispatch",
    "inspect_trace_audit": "inspect_agent_trace_audit",
    "inspect_write_gate_coverage": "inspect_agent_write_gate_coverage",
    "inspect_tool_contracts": "inspect_agent_tool_contracts",
}


def plan_dialog_intent_agent_run(
    db: Session,
    project_id: str,
    *,
    text: str,
    dialog_state: str = "chatting",
    pending_action_id: str | None = None,
    diagnosis: ProjectDiagnosisOut | None = None,
) -> dict[str, Any]:
    resolved_diagnosis = diagnosis or build_project_diagnosis(db, project_id)
    intent_projection = IntentRouter().project(
        text,
        dialog_state,
        pending_action_id,
        resolved_diagnosis,
    ).to_dict()
    projection_id = str(intent_projection.get("trace", {}).get("projection_id") or "")
    candidate = intent_projection.get("candidate") if isinstance(intent_projection.get("candidate"), dict) else None
    action_type = str(candidate.get("type") or "").strip() if candidate else ""
    planner_intent = _ACTION_TO_PLANNER_INTENT.get(action_type)
    direct_read_tool = _ACTION_TO_DIRECT_READ_TOOL.get(action_type)

    if not candidate:
        return _empty_plan(
            status="no_plan",
            reason="intent_not_matched",
            intent_projection=intent_projection,
            projection_id=projection_id,
        )
    if direct_read_tool:
        return _direct_read_tool_plan(
            action_type=action_type,
            tool_name=direct_read_tool,
            params=candidate.get("params") if isinstance(candidate.get("params"), dict) else {},
            intent_projection=intent_projection,
            projection_id=projection_id,
        )
    if not planner_intent:
        return _empty_plan(
            status="blocked",
            reason="unsupported_dialog_action_for_agent_plan",
            intent_projection=intent_projection,
            projection_id=projection_id,
            action_type=action_type,
        )

    params = candidate.get("params") if isinstance(candidate.get("params"), dict) else {}
    chapter_index = _optional_int(params.get("chapter_index"))
    plan_id = _plan_id(project_id, projection_id, planner_intent, chapter_index)
    plan = build_writing_agent_run_plan(
        db,
        project_id,
        goal=text,
        chapter_index=chapter_index,
        intent=planner_intent,
        source_projection_id=projection_id,
        source_plan_id=plan_id,
        chapter_generation_route=_ACTION_TO_CHAPTER_GENERATION_ROUTE.get(action_type),
    )
    return {
        "status": plan.get("status"),
        "version": DIALOG_INTENT_AGENT_PLAN_VERSION,
        "project_id": project_id,
        "intent_projection": intent_projection,
        "planner": {
            "plan_id": plan_id,
            "intent_class": plan.get("intent_class"),
            "planner_version": plan.get("planner_version"),
            "mapped_from_action_type": action_type,
            "mapped_from_rule_id": intent_projection.get("rule_id"),
            "chapter_index": plan.get("chapter_index"),
            "chapter_generation_route": plan.get("trace", {}).get("chapter_generation_route"),
        },
        "plan": plan,
        "tools": list(plan.get("tools") or []),
        "approval_contract": plan.get("approval_contract"),
        "trace": {
            "reason": "planned_from_intent_projection",
            "projection_id": projection_id,
            "plan_id": plan_id,
            "selected_tool": intent_projection.get("tool_selection", {}).get("selected_tool"),
            "missing_dependencies": plan.get("trace", {}).get("missing_dependencies", []),
            "risk_flags": plan.get("trace", {}).get("risk_flags", []),
            "reference_pattern_version": REFERENCE_PATTERN_PROJECTION_VERSION,
            "reference_patterns": build_reference_pattern_projection(),
        },
    }


def _direct_read_tool_plan(
    *,
    action_type: str,
    tool_name: str,
    params: dict[str, Any],
    intent_projection: dict[str, Any],
    projection_id: str,
) -> dict[str, Any]:
    planner_intent = action_type
    tool_request = {"tool_name": tool_name, "params": dict(params)}
    plan = {
        "status": "completed",
        "intent_class": planner_intent,
        "steps": [
            {
                "step_index": 1,
                "tool_name": tool_name,
                "params": dict(params),
                "mutability": "read",
                "requires_confirmation": False,
            }
        ],
        "tools": [tool_request],
        "approval_contract": {"status": "not_required", "write_steps": []},
    }
    return {
        "status": "completed",
        "version": DIALOG_INTENT_AGENT_PLAN_VERSION,
        "intent_projection": intent_projection,
        "planner": {
            "plan_id": None,
            "intent_class": planner_intent,
            "mapped_from_action_type": action_type,
            "mapped_from_rule_id": intent_projection.get("rule_id"),
            "chapter_index": _optional_int(params.get("chapter_index")),
        },
        "plan": plan,
        "tools": [tool_request],
        "approval_contract": plan["approval_contract"],
        "trace": {
            "reason": "planned_direct_read_tool_from_intent_projection",
            "projection_id": projection_id,
            "plan_id": None,
            "selected_tool": tool_name,
            "missing_dependencies": [],
            "risk_flags": [],
            "reference_pattern_version": REFERENCE_PATTERN_PROJECTION_VERSION,
            "reference_patterns": build_reference_pattern_projection(),
        },
    }


def project_diagnosis_from_params(params: dict[str, Any]) -> ProjectDiagnosisOut | None:
    if "missing_items" not in params and "completed_items" not in params and "suggested_next_step" not in params:
        return None
    return ProjectDiagnosisOut(
        missing_items=_string_list(params.get("missing_items")),
        completed_items=_string_list(params.get("completed_items")),
        suggested_next_step=str(params.get("suggested_next_step") or "").strip() or None,
    )


def _empty_plan(
    *,
    status: str,
    reason: str,
    intent_projection: dict[str, Any],
    projection_id: str,
    action_type: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "version": DIALOG_INTENT_AGENT_PLAN_VERSION,
        "intent_projection": intent_projection,
        "planner": {
            "plan_id": None,
            "intent_class": None,
            "mapped_from_action_type": action_type,
            "mapped_from_rule_id": intent_projection.get("rule_id"),
            "chapter_index": None,
        },
        "plan": None,
        "tools": [],
        "trace": {
            "reason": reason,
            "projection_id": projection_id,
            "plan_id": None,
            "selected_tool": intent_projection.get("tool_selection", {}).get("selected_tool"),
            "missing_dependencies": [],
            "risk_flags": [reason] if status == "blocked" else [],
        },
    }


def _plan_id(project_id: str, projection_id: str, planner_intent: str, chapter_index: int | None) -> str:
    source = f"{project_id}:{projection_id}:{planner_intent}:{chapter_index or ''}"
    return f"plan:{hashlib.sha256(source.encode('utf-8')).hexdigest()[:16]}"


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    cleaned = str(value).strip()
    return [cleaned] if cleaned else []

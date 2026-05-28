from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Project
from app.services.writing_agent.agent_knowledge_base_candidates import record_agent_knowledge_base_candidate
from app.services.writing_agent.agent_step_binding import build_agent_step_binding, verify_resource_binding_target
from app.services.writing_agent.approval_contract import (
    build_agent_plan_approval_contract,
    verify_agent_plan_approval_contract,
)
from app.services.writing_agent.approval_verification_event import build_approval_verification_event
from app.services.writing_agent.mutation_fingerprint import build_mutation_fingerprint

PREPARE_RECORD_KNOWLEDGE_BASE_CANDIDATE_VERSION = "phase189.knowledge_base_candidate_prepare.v1"
EXECUTE_RECORD_KNOWLEDGE_BASE_CANDIDATE_WITH_APPROVAL_VERSION = (
    "phase189.knowledge_base_candidate_with_approval_execute.v1"
)
APPROVAL_GATE_VERSION = "phase189.knowledge_base_candidate_agent_plan_approval.v1"
_APPROVAL_PARAM_NAMES = {"confirm_execute", "approval_contract_hash", "approval_contract"}


def prepare_record_agent_knowledge_base_candidate(
    db: Session,
    project_id: str,
    *,
    action_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}

    agent_plan = _record_knowledge_base_candidate_agent_plan(project_id, action_params)
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    return {
        "status": "approval_required",
        "prepare_version": PREPARE_RECORD_KNOWLEDGE_BASE_CANDIDATE_VERSION,
        "project_id": project_id,
        "target_type": "agent_knowledge_base_candidate",
        "mutation_fingerprint": first_step.get("mutation_fingerprint"),
        "tool_call_id": first_step.get("tool_call_id"),
        "resource_binding": first_step.get("resource_binding"),
        "agent_plan": agent_plan,
        "agent_plan_approval_contract": approval_contract,
        "agent_plan_approval_contract_hash": approval_hash,
        "required_confirmation": {
            "confirm_execute": True,
            "approval_contract_hash": approval_hash,
        },
        "side_effects": {"executed": [], "skipped": ["record_agent_knowledge_base_candidate"]},
        "recommended_next_tools": ["execute_record_agent_knowledge_base_candidate_with_approval"],
        "trace": {
            "selected_tools": ["prepare_record_agent_knowledge_base_candidate"],
            "rejected_tools": [
                {"tool_name": "record_agent_knowledge_base_candidate", "reason": "approval_required_before_write"}
            ],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def execute_record_agent_knowledge_base_candidate_with_approval(
    db: Session,
    project_id: str,
    *,
    confirm_execute: bool,
    approval_contract_hash: str | None,
    approval_contract: dict[str, Any] | None,
    approval_tool_metadata_provider,
    action_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}
    if confirm_execute is not True:
        return _blocked_output(project_id, reason="confirmation_required")
    if not approval_contract_hash or not isinstance(approval_contract, dict):
        return _blocked_output(project_id, reason="approval_contract_required")
    if approval_tool_metadata_provider is None:
        return _blocked_output(project_id, reason="agent_plan_tool_metadata_missing")

    agent_plan = _record_knowledge_base_candidate_agent_plan(project_id, action_params)
    verification = verify_agent_plan_approval_contract(
        agent_plan,
        approval_contract_hash=approval_contract_hash,
        approval_contract=approval_contract,
        project_id=project_id,
        tool_metadata_by_name=approval_tool_metadata_provider(agent_plan),
    )
    if verification.get("status") != "ready":
        return _blocked_output(
            project_id,
            reason=str(verification.get("reason") or "agent_plan_approval_not_ready"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
            },
        )

    target_id = _target_id_from_plan(agent_plan)
    binding_check = verify_resource_binding_target(
        verification,
        tool_name="record_agent_knowledge_base_candidate",
        target_type="agent_knowledge_base_candidate",
        target_id=target_id,
    )
    if binding_check.get("status") != "ready":
        return _blocked_output(
            project_id,
            reason=str(binding_check.get("reason") or "resource_binding_target_mismatch"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
                "execution_resource_binding": binding_check,
            },
        )

    params = _candidate_action_params(action_params)
    record_result = record_agent_knowledge_base_candidate(
        db,
        project_id,
        memory_type=str(params.get("memory_type") or ""),
        title=str(params.get("title") or ""),
        summary=str(params.get("summary") or ""),
        source_refs=list(params.get("source_refs") or []),
        confidence=params.get("confidence") if isinstance(params.get("confidence"), float) else None,
        status=str(params.get("status") or "").strip() or None,
        tags=list(params.get("tags") or []),
    )
    if record_result.get("status") != "completed":
        return _blocked_output(
            project_id,
            reason="knowledge_base_candidate_record_failed",
            extra={
                "record_result": record_result,
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
                "execution_resource_binding": binding_check,
            },
        )

    return {
        "status": "success",
        "execute_version": EXECUTE_RECORD_KNOWLEDGE_BASE_CANDIDATE_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "target_type": "agent_knowledge_base_candidate",
        "action": record_result.get("action"),
        "candidate": record_result.get("candidate"),
        "candidate_count": record_result.get("candidate_count"),
        "agent_plan_approval_verification": verification,
        "approval_verification_event": build_approval_verification_event(verification),
        "execution_resource_binding": binding_check,
        "evidence": {
            "agent_plan_approval_verified": True,
            "legacy_action": "record_agent_knowledge_base_candidate",
            "execution_route": "static_adapter",
        },
        "side_effects": {"executed": ["record_agent_knowledge_base_candidate"], "skipped": []},
        "recommended_next_tools": ["inspect_agent_knowledge_base_route"],
        "trace": {
            "selected_tools": ["execute_record_agent_knowledge_base_candidate_with_approval"],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }


def _record_knowledge_base_candidate_agent_plan(
    project_id: str,
    action_params: dict[str, Any] | None,
) -> dict[str, Any]:
    params = _candidate_action_params(action_params)
    mutation_fingerprint = build_mutation_fingerprint(project_id, "record_agent_knowledge_base_candidate", params)
    target_suffix = str(mutation_fingerprint.get("fingerprint") or "pending")[:16]
    plan_id = f"knowledge-base-candidate:{project_id}:{target_suffix}"
    step = {
        "step_index": 1,
        "step_id": plan_id,
        "tool_name": "record_agent_knowledge_base_candidate",
        "approval_executor_tool_name": "execute_record_agent_knowledge_base_candidate_with_approval",
        "params": params,
        "mutability": "write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": "记录长期写作知识库候选项，沉淀作者偏好、写法模式或自优化经验。",
    }
    step.update(
        build_agent_step_binding(
            project_id=project_id,
            plan_id=plan_id,
            source_projection_id=None,
            step=step,
            mutation_fingerprint=mutation_fingerprint,
        )
    )
    return {
        "project_id": project_id,
        "intent_class": "record_agent_knowledge_base_candidate",
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": None,
            "planner_version": PREPARE_RECORD_KNOWLEDGE_BASE_CANDIDATE_VERSION,
        },
        "steps": [step],
    }


def _candidate_action_params(action_params: dict[str, Any] | None) -> dict[str, Any]:
    raw = {key: value for key, value in (action_params or {}).items() if key not in _APPROVAL_PARAM_NAMES}
    params: dict[str, Any] = {
        "memory_type": str(raw.get("memory_type") or "").strip(),
        "title": str(raw.get("title") or "").strip(),
        "summary": str(raw.get("summary") or "").strip(),
        "source_refs": _string_list(raw.get("source_refs")),
    }
    confidence = _optional_float(raw.get("confidence"))
    if confidence is not None:
        params["confidence"] = confidence
    status = str(raw.get("status") or "").strip()
    if status:
        params["status"] = status
    tags = _string_list(raw.get("tags"))
    if tags:
        params["tags"] = tags
    return params


def _target_id_from_plan(agent_plan: dict[str, Any]) -> str:
    step = agent_plan["steps"][0]
    fingerprint = step.get("mutation_fingerprint") if isinstance(step.get("mutation_fingerprint"), dict) else {}
    components = fingerprint.get("components") if isinstance(fingerprint.get("components"), dict) else {}
    return str(components.get("target_id") or "")


def _blocked_output(
    project_id: str,
    *,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = {
        "status": "blocked",
        "execute_version": EXECUTE_RECORD_KNOWLEDGE_BASE_CANDIDATE_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "target_type": "agent_knowledge_base_candidate",
        "reason": reason,
        "side_effects": {"executed": [], "skipped": ["record_agent_knowledge_base_candidate"]},
        "recommended_next_tools": ["prepare_record_agent_knowledge_base_candidate"],
        "trace": {
            "selected_tools": ["execute_record_agent_knowledge_base_candidate_with_approval"],
            "rejected_tools": [{"tool_name": "record_agent_knowledge_base_candidate", "reason": reason}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }
    if extra:
        output.update(extra)
    return output


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    cleaned = str(value or "").strip()
    return [cleaned] if cleaned else []

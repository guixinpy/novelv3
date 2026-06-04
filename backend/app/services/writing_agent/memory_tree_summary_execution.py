from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import Project
from app.services.writing_agent.agent_step_binding import build_agent_step_binding, verify_resource_binding_target
from app.services.writing_agent.approval_contract import (
    build_agent_plan_approval_contract,
    verify_agent_plan_approval_contract,
)
from app.services.writing_agent.approval_verification_event import build_approval_verification_event
from app.services.writing_agent.memory_tree import (
    inspect_agent_memory_tree_llm_candidate_trace,
    inspect_agent_memory_tree_quality,
    materialize_agent_memory_tree_llm_candidate_summary,
    materialize_agent_memory_tree_summaries,
)
from app.services.writing_agent.mutation_fingerprint import build_mutation_fingerprint

PREPARE_RECORD_MEMORY_TREE_SUMMARIES_VERSION = "phase246.memory_tree_summary_prepare.v1"
EXECUTE_RECORD_MEMORY_TREE_SUMMARIES_WITH_APPROVAL_VERSION = (
    "phase246.memory_tree_summary_with_approval_execute.v1"
)
PREPARE_RECORD_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_VERSION = (
    "phase250.memory_tree_llm_candidate_summary_prepare.v1"
)
EXECUTE_RECORD_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_WITH_APPROVAL_VERSION = (
    "phase250.memory_tree_llm_candidate_summary_with_approval_execute.v1"
)
APPROVAL_GATE_VERSION = "phase246.memory_tree_summary_agent_plan_approval.v1"
LLM_CANDIDATE_APPROVAL_GATE_VERSION = "phase250.memory_tree_llm_candidate_summary_agent_plan_approval.v1"
TARGET_TYPE = "agent_memory_tree_summary"
CANDIDATE_TARGET_TYPE = "agent_memory_tree_llm_candidate_summary"
RECORD_TOOL = "record_agent_memory_tree_summaries"
CANDIDATE_RECORD_TOOL = "record_agent_memory_tree_llm_candidate_summary"
PREPARE_TOOL = "prepare_record_agent_memory_tree_summaries"
EXECUTE_TOOL = "execute_record_agent_memory_tree_summaries_with_approval"
CANDIDATE_PREPARE_TOOL = "prepare_record_agent_memory_tree_llm_candidate_summary"
CANDIDATE_EXECUTE_TOOL = "execute_record_agent_memory_tree_llm_candidate_summary_with_approval"
_APPROVAL_PARAM_NAMES = {
    "confirm_execute",
    "approval_contract_hash",
    "approval_contract",
    "post_approval_continuation_tools",
}


def prepare_record_agent_memory_tree_llm_candidate_summary(
    db: Session,
    project_id: str,
    *,
    action_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}

    candidate_params = _candidate_action_params(db, project_id, action_params)
    if candidate_params["status"] != "ready":
        return _blocked_candidate_prepare_output(
            project_id,
            reason=str(candidate_params.get("reason") or "candidate_summary_not_ready"),
            candidate_summary=candidate_params.get("candidate_summary"),
        )

    record_params = candidate_params["record_params"]
    quality_params = candidate_params["quality_params"]
    agent_plan = _memory_tree_llm_candidate_summary_agent_plan(project_id, record_params)
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    post_approval_continuation_tools = _post_approval_continuation_tools(action_params)
    return _json_safe_output(
        {
            "status": "approval_required",
            "prepare_version": PREPARE_RECORD_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_VERSION,
            "project_id": project_id,
            "target_type": CANDIDATE_TARGET_TYPE,
            "candidate_summary": candidate_params["candidate_summary"],
            "summary_plan": {
                "candidate_trace_id": record_params.get("candidate_trace_id"),
                "chapter_index": record_params.get("chapter_index"),
                "summary_scope_key": record_params.get("summary_scope_key"),
                "quality_chapter_index": quality_params.get("chapter_index"),
                "quality_query": quality_params.get("query"),
            },
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
            "side_effects": {"executed": [], "skipped": [CANDIDATE_RECORD_TOOL]},
            "recommended_next_tools": [CANDIDATE_EXECUTE_TOOL],
            "post_approval_continuation_tools": post_approval_continuation_tools,
            "trace": {
                "selected_tools": [CANDIDATE_PREPARE_TOOL],
                "rejected_tools": [
                    {"tool_name": CANDIDATE_RECORD_TOOL, "reason": "approval_required_before_write"}
                ],
                "approval_gate_version": LLM_CANDIDATE_APPROVAL_GATE_VERSION,
                "post_approval_continuation_count": len(post_approval_continuation_tools),
            },
        }
    )


def execute_record_agent_memory_tree_llm_candidate_summary_with_approval(
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
        return _blocked_candidate_execute_output(project_id, reason="confirmation_required")
    if not approval_contract_hash or not isinstance(approval_contract, dict):
        return _blocked_candidate_execute_output(project_id, reason="approval_contract_required")
    if approval_tool_metadata_provider is None:
        return _blocked_candidate_execute_output(project_id, reason="agent_plan_tool_metadata_missing")

    candidate_params = _candidate_action_params(db, project_id, action_params)
    if candidate_params["status"] != "ready":
        return _blocked_candidate_execute_output(
            project_id,
            reason=str(candidate_params.get("reason") or "candidate_summary_not_ready"),
            extra={"candidate_summary": candidate_params.get("candidate_summary")},
        )

    record_params = candidate_params["record_params"]
    quality_params = candidate_params["quality_params"]
    agent_plan = _memory_tree_llm_candidate_summary_agent_plan(project_id, record_params)
    verification = verify_agent_plan_approval_contract(
        agent_plan,
        approval_contract_hash=approval_contract_hash,
        approval_contract=approval_contract,
        project_id=project_id,
        tool_metadata_by_name=approval_tool_metadata_provider(agent_plan),
    )
    if verification.get("status") != "ready":
        return _blocked_candidate_execute_output(
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
        tool_name=CANDIDATE_RECORD_TOOL,
        target_type=CANDIDATE_TARGET_TYPE,
        target_id=target_id,
    )
    if binding_check.get("status") != "ready":
        return _blocked_candidate_execute_output(
            project_id,
            reason=str(binding_check.get("reason") or "resource_binding_target_mismatch"),
            extra={
                "agent_plan_approval_verification": verification,
                "approval_verification_event": build_approval_verification_event(verification),
                "execution_resource_binding": binding_check,
            },
        )

    materialization = materialize_agent_memory_tree_llm_candidate_summary(
        db,
        project_id,
        candidate_trace_id=record_params.get("candidate_trace_id"),
    )
    if materialization.get("status") != "completed":
        return _blocked_candidate_execute_output(
            project_id,
            reason=str(materialization.get("reason") or "candidate_materialization_failed"),
            extra={"materialization": materialization},
        )
    quality = inspect_agent_memory_tree_quality(
        db,
        project_id,
        chapter_index=quality_params.get("chapter_index"),
        query=quality_params.get("query"),
    )
    post_approval_continuation_tools = _post_approval_continuation_tools(action_params)
    recommended_next_tools = _continuation_tool_names(post_approval_continuation_tools) or [
        "inspect_agent_memory_tree_quality"
    ]
    return _json_safe_output(
        {
            "status": "success",
            "execute_version": EXECUTE_RECORD_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_WITH_APPROVAL_VERSION,
            "project_id": project_id,
            "target_type": CANDIDATE_TARGET_TYPE,
            "materialization": materialization,
            "post_materialization_quality": quality,
            "agent_plan_approval_verification": verification,
            "approval_verification_event": build_approval_verification_event(verification),
            "execution_resource_binding": binding_check,
            "evidence": {
                "agent_plan_approval_verified": True,
                "legacy_action": CANDIDATE_RECORD_TOOL,
                "execution_route": "static_adapter",
            },
            "side_effects": {"executed": [CANDIDATE_RECORD_TOOL], "skipped": []},
            "recommended_next_tools": recommended_next_tools,
            "post_approval_continuation_tools": post_approval_continuation_tools,
            "trace": {
                "selected_tools": [CANDIDATE_EXECUTE_TOOL],
                "approval_gate_version": LLM_CANDIDATE_APPROVAL_GATE_VERSION,
                "post_approval_continuation_count": len(post_approval_continuation_tools),
            },
        }
    )


def prepare_record_agent_memory_tree_summaries(
    db: Session,
    project_id: str,
    *,
    action_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return {"status": "failed", "error": "Project not found", "project_id": project_id}

    summary_params, quality_params = _summary_action_params(action_params)
    agent_plan = _memory_tree_summary_agent_plan(project_id, summary_params)
    approval_contract = build_agent_plan_approval_contract(agent_plan)
    approval_hash = str(((approval_contract.get("approval") or {}).get("approval_contract_hash")) or "")
    first_step = agent_plan["steps"][0]
    post_approval_continuation_tools = _post_approval_continuation_tools(action_params)
    return _json_safe_output(
        {
            "status": "approval_required",
            "prepare_version": PREPARE_RECORD_MEMORY_TREE_SUMMARIES_VERSION,
            "project_id": project_id,
            "target_type": TARGET_TYPE,
            "summary_plan": {
                "chapter_index": summary_params.get("chapter_index"),
                "quality_chapter_index": quality_params.get("chapter_index"),
                "quality_query": quality_params.get("query"),
            },
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
            "side_effects": {"executed": [], "skipped": [RECORD_TOOL]},
            "recommended_next_tools": [EXECUTE_TOOL],
            "post_approval_continuation_tools": post_approval_continuation_tools,
            "trace": {
                "selected_tools": [PREPARE_TOOL],
                "rejected_tools": [{"tool_name": RECORD_TOOL, "reason": "approval_required_before_write"}],
                "approval_gate_version": APPROVAL_GATE_VERSION,
                "post_approval_continuation_count": len(post_approval_continuation_tools),
            },
        }
    )


def execute_record_agent_memory_tree_summaries_with_approval(
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

    summary_params, quality_params = _summary_action_params(action_params)
    agent_plan = _memory_tree_summary_agent_plan(project_id, summary_params)
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
        tool_name=RECORD_TOOL,
        target_type=TARGET_TYPE,
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

    materialization = materialize_agent_memory_tree_summaries(
        db,
        project_id,
        chapter_index=summary_params.get("chapter_index"),
    )
    quality = inspect_agent_memory_tree_quality(
        db,
        project_id,
        chapter_index=quality_params.get("chapter_index"),
        query=quality_params.get("query"),
    )
    post_approval_continuation_tools = _post_approval_continuation_tools(action_params)
    recommended_next_tools = _continuation_tool_names(post_approval_continuation_tools) or [
        "inspect_agent_memory_tree_quality"
    ]
    return _json_safe_output(
        {
            "status": "success",
            "execute_version": EXECUTE_RECORD_MEMORY_TREE_SUMMARIES_WITH_APPROVAL_VERSION,
            "project_id": project_id,
            "target_type": TARGET_TYPE,
            "materialization": materialization,
            "post_materialization_quality": quality,
            "agent_plan_approval_verification": verification,
            "approval_verification_event": build_approval_verification_event(verification),
            "execution_resource_binding": binding_check,
            "evidence": {
                "agent_plan_approval_verified": True,
                "legacy_action": RECORD_TOOL,
                "execution_route": "static_adapter",
            },
            "side_effects": {"executed": [RECORD_TOOL], "skipped": []},
            "recommended_next_tools": recommended_next_tools,
            "post_approval_continuation_tools": post_approval_continuation_tools,
            "trace": {
                "selected_tools": [EXECUTE_TOOL],
                "approval_gate_version": APPROVAL_GATE_VERSION,
                "post_approval_continuation_count": len(post_approval_continuation_tools),
            },
        }
    )


def _memory_tree_summary_agent_plan(project_id: str, params: dict[str, Any]) -> dict[str, Any]:
    mutation_fingerprint = build_mutation_fingerprint(project_id, RECORD_TOOL, params)
    target_suffix = str(mutation_fingerprint.get("fingerprint") or "pending")[:16]
    plan_id = f"memory-tree-summary:{project_id}:{target_suffix}"
    step = {
        "step_index": 1,
        "step_id": plan_id,
        "tool_name": RECORD_TOOL,
        "approval_executor_tool_name": EXECUTE_TOOL,
        "params": params,
        "mutability": "write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": "Materialize Memory Tree volume/chapter summary nodes into LongformMemory.",
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
        "intent_class": RECORD_TOOL,
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": None,
            "planner_version": PREPARE_RECORD_MEMORY_TREE_SUMMARIES_VERSION,
        },
        "steps": [step],
    }


def _memory_tree_llm_candidate_summary_agent_plan(project_id: str, params: dict[str, Any]) -> dict[str, Any]:
    mutation_fingerprint = build_mutation_fingerprint(project_id, CANDIDATE_RECORD_TOOL, params)
    target_suffix = str(mutation_fingerprint.get("fingerprint") or "pending")[:16]
    candidate_trace_id = _clean_string(params.get("candidate_trace_id")) or "missing"
    plan_id = f"memory-tree-llm-candidate-summary:{project_id}:{target_suffix}"
    step = {
        "step_index": 1,
        "step_id": f"{plan_id}:{candidate_trace_id}",
        "tool_name": CANDIDATE_RECORD_TOOL,
        "approval_executor_tool_name": CANDIDATE_EXECUTE_TOOL,
        "params": params,
        "mutability": "write",
        "requires_confirmation": True,
        "mutation_fingerprint": mutation_fingerprint,
        "reason": "Materialize an approved Memory Tree LLM candidate summary into LongformMemory.",
    }
    step.update(
        build_agent_step_binding(
            project_id=project_id,
            plan_id=plan_id,
            source_projection_id=candidate_trace_id,
            step=step,
            mutation_fingerprint=mutation_fingerprint,
        )
    )
    return {
        "project_id": project_id,
        "intent_class": CANDIDATE_RECORD_TOOL,
        "trace": {
            "plan_id": plan_id,
            "source_projection_id": candidate_trace_id,
            "planner_version": PREPARE_RECORD_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_VERSION,
        },
        "steps": [step],
    }


def _summary_action_params(action_params: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = {key: value for key, value in (action_params or {}).items() if key not in _APPROVAL_PARAM_NAMES}
    chapter_index = _positive_int(raw.get("chapter_index"))
    quality_chapter_index = _positive_int(raw.get("quality_chapter_index") or raw.get("chapter_index"))
    quality_query = _clean_string(raw.get("quality_query") or raw.get("query"))
    summary_params: dict[str, Any] = {}
    if chapter_index is not None:
        summary_params["chapter_index"] = chapter_index
    return summary_params, {"chapter_index": quality_chapter_index, "query": quality_query}


def _candidate_action_params(
    db: Session,
    project_id: str,
    action_params: dict[str, Any] | None,
) -> dict[str, Any]:
    raw = {key: value for key, value in (action_params or {}).items() if key not in _APPROVAL_PARAM_NAMES}
    candidate_trace_id = _clean_string(raw.get("candidate_trace_id") or raw.get("trace_id"))
    candidate_summary = inspect_agent_memory_tree_llm_candidate_trace(
        db,
        project_id,
        candidate_trace_id=candidate_trace_id,
    )
    if candidate_summary.get("status") != "ready":
        return {
            "status": "blocked",
            "reason": candidate_summary.get("reason"),
            "candidate_summary": candidate_summary,
        }
    summary_target = candidate_summary["summary_target"]
    chapter_index = _positive_int(summary_target.get("chapter_index"))
    quality_chapter_index = _positive_int(raw.get("quality_chapter_index") or raw.get("chapter_index")) or chapter_index
    quality_query = _clean_string(raw.get("quality_query") or raw.get("query"))
    return {
        "status": "ready",
        "candidate_summary": candidate_summary,
        "record_params": {
            "candidate_trace_id": candidate_summary["candidate_trace_id"],
            "chapter_index": chapter_index,
            "summary_scope_key": summary_target.get("scope_key"),
            "candidate_summary_hash": candidate_summary["candidate_summary_hash"],
        },
        "quality_params": {"chapter_index": quality_chapter_index, "query": quality_query},
    }


def _target_id_from_plan(agent_plan: dict[str, Any]) -> str:
    step = agent_plan["steps"][0]
    fingerprint = step.get("mutation_fingerprint") if isinstance(step.get("mutation_fingerprint"), dict) else {}
    components = fingerprint.get("components") if isinstance(fingerprint.get("components"), dict) else {}
    return str(components.get("target_id") or "")


def _post_approval_continuation_tools(action_params: dict[str, Any] | None) -> list[dict[str, Any]]:
    raw_tools = (action_params or {}).get("post_approval_continuation_tools")
    if not isinstance(raw_tools, list):
        return []
    tools: list[dict[str, Any]] = []
    for item in raw_tools:
        if not isinstance(item, dict):
            continue
        tool_name = _clean_string(item.get("tool_name"))
        if not tool_name:
            continue
        params = item.get("params") if isinstance(item.get("params"), dict) else {}
        tool: dict[str, Any] = {"tool_name": tool_name, "params": dict(params)}
        for field in ("reason", "expected_output"):
            value = _clean_string(item.get(field))
            if value:
                tool[field] = value
        tools.append(tool)
    return _json_safe_output({"tools": tools})["tools"]


def _continuation_tool_names(tools: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    names: list[str] = []
    for tool in tools:
        tool_name = _clean_string(tool.get("tool_name"))
        if not tool_name or tool_name in seen:
            continue
        seen.add(tool_name)
        names.append(tool_name)
    return names


def _blocked_output(
    project_id: str,
    *,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = {
        "status": "blocked",
        "execute_version": EXECUTE_RECORD_MEMORY_TREE_SUMMARIES_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "target_type": TARGET_TYPE,
        "reason": reason,
        "side_effects": {"executed": [], "skipped": [RECORD_TOOL]},
        "recommended_next_tools": [PREPARE_TOOL],
        "trace": {
            "selected_tools": [EXECUTE_TOOL],
            "rejected_tools": [{"tool_name": RECORD_TOOL, "reason": reason}],
            "approval_gate_version": APPROVAL_GATE_VERSION,
        },
    }
    if extra:
        output.update(extra)
    return _json_safe_output(output)


def _blocked_candidate_prepare_output(
    project_id: str,
    *,
    reason: str,
    candidate_summary: object = None,
) -> dict[str, Any]:
    return _json_safe_output(
        {
            "status": "blocked",
            "prepare_version": PREPARE_RECORD_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_VERSION,
            "project_id": project_id,
            "target_type": CANDIDATE_TARGET_TYPE,
            "reason": reason,
            "candidate_summary": candidate_summary,
            "side_effects": {"executed": [], "skipped": [CANDIDATE_RECORD_TOOL]},
            "recommended_next_tools": [
                "inspect_agent_memory_tree_llm_candidates",
                "summarize_agent_memory_tree_llm_candidate",
            ],
            "trace": {
                "selected_tools": [CANDIDATE_PREPARE_TOOL],
                "rejected_tools": [{"tool_name": CANDIDATE_RECORD_TOOL, "reason": reason}],
                "approval_gate_version": LLM_CANDIDATE_APPROVAL_GATE_VERSION,
            },
        }
    )


def _blocked_candidate_execute_output(
    project_id: str,
    *,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = {
        "status": "blocked",
        "execute_version": EXECUTE_RECORD_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_WITH_APPROVAL_VERSION,
        "project_id": project_id,
        "target_type": CANDIDATE_TARGET_TYPE,
        "reason": reason,
        "side_effects": {"executed": [], "skipped": [CANDIDATE_RECORD_TOOL]},
        "recommended_next_tools": [CANDIDATE_PREPARE_TOOL],
        "trace": {
            "selected_tools": [CANDIDATE_EXECUTE_TOOL],
            "rejected_tools": [{"tool_name": CANDIDATE_RECORD_TOOL, "reason": reason}],
            "approval_gate_version": LLM_CANDIDATE_APPROVAL_GATE_VERSION,
        },
    }
    if extra:
        output.update(extra)
    return _json_safe_output(output)


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


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

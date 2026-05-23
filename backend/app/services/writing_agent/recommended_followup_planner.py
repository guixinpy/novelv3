from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.models import WritingAgentRun, WritingAgentStep
from app.services.writing_agent.tool_registry import allowed_tool_names, get_agent_tool_descriptor

FOLLOWUP_PLANNER_VERSION = "phase101.recommended_followup_planner.v1"
SAFE_RECOMMENDED_FOLLOWUP_TOOLS = frozenset(
    {
        "describe_agent_tools",
        "plan_writing_agent_run",
        "plan_recovery_tools",
        "plan_longform_chapter_batch",
        "inspect_longform_chapter_batch",
        "inspect_agent_job_projection",
        "inspect_agent_tool_contracts",
        "inspect_agent_knowledge_base_route",
        "inspect_agent_trace_audit",
        "inspect_agent_memory_route",
        "summarize_longform_context",
        "review_chapter_quality",
        "review_chapter_continuity",
        "plan_chapter_revision",
        "review_world_model_proposals",
        "inspect_agent_world_model_route",
        "plan_world_model_proposal_resolution",
        "preview_world_model_proposal_resolution",
        "draft_world_model_proposal_resolution_decisions",
        "draft_high_value_world_proposal_resolution_decisions",
        "preview_pending_action_route_approval_opt_in_apply_contract",
    }
)
LOOPING_FOLLOWUP_TOOLS = frozenset({"plan_recommended_followups"})


def latest_recommended_followup_state(steps: Sequence[WritingAgentStep]) -> dict[str, Any]:
    source = _latest_recommended_followup_source(steps)
    if source is None:
        return {"version": FOLLOWUP_PLANNER_VERSION, "status": "none"}
    step, recommendations = source
    return _followup_state_from_recommendations(step, recommendations)


def build_recommended_followup_tool_plan(db: Session, project_id: str, run_id: str | None) -> dict[str, Any]:
    if not run_id:
        return {
            "status": "failed",
            "error": "run_id is required",
            "source_run_id": None,
            "tools": [],
            "trace": {"selected_tools": [], "rejected_tools": [{"reason": "missing_run_id"}]},
        }

    run = db.query(WritingAgentRun).filter(WritingAgentRun.project_id == project_id, WritingAgentRun.id == run_id).first()
    if run is None:
        return {
            "status": "failed",
            "error": "Writing agent run not found",
            "source_run_id": run_id,
            "tools": [],
            "trace": {"selected_tools": [], "rejected_tools": [{"reason": "missing_run"}]},
        }

    steps = (
        db.query(WritingAgentStep)
        .filter(WritingAgentStep.project_id == project_id, WritingAgentStep.run_id == run_id)
        .order_by(WritingAgentStep.step_index.asc(), WritingAgentStep.id.asc())
        .all()
    )
    recovery = _latest_recommended_recovery_state(steps)
    if run.status in {"blocked", "failed"} and recovery.get("status") == "recommended":
        return {
            "status": "blocked",
            "preview_version": FOLLOWUP_PLANNER_VERSION,
            "preview_only": True,
            "mode": "preview",
            "source_run_id": run_id,
            "source_run_status": run.status,
            "recovery": recovery,
            "tools": [],
            "trace": {"selected_tools": [], "rejected_tools": [{"reason": "source_run_requires_recovery"}]},
        }
    source = _latest_recommended_followup_source(steps)
    if source is None:
        return {
            "status": "ready",
            "preview_version": FOLLOWUP_PLANNER_VERSION,
            "preview_only": True,
            "mode": "preview",
            "source_run_id": run_id,
            "source_run_status": run.status,
            "source_step": None,
            "recommended_followups": {"version": FOLLOWUP_PLANNER_VERSION, "status": "none"},
            "tools": [],
            "trace": {"selected_tools": [], "rejected_tools": [{"reason": "no_recommended_followups"}]},
        }

    step, recommendations = source
    state = _followup_state_from_recommendations(step, recommendations)
    tools, rejected_tools = _tool_requests_from_followups(
        state["canonical_followups"],
        source_step=step,
        source_run_id=run_id,
    )
    selected_tools = [str(tool.get("tool_name") or "") for tool in tools]
    hash_payload = {
        "preview_version": FOLLOWUP_PLANNER_VERSION,
        "project_id": project_id,
        "source_run_id": run_id,
        "source_step_id": step.id,
        "source_step_index": step.step_index,
        "source_tool": step.tool_name,
        "tools": tools,
    }
    return {
        "status": "completed" if tools else "ready",
        "preview_version": FOLLOWUP_PLANNER_VERSION,
        "preview_only": True,
        "mode": "preview",
        "can_execute": False,
        "requires_followup_run": True,
        "plan_hash": _plan_hash(hash_payload),
        "hash_payload": hash_payload,
        "source_run_id": run_id,
        "source_run_status": run.status,
        "source_step_id": step.id,
        "source_step": {
            "id": step.id,
            "step_index": step.step_index,
            "tool_name": step.tool_name,
            "status": step.status,
            "chapter_index": step.chapter_index,
        },
        "recommended_followups": state,
        "tools": tools,
        "execution_policy": {
            "mode": "preview",
            "status": "preview_only" if tools else "no_executable_followup",
            "auto_execute": False,
            "requires_followup_run": True,
        },
        "trace": {
            "selected_tools": selected_tools,
            "rejected_tools": rejected_tools,
        },
    }


def _latest_recommended_followup_source(
    steps: Sequence[WritingAgentStep],
) -> tuple[WritingAgentStep, dict[str, Any]] | None:
    for step in reversed(list(steps)):
        output = step.output if isinstance(step.output, dict) else {}
        envelope = output.get("agent_tool_result") if isinstance(output.get("agent_tool_result"), dict) else {}
        recommendations = envelope.get("recommendations") if isinstance(envelope.get("recommendations"), dict) else None
        if not recommendations:
            continue
        if _string_list(recommendations.get("canonical_followups")):
            return step, recommendations
    return None


def _followup_state_from_recommendations(
    step: WritingAgentStep,
    recommendations: dict[str, Any],
) -> dict[str, Any]:
    allowed = allowed_tool_names()
    canonical_followups = _string_list(recommendations.get("canonical_followups"))
    allowed_followups = [tool_name for tool_name in canonical_followups if tool_name in allowed]
    return {
        "version": FOLLOWUP_PLANNER_VERSION,
        "status": "recommended" if allowed_followups else "none",
        "source_step_index": step.step_index,
        "source_tool": step.tool_name,
        "source_fields": _string_list(recommendations.get("source_fields")),
        "runtime_followups": _string_list(recommendations.get("runtime_followups")),
        "policy_followups": _string_list(recommendations.get("policy_followups")),
        "canonical_followups": canonical_followups,
        "non_tool_recommendations": _string_list(recommendations.get("non_tool_recommendations")),
        "next_tool": allowed_followups[0] if allowed_followups else None,
    }


def _tool_requests_from_followups(
    followups: list[str],
    *,
    source_step: WritingAgentStep,
    source_run_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    allowed = allowed_tool_names()
    tools: list[dict[str, Any]] = []
    rejected_tools: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, tool_name in enumerate(followups, start=1):
        if tool_name in seen:
            continue
        seen.add(tool_name)
        if tool_name in LOOPING_FOLLOWUP_TOOLS or tool_name == source_step.tool_name:
            rejected_tools.append({"tool_name": tool_name, "reason": "planner_loop"})
            continue
        if tool_name not in allowed:
            rejected_tools.append({"tool_name": tool_name, "reason": "not_allowed"})
            continue
        if tool_name not in SAFE_RECOMMENDED_FOLLOWUP_TOOLS:
            rejected_tools.append({"tool_name": tool_name, "reason": "requires_confirmation"})
            continue
        tools.append(_tool_request_from_followup(tool_name, source_step=source_step, source_run_id=source_run_id, index=index))
    return tools, rejected_tools


def _tool_request_from_followup(
    tool_name: str,
    *,
    source_step: WritingAgentStep,
    source_run_id: str,
    index: int,
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "params": _params_for_followup(tool_name, source_step=source_step, source_run_id=source_run_id),
        "planner": {
            "step_index": index,
            "reason": f"根据上一轮 {source_step.tool_name} 的运行时推荐规划后继工具 {tool_name}。",
            "on_missing": "record_issue",
            "on_failure": "record_issue",
            "expected_output": "推荐后继工具输出。",
            "post_generation": False,
            "planner_version": FOLLOWUP_PLANNER_VERSION,
            "source_run_id": source_run_id,
            "source_step_index": source_step.step_index,
            "source_tool": source_step.tool_name,
        },
    }


def _params_for_followup(
    tool_name: str,
    *,
    source_step: WritingAgentStep,
    source_run_id: str,
) -> dict[str, Any]:
    descriptor = get_agent_tool_descriptor(tool_name)
    properties = {}
    if descriptor is not None:
        properties = descriptor.input_schema.get("properties") if isinstance(descriptor.input_schema, dict) else {}
        properties = properties if isinstance(properties, dict) else {}
    chapter_index = _source_chapter_index(source_step)
    params: dict[str, Any] = {}
    if "chapter_index" in properties and chapter_index:
        params["chapter_index"] = chapter_index
    if "start_chapter" in properties and chapter_index:
        params["start_chapter"] = chapter_index
    if "end_chapter" in properties and chapter_index:
        params["end_chapter"] = chapter_index
    if "before_chapter" in properties and chapter_index:
        params["before_chapter"] = chapter_index
    if "run_id" in properties:
        params["run_id"] = source_run_id
    if "source_run_id" in properties:
        params["source_run_id"] = source_run_id
    if "pending_action_id" in properties:
        pending_action_id = _source_pending_action_id(source_step)
        if pending_action_id:
            params["pending_action_id"] = pending_action_id
    return params


def _source_chapter_index(step: WritingAgentStep) -> int | None:
    if step.chapter_index:
        return int(step.chapter_index)
    output = step.output if isinstance(step.output, dict) else {}
    value = _optional_int(output.get("chapter_index"))
    if value:
        return value
    step_input = step.input if isinstance(step.input, dict) else {}
    params = step_input.get("params") if isinstance(step_input.get("params"), dict) else {}
    for key in ("chapter_index", "start_chapter", "end_chapter", "before_chapter"):
        value = _optional_int(params.get(key))
        if value:
            return value
    return None


def _source_pending_action_id(step: WritingAgentStep) -> str | None:
    output = step.output if isinstance(step.output, dict) else {}
    pending_action_id = _optional_string(output.get("pending_action_id"))
    if pending_action_id:
        return pending_action_id
    envelope = output.get("agent_tool_result") if isinstance(output.get("agent_tool_result"), dict) else {}
    envelope_output = envelope.get("output") if isinstance(envelope.get("output"), dict) else {}
    pending_action_id = _optional_string(envelope_output.get("pending_action_id"))
    if pending_action_id:
        return pending_action_id
    step_input = step.input if isinstance(step.input, dict) else {}
    params = step_input.get("params") if isinstance(step_input.get("params"), dict) else {}
    return _optional_string(params.get("pending_action_id"))


def _latest_recommended_recovery_state(steps: Sequence[WritingAgentStep]) -> dict[str, Any]:
    for step in reversed(list(steps)):
        output = step.output if isinstance(step.output, dict) else {}
        envelope = output.get("agent_tool_result") if isinstance(output.get("agent_tool_result"), dict) else {}
        recovery = envelope.get("recovery") if isinstance(envelope.get("recovery"), dict) else {}
        if recovery.get("status") == "recommended":
            return {
                "status": "recommended",
                "source_step_index": step.step_index,
                "source_tool": recovery.get("source_tool") or step.tool_name,
                "next_tool": recovery.get("next_tool"),
                "reason_code": recovery.get("reason_code"),
            }
    return {"status": "none"}


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    cleaned = str(value).strip()
    return [cleaned] if cleaned else []


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _plan_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

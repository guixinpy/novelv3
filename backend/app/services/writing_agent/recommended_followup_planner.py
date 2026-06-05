from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.models import WritingAgentRun, WritingAgentStep
from app.services.writing_agent.agent_worker_dispatch import (
    agent_worker_profile_for_tool,
    preview_agent_worker_dispatches,
)
from app.services.writing_agent.tool_registry import allowed_tool_names, get_agent_tool_descriptor

FOLLOWUP_PLANNER_VERSION = "phase101.recommended_followup_planner.v1"
SAFE_RECOMMENDED_FOLLOWUP_TOOLS = frozenset(
    {
        "describe_agent_tools",
        "inspect_agent_health_projection",
        "plan_writing_agent_run",
        "plan_recovery_tools",
        "plan_longform_chapter_batch",
        "inspect_longform_chapter_batch",
        "inspect_agent_job_projection",
        "inspect_agent_tool_contracts",
        "inspect_agent_control_plane_readiness",
        "inspect_agent_command_contracts",
        "inspect_agent_knowledge_base_route",
        "inspect_agent_trace_audit",
        "inspect_agent_route_preference_projection",
        "inspect_agent_memory_route",
        "inspect_agent_memory_tree",
        "inspect_agent_retrieval_strategy",
        "search_agent_retrieval_context",
        "summarize_longform_context",
        "prepare_generate_setup_execution",
        "prepare_generate_storyline_execution",
        "prepare_generate_outline_execution",
        "prepare_generate_chapter_execution",
        "plan_post_chapter_memory_capture",
        "prepare_record_agent_knowledge_base_candidate",
        "prepare_analyze_chapter_world_model_execution",
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
        "prepare_apply_pending_action_route_approval_opt_in",
    }
)
LOOPING_FOLLOWUP_TOOLS = frozenset({"plan_recommended_followups"})
APPROVAL_PREPARE_FOLLOWUP_TOOLS = {
    "generate_setup": "prepare_generate_setup_execution",
    "generate_storyline": "prepare_generate_storyline_execution",
    "generate_outline": "prepare_generate_outline_execution",
    "generate_chapter": "prepare_generate_chapter_execution",
    "analyze_chapter_world_model": "prepare_analyze_chapter_world_model_execution",
}


def latest_recommended_followup_state(steps: Sequence[WritingAgentStep]) -> dict[str, Any]:
    source = _latest_recommended_followup_source(steps)
    if source is None:
        return {"version": FOLLOWUP_PLANNER_VERSION, "status": "none"}
    step, recommendations = source
    return _followup_state_from_recommendations(step, recommendations)


def latest_recommended_followup_run_id(db: Session, project_id: str) -> str | None:
    runs = (
        db.query(WritingAgentRun)
        .filter(WritingAgentRun.project_id == project_id, WritingAgentRun.status.in_(("success", "completed")))
        .order_by(WritingAgentRun.updated_at.desc(), WritingAgentRun.id.desc())
        .limit(20)
        .all()
    )
    for run in runs:
        steps = (
            db.query(WritingAgentStep)
            .filter(WritingAgentStep.project_id == project_id, WritingAgentStep.run_id == run.id)
            .order_by(WritingAgentStep.step_index.asc(), WritingAgentStep.id.asc())
            .all()
        )
        state = latest_recommended_followup_state(steps)
        if state.get("status") == "recommended":
            return str(run.id)
    return None


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
    pending_confirmation_tool_calls = [
        tool_call for tool_call in state["recommended_next_tool_calls"] if tool_call.get("requires_confirmation") is True
    ]
    tools, rejected_tools = _tool_requests_from_followups(
        state["canonical_followups"],
        source_step=step,
        source_run_id=run_id,
        provenance_tools=state["provenance_recovery_tools"] + state["post_approval_continuation_tools"],
    )
    selected_tools = [str(tool.get("tool_name") or "") for tool in tools]
    worker_profiles = [
        str(profile)
        for tool in tools
        if (
            profile := (
                (tool.get("planner") or {}).get("agent_profile")
                if isinstance(tool.get("planner"), dict)
                else None
            )
        )
    ]
    worker_dispatch = preview_agent_worker_dispatches(tools, parent_run_id=run_id)
    hash_payload = {
        "preview_version": FOLLOWUP_PLANNER_VERSION,
        "project_id": project_id,
        "source_run_id": run_id,
        "source_step_id": step.id,
        "source_step_index": step.step_index,
        "source_tool": step.tool_name,
        "tools": tools,
        "pending_confirmation_tool_calls": pending_confirmation_tool_calls,
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
        "pending_confirmation_tool_calls": pending_confirmation_tool_calls,
        "worker_dispatch": worker_dispatch,
        "execution_policy": {
            "mode": "preview",
            "status": "preview_only" if tools else "no_executable_followup",
            "auto_execute": False,
            "requires_followup_run": True,
            "pending_confirmation_tool_calls": len(pending_confirmation_tool_calls),
        },
        "trace": {
            "selected_tools": selected_tools,
            "worker_profiles": worker_profiles,
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
        "provenance_recovery_tools": _tool_request_list(recommendations.get("provenance_recovery_tools")),
        "post_approval_continuation_tools": _tool_request_list(
            recommendations.get("post_approval_continuation_tools")
        ),
        "recommended_next_tool_calls": _tool_request_list(recommendations.get("recommended_next_tool_calls")),
        "provenance_write_tools": _tool_request_list(recommendations.get("provenance_write_tools")),
        "next_tool": allowed_followups[0] if allowed_followups else None,
    }


def _tool_requests_from_followups(
    followups: list[str],
    *,
    source_step: WritingAgentStep,
    source_run_id: str,
    provenance_tools: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    allowed = allowed_tool_names()
    tools: list[dict[str, Any]] = []
    rejected_tools: list[dict[str, str]] = []
    seen: set[str] = set()
    provenance_tools = provenance_tools or []
    for index, tool_name in enumerate(followups, start=1):
        matched_provenance_tools = _matching_provenance_tools(tool_name, provenance_tools)
        if not matched_provenance_tools and tool_name in seen:
            continue
        candidate_tools: list[dict[str, Any] | None] = matched_provenance_tools or [None]
        for provenance_tool in candidate_tools:
            effective_tool_name = _effective_followup_tool_name(tool_name)
            seen_key = _seen_key(effective_tool_name, provenance_tool)
            if seen_key in seen:
                continue
            seen.add(seen_key)
            if effective_tool_name in LOOPING_FOLLOWUP_TOOLS or (
                effective_tool_name == source_step.tool_name
                and not _is_distinct_provenance_retry(source_step, provenance_tool)
            ):
                rejected_tools.append({"tool_name": tool_name, "reason": "planner_loop"})
                continue
            if effective_tool_name not in allowed:
                rejected_tools.append({"tool_name": tool_name, "reason": "not_allowed"})
                continue
            if effective_tool_name not in SAFE_RECOMMENDED_FOLLOWUP_TOOLS and not _is_safe_parameterized_followup(
                effective_tool_name,
                provenance_tool,
                source_step=source_step,
            ):
                rejected_tools.append({"tool_name": tool_name, "reason": "requires_confirmation"})
                continue
            selected_index = len(tools) + 1
            if provenance_tool is None:
                tools.append(
                    _tool_request_from_followup(
                        effective_tool_name,
                        source_step=source_step,
                        source_run_id=source_run_id,
                        index=selected_index,
                    )
                )
                continue
            tools.append(
                _tool_request_from_provenance_followup(
                    provenance_tool,
                    source_step=source_step,
                    source_run_id=source_run_id,
                    index=selected_index,
                )
            )
    return tools, rejected_tools


def _tool_request_from_followup(
    tool_name: str,
    *,
    source_step: WritingAgentStep,
    source_run_id: str,
    index: int,
) -> dict[str, Any]:
    request = {
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
    return _with_worker_dispatch(request, source_run_id=source_run_id)


def _tool_request_from_provenance_followup(
    provenance_tool: dict[str, Any],
    *,
    source_step: WritingAgentStep,
    source_run_id: str,
    index: int,
) -> dict[str, Any]:
    tool_name = str(provenance_tool.get("tool_name") or "").strip()
    params = provenance_tool.get("params") if isinstance(provenance_tool.get("params"), dict) else {}
    request = {
        "tool_name": tool_name,
        "params": dict(params),
        "planner": {
            "step_index": index,
            "reason": f"根据上一轮 {source_step.tool_name} 的 provenance 恢复建议规划后继工具 {tool_name}。",
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
    return _with_worker_dispatch(request, source_run_id=source_run_id)


def _with_worker_dispatch(request: dict[str, Any], *, source_run_id: str) -> dict[str, Any]:
    worker_profile = agent_worker_profile_for_tool(str(request.get("tool_name") or ""))
    if not worker_profile:
        return request
    planner = request.get("planner") if isinstance(request.get("planner"), dict) else {}
    request["planner"] = {
        **planner,
        "agent_profile": worker_profile,
        "worker_dispatch": {
            "status": "planned",
            "worker": worker_profile,
            "parent_run_id": source_run_id,
            "dispatch_mode": "preview_only",
            "will_execute": False,
        },
    }
    return request


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
    if "command_args" in properties:
        command_args = _source_command_args(source_step)
        if command_args:
            params["command_args"] = command_args
    if tool_name == "search_agent_retrieval_context" and chapter_index:
        params.setdefault("query", f"第{chapter_index}章相关记忆与检索证据")
        params.setdefault("max_chapter_index", chapter_index)
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


def _source_command_args(step: WritingAgentStep) -> str | None:
    output = step.output if isinstance(step.output, dict) else {}
    command_args = _optional_string(output.get("command_args"))
    if command_args:
        return command_args
    envelope = output.get("agent_tool_result") if isinstance(output.get("agent_tool_result"), dict) else {}
    envelope_output = envelope.get("output") if isinstance(envelope.get("output"), dict) else {}
    command_args = _optional_string(envelope_output.get("command_args"))
    if command_args:
        return command_args
    params = _source_step_params(step)
    return _optional_string(params.get("command_args"))


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


def _matching_provenance_tools(tool_name: str, provenance_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in provenance_tools if str(item.get("tool_name") or "").strip() == tool_name]


def _effective_followup_tool_name(tool_name: str) -> str:
    return APPROVAL_PREPARE_FOLLOWUP_TOOLS.get(tool_name, tool_name)


def _seen_key(tool_name: str, provenance_tool: dict[str, Any] | None) -> str:
    if provenance_tool is None:
        return tool_name
    params = provenance_tool.get("params") if isinstance(provenance_tool.get("params"), dict) else {}
    return f"{tool_name}:{_stable_json(params)}"


def _is_distinct_provenance_retry(source_step: WritingAgentStep, provenance_tool: dict[str, Any] | None) -> bool:
    if provenance_tool is None:
        return False
    params = provenance_tool.get("params") if isinstance(provenance_tool.get("params"), dict) else {}
    return _stable_json(params) != _stable_json(_source_step_params(source_step))


def _is_safe_parameterized_followup(
    tool_name: str,
    provenance_tool: dict[str, Any] | None,
    *,
    source_step: WritingAgentStep,
) -> bool:
    if tool_name != "preflight_writing":
        return False
    if provenance_tool is not None:
        params = provenance_tool.get("params") if isinstance(provenance_tool.get("params"), dict) else {}
        return _optional_int(params.get("chapter_index")) is not None
    return source_step.tool_name in {
        "inspect_agent_knowledge_base_route",
        "inspect_agent_memory_route",
    } and _source_chapter_index(source_step) is not None


def _source_step_params(step: WritingAgentStep) -> dict[str, Any]:
    step_input = step.input if isinstance(step.input, dict) else {}
    params = step_input.get("params") if isinstance(step_input.get("params"), dict) else {}
    return dict(params)


def _tool_request_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    results: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        tool_name = _optional_string(item.get("tool_name"))
        if not tool_name:
            continue
        params = item.get("params") if isinstance(item.get("params"), dict) else {}
        normalized: dict[str, Any] = {"tool_name": tool_name, "params": dict(params)}
        visibility = _optional_string(item.get("visibility"))
        if visibility:
            normalized["visibility"] = visibility
        if "requires_confirmation" in item:
            normalized["requires_confirmation"] = item.get("requires_confirmation") is True
        results.append(normalized)
    return results


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


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

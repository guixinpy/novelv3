from __future__ import annotations

from typing import Literal

DIALOG_AGENT_ROUTE_VERSION = "phase104.dialog_agent_route.v1"
DIALOG_AGENT_ROUTE_APPROVAL_CHAIN_OPT_IN_KEY = "use_agent_approval_chain"
_READ_ONLY_AGENT_TOOLS = {
    "inspect_agent_control_plane_readiness",
    "inspect_agent_health_projection",
    "inspect_agent_memory_tree",
    "inspect_agent_memory_route",
    "inspect_agent_memory_activation_plan",
    "inspect_agent_knowledge_base_route",
    "inspect_agent_world_model_route",
    "search_agent_retrieval_context",
    "summarize_longform_context",
    "inspect_agent_context_compression_projection",
    "inspect_agent_worker_dispatch",
    "inspect_agent_trace_audit",
    "inspect_agent_write_gate_coverage",
    "inspect_agent_tool_contracts",
    "inspect_agent_command_contracts",
    "inspect_agent_slash_command_route",
    "inspect_agent_dialog_route_projection",
    "inspect_agent_intent_projection",
    "inspect_agent_dialog_control_plane_projection",
    "inspect_agent_mutation_fingerprints",
    "inspect_agent_reference_alignment",
    "inspect_agent_dogfood_evidence",
    "inspect_agent_route_preference_projection",
    "inspect_agent_job_projection",
    "plan_chapter_conflict_recovery",
}

DialogAgentRouteSource = Literal["slash_command", "text_intent", "button_action"]

_DIALOG_ACTION_TO_AGENT_TOOL: dict[str, str] = {
    "preview_setup": "generate_setup",
    "preview_storyline": "generate_storyline",
    "preview_outline": "generate_outline",
    "preview_chapter": "generate_chapter",
    "preview_review": "plan_writing_agent_run",
    "preview_recovery": "plan_writing_agent_run",
    "inspect_agent_health": "inspect_agent_health_projection",
    "inspect_control_plane_readiness": "inspect_agent_control_plane_readiness",
    "inspect_memory_tree": "inspect_agent_memory_tree",
    "inspect_memory_route": "inspect_agent_memory_route",
    "inspect_memory_activation_plan": "inspect_agent_memory_activation_plan",
    "inspect_knowledge_base_route": "inspect_agent_knowledge_base_route",
    "inspect_world_model_route": "inspect_agent_world_model_route",
    "search_retrieval_context": "search_agent_retrieval_context",
    "summarize_longform_context": "summarize_longform_context",
    "inspect_context_compression": "inspect_agent_context_compression_projection",
    "inspect_worker_dispatch": "inspect_agent_worker_dispatch",
    "inspect_trace_audit": "inspect_agent_trace_audit",
    "inspect_write_gate_coverage": "inspect_agent_write_gate_coverage",
    "inspect_tool_contracts": "inspect_agent_tool_contracts",
    "inspect_command_contracts": "inspect_agent_command_contracts",
    "inspect_slash_command_route": "inspect_agent_slash_command_route",
    "inspect_dialog_route": "inspect_agent_dialog_route_projection",
    "inspect_intent_projection": "inspect_agent_intent_projection",
    "inspect_dialog_control_plane": "inspect_agent_dialog_control_plane_projection",
    "inspect_mutation_fingerprints": "inspect_agent_mutation_fingerprints",
    "inspect_reference_alignment": "inspect_agent_reference_alignment",
    "inspect_dogfood_evidence": "inspect_agent_dogfood_evidence",
    "inspect_route_preference": "inspect_agent_route_preference_projection",
    "inspect_agent_job_projection": "inspect_agent_job_projection",
    "plan_chapter_conflict_recovery": "plan_chapter_conflict_recovery",
    "generate_setup": "generate_setup",
    "generate_storyline": "generate_storyline",
    "generate_outline": "generate_outline",
    "generate_chapter": "generate_chapter",
    "review_chapter": "plan_writing_agent_run",
    "recover_blocked_run": "plan_writing_agent_run",
}

_PREVIEW_DIALOG_ACTION_TYPES = (
    "preview_setup",
    "preview_storyline",
    "preview_outline",
    "preview_chapter",
    "preview_review",
    "preview_recovery",
)


def preview_dialog_action_types() -> tuple[str, ...]:
    return _PREVIEW_DIALOG_ACTION_TYPES


def dialog_action_to_agent_tool_name(action_type: str | None) -> str | None:
    return _DIALOG_ACTION_TO_AGENT_TOOL.get((action_type or "").strip())


def build_dialog_agent_route(
    action_type: str | None,
    *,
    source: DialogAgentRouteSource,
    command_name: str | None = None,
    use_agent_approval_chain: bool = False,
) -> dict[str, str | bool] | None:
    normalized_action_type = (action_type or "").strip()
    agent_tool_name = dialog_action_to_agent_tool_name(normalized_action_type)
    if not normalized_action_type or not agent_tool_name:
        return None
    route: dict[str, str | bool] = {
        "version": DIALOG_AGENT_ROUTE_VERSION,
        "source": source,
        "action_type": normalized_action_type,
        "agent_action_type": agent_tool_name,
        "agent_tool_name": agent_tool_name,
        "requires_confirmation": agent_tool_name not in _READ_ONLY_AGENT_TOOLS,
        "entrypoint": "dialog_pending_action",
    }
    normalized_command_name = (command_name or "").strip().lower()
    if normalized_command_name:
        route["command_name"] = normalized_command_name
    if use_agent_approval_chain is True:
        route[DIALOG_AGENT_ROUTE_APPROVAL_CHAIN_OPT_IN_KEY] = True
    return route

from datetime import datetime

import pytest

from app.core.dialog_agent_routes import build_dialog_agent_route
from app.models import (
    ChapterContent,
    Dialog,
    Outline,
    PendingAction,
    Project,
    Setup,
    Storyline,
    WritingAgentRun,
    WritingAgentStep,
)
from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.chapter_generation_execution import (
    execute_generate_chapter_with_approval,
    prepare_generate_chapter_execution,
)
from app.services.writing_agent.chapter_generation_tool import execute_generate_chapter_tool
from app.services.writing_agent.agent_core_tool_adapters import build_agent_core_tool_adapters
from app.services.writing_agent.agent_generation_tool_adapters import build_agent_generation_tool_adapters
from app.services.writing_agent.agent_memory_trace_tool_adapters import (
    AGENT_MEMORY_TRACE_TOOL_ADAPTERS,
    build_agent_memory_trace_tool_adapters,
)
from app.services.writing_agent.agent_task_queue_tool_adapters import AGENT_TASK_QUEUE_TOOL_ADAPTERS
from app.services.writing_agent.knowledge_base_tool_adapters import (
    KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS,
    build_knowledge_base_agent_tool_adapters,
)
from app.services.writing_agent.longform_tool_adapters import build_longform_agent_tool_adapters
from app.services.writing_agent.outline_generation_execution import prepare_generate_outline_execution
from app.services.writing_agent.outline_generation_tool_adapters import build_outline_generation_agent_tool_adapters
from app.services.writing_agent.review_revision_tool_adapters import REVIEW_REVISION_AGENT_TOOL_ADAPTERS
from app.services.writing_agent.setup_generation_execution import prepare_generate_setup_execution
from app.services.writing_agent.setup_generation_tool_adapters import build_setup_generation_agent_tool_adapters
from app.services.writing_agent.storyline_generation_execution import prepare_generate_storyline_execution
from app.services.writing_agent.storyline_generation_tool_adapters import build_storyline_generation_agent_tool_adapters
from app.services.writing_agent.tool_adapter_types import WritingAgentToolContext
from app.services.writing_agent.tool_registry import internal_tool_names
from app.services.writing_agent.tool_executor import (
    execute_writing_agent_tool,
    static_writing_agent_tool_adapter_names,
    unhandled_internal_writing_agent_tool_names,
    writing_agent_tool_adapter_metadata,
    writing_agent_tool_adapter_metadata_by_name,
)
from app.services.writing_agent.world_model_tool_adapters import WORLD_MODEL_AGENT_TOOL_ADAPTERS


def test_agent_core_tool_adapters_live_in_dedicated_module():
    adapters = build_agent_core_tool_adapters(
        adapter_metadata_by_name_provider=lambda: {},
        static_adapter_tool_names_provider=lambda: set(),
    )
    names = list(adapters)

    assert names == [
        "describe_agent_tools",
        "plan_writing_agent_run",
        "plan_dialog_intent_agent_run",
        "preview_agent_plan_approval_contract",
        "verify_agent_plan_approval_contract",
        "plan_recovery_tools",
        "plan_recommended_followups",
        "inspect_agent_worker_dispatch",
        "apply_agent_worker_orphan_recovery",
        "inspect_agent_health_projection",
        "inspect_agent_control_plane_readiness",
        "inspect_agent_slash_command_route",
        "inspect_agent_dialog_route_projection",
        "inspect_agent_route_preference_projection",
        "plan_agent_route_approval_opt_in",
        "preview_pending_action_route_approval_opt_in_apply",
        "preview_pending_action_route_approval_opt_in_apply_contract",
        "apply_pending_action_route_approval_opt_in",
        "prepare_apply_pending_action_route_approval_opt_in",
        "execute_apply_pending_action_route_approval_opt_in_with_approval",
        "inspect_agent_dialog_control_plane_projection",
        "inspect_agent_intent_projection",
        "inspect_agent_reference_alignment",
        "inspect_agent_dogfood_evidence",
        "inspect_agent_tool_contracts",
        "inspect_agent_command_contracts",
        "inspect_legacy_hermes_action_migration",
        "inspect_agent_write_gate_coverage",
        "inspect_agent_mutation_fingerprints",
    ]
    assert "preflight_writing" not in names
    assert {adapter.category for adapter in adapters.values()} == {"preflight"}
    assert adapters["apply_pending_action_route_approval_opt_in"].mutability == "guarded_write"
    assert adapters["apply_pending_action_route_approval_opt_in"].write_policy == "approval_required_redirect"
    assert adapters["apply_agent_worker_orphan_recovery"].mutability == "guarded_write"
    assert adapters["apply_agent_worker_orphan_recovery"].write_policy == "confirmation_required"
    assert adapters["prepare_apply_pending_action_route_approval_opt_in"].mutability == "read"
    assert adapters["execute_apply_pending_action_route_approval_opt_in_with_approval"].mutability == "write"
    assert {
        adapter.mutability
        for name, adapter in adapters.items()
        if name
            not in {
                "apply_pending_action_route_approval_opt_in",
                "apply_agent_worker_orphan_recovery",
                "execute_apply_pending_action_route_approval_opt_in_with_approval",
            }
    } == {"read"}
    assert adapters["verify_agent_plan_approval_contract"].handler.__name__ == "_verify_agent_plan_approval_contract"
    assert adapters["inspect_agent_intent_projection"].handler.__name__ == "_inspect_agent_intent_projection"


def test_agent_memory_trace_tool_adapters_live_in_dedicated_module():
    names = list(AGENT_MEMORY_TRACE_TOOL_ADAPTERS)

    assert names == [
        "inspect_agent_trace_audit",
        "inspect_agent_memory_route",
        "search_agent_retrieval_context",
        "summarize_longform_context",
        "inspect_agent_context_compression_projection",
        "build_agent_context_compression_payload",
        "record_agent_context_compression_summary",
        "inspect_agent_memory_activation_plan",
        "repair_longform_maintenance",
    ]
    assert {adapter.category for adapter in AGENT_MEMORY_TRACE_TOOL_ADAPTERS.values()} == {
        "trace",
        "longform_memory",
        "retrieval",
        "maintenance",
    }
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["inspect_agent_trace_audit"].mutability == "read"
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["search_agent_retrieval_context"].mutability == "read"
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["summarize_longform_context"].mutability == "read"
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["inspect_agent_context_compression_projection"].mutability == "read"
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["build_agent_context_compression_payload"].mutability == "read"
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["record_agent_context_compression_summary"].mutability == "write"
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["inspect_agent_memory_activation_plan"].mutability == "read"
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["repair_longform_maintenance"].mutability == "guarded_write"
    assert (
        AGENT_MEMORY_TRACE_TOOL_ADAPTERS["repair_longform_maintenance"].write_policy
        == "approval_required_redirect"
    )
    assert (
        AGENT_MEMORY_TRACE_TOOL_ADAPTERS["inspect_agent_context_compression_projection"].handler.__name__
        == "_inspect_agent_context_compression_projection"
    )
    assert (
        AGENT_MEMORY_TRACE_TOOL_ADAPTERS["build_agent_context_compression_payload"].handler.__name__
        == "_build_agent_context_compression_payload"
    )
    assert (
        AGENT_MEMORY_TRACE_TOOL_ADAPTERS["record_agent_context_compression_summary"].handler.__name__
        == "_record_agent_context_compression_summary"
    )
    assert (
        AGENT_MEMORY_TRACE_TOOL_ADAPTERS["search_agent_retrieval_context"].handler.__name__
        == "_search_agent_retrieval_context"
    )
    assert (
        AGENT_MEMORY_TRACE_TOOL_ADAPTERS["repair_longform_maintenance"].handler.__name__
        == "_repair_longform_maintenance"
    )
    assert (
        AGENT_MEMORY_TRACE_TOOL_ADAPTERS["inspect_agent_memory_activation_plan"].handler.__name__
        == "_inspect_agent_memory_activation_plan"
    )


def test_agent_memory_trace_tool_adapter_builder_adds_maintenance_approval_chain():
    adapters = build_agent_memory_trace_tool_adapters(approval_tool_metadata_provider=lambda plan: {})
    names = list(adapters)

    assert names == [
        "inspect_agent_trace_audit",
        "inspect_agent_memory_route",
        "search_agent_retrieval_context",
        "summarize_longform_context",
        "inspect_agent_context_compression_projection",
        "build_agent_context_compression_payload",
        "record_agent_context_compression_summary",
        "inspect_agent_memory_activation_plan",
        "repair_longform_maintenance",
        "prepare_repair_longform_maintenance",
        "execute_repair_longform_maintenance_with_approval",
    ]
    assert adapters["prepare_repair_longform_maintenance"].mutability == "read"
    assert adapters["execute_repair_longform_maintenance_with_approval"].mutability == "write"
    assert (
        adapters["execute_repair_longform_maintenance_with_approval"].handler.__name__
        == "_execute_repair_longform_maintenance_with_approval"
    )


def test_agent_generation_tool_adapters_live_in_dedicated_module():
    adapters = build_agent_generation_tool_adapters(approval_tool_metadata_provider=lambda plan: {})
    names = list(adapters)

    assert names == [
        "generate_chapter",
        "prepare_generate_chapter_execution",
        "execute_generate_chapter_with_approval",
        "expand_outline_window",
        "prepare_expand_outline_window_execution",
        "execute_expand_outline_window_with_approval",
        "backfill_outline_gaps",
        "prepare_backfill_outline_gaps_execution",
        "execute_backfill_outline_gaps_with_approval",
    ]
    assert adapters["generate_chapter"].mutability == "guarded_write"
    assert adapters["generate_chapter"].write_policy == "approval_required_redirect"
    assert adapters["prepare_generate_chapter_execution"].mutability == "read"
    assert adapters["execute_generate_chapter_with_approval"].mutability == "write"
    assert adapters["expand_outline_window"].mutability == "guarded_write"
    assert adapters["expand_outline_window"].write_policy == "approval_required_redirect"
    assert adapters["prepare_expand_outline_window_execution"].mutability == "read"
    assert adapters["execute_expand_outline_window_with_approval"].mutability == "write"
    assert adapters["backfill_outline_gaps"].mutability == "guarded_write"
    assert adapters["backfill_outline_gaps"].write_policy == "approval_required_redirect"
    assert adapters["backfill_outline_gaps"].handler.__name__ == "_backfill_outline_gaps"
    assert adapters["prepare_backfill_outline_gaps_execution"].mutability == "read"
    assert adapters["execute_backfill_outline_gaps_with_approval"].mutability == "write"


def test_setup_generation_tool_adapters_live_in_dedicated_module():
    adapters = build_setup_generation_agent_tool_adapters(approval_tool_metadata_provider=lambda plan: {})
    names = list(adapters)

    assert names == [
        "generate_setup",
        "preview_generate_setup_execution",
        "prepare_generate_setup_execution",
        "execute_generate_setup_with_approval",
    ]
    assert adapters["generate_setup"].mutability == "guarded_write"
    assert adapters["generate_setup"].write_policy == "approval_required_redirect"
    assert adapters["preview_generate_setup_execution"].mutability == "read"
    assert adapters["prepare_generate_setup_execution"].mutability == "read"
    assert adapters["execute_generate_setup_with_approval"].mutability == "write"
    assert adapters["execute_generate_setup_with_approval"].handler.__name__ == "_execute_generate_setup_with_approval"


def test_storyline_generation_tool_adapters_live_in_dedicated_module():
    adapters = build_storyline_generation_agent_tool_adapters(approval_tool_metadata_provider=lambda plan: {})
    names = list(adapters)

    assert names == [
        "generate_storyline",
        "preview_generate_storyline_execution",
        "prepare_generate_storyline_execution",
        "execute_generate_storyline_with_approval",
    ]
    assert adapters["generate_storyline"].mutability == "guarded_write"
    assert adapters["generate_storyline"].write_policy == "approval_required_redirect"
    assert adapters["preview_generate_storyline_execution"].mutability == "read"
    assert adapters["prepare_generate_storyline_execution"].mutability == "read"
    assert adapters["execute_generate_storyline_with_approval"].mutability == "write"
    assert adapters["execute_generate_storyline_with_approval"].handler.__name__ == (
        "_execute_generate_storyline_with_approval"
    )


def test_outline_generation_tool_adapters_live_in_dedicated_module():
    adapters = build_outline_generation_agent_tool_adapters(approval_tool_metadata_provider=lambda plan: {})
    names = list(adapters)

    assert names == [
        "generate_outline",
        "preview_generate_outline_execution",
        "prepare_generate_outline_execution",
        "execute_generate_outline_with_approval",
    ]
    assert adapters["generate_outline"].mutability == "guarded_write"
    assert adapters["generate_outline"].write_policy == "approval_required_redirect"
    assert adapters["preview_generate_outline_execution"].mutability == "read"
    assert adapters["prepare_generate_outline_execution"].mutability == "read"
    assert adapters["execute_generate_outline_with_approval"].mutability == "write"
    assert adapters["execute_generate_outline_with_approval"].handler.__name__ == (
        "_execute_generate_outline_with_approval"
    )


def test_agent_task_queue_tool_adapters_live_in_dedicated_module():
    names = list(AGENT_TASK_QUEUE_TOOL_ADAPTERS)

    assert names == [
        "plan_chapter_conflict_recovery",
        "inspect_agent_job_projection",
        "inspect_agent_event_projection",
    ]
    assert {adapter.category for adapter in AGENT_TASK_QUEUE_TOOL_ADAPTERS.values()} == {"task_queue"}
    assert {adapter.mutability for adapter in AGENT_TASK_QUEUE_TOOL_ADAPTERS.values()} == {"read"}
    assert (
        AGENT_TASK_QUEUE_TOOL_ADAPTERS["plan_chapter_conflict_recovery"].handler.__name__
        == "_plan_chapter_conflict_recovery"
    )
    assert (
        AGENT_TASK_QUEUE_TOOL_ADAPTERS["inspect_agent_job_projection"].handler.__name__
        == "_inspect_agent_job_projection"
    )
    assert (
        AGENT_TASK_QUEUE_TOOL_ADAPTERS["inspect_agent_event_projection"].handler.__name__
        == "_inspect_agent_event_projection"
    )


def test_review_revision_tool_adapters_live_in_dedicated_module():
    names = list(REVIEW_REVISION_AGENT_TOOL_ADAPTERS)

    assert names == [
        "review_chapter_quality",
        "review_chapter_continuity",
        "plan_chapter_revision",
        "create_revision_draft",
        "prepare_create_revision_draft_execution",
        "execute_create_revision_draft_with_approval",
        "apply_planner_revision_patch",
        "prepare_apply_planner_revision_patch_execution",
        "execute_apply_planner_revision_patch_with_approval",
        "expand_chapter_to_target",
        "prepare_expand_chapter_to_target_execution",
        "execute_expand_chapter_to_target_with_approval",
        "compress_chapter_to_target",
        "prepare_compress_chapter_to_target_execution",
        "execute_compress_chapter_to_target_with_approval",
    ]
    assert {adapter.category for adapter in REVIEW_REVISION_AGENT_TOOL_ADAPTERS.values()} == {"review", "revision"}
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["review_chapter_quality"].mutability == "read"
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["create_revision_draft"].mutability == "guarded_write"
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["create_revision_draft"].write_policy == "approval_required_redirect"
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["prepare_create_revision_draft_execution"].mutability == "read"
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["execute_create_revision_draft_with_approval"].mutability == "write"
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["apply_planner_revision_patch"].mutability == "guarded_write"
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["apply_planner_revision_patch"].write_policy == (
        "approval_required_redirect"
    )
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["prepare_apply_planner_revision_patch_execution"].mutability == "read"
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["execute_apply_planner_revision_patch_with_approval"].mutability == (
        "write"
    )
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["expand_chapter_to_target"].mutability == "guarded_write"
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["expand_chapter_to_target"].write_policy == (
        "approval_required_redirect"
    )
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["prepare_expand_chapter_to_target_execution"].mutability == "read"
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["execute_expand_chapter_to_target_with_approval"].mutability == "write"
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["compress_chapter_to_target"].mutability == "guarded_write"
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["compress_chapter_to_target"].write_policy == (
        "approval_required_redirect"
    )
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["prepare_compress_chapter_to_target_execution"].mutability == "read"
    assert REVIEW_REVISION_AGENT_TOOL_ADAPTERS["execute_compress_chapter_to_target_with_approval"].mutability == (
        "write"
    )
    assert (
        REVIEW_REVISION_AGENT_TOOL_ADAPTERS["apply_planner_revision_patch"].handler.__name__
        == "_apply_planner_revision_patch"
    )


def test_world_model_tool_adapters_live_in_dedicated_module():
    names = list(WORLD_MODEL_AGENT_TOOL_ADAPTERS)

    assert names == [
        "import_setup_world_model",
        "prepare_import_setup_world_model_execution",
        "execute_import_setup_world_model_with_approval",
        "analyze_chapter_world_model",
        "prepare_analyze_chapter_world_model_execution",
        "execute_analyze_chapter_world_model_with_approval",
        "review_world_model_proposals",
        "inspect_agent_world_model_route",
        "plan_world_model_proposal_resolution",
        "preview_world_model_proposal_resolution",
        "apply_world_model_proposal_resolution",
        "prepare_apply_world_model_proposal_resolution",
        "execute_apply_world_model_proposal_resolution_with_approval",
        "draft_world_model_proposal_resolution_decisions",
        "draft_high_value_world_proposal_resolution_decisions",
        "seed_continuity_anchor_proposals",
        "prepare_seed_continuity_anchor_proposals_execution",
        "execute_seed_continuity_anchor_proposals_with_approval",
    ]
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["import_setup_world_model"].mutability == "guarded_write"
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["import_setup_world_model"].write_policy == "approval_required_redirect"
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["execute_import_setup_world_model_with_approval"].mutability == "write"
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["analyze_chapter_world_model"].mutability == "guarded_write"
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["analyze_chapter_world_model"].write_policy == "approval_required_redirect"
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["execute_analyze_chapter_world_model_with_approval"].mutability == "write"
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["inspect_agent_world_model_route"].mutability == "read"
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["apply_world_model_proposal_resolution"].mutability == "guarded_write"
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["apply_world_model_proposal_resolution"].write_policy == (
        "approval_required_redirect"
    )
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["prepare_apply_world_model_proposal_resolution"].mutability == "read"
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["execute_apply_world_model_proposal_resolution_with_approval"].mutability == (
        "write"
    )
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["seed_continuity_anchor_proposals"].mutability == "guarded_write"
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["seed_continuity_anchor_proposals"].write_policy == (
        "approval_required_redirect"
    )
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["prepare_seed_continuity_anchor_proposals_execution"].mutability == "read"
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["execute_seed_continuity_anchor_proposals_with_approval"].mutability == (
        "write"
    )
    assert (
        WORLD_MODEL_AGENT_TOOL_ADAPTERS["apply_world_model_proposal_resolution"].handler.__name__
        == "_apply_world_model_proposal_resolution"
    )


def test_knowledge_base_tool_adapters_live_in_dedicated_module():
    names = list(KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS)

    assert names == [
        "inspect_agent_knowledge_base_route",
        "plan_post_chapter_memory_capture",
        "record_agent_knowledge_base_candidate",
    ]
    assert {adapter.category for adapter in KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS.values()} == {"knowledge_base"}
    assert KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS["inspect_agent_knowledge_base_route"].mutability == "read"
    assert KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS["record_agent_knowledge_base_candidate"].mutability == "guarded_write"
    assert (
        KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS["record_agent_knowledge_base_candidate"].write_policy
        == "approval_required_redirect"
    )
    assert (
        KNOWLEDGE_BASE_AGENT_TOOL_ADAPTERS["record_agent_knowledge_base_candidate"].handler.__name__
        == "_record_agent_knowledge_base_candidate"
    )


def test_knowledge_base_tool_adapter_builder_adds_approval_chain():
    adapters = build_knowledge_base_agent_tool_adapters(approval_tool_metadata_provider=lambda plan: {})
    names = list(adapters)

    assert names == [
        "inspect_agent_knowledge_base_route",
        "plan_post_chapter_memory_capture",
        "record_agent_knowledge_base_candidate",
        "prepare_record_agent_knowledge_base_candidate",
        "execute_record_agent_knowledge_base_candidate_with_approval",
    ]
    assert adapters["prepare_record_agent_knowledge_base_candidate"].mutability == "read"
    assert adapters["execute_record_agent_knowledge_base_candidate_with_approval"].mutability == "write"
    assert (
        adapters["execute_record_agent_knowledge_base_candidate_with_approval"].handler.__name__
        == "_execute_record_agent_knowledge_base_candidate_with_approval"
    )


def test_longform_tool_adapters_live_in_dedicated_module():
    adapters = build_longform_agent_tool_adapters(approval_tool_metadata_provider=lambda plan: {})
    names = list(adapters)

    assert names == [
        "plan_longform_chapter_batch",
        "enqueue_longform_chapter_batch",
        "prepare_enqueue_longform_chapter_batch",
        "execute_enqueue_longform_chapter_batch_with_approval",
        "inspect_longform_chapter_batch",
        "execute_longform_chapter_batch_preflight",
        "prepare_longform_chapter_batch_preflight",
        "execute_longform_chapter_batch_preflight_with_approval",
        "prepare_longform_chapter_batch_execution",
        "prepare_longform_chapter_batch_execution_prepare",
        "execute_longform_chapter_batch_execution_prepare_with_approval",
        "execute_longform_chapter_batch",
        "review_longform_chapter_batch_execution",
        "prepare_longform_chapter_batch_execution_review",
        "execute_longform_chapter_batch_execution_review_with_approval",
        "route_longform_chapter_batch_after_review",
        "prepare_longform_chapter_batch_after_review_route",
        "execute_longform_chapter_batch_after_review_route_with_approval",
    ]
    assert {adapter.category for adapter in adapters.values()} == {"task_queue"}
    assert adapters["plan_longform_chapter_batch"].mutability == "read"
    assert adapters["enqueue_longform_chapter_batch"].mutability == "guarded_write"
    assert adapters["enqueue_longform_chapter_batch"].write_policy == "approval_required_redirect"
    assert adapters["prepare_enqueue_longform_chapter_batch"].mutability == "read"
    assert adapters["execute_enqueue_longform_chapter_batch_with_approval"].mutability == "write"
    assert adapters["inspect_longform_chapter_batch"].mutability == "read"
    assert adapters["execute_longform_chapter_batch_preflight"].mutability == "guarded_write"
    assert adapters["execute_longform_chapter_batch_preflight"].write_policy == "approval_required_redirect"
    assert adapters["prepare_longform_chapter_batch_preflight"].mutability == "read"
    assert adapters["execute_longform_chapter_batch_preflight_with_approval"].mutability == "write"
    assert adapters["prepare_longform_chapter_batch_execution"].mutability == "guarded_write"
    assert adapters["prepare_longform_chapter_batch_execution"].write_policy == "approval_required_redirect"
    assert adapters["prepare_longform_chapter_batch_execution_prepare"].mutability == "read"
    assert adapters["execute_longform_chapter_batch_execution_prepare_with_approval"].mutability == "write"
    assert adapters["execute_longform_chapter_batch"].mutability == "write"
    assert adapters["review_longform_chapter_batch_execution"].mutability == "guarded_write"
    assert adapters["review_longform_chapter_batch_execution"].write_policy == "approval_required_redirect"
    assert adapters["prepare_longform_chapter_batch_execution_review"].mutability == "read"
    assert adapters["execute_longform_chapter_batch_execution_review_with_approval"].mutability == "write"
    assert adapters["route_longform_chapter_batch_after_review"].mutability == "guarded_write"
    assert adapters["route_longform_chapter_batch_after_review"].write_policy == "approval_required_redirect"
    assert adapters["prepare_longform_chapter_batch_after_review_route"].mutability == "read"
    assert adapters["execute_longform_chapter_batch_after_review_route_with_approval"].mutability == "write"
    assert adapters["execute_longform_chapter_batch"].handler.__name__ == "_execute_longform_chapter_batch"


@pytest.mark.asyncio
async def test_tool_executor_handles_describe_agent_tools(db_session):
    project = Project(name="Executor Tool Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-1"),
        WritingAgentToolRequest(tool_name="describe_agent_tools", params={"chapter_index": 1}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["agent_profile_scope"]["status"] == "not_requested"
    assert "visible_tools" in result.output
    assert "hidden_tools" in result.output
    tools = {tool["name"]: tool for tool in [*result.output["visible_tools"], *result.output["hidden_tools"]]}
    describe_surface = tools["describe_agent_tools"]["agent_tool_surface"]
    assert describe_surface["mutability"] == "read"
    assert describe_surface["permission_level"] == "read"
    assert describe_surface["parallel_safe"] is True
    assert tools["verify_agent_plan_approval_contract"]["agent_tool_surface"]["mutability"] == "read"
    assert tools["verify_agent_plan_approval_contract"]["agent_tool_surface"]["requires_confirmation"] is False
    assert tools["preflight_writing"]["agent_tool_surface"]["mutability"] == "read"
    assert tools["preflight_writing"]["agent_tool_surface"]["permission_level"] == "read"
    assert tools["inspect_longform_chapter_batch"]["agent_tool_surface"]["mutability"] == "read"
    assert tools["seed_continuity_anchor_proposals"]["agent_tool_surface"]["mutability"] == "guarded_write"
    assert tools["seed_continuity_anchor_proposals"]["agent_tool_surface"]["permission_level"] == "confirm_required"
    assert tools["review_longform_chapter_batch_execution"]["agent_tool_surface"]["mutability"] == "guarded_write"
    assert tools["review_longform_chapter_batch_execution"]["agent_tool_surface"]["permission_level"] == "confirm_required"
    assert tools["execute_longform_chapter_batch"]["agent_tool_surface"]["mutability"] == "guarded_write"
    assert tools["execute_longform_chapter_batch"]["agent_tool_surface"]["permission_level"] == "confirm_required"


@pytest.mark.asyncio
async def test_tool_executor_scopes_describe_agent_tools_by_agent_profile(db_session):
    project = _seed_profile_scope_project(db_session)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-profile-scope"),
        WritingAgentToolRequest(
            tool_name="describe_agent_tools",
            params={"chapter_index": 2, "agent_profile": "reviewer_worker"},
        ),
    )

    assert result.handled is True
    assert result.output["agent_profile_scope"]["status"] == "applied"
    assert result.output["agent_profile_scope"]["agent_profile"] == "reviewer_worker"
    assert "generate_chapter" in result.output["agent_profile_scope"]["profile_filtered_visible_tools"]
    visible = {tool["name"] for tool in result.output["visible_tools"]}
    hidden = {tool["name"] for tool in result.output["hidden_tools"]}

    assert "review_chapter_quality" in visible
    assert "generate_chapter" not in visible
    assert "generate_chapter" not in hidden
    assert "generate_chapter" not in result.output["tool_policy_projection"]["approval_required_tools"]
    assert "generate_chapter" not in result.output["agent_profile_tool_projection"]["profiles"]["reviewer_worker"]["allowed_visible_tools"]


@pytest.mark.asyncio
async def test_tool_executor_fails_closed_for_unknown_describe_agent_tools_profile(db_session):
    project = _seed_profile_scope_project(db_session)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-profile-unknown"),
        WritingAgentToolRequest(
            tool_name="describe_agent_tools",
            params={"chapter_index": 2, "agent_profile": "unknown_worker"},
        ),
    )

    assert result.handled is True
    assert result.output["agent_profile_scope"]["status"] == "unknown_profile"
    assert result.output["visible_tools"] == []
    assert result.output["hidden_tools"] == []
    assert "reviewer_worker" in result.output["agent_profile_scope"]["available_profiles"]


@pytest.mark.asyncio
async def test_tool_executor_handles_inspect_agent_slash_command_route(db_session):
    project = Project(name="Slash Command Route Projection")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-slash"),
        WritingAgentToolRequest(tool_name="inspect_agent_slash_command_route", params={}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "ready"
    assert result.output["version"] == "phase103.slash_command_route_projection.v1"
    assert result.output["routes"] == []
    assert result.output["trace"]["public_commands"] == ["continue", "status", "clear", "compact"]
    assert result.output["trace"]["session_or_control_commands"] == ["continue", "status", "clear", "compact"]
    assert result.output["trace"]["legacy_aliases"] == ["setup", "storyline", "outline", "chapter"]


@pytest.mark.asyncio
async def test_tool_executor_handles_inspect_agent_dialog_route_projection(db_session):
    project = Project(name="Dialog Route Projection")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-dialog-route"),
        WritingAgentToolRequest(tool_name="inspect_agent_dialog_route_projection", params={}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "ready"
    assert result.output["version"] == "phase104.dialog_route_projection.v1"
    keys = {
        (route["source"], route["action_type"], route.get("command_name"))
        for route in result.output["routes"]
    }
    assert all(source != "slash_command" for source, _, _ in keys)
    assert ("text_intent", "preview_chapter", None) in keys
    assert ("button_action", "preview_chapter", None) in keys
    assert result.output["trace"]["sources"] == ["slash_command", "text_intent", "button_action"]
    assert result.output["trace"]["unsupported_tools"] == []


@pytest.mark.asyncio
async def test_tool_executor_handles_inspect_agent_route_preference_projection(db_session):
    project = Project(name="Route Preference Projection")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-preference"),
        WritingAgentToolRequest(tool_name="inspect_agent_route_preference_projection", params={}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "ready"
    assert result.output["version"] == "phase115.route_preference_projection.v1"
    chapter_route = next(
        route
        for route in result.output["routes"]
        if route["source"] == "text_intent" and route["action_type"] == "preview_chapter"
    )
    assert chapter_route["current_tool_name"] == "generate_chapter"
    assert chapter_route["preferred_tool_chain"] == [
        "prepare_generate_chapter_execution",
        "execute_generate_chapter_with_approval",
    ]
    assert chapter_route["runtime_route_changed"] is False
    assert chapter_route["migration_status"] == "recommended_not_applied"
    expected_routes = {
        "preview_setup": [
            "prepare_generate_setup_execution",
            "execute_generate_setup_with_approval",
        ],
        "preview_storyline": [
            "prepare_generate_storyline_execution",
            "execute_generate_storyline_with_approval",
        ],
        "preview_outline": [
            "prepare_generate_outline_execution",
            "execute_generate_outline_with_approval",
        ],
    }
    for action_type, preferred_chain in expected_routes.items():
        route = next(
            route
            for route in result.output["routes"]
            if route["source"] == "text_intent" and route["action_type"] == action_type
        )
        assert route["preferred_tool_chain"] == preferred_chain
        assert route["preferred_prepare_tool_name"] == preferred_chain[0]
        assert route["preferred_execute_tool_name"] == preferred_chain[1]
        assert route["runtime_tool_name"] == route["current_tool_name"]
        assert route["runtime_route_changed"] is False
        assert route["runtime_behavior_changed"] is False
        assert route["migration_status"] == "recommended_not_applied"
    assert result.output["trace"]["runtime_behavior_changed"] is False


@pytest.mark.asyncio
async def test_tool_executor_handles_inspect_agent_route_preference_projection_opt_in_metadata(db_session):
    project = Project(name="Route Preference Projection Opt In")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-preference-opt-in"),
        WritingAgentToolRequest(
            tool_name="inspect_agent_route_preference_projection",
            params={
                "source": "text_intent",
                "approval_chain_opt_in_action_types": ["preview_setup"],
            },
        ),
    )

    setup_route = next(route for route in result.output["routes"] if route["action_type"] == "preview_setup")
    assert result.handled is True
    assert result.output["summary"]["opt_in_declared_count"] == 1
    assert result.output["trace"]["approval_chain_opt_in_action_types"] == ["preview_setup"]
    assert setup_route["approval_chain_opt_in_declared"] is True
    assert setup_route["migration_status"] == "opt_in_declared"


@pytest.mark.asyncio
async def test_tool_executor_handles_inspect_agent_route_preference_projection_migration_suggestion(db_session):
    project = Project(name="Route Preference Migration Suggestion")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-preference-suggestion"),
        WritingAgentToolRequest(
            tool_name="inspect_agent_route_preference_projection",
            params={"source": "text_intent"},
        ),
    )

    setup_route = next(route for route in result.output["routes"] if route["action_type"] == "preview_setup")
    suggestion = setup_route["approval_chain_opt_in_suggestion"]
    assert result.handled is True
    assert suggestion["status"] == "available"
    assert suggestion["route_metadata_patch"] == {"use_agent_approval_chain": True}
    assert suggestion["expected_prepare_tool_name"] == "prepare_generate_setup_execution"


@pytest.mark.asyncio
async def test_tool_executor_handles_route_approval_opt_in_plan(db_session):
    project = Project(name="Route Approval Opt In Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-opt-in-plan"),
        WritingAgentToolRequest(
            tool_name="plan_agent_route_approval_opt_in",
            params={
                "action_type": "preview_setup",
                "source": "slash_command",
                "command_name": "setup",
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "ready"
    assert result.output["can_apply"] is True
    assert result.output["write_performed"] is False
    assert result.output["metadata_patch"] == {"use_agent_approval_chain": True}
    assert result.output["route_after"]["use_agent_approval_chain"] is True


@pytest.mark.asyncio
async def test_tool_executor_handles_pending_action_route_opt_in_plan(db_session):
    project = Project(name="Pending Route Approval Opt In Plan")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-pending-route-opt-in-plan"),
        WritingAgentToolRequest(
            tool_name="plan_agent_route_approval_opt_in",
            params={"pending_action_id": pending.id},
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "ready"
    assert result.output["can_apply"] is True
    assert result.output["write_performed"] is False
    assert result.output["metadata_patch"] == {"use_agent_approval_chain": True}
    assert result.output["trace"]["pending_action_id"] == pending.id
    assert result.output["trace"]["pending_action_type"] == "preview_setup"
    assert result.output["trace"]["pending_action_route_source"] == "pending_action"
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_blocks_missing_pending_action_route_opt_in_plan(db_session):
    project = Project(name="Missing Pending Route Approval Opt In Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-missing-pending-route-plan"),
        WritingAgentToolRequest(
            tool_name="plan_agent_route_approval_opt_in",
            params={"pending_action_id": "missing-pending-action"},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["can_apply"] is False
    assert result.output["write_performed"] is False
    assert result.output["risk"]["codes"] == ["pending_action_not_found"]
    assert result.output["trace"]["pending_action_id"] == "missing-pending-action"


@pytest.mark.asyncio
async def test_tool_executor_previews_pending_action_route_opt_in_apply_diff(db_session):
    project = Project(name="Pending Route Opt In Apply Preview")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route, "command_args": "雾港悬疑"},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-apply-preview"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply",
            params={"pending_action_id": pending.id},
        ),
    )

    db_session.refresh(pending)
    diff = result.output["params_diff"]["agent_route"]
    assert result.handled is True
    assert result.output["status"] == "ready"
    assert result.output["write_performed"] is False
    assert result.output["route_plan"]["status"] == "ready"
    assert result.output["params_before"] == original_params
    assert result.output["params_after"]["agent_route"]["use_agent_approval_chain"] is True
    assert diff["before"] == original_params["agent_route"]
    assert diff["after"]["use_agent_approval_chain"] is True
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_previews_pending_action_route_opt_in_apply_already_declared_no_diff(db_session):
    project = Project(name="Pending Route Opt In Apply Preview Declared")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = {
        **build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup"),
        "use_agent_approval_chain": True,
    }
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-apply-preview-declared"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply",
            params={"pending_action_id": pending.id},
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "already_declared"
    assert result.output["write_performed"] is False
    assert result.output["params_diff"] == {}
    assert result.output["params_after"] == original_params
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_blocks_missing_pending_action_route_opt_in_apply_preview(db_session):
    project = Project(name="Missing Pending Route Opt In Apply Preview")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-missing-route-apply-preview"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply",
            params={"pending_action_id": "missing-pending-action"},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["risk"]["codes"] == ["pending_action_not_found"]
    assert result.output["params_diff"] == {}


@pytest.mark.asyncio
async def test_tool_executor_blocks_pending_action_route_opt_in_apply_preview_without_agent_route(db_session):
    project = Project(name="Pending Route Opt In Apply Preview Missing Route")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "command_args": "雾港悬疑"},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-apply-preview-missing-route"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply",
            params={"pending_action_id": pending.id},
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["risk"]["codes"] == ["pending_action_agent_route_missing"]
    assert result.output["params_diff"] == {}
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_blocks_pending_action_route_opt_in_apply_preview_with_top_level_override(db_session):
    project = Project(name="Pending Route Opt In Apply Preview Override")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route, "use_agent_approval_chain": False},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-apply-preview-override"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply",
            params={"pending_action_id": pending.id},
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["risk"]["codes"] == ["pending_action_top_level_override"]
    assert result.output["params_diff"] == {}
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_previews_pending_route_opt_in_apply_contract(db_session):
    project = Project(name="Pending Route Opt In Apply Contract")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route, "command_args": "雾港悬疑"},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-contract"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply_contract",
            params={"pending_action_id": pending.id},
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "requires_confirmation"
    assert result.output["required_confirmation"] is True
    assert result.output["approval_contract_hash"].startswith("approval:")
    assert (
        result.output["approval_contract"]["approval"]["approval_contract_hash"]
        == result.output["approval_contract_hash"]
    )
    assert result.output["route_apply_preview"]["status"] == "ready"
    assert result.output["route_apply_preview"]["write_performed"] is False
    assert result.output["approval_contract"]["mutation_target"] == "PendingAction.params.agent_route"
    assert result.output["approval_contract"]["mutation_path"] == "params.agent_route.use_agent_approval_chain"
    assert result.output["recommended_next_tools"] == ["prepare_apply_pending_action_route_approval_opt_in"]
    assert result.output["recommended_next_tool_calls"] == [
        {
            "tool_name": "prepare_apply_pending_action_route_approval_opt_in",
            "visibility": "agent_internal",
            "requires_confirmation": False,
            "params": {
                "pending_action_id": pending.id,
            },
        }
    ]
    assert pending.params == original_params


def test_pending_route_opt_in_apply_contract_hash_is_stable_for_trace_and_unrelated_params():
    from app.services.writing_agent.slash_command_route import (
        build_pending_action_route_approval_opt_in_apply_contract,
        preview_pending_action_route_approval_opt_in_apply,
    )

    route_plan = {
        "status": "ready",
        "version": "phase196.route_approval_opt_in_plan.v1",
        "metadata_patch": {"use_agent_approval_chain": True},
        "route_before": {"agent_tool_name": "generate_setup"},
        "route_after": {"agent_tool_name": "generate_setup", "use_agent_approval_chain": True},
        "preference": {
            "preferred_prepare_tool_name": "prepare_generate_setup_execution",
            "preferred_execute_tool_name": "execute_generate_setup_with_approval",
        },
        "risk": {"codes": []},
        "trace": {"volatile": "a"},
    }
    preview_a = preview_pending_action_route_approval_opt_in_apply(
        pending_action_id="pending-1",
        pending_action_type="preview_setup",
        pending_params={"agent_route": {"agent_tool_name": "generate_setup"}, "command_args": "A"},
        route_plan=route_plan,
    )
    preview_b = preview_pending_action_route_approval_opt_in_apply(
        pending_action_id="pending-1",
        pending_action_type="preview_setup",
        pending_params={"command_args": "B", "agent_route": {"agent_tool_name": "generate_setup"}},
        route_plan={**route_plan, "trace": {"volatile": "b"}},
    )

    contract_a = build_pending_action_route_approval_opt_in_apply_contract(
        project_id="project-1",
        route_apply_preview=preview_a,
    )
    contract_b = build_pending_action_route_approval_opt_in_apply_contract(
        project_id="project-1",
        route_apply_preview=preview_b,
    )

    assert contract_a["approval_contract_hash"] == contract_b["approval_contract_hash"]


def test_pending_route_opt_in_apply_contract_hash_changes_for_target_or_route_after():
    from app.services.writing_agent.slash_command_route import (
        build_pending_action_route_approval_opt_in_apply_contract,
        preview_pending_action_route_approval_opt_in_apply,
    )

    route_plan = {
        "status": "ready",
        "version": "phase196.route_approval_opt_in_plan.v1",
        "metadata_patch": {"use_agent_approval_chain": True},
        "route_before": {"agent_tool_name": "generate_setup"},
        "route_after": {"agent_tool_name": "generate_setup", "use_agent_approval_chain": True},
        "preference": {
            "preferred_prepare_tool_name": "prepare_generate_setup_execution",
            "preferred_execute_tool_name": "execute_generate_setup_with_approval",
        },
        "risk": {"codes": []},
    }
    preview_a = preview_pending_action_route_approval_opt_in_apply(
        pending_action_id="pending-1",
        pending_action_type="preview_setup",
        pending_params={"agent_route": {"agent_tool_name": "generate_setup"}},
        route_plan=route_plan,
    )
    preview_b = preview_pending_action_route_approval_opt_in_apply(
        pending_action_id="pending-2",
        pending_action_type="preview_setup",
        pending_params={"agent_route": {"agent_tool_name": "generate_setup"}},
        route_plan=route_plan,
    )
    preview_c = preview_pending_action_route_approval_opt_in_apply(
        pending_action_id="pending-1",
        pending_action_type="preview_setup",
        pending_params={"agent_route": {"agent_tool_name": "generate_setup"}},
        route_plan={
            **route_plan,
            "route_after": {
                "agent_tool_name": "generate_setup",
                "use_agent_approval_chain": True,
                "source": "slash_command",
            },
        },
    )

    contract_a = build_pending_action_route_approval_opt_in_apply_contract(
        project_id="project-1",
        route_apply_preview=preview_a,
    )
    contract_b = build_pending_action_route_approval_opt_in_apply_contract(
        project_id="project-1",
        route_apply_preview=preview_b,
    )
    contract_c = build_pending_action_route_approval_opt_in_apply_contract(
        project_id="project-1",
        route_apply_preview=preview_c,
    )

    assert contract_a["approval_contract_hash"] != contract_b["approval_contract_hash"]
    assert contract_a["approval_contract_hash"] != contract_c["approval_contract_hash"]


@pytest.mark.asyncio
async def test_tool_executor_blocks_pending_route_opt_in_apply_contract_when_preview_blocked(db_session):
    project = Project(name="Blocked Pending Route Opt In Apply Contract")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-contract-blocked"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply_contract",
            params={"pending_action_id": "missing-pending-action"},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["required_confirmation"] is False
    assert result.output["approval_contract_hash"] is None
    assert result.output["risk"]["codes"] == ["pending_action_not_found"]
    assert result.output["recommended_next_tools"] == []
    assert result.output["recommended_next_tool_calls"] == []


@pytest.mark.asyncio
async def test_tool_executor_hides_foreign_non_pending_route_opt_in_apply_contract_params(db_session):
    own_project = Project(name="Own Route Opt In Apply Contract")
    foreign_project = Project(name="Foreign Route Opt In Apply Contract")
    db_session.add_all([own_project, foreign_project])
    db_session.commit()
    foreign_dialog = Dialog(project_id=foreign_project.id, state="pending_action")
    db_session.add(foreign_dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=foreign_dialog.id,
        type="preview_setup",
        status="resolved",
        params={
            "project_id": foreign_project.id,
            "agent_route": route,
            "command_args": "foreign-secret",
        },
    )
    db_session.add(pending)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=own_project.id, run_id="run-route-contract-foreign"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply_contract",
            params={"pending_action_id": pending.id},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["required_confirmation"] is False
    assert result.output["approval_contract_hash"] is None
    assert result.output["risk"]["codes"] == ["pending_action_not_found"]
    assert result.output["route_apply_preview"]["params_before"] == {}
    assert result.output["route_apply_preview"]["params_after"] == {}
    assert result.output["recommended_next_tools"] == []
    assert result.output["recommended_next_tool_calls"] == []
    assert "foreign-secret" not in str(result.output)


@pytest.mark.asyncio
async def test_tool_executor_does_not_require_route_opt_in_apply_contract_for_already_declared(db_session):
    project = Project(name="Noop Pending Route Opt In Apply Contract")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = {
        **build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup"),
        "use_agent_approval_chain": True,
    }
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route},
    )
    db_session.add(pending)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-route-contract-noop"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply_contract",
            params={"pending_action_id": pending.id},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "not_required"
    assert result.output["required_confirmation"] is False
    assert result.output["approval_contract_hash"] is None
    assert result.output["route_apply_preview"]["status"] == "already_declared"
    assert result.output["recommended_next_tools"] == []
    assert result.output["recommended_next_tool_calls"] == []


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_updates_pending_params(db_session):
    project = Project(name="Apply Route Opt In Approval")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route, "command_args": "雾港悬疑"},
    )
    db_session.add(pending)
    db_session.commit()
    contract = await _preview_route_opt_in_apply_contract(db_session, project.id, pending.id)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": contract["approval_contract_hash"],
                "approval_contract": contract["approval_contract"],
            },
        ),
    )

    db_session.expire_all()
    reloaded = db_session.query(PendingAction).filter(PendingAction.id == pending.id).first()
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["write_performed"] is False
    assert result.output["required_approval"]["prepare_tool"] == "prepare_apply_pending_action_route_approval_opt_in"
    assert result.output["required_approval"]["execute_tool"] == (
        "execute_apply_pending_action_route_approval_opt_in_with_approval"
    )
    assert reloaded.params == pending.params
    assert reloaded.status == "pending"


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_requires_confirmation(db_session):
    project = Project(name="Apply Route Opt In Approval Confirmation")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-confirm"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={"pending_action_id": pending.id},
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["reason"] == "confirmation_required"
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_blocks_hash_mismatch(db_session):
    project = Project(name="Apply Route Opt In Approval Hash")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)
    contract = await _preview_route_opt_in_apply_contract(db_session, project.id, pending.id)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-hash"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": "approval:mismatch",
                "approval_contract": contract["approval_contract"],
            },
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["reason"] == "approval_contract_hash_mismatch"
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_blocks_contract_snapshot_mismatch(db_session):
    project = Project(name="Apply Route Opt In Approval Snapshot")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)
    contract = await _preview_route_opt_in_apply_contract(db_session, project.id, pending.id)
    tampered_contract = {**contract["approval_contract"], "mutation_path": "params.agent_route.tampered"}

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-snapshot"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": contract["approval_contract_hash"],
                "approval_contract": tampered_contract,
            },
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["reason"] == "approval_contract_snapshot_mismatch"
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_blocks_stale_pending_status(db_session):
    project = Project(name="Apply Route Opt In Approval Stale")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)
    contract = await _preview_route_opt_in_apply_contract(db_session, project.id, pending.id)
    pending.status = "resolved"
    db_session.add(pending)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-stale"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": contract["approval_contract_hash"],
                "approval_contract": contract["approval_contract"],
            },
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["reason"] == "pending_action_not_pending"
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_blocks_stale_pending_resolved_at(db_session):
    project = Project(name="Apply Route Opt In Approval Resolved At")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)
    contract = await _preview_route_opt_in_apply_contract(db_session, project.id, pending.id)
    pending.resolved_at = datetime.now()
    db_session.add(pending)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-resolved-at"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": contract["approval_contract_hash"],
                "approval_contract": contract["approval_contract"],
            },
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["reason"] == "pending_action_not_pending"
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_blocks_missing_hash_or_contract(db_session):
    project = Project(name="Apply Route Opt In Approval Missing Contract")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)

    missing_hash = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-missing-hash"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract": {"approval": {"approval_contract_hash": "approval:any"}},
            },
        ),
    )
    missing_contract = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-missing-contract"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": "approval:any",
            },
        ),
    )

    db_session.refresh(pending)
    assert missing_hash.handled is True
    assert missing_hash.output["reason"] == "approval_contract_hash_required"
    assert missing_contract.handled is True
    assert missing_contract.output["reason"] == "approval_contract_required"
    assert pending.params == original_params


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_blocks_stale_pending_route_after_contract(db_session):
    project = Project(name="Apply Route Opt In Approval Route Drift")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route},
    )
    db_session.add(pending)
    db_session.commit()
    contract = await _preview_route_opt_in_apply_contract(db_session, project.id, pending.id)
    drifted_route = {**route, "command_name": "setup-drift"}
    pending.params = {"project_id": project.id, "agent_route": drifted_route}
    db_session.add(pending)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-route-drift"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": contract["approval_contract_hash"],
                "approval_contract": contract["approval_contract"],
            },
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["reason"] == "approval_contract_hash_mismatch"
    assert pending.params["agent_route"]["command_name"] == "setup-drift"


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_hides_foreign_pending_params(db_session):
    own_project = Project(name="Own Apply Route Opt In")
    foreign_project = Project(name="Foreign Apply Route Opt In")
    db_session.add_all([own_project, foreign_project])
    db_session.commit()
    foreign_dialog = Dialog(project_id=foreign_project.id, state="pending_action")
    db_session.add(foreign_dialog)
    db_session.commit()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=foreign_dialog.id,
        type="preview_setup",
        params={
            "project_id": foreign_project.id,
            "agent_route": route,
            "command_args": "foreign-secret",
        },
    )
    db_session.add(pending)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=own_project.id, run_id="run-apply-route-opt-in-foreign"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": "approval:any",
                "approval_contract": {"approval": {"approval_contract_hash": "approval:any"}},
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["reason"] == "pending_action_not_found"
    assert "foreign-secret" not in str(result.output)


@pytest.mark.asyncio
async def test_tool_executor_apply_route_opt_in_approval_blocks_when_no_diff_required(db_session):
    project = Project(name="Apply Route Opt In Approval No Diff")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.commit()
    route = {
        **build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup"),
        "use_agent_approval_chain": True,
    }
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route},
    )
    db_session.add(pending)
    db_session.commit()
    original_params = dict(pending.params)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-apply-route-opt-in-no-diff"),
        WritingAgentToolRequest(
            tool_name="apply_pending_action_route_approval_opt_in",
            params={
                "pending_action_id": pending.id,
                "confirm_apply": True,
                "approval_contract_hash": "approval:any",
                "approval_contract": {"approval": {"approval_contract_hash": "approval:any"}},
            },
        ),
    )

    db_session.refresh(pending)
    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["write_performed"] is False
    assert result.output["reason"] == "route_apply_contract_not_required"
    assert pending.params == original_params


async def _preview_route_opt_in_apply_contract(db_session, project_id: str, pending_action_id: str) -> dict:
    preview = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project_id, run_id="run-route-contract-helper"),
        WritingAgentToolRequest(
            tool_name="preview_pending_action_route_approval_opt_in_apply_contract",
            params={"pending_action_id": pending_action_id},
        ),
    )
    assert preview.handled is True
    assert preview.output["status"] == "requires_confirmation"
    return preview.output


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_control_plane_projection(db_session):
    project = Project(name="Dialog Control Plane Projection")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-control-plane"),
        WritingAgentToolRequest(tool_name="inspect_agent_dialog_control_plane_projection", params={}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "ready"
    assert result.output["version"] == "phase191.dialog_control_plane_projection.v1"
    actions_by_type = {action["action_type"]: action for action in result.output["actions"]}
    setup_action = actions_by_type["generate_setup"]
    assert setup_action["current_runtime_tool_name"] == "prepare_generate_setup_execution"
    assert setup_action["current_approval_execute_tool_name"] == "execute_generate_setup_with_approval"
    assert setup_action["recommended_tool_chain"] == [
        "prepare_generate_setup_execution",
        "execute_generate_setup_with_approval",
    ]
    assert setup_action["runtime_behavior_changed"] is True
    assert setup_action["runtime_already_uses_approval_chain"] is True
    chapter_action = actions_by_type["generate_chapter"]
    assert chapter_action["current_runtime_tool_name"] == "prepare_generate_chapter_execution"
    assert chapter_action["current_approval_execute_tool_name"] == "execute_generate_chapter_with_approval"
    assert chapter_action["recommended_tool_chain"] == [
        "prepare_generate_chapter_execution",
        "execute_generate_chapter_with_approval",
    ]
    assert chapter_action["runtime_already_uses_approval_chain"] is True
    assert result.output["trace"]["runtime_behavior_changed"] is False


@pytest.mark.asyncio
async def test_tool_executor_handles_inspect_agent_intent_projection(db_session):
    project = Project(name="Intent Projection")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-intent"),
        WritingAgentToolRequest(
            tool_name="inspect_agent_intent_projection",
            params={
                "text": "请开始写正文，从第3章开始生成。",
                "missing_items": [],
                "completed_items": ["setup", "storyline", "outline"],
                "suggested_next_step": "preview_chapter",
            },
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "matched"
    assert result.output["version"] == "phase105.intent_projection.v1"
    assert result.output["rule_id"] == "chapter_intent"
    assert result.output["decision"]["reason_code"] == "intent_rule_matched"
    assert result.output["decision"]["match_evidence"] == [{"kind": "pattern", "name": "chapter_generation_phrase"}]
    assert result.output["candidate"] == {
        "type": "preview_chapter",
        "params": {"chapter_index": 3, "chapter_index_source": "explicit_user"},
    }
    assert result.output["agent_route"]["agent_tool_name"] == "generate_chapter"
    assert result.output["tool_selection"]["selected_tool"] == "generate_chapter"
    assert result.output["extracted_params"] == {"chapter_index": 3, "chapter_index_source": "explicit_user"}


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_setup(db_session):
    project = Project(name="Dialog Intent Agent Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-dialog-intent-plan"),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={
                "text": "帮我创建这个都市悬疑新书的基础设定",
                "missing_items": ["setup", "storyline", "outline"],
                "completed_items": [],
                "suggested_next_step": "preview_setup",
            },
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["version"] == "phase106.dialog_intent_agent_plan.v1"
    assert result.output["intent_projection"]["rule_id"] == "setup_intent"
    assert result.output["planner"]["intent_class"] == "setup_project"
    assert result.output["planner"]["mapped_from_action_type"] == "preview_setup"
    assert [tool["tool_name"] for tool in result.output["tools"]] == [
        "describe_agent_tools",
        "prepare_generate_setup_execution",
    ]


@pytest.mark.asyncio
async def test_tool_executor_dialog_intent_agent_plan_returns_no_plan_for_unmatched_text(db_session):
    project = Project(name="Dialog Intent No Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-dialog-intent-no-plan"),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "今天先随便聊聊"},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "no_plan"
    assert result.output["tools"] == []
    assert result.output["intent_projection"]["status"] == "no_match"
    assert result.output["trace"]["reason"] == "intent_not_matched"


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_memory_tree_read(db_session):
    project = Project(name="Dialog Intent Memory Tree Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-dialog-intent-memory-tree-plan"),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "浏览记忆树里灯塔旧回声"},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "memory_tree_intent"
    assert result.output["planner"]["intent_class"] == "inspect_memory_tree"
    assert result.output["planner"]["mapped_from_action_type"] == "inspect_memory_tree"
    assert result.output["plan"] == {
        "status": "completed",
        "intent_class": "inspect_memory_tree",
        "steps": [
            {
                "step_index": 1,
                "tool_name": "inspect_agent_memory_tree",
                "params": {"query": "灯塔旧回声", "include_ancestors": True},
                "mutability": "read",
                "requires_confirmation": False,
            }
        ],
        "tools": [
            {
                "tool_name": "inspect_agent_memory_tree",
                "params": {"query": "灯塔旧回声", "include_ancestors": True},
            }
        ],
        "approval_contract": {"status": "not_required", "write_steps": []},
    }
    assert result.output["tools"] == [
        {"tool_name": "inspect_agent_memory_tree", "params": {"query": "灯塔旧回声", "include_ancestors": True}}
    ]
    assert result.output["approval_contract"] == {"status": "not_required", "write_steps": []}
    assert result.output["trace"]["reason"] == "planned_direct_read_tool_from_intent_projection"


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_context_compression_read(db_session):
    project = Project(name="Dialog Intent Context Compression Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(
            db=db_session,
            project_id=project.id,
            run_id="run-dialog-intent-context-compression-plan",
        ),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "检查第3章上下文压缩压力"},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "context_compression_intent"
    assert result.output["planner"]["intent_class"] == "inspect_context_compression"
    assert result.output["planner"]["mapped_from_action_type"] == "inspect_context_compression"
    assert result.output["planner"]["chapter_index"] == 3
    assert result.output["plan"] == {
        "status": "completed",
        "intent_class": "inspect_context_compression",
        "steps": [
            {
                "step_index": 1,
                "tool_name": "inspect_agent_context_compression_projection",
                "params": {"chapter_index": 3},
                "mutability": "read",
                "requires_confirmation": False,
            }
        ],
        "tools": [
            {
                "tool_name": "inspect_agent_context_compression_projection",
                "params": {"chapter_index": 3},
            }
        ],
        "approval_contract": {"status": "not_required", "write_steps": []},
    }
    assert result.output["tools"] == [
        {"tool_name": "inspect_agent_context_compression_projection", "params": {"chapter_index": 3}}
    ]
    assert result.output["approval_contract"] == {"status": "not_required", "write_steps": []}
    assert result.output["trace"]["reason"] == "planned_direct_read_tool_from_intent_projection"


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_worker_dispatch_read(db_session):
    project = Project(name="Dialog Intent Worker Dispatch Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(
            db=db_session,
            project_id=project.id,
            run_id="run-dialog-intent-worker-dispatch-plan",
        ),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "检查 reviewer_worker 的 worker 分发和孤儿恢复"},
        ),
    )

    expected_params = {"worker_name": "reviewer_worker", "tasks": []}
    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "worker_dispatch_intent"
    assert result.output["planner"]["intent_class"] == "inspect_worker_dispatch"
    assert result.output["planner"]["mapped_from_action_type"] == "inspect_worker_dispatch"
    assert result.output["plan"] == {
        "status": "completed",
        "intent_class": "inspect_worker_dispatch",
        "steps": [
            {
                "step_index": 1,
                "tool_name": "inspect_agent_worker_dispatch",
                "params": expected_params,
                "mutability": "read",
                "requires_confirmation": False,
            }
        ],
        "tools": [
            {
                "tool_name": "inspect_agent_worker_dispatch",
                "params": expected_params,
            }
        ],
        "approval_contract": {"status": "not_required", "write_steps": []},
    }
    assert result.output["tools"] == [{"tool_name": "inspect_agent_worker_dispatch", "params": expected_params}]
    assert result.output["approval_contract"] == {"status": "not_required", "write_steps": []}
    assert result.output["trace"]["reason"] == "planned_direct_read_tool_from_intent_projection"


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_trace_audit_read(db_session):
    project = Project(name="Dialog Intent Trace Audit Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(
            db=db_session,
            project_id=project.id,
            run_id="run-dialog-intent-trace-audit-plan",
        ),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "检查 run-abc123 的 trace 审计链路"},
        ),
    )

    expected_params = {"run_id": "run-abc123"}
    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "trace_audit_intent"
    assert result.output["planner"]["intent_class"] == "inspect_trace_audit"
    assert result.output["planner"]["mapped_from_action_type"] == "inspect_trace_audit"
    assert result.output["planner"]["chapter_index"] is None
    assert result.output["plan"] == {
        "status": "completed",
        "intent_class": "inspect_trace_audit",
        "steps": [
            {
                "step_index": 1,
                "tool_name": "inspect_agent_trace_audit",
                "params": expected_params,
                "mutability": "read",
                "requires_confirmation": False,
            }
        ],
        "tools": [
            {
                "tool_name": "inspect_agent_trace_audit",
                "params": expected_params,
            }
        ],
        "approval_contract": {"status": "not_required", "write_steps": []},
    }
    assert result.output["tools"] == [{"tool_name": "inspect_agent_trace_audit", "params": expected_params}]
    assert result.output["approval_contract"] == {"status": "not_required", "write_steps": []}
    assert result.output["trace"]["reason"] == "planned_direct_read_tool_from_intent_projection"


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_write_gate_coverage_read(db_session):
    project = Project(name="Dialog Intent Write Gate Coverage Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(
            db=db_session,
            project_id=project.id,
            run_id="run-dialog-intent-write-gate-coverage-plan",
        ),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "检查写入工具的审批门禁覆盖"},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "write_gate_coverage_intent"
    assert result.output["planner"]["intent_class"] == "inspect_write_gate_coverage"
    assert result.output["planner"]["mapped_from_action_type"] == "inspect_write_gate_coverage"
    assert result.output["planner"]["chapter_index"] is None
    assert result.output["plan"] == {
        "status": "completed",
        "intent_class": "inspect_write_gate_coverage",
        "steps": [
            {
                "step_index": 1,
                "tool_name": "inspect_agent_write_gate_coverage",
                "params": {},
                "mutability": "read",
                "requires_confirmation": False,
            }
        ],
        "tools": [
            {
                "tool_name": "inspect_agent_write_gate_coverage",
                "params": {},
            }
        ],
        "approval_contract": {"status": "not_required", "write_steps": []},
    }
    assert result.output["tools"] == [{"tool_name": "inspect_agent_write_gate_coverage", "params": {}}]
    assert result.output["approval_contract"] == {"status": "not_required", "write_steps": []}
    assert result.output["trace"]["reason"] == "planned_direct_read_tool_from_intent_projection"


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_tool_contracts_read(db_session):
    project = Project(name="Dialog Intent Tool Contracts Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(
            db=db_session,
            project_id=project.id,
            run_id="run-dialog-intent-tool-contracts-plan",
        ),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "检查工具契约覆盖率和迁移差距"},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "tool_contracts_intent"
    assert result.output["planner"]["intent_class"] == "inspect_tool_contracts"
    assert result.output["planner"]["mapped_from_action_type"] == "inspect_tool_contracts"
    assert result.output["planner"]["chapter_index"] is None
    assert result.output["plan"] == {
        "status": "completed",
        "intent_class": "inspect_tool_contracts",
        "steps": [
            {
                "step_index": 1,
                "tool_name": "inspect_agent_tool_contracts",
                "params": {},
                "mutability": "read",
                "requires_confirmation": False,
            }
        ],
        "tools": [
            {
                "tool_name": "inspect_agent_tool_contracts",
                "params": {},
            }
        ],
        "approval_contract": {"status": "not_required", "write_steps": []},
    }
    assert result.output["tools"] == [{"tool_name": "inspect_agent_tool_contracts", "params": {}}]
    assert result.output["approval_contract"] == {"status": "not_required", "write_steps": []}
    assert result.output["trace"]["reason"] == "planned_direct_read_tool_from_intent_projection"


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_command_contracts_read(db_session):
    project = Project(name="Dialog Intent Command Contracts Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(
            db=db_session,
            project_id=project.id,
            run_id="run-dialog-intent-command-contracts-plan",
        ),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "检查命令契约缺口和 slash command 投影"},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "command_contracts_intent"
    assert result.output["planner"]["intent_class"] == "inspect_command_contracts"
    assert result.output["planner"]["mapped_from_action_type"] == "inspect_command_contracts"
    assert result.output["planner"]["chapter_index"] is None
    assert result.output["plan"] == {
        "status": "completed",
        "intent_class": "inspect_command_contracts",
        "steps": [
            {
                "step_index": 1,
                "tool_name": "inspect_agent_command_contracts",
                "params": {},
                "mutability": "read",
                "requires_confirmation": False,
            }
        ],
        "tools": [
            {
                "tool_name": "inspect_agent_command_contracts",
                "params": {},
            }
        ],
        "approval_contract": {"status": "not_required", "write_steps": []},
    }
    assert result.output["tools"] == [{"tool_name": "inspect_agent_command_contracts", "params": {}}]
    assert result.output["approval_contract"] == {"status": "not_required", "write_steps": []}
    assert result.output["trace"]["reason"] == "planned_direct_read_tool_from_intent_projection"


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_slash_command_route_read(db_session):
    project = Project(name="Dialog Intent Slash Command Route Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(
            db=db_session,
            project_id=project.id,
            run_id="run-dialog-intent-slash-command-route-plan",
        ),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "检查 /continue 斜杠命令路由"},
        ),
    )

    expected_params = {"command_name": "continue"}
    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "slash_command_route_intent"
    assert result.output["planner"]["intent_class"] == "inspect_slash_command_route"
    assert result.output["planner"]["mapped_from_action_type"] == "inspect_slash_command_route"
    assert result.output["planner"]["chapter_index"] is None
    assert result.output["plan"] == {
        "status": "completed",
        "intent_class": "inspect_slash_command_route",
        "steps": [
            {
                "step_index": 1,
                "tool_name": "inspect_agent_slash_command_route",
                "params": expected_params,
                "mutability": "read",
                "requires_confirmation": False,
            }
        ],
        "tools": [
            {
                "tool_name": "inspect_agent_slash_command_route",
                "params": expected_params,
            }
        ],
        "approval_contract": {"status": "not_required", "write_steps": []},
    }
    assert result.output["tools"] == [{"tool_name": "inspect_agent_slash_command_route", "params": expected_params}]
    assert result.output["approval_contract"] == {"status": "not_required", "write_steps": []}
    assert result.output["trace"]["reason"] == "planned_direct_read_tool_from_intent_projection"


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_reference_alignment_read(db_session):
    project = Project(name="Dialog Intent Reference Alignment Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(
            db=db_session,
            project_id=project.id,
            run_id="run-dialog-intent-reference-alignment-plan",
        ),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "检查参考项目模式对齐和开源项目适配"},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "reference_alignment_intent"
    assert result.output["planner"]["intent_class"] == "inspect_reference_alignment"
    assert result.output["planner"]["mapped_from_action_type"] == "inspect_reference_alignment"
    assert result.output["planner"]["chapter_index"] is None
    assert result.output["plan"] == {
        "status": "completed",
        "intent_class": "inspect_reference_alignment",
        "steps": [
            {
                "step_index": 1,
                "tool_name": "inspect_agent_reference_alignment",
                "params": {},
                "mutability": "read",
                "requires_confirmation": False,
            }
        ],
        "tools": [
            {
                "tool_name": "inspect_agent_reference_alignment",
                "params": {},
            }
        ],
        "approval_contract": {"status": "not_required", "write_steps": []},
    }
    assert result.output["tools"] == [{"tool_name": "inspect_agent_reference_alignment", "params": {}}]
    assert result.output["approval_contract"] == {"status": "not_required", "write_steps": []}
    assert result.output["trace"]["reason"] == "planned_direct_read_tool_from_intent_projection"


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_dogfood_evidence_read(db_session):
    project = Project(name="Dialog Intent Dogfood Evidence Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(
            db=db_session,
            project_id=project.id,
            run_id="run-dialog-intent-dogfood-evidence-plan",
        ),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "检查 dogfood pressure-test 证据覆盖"},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "dogfood_evidence_intent"
    assert result.output["planner"]["intent_class"] == "inspect_dogfood_evidence"
    assert result.output["planner"]["mapped_from_action_type"] == "inspect_dogfood_evidence"
    assert result.output["planner"]["chapter_index"] is None
    assert result.output["plan"] == {
        "status": "completed",
        "intent_class": "inspect_dogfood_evidence",
        "steps": [
            {
                "step_index": 1,
                "tool_name": "inspect_agent_dogfood_evidence",
                "params": {},
                "mutability": "read",
                "requires_confirmation": False,
            }
        ],
        "tools": [
            {
                "tool_name": "inspect_agent_dogfood_evidence",
                "params": {},
            }
        ],
        "approval_contract": {"status": "not_required", "write_steps": []},
    }
    assert result.output["tools"] == [{"tool_name": "inspect_agent_dogfood_evidence", "params": {}}]
    assert result.output["approval_contract"] == {"status": "not_required", "write_steps": []}
    assert result.output["trace"]["reason"] == "planned_direct_read_tool_from_intent_projection"


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_route_preference_read(db_session):
    project = Project(name="Dialog Intent Route Preference Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(
            db=db_session,
            project_id=project.id,
            run_id="run-dialog-intent-route-preference-plan",
        ),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "检查 text_intent 路由偏好和 Agent 审批链迁移建议"},
        ),
    )

    expected_params = {"source": "text_intent"}
    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "route_preference_intent"
    assert result.output["planner"]["intent_class"] == "inspect_route_preference"
    assert result.output["planner"]["mapped_from_action_type"] == "inspect_route_preference"
    assert result.output["planner"]["chapter_index"] is None
    assert result.output["plan"] == {
        "status": "completed",
        "intent_class": "inspect_route_preference",
        "steps": [
            {
                "step_index": 1,
                "tool_name": "inspect_agent_route_preference_projection",
                "params": expected_params,
                "mutability": "read",
                "requires_confirmation": False,
            }
        ],
        "tools": [
            {
                "tool_name": "inspect_agent_route_preference_projection",
                "params": expected_params,
            }
        ],
        "approval_contract": {"status": "not_required", "write_steps": []},
    }
    assert result.output["tools"] == [
        {"tool_name": "inspect_agent_route_preference_projection", "params": expected_params}
    ]
    assert result.output["approval_contract"] == {"status": "not_required", "write_steps": []}
    assert result.output["trace"]["reason"] == "planned_direct_read_tool_from_intent_projection"


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_dialog_route_projection_read(db_session):
    project = Project(name="Dialog Intent Dialog Route Projection Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(
            db=db_session,
            project_id=project.id,
            run_id="run-dialog-intent-dialog-route-projection-plan",
        ),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "检查 button action 统一对话路由投影"},
        ),
    )

    expected_params = {"source": "button_action"}
    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "dialog_route_projection_intent"
    assert result.output["planner"]["intent_class"] == "inspect_dialog_route"
    assert result.output["planner"]["mapped_from_action_type"] == "inspect_dialog_route"
    assert result.output["planner"]["chapter_index"] is None
    assert result.output["plan"] == {
        "status": "completed",
        "intent_class": "inspect_dialog_route",
        "steps": [
            {
                "step_index": 1,
                "tool_name": "inspect_agent_dialog_route_projection",
                "params": expected_params,
                "mutability": "read",
                "requires_confirmation": False,
            }
        ],
        "tools": [
            {
                "tool_name": "inspect_agent_dialog_route_projection",
                "params": expected_params,
            }
        ],
        "approval_contract": {"status": "not_required", "write_steps": []},
    }
    assert result.output["tools"] == [
        {"tool_name": "inspect_agent_dialog_route_projection", "params": expected_params}
    ]
    assert result.output["approval_contract"] == {"status": "not_required", "write_steps": []}
    assert result.output["trace"]["reason"] == "planned_direct_read_tool_from_intent_projection"


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_intent_projection_read(db_session):
    project = Project(name="Dialog Intent Intent Projection Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(
            db=db_session,
            project_id=project.id,
            run_id="run-dialog-intent-intent-projection-plan",
        ),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "检查意图投影：请开始写正文，从第3章开始生成。"},
        ),
    )

    expected_params = {"text": "请开始写正文，从第3章开始生成。"}
    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "intent_projection_intent"
    assert result.output["planner"]["intent_class"] == "inspect_intent_projection"
    assert result.output["planner"]["mapped_from_action_type"] == "inspect_intent_projection"
    assert result.output["planner"]["chapter_index"] is None
    assert result.output["plan"] == {
        "status": "completed",
        "intent_class": "inspect_intent_projection",
        "steps": [
            {
                "step_index": 1,
                "tool_name": "inspect_agent_intent_projection",
                "params": expected_params,
                "mutability": "read",
                "requires_confirmation": False,
            }
        ],
        "tools": [
            {
                "tool_name": "inspect_agent_intent_projection",
                "params": expected_params,
            }
        ],
        "approval_contract": {"status": "not_required", "write_steps": []},
    }
    assert result.output["tools"] == [{"tool_name": "inspect_agent_intent_projection", "params": expected_params}]
    assert result.output["approval_contract"] == {"status": "not_required", "write_steps": []}
    assert result.output["trace"]["reason"] == "planned_direct_read_tool_from_intent_projection"


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_agent_health_read(db_session):
    project = Project(name="Dialog Intent Agent Health Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(
            db=db_session,
            project_id=project.id,
            run_id="run-dialog-intent-agent-health-plan",
        ),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "检查第3章 Agent 健康"},
        ),
    )

    expected_params = {"chapter_index": 3}
    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "agent_health_intent"
    assert result.output["planner"]["intent_class"] == "inspect_agent_health"
    assert result.output["planner"]["mapped_from_action_type"] == "inspect_agent_health"
    assert result.output["planner"]["chapter_index"] == 3
    assert result.output["plan"] == {
        "status": "completed",
        "intent_class": "inspect_agent_health",
        "steps": [
            {
                "step_index": 1,
                "tool_name": "inspect_agent_health_projection",
                "params": expected_params,
                "mutability": "read",
                "requires_confirmation": False,
            }
        ],
        "tools": [
            {
                "tool_name": "inspect_agent_health_projection",
                "params": expected_params,
            }
        ],
        "approval_contract": {"status": "not_required", "write_steps": []},
    }
    assert result.output["tools"] == [{"tool_name": "inspect_agent_health_projection", "params": expected_params}]
    assert result.output["approval_contract"] == {"status": "not_required", "write_steps": []}
    assert result.output["trace"]["reason"] == "planned_direct_read_tool_from_intent_projection"


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_control_plane_readiness(db_session):
    project = Project(name="Dialog Intent Control Plane Readiness Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(
            db=db_session,
            project_id=project.id,
            run_id="run-dialog-intent-control-plane-readiness-plan",
        ),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "检查 Agent 控制面就绪度和工具契约"},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "control_plane_readiness_intent"
    assert result.output["planner"]["intent_class"] == "inspect_control_plane_readiness"
    assert result.output["planner"]["mapped_from_action_type"] == "inspect_control_plane_readiness"
    assert result.output["planner"]["chapter_index"] is None
    assert result.output["plan"] == {
        "status": "completed",
        "intent_class": "inspect_control_plane_readiness",
        "steps": [
            {
                "step_index": 1,
                "tool_name": "inspect_agent_control_plane_readiness",
                "params": {},
                "mutability": "read",
                "requires_confirmation": False,
            }
        ],
        "tools": [{"tool_name": "inspect_agent_control_plane_readiness", "params": {}}],
        "approval_contract": {"status": "not_required", "write_steps": []},
    }
    assert result.output["tools"] == [{"tool_name": "inspect_agent_control_plane_readiness", "params": {}}]
    assert result.output["approval_contract"] == {"status": "not_required", "write_steps": []}
    assert result.output["trace"]["reason"] == "planned_direct_read_tool_from_intent_projection"


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_chapter(db_session):
    project = Project(name="Dialog Intent Chapter Plan")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        Setup(
            project_id=project.id,
            status="generated",
            world_building={"background": "雾港被记忆异常影响。"},
            characters=[{"name": "林深"}],
            core_concept={"hook": "雾会回放记忆"},
        )
    )
    db_session.add(
        Storyline(
            project_id=project.id,
            status="generated",
            plotlines=[{"name": "主线", "type": "main", "summary": "追查记忆异常"}],
            foreshadowing=[],
        )
    )
    db_session.add(
        Outline(
            project_id=project.id,
            total_chapters=600,
            status="generated",
            chapters=[
                {
                    "chapter_index": 2,
                    "title": "雾港线索2",
                    "summary": "林深追查第二条线索。",
                    "scenes": ["诊所追问"],
                    "characters": ["林深"],
                    "purpose": "推进主线",
                }
            ],
            plotlines=[],
            foreshadowing=[],
        )
    )
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="雾港线索1",
            content="林深发现雾港记忆异常的新证据。",
            word_count=2200,
            status="generated",
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-dialog-intent-chapter-plan"),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "继续写第2章正文"},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "chapter_intent"
    assert result.output["planner"]["intent_class"] == "continue_next_chapter"
    assert result.output["planner"]["mapped_from_action_type"] == "preview_chapter"
    assert result.output["planner"]["chapter_index"] == 2
    assert result.output["planner"]["chapter_generation_route"] == "approved_prepare"
    projection_id = result.output["intent_projection"]["trace"]["projection_id"]
    plan = result.output["plan"]
    assert result.output["planner"]["plan_id"] == plan["trace"]["plan_id"]
    assert plan["trace"]["source_projection_id"] == projection_id
    assert plan["trace"]["chapter_generation_route"] == "approved_prepare"
    assert all(step["source_projection_id"] == projection_id for step in plan["steps"])
    assert result.output["approval_contract"]["status"] == "not_required"
    assert result.output["approval_contract"]["plan_id"] == result.output["planner"]["plan_id"]
    assert result.output["approval_contract"] == plan["approval_contract"]
    reference_patterns = result.output["trace"]["reference_patterns"]
    assert [item["source"] for item in reference_patterns] == ["hermes-agent", "openhuman", "openclaw"]
    assert "tool_lifecycle_hooks" in reference_patterns[0]["applied_patterns"]
    assert "agent_definition_visible_tool_split" in reference_patterns[1]["applied_patterns"]
    assert "schema_and_audit_discipline" in reference_patterns[2]["applied_patterns"]
    assert [tool["tool_name"] for tool in result.output["tools"]] == [
        "describe_agent_tools",
        "inspect_agent_knowledge_base_route",
        "search_agent_retrieval_context",
        "summarize_longform_context",
        "preflight_writing",
        "prepare_generate_chapter_execution",
    ]


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_storyline(db_session):
    project = Project(name="Dialog Intent Storyline Plan")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        Setup(
            project_id=project.id,
            status="generated",
            world_building={"background": "雾港被记忆异常影响。"},
            characters=[{"name": "林深"}],
            core_concept={"hook": "雾会回放记忆"},
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-dialog-intent-storyline-plan"),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={
                "text": "生成故事线",
                "missing_items": ["storyline", "outline"],
                "completed_items": ["setup"],
                "suggested_next_step": "preview_storyline",
            },
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "storyline_intent"
    assert result.output["planner"]["intent_class"] == "build_storyline"
    assert result.output["planner"]["mapped_from_action_type"] == "preview_storyline"
    assert [tool["tool_name"] for tool in result.output["tools"]] == [
        "describe_agent_tools",
        "prepare_generate_storyline_execution",
    ]


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_outline(db_session):
    project = Project(name="Dialog Intent Outline Plan")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        Setup(
            project_id=project.id,
            status="generated",
            world_building={"background": "雾港被记忆异常影响。"},
            characters=[{"name": "林深"}],
            core_concept={"hook": "雾会回放记忆"},
        )
    )
    db_session.add(
        Storyline(
            project_id=project.id,
            status="generated",
            plotlines=[{"name": "主线", "type": "main", "summary": "追查记忆异常"}],
            foreshadowing=[],
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-dialog-intent-outline-plan"),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={
                "text": "生成章节大纲",
                "missing_items": ["outline"],
                "completed_items": ["setup", "storyline"],
                "suggested_next_step": "preview_outline",
            },
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "outline_intent"
    assert result.output["planner"]["intent_class"] == "build_outline"
    assert result.output["planner"]["mapped_from_action_type"] == "preview_outline"
    assert [tool["tool_name"] for tool in result.output["tools"]] == [
        "describe_agent_tools",
        "prepare_generate_outline_execution",
    ]


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_review(db_session):
    project = Project(name="Dialog Intent Review Plan")
    db_session.add(project)
    db_session.flush()
    db_session.add(Setup(project_id=project.id, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=project.id, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=project.id,
            status="generated",
            total_chapters=2,
            chapters=[{"chapter_index": 2, "title": "雾中人", "summary": "线索指向失踪档案。"}],
        )
    )
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=2,
            title="雾中人",
            content="林深在雾里追上失踪档案的线索。",
            status="generated",
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-dialog-intent-review-plan"),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={
                "text": "审稿第2章并给出修订计划",
                "completed_items": ["setup", "storyline", "outline", "content"],
                "suggested_next_step": "preview_chapter",
            },
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "review_intent"
    assert result.output["planner"]["intent_class"] == "review_chapter"
    assert result.output["planner"]["mapped_from_action_type"] == "preview_review"
    assert result.output["planner"]["chapter_index"] == 2
    assert [tool["tool_name"] for tool in result.output["tools"]] == [
        "describe_agent_tools",
        "review_chapter_quality",
        "review_chapter_continuity",
        "plan_chapter_revision",
    ]


@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_recovery(db_session):
    project = Project(name="Dialog Intent Recovery Plan")
    db_session.add(project)
    db_session.flush()
    db_session.add(Setup(project_id=project.id, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=project.id, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=project.id,
            status="generated",
            total_chapters=2,
            chapters=[{"chapter_index": 2, "title": "雾中人", "summary": "线索指向失踪档案。"}],
        )
    )
    db_session.add(ChapterContent(project_id=project.id, chapter_index=1, title="旧灯塔", content="第一章正文"))
    blocked_run = WritingAgentRun(
        project_id=project.id,
        goal="阻塞的直接章节执行",
        status="blocked",
        entrypoint="api",
        input={},
    )
    db_session.add(blocked_run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=blocked_run.id,
            project_id=project.id,
            step_index=1,
            tool_name="execute_generate_chapter_with_approval",
            status="blocked",
            input={"params": {"chapter_index": 2}},
            output={
                "status": "blocked",
                "agent_tool_result": {
                    "recovery": {
                        "status": "recommended",
                        "source_tool": "execute_generate_chapter_with_approval",
                        "reason_code": "resource_binding_target_mismatch",
                        "next_tool": "prepare_generate_chapter_execution",
                        "next_params": {"chapter_index": 2},
                    }
                },
            },
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-dialog-intent-recovery-plan"),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={
                "text": "恢复上一轮阻塞的写作任务",
                "completed_items": ["setup", "storyline", "outline"],
                "suggested_next_step": "preview_chapter",
            },
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_projection"]["rule_id"] == "recovery_intent"
    assert result.output["planner"]["intent_class"] == "recover_blocked_run"
    assert result.output["planner"]["mapped_from_action_type"] == "preview_recovery"
    assert [tool["tool_name"] for tool in result.output["tools"]] == ["describe_agent_tools", "plan_recovery_tools"]


@pytest.mark.asyncio
async def test_tool_executor_handles_planner_tool(db_session):
    project = Project(name="Executor Planner")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="plan_writing_agent_run",
            params={"goal": "创建一个都市悬疑项目", "chapter_index": 1, "intent": "setup_project"},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["intent_class"] == "setup_project"
    assert result.output["steps"][0]["tool_name"] == "describe_agent_tools"
    assert result.output["approval_contract"]["status"] == "not_required"


@pytest.mark.asyncio
async def test_tool_executor_handles_agent_plan_approval_contract_preview(db_session):
    project = Project(name="Approval Contract Preview")
    db_session.add(project)
    db_session.commit()
    plan = {
        "trace": {"plan_id": "plan:abc", "source_projection_id": None, "planner_version": "phase53.context_gate.v1"},
        "steps": [
            {
                "step_index": 1,
                "step_id": "step:write",
                "tool_name": "generate_chapter",
                "params": {"chapter_index": 2},
                "mutability": "write",
                "requires_confirmation": True,
            }
        ],
    }

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="preview_agent_plan_approval_contract", params={"plan": plan}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "requires_confirmation"
    assert result.output["plan_id"] == "plan:abc"
    assert result.output["write_step_count"] == 1


@pytest.mark.asyncio
async def test_tool_executor_handles_agent_plan_approval_contract_verification(db_session):
    project = Project(name="Approval Contract Verification")
    db_session.add(project)
    db_session.commit()
    plan = {
        "project_id": project.id,
        "trace": {"plan_id": "plan:abc", "source_projection_id": None, "planner_version": "phase53.context_gate.v1"},
        "steps": [
            {
                "step_index": 1,
                "step_id": "step:write",
                "tool_name": "generate_chapter",
                "params": {"chapter_index": 2},
                "mutability": "write",
                "requires_confirmation": True,
            }
        ],
    }
    preview = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="preview_agent_plan_approval_contract", params={"plan": plan}),
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="verify_agent_plan_approval_contract",
            params={
                "plan": plan,
                "approval_contract": preview.output,
                "approval_contract_hash": preview.output["approval"]["approval_contract_hash"],
            },
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "ready"
    assert result.output["reason"] == "approval_contract_verified"
    assert result.output["drift"]["hash_matches"] is True
    assert result.output["drift"]["tool_contracts_checked"] is True
    assert result.output["drift"]["tool_contract_drift_count"] == 0
    assert result.output["drift"]["tool_contracts"][0]["tool_name"] == "generate_chapter"
    assert result.output["drift"]["tool_contracts"][0]["tool_exists"] is True
    assert result.output["drift"]["tool_contracts"][0]["adapter_exists"] is True
    assert result.output["drift"]["tool_contracts"][0]["current_mutability"] == "guarded_write"
    assert result.output["drift"]["tool_contracts"][0]["current_requires_confirmation"] is True
    assert result.output["drift"]["tool_contracts"][0]["status"] == "ready"


@pytest.mark.asyncio
async def test_tool_executor_handles_plan_recommended_followups(db_session):
    project = Project(name="Recommended Followup Planner")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="生成第2章", status="success", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="generate_chapter",
            status="success",
            chapter_index=2,
            input={"params": {"chapter_index": 2}},
            output={
                "status": "success",
                "chapter_index": 2,
                "agent_tool_result": {
                    "recommendations": {
                        "canonical_followups": [
                            "review_chapter_quality",
                            "review_chapter_continuity",
                            "not_a_tool",
                        ],
                        "runtime_followups": ["review_chapter_quality", "review_chapter_continuity"],
                        "non_tool_recommendations": ["revise_chapter"],
                    }
                },
            },
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-followup"),
        WritingAgentToolRequest(tool_name="plan_recommended_followups", params={"run_id": run.id}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["source_step"]["tool_name"] == "generate_chapter"
    assert [tool["tool_name"] for tool in result.output["tools"]] == [
        "review_chapter_quality",
        "review_chapter_continuity",
    ]
    assert result.output["tools"][0]["params"] == {"chapter_index": 2}
    assert result.output["trace"]["rejected_tools"] == [{"tool_name": "not_a_tool", "reason": "not_allowed"}]


@pytest.mark.asyncio
async def test_tool_executor_handles_inspect_agent_worker_dispatch(db_session):
    project = Project(name="Worker Dispatch Tool")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-worker-dispatch"),
        WritingAgentToolRequest(
            tool_name="inspect_agent_worker_dispatch",
            params={
                "tasks": [
                    {"tool_name": "review_chapter_quality", "params": {"chapter_index": 2}},
                    {"tool_name": "search_agent_retrieval_context", "params": {"query": "第2章证据"}},
                    {"tool_name": "plan_post_chapter_memory_capture", "params": {"chapter_index": 2}},
                ],
            },
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "ready"
    assert result.output["summary"] == {"workers": 3, "planned_tasks": 3, "blocked_tasks": 0, "issues": 0}
    assert result.output["definition_registry"]["status"] == "passed"
    assert result.output["definition_registry"]["summary"] == {
        "worker_profiles": 7,
        "ready_worker_definitions": 7,
        "leaf_worker_definitions": 7,
        "issues": 0,
    }
    assert result.output["route_registry"]["status"] == "passed"
    assert result.output["route_registry"]["summary"] == {
        "routes": 51,
        "ready_routes": 51,
        "unrouted_allowed_tools": 0,
        "issues": 0,
    }
    assert [item["worker"]["name"] for item in result.output["worker_dispatches"]] == [
        "reviewer_worker",
        "retrieval_worker",
        "memory_worker",
    ]
    assert result.output["worker_dispatches"][0]["task_envelopes"][0]["will_execute"] is False


@pytest.mark.asyncio
async def test_plan_recommended_followups_allows_health_and_route_diagnosis_tools(db_session):
    project = Project(name="Recommended Health Followup")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="检查 Agent 健康", status="success", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="inspect_agent_trace_audit",
            status="success",
            output={
                "status": "completed",
                "agent_tool_result": {
                    "recommendations": {
                        "canonical_followups": [
                            "inspect_agent_health_projection",
                            "inspect_agent_control_plane_readiness",
                            "inspect_agent_command_contracts",
                            "inspect_agent_route_preference_projection",
                            "apply_pending_action_route_approval_opt_in",
                        ],
                    }
                },
            },
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-followup"),
        WritingAgentToolRequest(tool_name="plan_recommended_followups", params={"run_id": run.id}),
    )

    assert result.handled is True
    assert result.output is not None
    assert [tool["tool_name"] for tool in result.output["tools"]] == [
        "inspect_agent_health_projection",
        "inspect_agent_control_plane_readiness",
        "inspect_agent_command_contracts",
        "inspect_agent_route_preference_projection",
    ]
    assert result.output["trace"]["rejected_tools"] == [
        {"tool_name": "apply_pending_action_route_approval_opt_in", "reason": "requires_confirmation"}
    ]


@pytest.mark.asyncio
async def test_plan_recommended_followups_allows_memory_loop_read_followups(db_session):
    project = Project(name="Recommended Memory Loop Followup")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="生成第2章", status="success", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="execute_generate_chapter_with_approval",
            status="success",
            chapter_index=2,
            input={"params": {"chapter_index": 2}},
            output={
                "status": "success",
                "chapter_index": 2,
                "agent_tool_result": {
                    "recommendations": {
                        "canonical_followups": [
                            "search_agent_retrieval_context",
                            "plan_post_chapter_memory_capture",
                        ],
                    }
                },
            },
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-followup"),
        WritingAgentToolRequest(tool_name="plan_recommended_followups", params={"run_id": run.id}),
    )

    assert result.handled is True
    assert result.output is not None
    assert [tool["tool_name"] for tool in result.output["tools"]] == [
        "search_agent_retrieval_context",
        "plan_post_chapter_memory_capture",
    ]
    assert result.output["tools"][0]["params"] == {
        "query": "第2章相关记忆与检索证据",
        "max_chapter_index": 2,
    }
    assert result.output["tools"][1]["params"] == {"chapter_index": 2}
    assert result.output["trace"]["rejected_tools"] == []


@pytest.mark.asyncio
async def test_plan_recommended_followups_allows_memory_tree_drilldown(db_session):
    project = Project(name="Recommended Memory Tree Drilldown")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="诊断第8章记忆", status="success", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="inspect_agent_memory_route",
            status="success",
            chapter_index=8,
            input={"params": {"chapter_index": 8}},
            output={
                "status": "completed",
                "chapter_index": 8,
                "recommended_next_tools": ["inspect_agent_memory_tree"],
                "agent_tool_result": {
                    "recommendations": {
                        "canonical_followups": ["inspect_agent_memory_tree"],
                    }
                },
            },
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-followup-memory-tree"),
        WritingAgentToolRequest(tool_name="plan_recommended_followups", params={"run_id": run.id}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert [tool["tool_name"] for tool in result.output["tools"]] == ["inspect_agent_memory_tree"]
    assert result.output["tools"][0]["params"] == {"chapter_index": 8}
    planner = result.output["tools"][0]["planner"]
    assert planner["agent_profile"] == "memory_worker"
    assert planner["worker_dispatch"]["worker"] == "memory_worker"
    assert result.output["worker_dispatch"]["summary"] == {
        "workers": 1,
        "planned_tasks": 1,
        "blocked_tasks": 0,
        "issues": 0,
    }
    assert result.output["trace"]["worker_profiles"] == ["memory_worker"]
    assert result.output["trace"]["rejected_tools"] == []


@pytest.mark.asyncio
async def test_plan_recommended_followups_allows_knowledge_route_read_chain(db_session):
    project = Project(name="Recommended Knowledge Route Chain")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="检查第8章知识库", status="success", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="inspect_agent_knowledge_base_route",
            status="success",
            chapter_index=8,
            input={"params": {"chapter_index": 8}},
            output={
                "status": "completed",
                "chapter_index": 8,
                "recommended_next_tools": [
                    "summarize_longform_context",
                    "preflight_writing",
                    "review_chapter_quality",
                ],
                "agent_tool_result": {
                    "recommendations": {
                        "canonical_followups": [
                            "summarize_longform_context",
                            "preflight_writing",
                            "review_chapter_quality",
                        ],
                    }
                },
            },
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-followup-knowledge-route"),
        WritingAgentToolRequest(tool_name="plan_recommended_followups", params={"run_id": run.id}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert [tool["tool_name"] for tool in result.output["tools"]] == [
        "summarize_longform_context",
        "preflight_writing",
        "review_chapter_quality",
    ]
    assert [tool["params"] for tool in result.output["tools"]] == [
        {"chapter_index": 8},
        {"chapter_index": 8},
        {"chapter_index": 8},
    ]
    assert [tool["planner"].get("agent_profile") for tool in result.output["tools"]] == [
        "memory_worker",
        "drafting_worker",
        "reviewer_worker",
    ]
    assert result.output["worker_dispatch"]["summary"] == {
        "workers": 3,
        "planned_tasks": 3,
        "blocked_tasks": 0,
        "issues": 0,
    }
    assert result.output["trace"]["worker_profiles"] == [
        "memory_worker",
        "drafting_worker",
        "reviewer_worker",
    ]
    assert result.output["trace"]["rejected_tools"] == []


@pytest.mark.asyncio
async def test_plan_recommended_followups_prepares_chapter_generation_instead_of_writing(db_session):
    project = Project(name="Recommended Chapter Generation Followup")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="写前检查第3章", status="success", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="preflight_writing",
            status="success",
            chapter_index=3,
            input={"params": {"chapter_index": 3}},
            output={
                "status": "success",
                "chapter_index": 3,
                "agent_tool_result": {
                    "recommendations": {
                        "canonical_followups": ["generate_chapter"],
                    }
                },
            },
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-followup-chapter"),
        WritingAgentToolRequest(tool_name="plan_recommended_followups", params={"run_id": run.id}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert [tool["tool_name"] for tool in result.output["tools"]] == ["prepare_generate_chapter_execution"]
    assert result.output["tools"][0]["params"] == {"chapter_index": 3}
    planner = result.output["tools"][0]["planner"]
    assert planner["reason"] == (
        "根据上一轮 preflight_writing 的运行时推荐规划后继工具 prepare_generate_chapter_execution。"
    )
    assert planner["agent_profile"] == "drafting_worker"
    assert planner["worker_dispatch"]["worker"] == "drafting_worker"
    assert result.output["trace"]["rejected_tools"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("write_tool", "prepare_tool"),
    [
        ("generate_setup", "prepare_generate_setup_execution"),
        ("generate_storyline", "prepare_generate_storyline_execution"),
        ("generate_outline", "prepare_generate_outline_execution"),
    ],
)
async def test_plan_recommended_followups_prepares_story_assets_instead_of_writing(
    db_session,
    write_tool,
    prepare_tool,
):
    project = Project(name="Recommended Story Asset Followup")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="规划故事资产", status="success", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="inspect_agent_route_preference_projection",
            status="success",
            output={
                "status": "completed",
                "agent_tool_result": {
                    "recommendations": {
                        "canonical_followups": [write_tool],
                    }
                },
            },
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-followup-story-assets"),
        WritingAgentToolRequest(tool_name="plan_recommended_followups", params={"run_id": run.id}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert [tool["tool_name"] for tool in result.output["tools"]] == [prepare_tool]
    assert result.output["tools"][0]["params"] == {}
    assert result.output["tools"][0]["planner"]["agent_profile"] == "drafting_worker"
    assert result.output["trace"]["rejected_tools"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("preview_tool", "prepare_tool"),
    [
        ("preview_generate_setup_execution", "prepare_generate_setup_execution"),
        ("preview_generate_storyline_execution", "prepare_generate_storyline_execution"),
        ("preview_generate_outline_execution", "prepare_generate_outline_execution"),
    ],
)
async def test_plan_recommended_followups_preserves_story_asset_command_args(
    db_session,
    preview_tool,
    prepare_tool,
):
    project = Project(name="Recommended Story Asset Command Args")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="预览故事资产", status="success", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name=preview_tool,
            status="success",
            input={"params": {"command_args": "雾港悬疑"}},
            output={
                "status": "completed",
                "command_args": "雾港悬疑",
                "agent_tool_result": {
                    "recommendations": {
                        "canonical_followups": [prepare_tool],
                    }
                },
            },
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-followup-story-asset-preview"),
        WritingAgentToolRequest(tool_name="plan_recommended_followups", params={"run_id": run.id}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert [tool["tool_name"] for tool in result.output["tools"]] == [prepare_tool]
    assert result.output["tools"][0]["params"] == {"command_args": "雾港悬疑"}
    assert result.output["tools"][0]["planner"]["agent_profile"] == "drafting_worker"
    assert result.output["trace"]["rejected_tools"] == []


@pytest.mark.asyncio
async def test_plan_recommended_followups_projects_worker_dispatch_for_domain_followups(db_session):
    project = Project(name="Recommended Worker Dispatch Followup")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="生成第2章", status="success", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="execute_generate_chapter_with_approval",
            status="success",
            chapter_index=2,
            input={"params": {"chapter_index": 2}},
            output={
                "status": "success",
                "chapter_index": 2,
                "agent_tool_result": {
                    "recommendations": {
                        "canonical_followups": [
                            "review_chapter_quality",
                            "search_agent_retrieval_context",
                            "plan_post_chapter_memory_capture",
                            "prepare_analyze_chapter_world_model_execution",
                            "plan_chapter_revision",
                        ],
                    }
                },
            },
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-followup-workers"),
        WritingAgentToolRequest(tool_name="plan_recommended_followups", params={"run_id": run.id}),
    )

    assert result.handled is True
    assert result.output is not None
    assert [tool["planner"]["agent_profile"] for tool in result.output["tools"]] == [
        "reviewer_worker",
        "retrieval_worker",
        "memory_worker",
        "world_model_worker",
        "revision_worker",
    ]
    assert result.output["trace"]["worker_profiles"] == [
        "reviewer_worker",
        "retrieval_worker",
        "memory_worker",
        "world_model_worker",
        "revision_worker",
    ]
    dispatch = result.output["worker_dispatch"]
    assert dispatch["status"] == "ready"
    assert dispatch["summary"] == {"workers": 5, "planned_tasks": 5, "blocked_tasks": 0, "issues": 0}
    assert [item["worker"]["name"] for item in dispatch["worker_dispatches"]] == [
        "reviewer_worker",
        "retrieval_worker",
        "memory_worker",
        "world_model_worker",
        "revision_worker",
    ]
    assert all(item["summary"]["planned_tasks"] == 1 for item in dispatch["worker_dispatches"])


@pytest.mark.asyncio
async def test_plan_recommended_followups_rejects_write_followups(db_session):
    project = Project(name="Recommended Followup Guarded Write")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="修订章节", status="success", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="create_revision_draft",
            status="success",
            chapter_index=2,
            input={"params": {"chapter_index": 2}},
            output={
                "status": "success",
                "chapter_index": 2,
                "agent_tool_result": {
                    "recommendations": {
                        "canonical_followups": ["apply_planner_revision_patch", "review_chapter_quality"],
                    }
                },
            },
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-followup"),
        WritingAgentToolRequest(tool_name="plan_recommended_followups", params={"run_id": run.id}),
    )

    assert result.handled is True
    assert result.output is not None
    assert [tool["tool_name"] for tool in result.output["tools"]] == ["review_chapter_quality"]
    assert result.output["trace"]["rejected_tools"] == [
        {"tool_name": "apply_planner_revision_patch", "reason": "requires_confirmation"}
    ]


@pytest.mark.asyncio
async def test_plan_recommended_followups_plans_route_opt_in_contract_preview(db_session):
    project = Project(name="Recommended Route Opt In Contract")
    db_session.add(project)
    db_session.flush()
    dialog = Dialog(project_id=project.id, state="pending_action")
    db_session.add(dialog)
    db_session.flush()
    route = build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")
    pending = PendingAction(
        dialog_id=dialog.id,
        type="preview_setup",
        params={"project_id": project.id, "agent_route": route},
    )
    db_session.add(pending)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="升级 pending action route", status="success", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="preview_pending_action_route_approval_opt_in_apply",
            status="success",
            input={"params": {"pending_action_id": pending.id}},
            output={
                "status": "ready",
                "pending_action_id": pending.id,
                "agent_tool_result": {
                    "recommendations": {
                        "canonical_followups": ["preview_pending_action_route_approval_opt_in_apply_contract"],
                    }
                },
            },
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-followup-route-contract"),
        WritingAgentToolRequest(tool_name="plan_recommended_followups", params={"run_id": run.id}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert [tool["tool_name"] for tool in result.output["tools"]] == [
        "preview_pending_action_route_approval_opt_in_apply_contract"
    ]
    assert result.output["tools"][0]["params"] == {"pending_action_id": pending.id}
    assert result.output["trace"]["rejected_tools"] == []


@pytest.mark.asyncio
async def test_plan_recommended_followups_keeps_route_opt_in_apply_guarded(db_session):
    project = Project(name="Recommended Route Opt In Apply Guard")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="确认 route opt-in", status="success", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="preview_pending_action_route_approval_opt_in_apply_contract",
            status="success",
            input={"params": {"pending_action_id": "pending-route-1"}},
            output={
                "status": "requires_confirmation",
                "pending_action_id": "pending-route-1",
                "agent_tool_result": {
                    "recommendations": {
                        "canonical_followups": ["apply_pending_action_route_approval_opt_in"],
                    }
                },
            },
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-followup-route-apply"),
        WritingAgentToolRequest(tool_name="plan_recommended_followups", params={"run_id": run.id}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["tools"] == []
    assert result.output["trace"]["rejected_tools"] == [
        {"tool_name": "apply_pending_action_route_approval_opt_in", "reason": "requires_confirmation"}
    ]


@pytest.mark.asyncio
async def test_plan_recommended_followups_blocks_when_source_run_requires_recovery(db_session):
    project = Project(name="Recommended Followup Recovery First")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="继续写作", status="blocked", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="summarize_longform_context",
            status="success",
            chapter_index=2,
            input={"params": {"chapter_index": 2}},
            output={
                "status": "blocked",
                "chapter_index": 2,
                "agent_tool_result": {
                    "recovery": {"status": "recommended", "next_tool": "repair_longform_maintenance"},
                    "recommendations": {"canonical_followups": ["repair_longform_maintenance"]},
                },
            },
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-followup"),
        WritingAgentToolRequest(tool_name="plan_recommended_followups", params={"run_id": run.id}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "blocked"
    assert result.output["tools"] == []
    assert result.output["trace"]["rejected_tools"] == [{"reason": "source_run_requires_recovery"}]


@pytest.mark.asyncio
async def test_plan_recommended_followups_rejects_planner_loops(db_session):
    project = Project(name="Recommended Followup Loop")
    db_session.add(project)
    db_session.flush()
    run = WritingAgentRun(project_id=project.id, goal="规划后继", status="success", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project.id,
            step_index=1,
            tool_name="plan_writing_agent_run",
            status="success",
            input={"params": {}},
            output={
                "status": "success",
                "agent_tool_result": {
                    "recommendations": {"canonical_followups": ["plan_recommended_followups"]},
                },
            },
        )
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-followup"),
        WritingAgentToolRequest(tool_name="plan_recommended_followups", params={"run_id": run.id}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["tools"] == []
    assert result.output["trace"]["rejected_tools"] == [
        {"tool_name": "plan_recommended_followups", "reason": "planner_loop"}
    ]


@pytest.mark.asyncio
async def test_tool_executor_handles_preflight_with_injected_callback(db_session):
    project = Project(name="Executor Preflight")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, dict]] = []

    def fake_preflight(project_id: str, params: dict):
        calls.append((project_id, params))
        return {"status": "ready", "chapter_index": params["chapter_index"]}

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="preflight_writing", params={"chapter_index": 3}),
        preflight_writing=fake_preflight,
    )

    assert result.handled is True
    assert result.output == {"status": "ready", "chapter_index": 3}
    assert calls == [(project.id, {"chapter_index": 3})]


@pytest.mark.asyncio
async def test_generate_chapter_tool_appends_context_without_run_service(db_session, monkeypatch):
    project = Project(name="Direct Chapter Tool")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="空白信的秘密",
            content="林深和苏晚晴在灯塔下发现空白信，信纸显出雾晶是钥匙。两人决定前往下城黑市。",
            word_count=2000,
            status="generated",
        )
    )
    db_session.commit()
    captured: dict[str, object] = {}

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        captured["action_type"] = action_type
        captured["command_args"] = command_args
        captured["action_params"] = action_params
        return {"status": "success", "chapter_index": action_params["chapter_index"]}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    result = await execute_generate_chapter_tool(
        db_session,
        project.id,
        chapter_index=2,
        command_args="保持紧张感",
    )

    command_args = str(captured["command_args"])
    assert result["status"] == "success"
    assert captured["action_type"] == "generate_chapter"
    assert captured["action_params"] == {"chapter_index": 2}
    assert "保持紧张感" in command_args
    assert "上一章状态卡" in command_args
    assert "空白信" in command_args
    assert result["agent_continuity_feedback"]["status"] == "active"
    assert result["recommended_next_tools"] == [
        "review_chapter_quality",
        "review_chapter_continuity",
        "analyze_chapter_world_model",
        "plan_post_chapter_memory_capture",
    ]


@pytest.mark.asyncio
async def test_tool_executor_does_not_coerce_invalid_generate_chapter_index(db_session, monkeypatch):
    project = Project(name="Invalid Chapter Index")
    db_session.add(project)
    db_session.commit()
    calls: list[str] = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    with pytest.raises(ValueError):
        await execute_writing_agent_tool(
            WritingAgentToolContext(db=db_session, project_id=project.id),
            WritingAgentToolRequest(tool_name="generate_chapter", params={"chapter_index": "not-a-number"}),
        )

    assert calls == []


@pytest.mark.asyncio
async def test_tool_executor_redirects_direct_generate_chapter_to_approval(db_session, monkeypatch):
    project = Project(name="Direct Chapter Approval Redirect")
    db_session.add(project)
    db_session.commit()
    calls: list[str] = []

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        calls.append(action_type)
        return {"status": "success"}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="generate_chapter",
            command_args="保持紧张感",
            params={"chapter_index": 2},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["chapter_index"] == 2
    assert result.output["side_effects"] == {"executed": [], "skipped": ["generate_chapter"]}
    assert result.output["recommended_next_tools"] == ["prepare_generate_chapter_execution"]
    assert result.output["required_approval"]["prepare_tool"] == "prepare_generate_chapter_execution"
    assert calls == []


@pytest.mark.asyncio
async def test_tool_executor_dispatches_prepare_generate_chapter_execution(db_session):
    project = Project(name="Prepare Approved Direct Generate")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="prepare_generate_chapter_execution", params={"chapter_index": 2}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "approval_required"
    assert result.output["chapter_index"] == 2
    assert result.output["recommended_next_tools"] == ["execute_generate_chapter_with_approval"]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_execute_generate_chapter_with_approval(db_session, monkeypatch):
    project = Project(name="Execute Approved Direct Generate")
    db_session.add(project)
    db_session.commit()
    calls: list[dict] = []

    async def fake_execute(
        db,
        project_id: str,
        *,
        chapter_index: int,
        confirm_execute: bool,
        approval_contract_hash: str | None,
        approval_contract: dict | None,
        approval_tool_metadata_provider,
        command_args: str | None = None,
        action_params: dict | None = None,
    ):
        metadata = approval_tool_metadata_provider(
            {"steps": [{"tool_name": "generate_chapter", "mutability": "guarded_write", "requires_confirmation": True}]}
        )
        calls.append(
            {
                "project_id": project_id,
                "chapter_index": chapter_index,
                "confirm_execute": confirm_execute,
                "approval_contract_hash": approval_contract_hash,
                "approval_contract": approval_contract,
                "metadata_tool_exists": metadata["generate_chapter"]["tool_exists"],
                "command_args": command_args,
                "action_params": action_params,
            }
        )
        return {"status": "success", "chapter_index": chapter_index}

    monkeypatch.setattr(
        "app.services.writing_agent.chapter_generation_execution.execute_generate_chapter_with_approval",
        fake_execute,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_generate_chapter_with_approval",
            command_args="加快节奏",
            params={
                "chapter_index": 2,
                "confirm_execute": True,
                "approval_contract_hash": "approval:abc",
                "approval_contract": {"status": "requires_confirmation"},
            },
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "success", "chapter_index": 2}
    assert calls == [
        {
            "project_id": project.id,
            "chapter_index": 2,
            "confirm_execute": True,
            "approval_contract_hash": "approval:abc",
            "approval_contract": {"status": "requires_confirmation"},
            "metadata_tool_exists": True,
            "command_args": "加快节奏",
            "action_params": {
                "chapter_index": 2,
                "confirm_execute": True,
                "approval_contract_hash": "approval:abc",
                "approval_contract": {"status": "requires_confirmation"},
            },
        }
    ]


@pytest.mark.asyncio
async def test_execute_generate_chapter_with_approval_records_verification_event(db_session, monkeypatch):
    project = Project(name="Execute Approval Verification Event")
    db_session.add(project)
    db_session.commit()
    prepare = prepare_generate_chapter_execution(db_session, project.id, chapter_index=2)

    async def fake_generate_chapter_tool(
        db,
        project_id: str,
        *,
        chapter_index: int,
        command_args: str | None = None,
        action_params: dict | None = None,
    ):
        return {"status": "success", "chapter_index": chapter_index, "trace_id": "trace-ok"}

    monkeypatch.setattr(
        "app.services.writing_agent.chapter_generation_tool.execute_generate_chapter_tool",
        fake_generate_chapter_tool,
    )

    result = await execute_generate_chapter_with_approval(
        db_session,
        project.id,
        chapter_index=2,
        confirm_execute=True,
        approval_contract_hash=prepare["agent_plan_approval_contract_hash"],
        approval_contract=prepare["agent_plan_approval_contract"],
        approval_tool_metadata_provider=lambda plan: {
            "generate_chapter": {
                "tool_exists": True,
                "adapter_exists": True,
                "mutability": "guarded_write",
                "requires_confirmation": True,
                "required_fields": [],
            }
        },
    )

    assert result["status"] == "success"
    verification_event = result["approval_verification_event"]
    assert {
        key: verification_event[key]
        for key in (
            "event_type",
            "status",
            "reason",
            "approval_contract_bound",
            "approval_contract_version",
            "write_step_count",
            "tool_contract_drift_count",
        )
    } == {
        "event_type": "contract_verified",
        "status": "ready",
        "reason": "approval_contract_verified",
        "approval_contract_bound": True,
        "approval_contract_version": "phase108.agent_plan_approval_contract.v1",
        "write_step_count": 1,
        "tool_contract_drift_count": 0,
    }
    assert verification_event["resource_bindings"][0]["tool_name"] == "generate_chapter"
    assert verification_event["resource_bindings"][0]["target_id"] == "chapter:2"
    assert "approval:" not in str(verification_event)


@pytest.mark.asyncio
async def test_tool_executor_dispatches_preview_generate_setup_execution(db_session):
    project = Project(name="Preview Setup Generation")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="preview_generate_setup_execution", command_args="城市悬疑"),
    )

    assert result.handled is True
    assert result.output["status"] == "completed"
    assert result.output["target_type"] == "setup"
    assert result.output["side_effects"] == {"executed": [], "skipped": ["generate_setup"]}
    assert result.output["recommended_next_tools"] == ["prepare_generate_setup_execution"]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_prepare_generate_setup_execution(db_session):
    project = Project(name="Prepare Setup Generation")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="prepare_generate_setup_execution", command_args="城市悬疑"),
    )

    assert result.handled is True
    assert result.output["status"] == "approval_required"
    plan_step = result.output["agent_plan"]["steps"][0]
    assert plan_step["tool_name"] == "generate_setup"
    assert plan_step["approval_executor_tool_name"] == "execute_generate_setup_with_approval"
    assert result.output["agent_plan_approval_contract_hash"]
    assert result.output["agent_plan_approval_contract"]["write_steps"][0]["tool_name"] == "generate_setup"
    assert result.output["required_confirmation"]["confirm_execute"] is True
    assert result.output["recommended_next_tools"] == ["execute_generate_setup_with_approval"]


@pytest.mark.asyncio
async def test_tool_executor_blocks_execute_generate_setup_without_confirmation(db_session):
    project = Project(name="Blocked Setup Generation")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="execute_generate_setup_with_approval"),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "confirmation_required"
    assert result.output["side_effects"] == {"executed": [], "skipped": ["generate_setup"]}


@pytest.mark.asyncio
async def test_tool_executor_executes_generate_setup_with_approval(db_session, monkeypatch):
    project = Project(name="Execute Setup Generation")
    db_session.add(project)
    db_session.commit()
    prepare = prepare_generate_setup_execution(db_session, project.id, command_args="城市悬疑")
    calls: list[dict] = []

    async def fake_generate_setup(project_id: str, db, command_args=None):
        calls.append({"project_id": project_id, "command_args": command_args})

    monkeypatch.setattr("app.api.setups.generate_setup", fake_generate_setup)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_generate_setup_with_approval",
            command_args="城市悬疑",
            params={
                "confirm_execute": True,
                "approval_contract_hash": prepare["agent_plan_approval_contract_hash"],
                "approval_contract": prepare["agent_plan_approval_contract"],
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "success"
    assert result.output["execute_version"]
    assert result.output["agent_plan_approval_verification"]["status"] == "ready"
    assert result.output["execution_resource_binding"]["status"] == "ready"
    assert result.output["execution_resource_binding"]["expected"]["tool_name"] == "generate_setup"
    assert result.output["side_effects"] == {"executed": ["generate_setup"], "skipped": []}
    assert calls == [{"project_id": project.id, "command_args": "城市悬疑"}]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_preview_generate_storyline_execution(db_session):
    project = Project(name="Preview Storyline Generation")
    db_session.add(project)
    db_session.commit()
    db_session.add(Setup(project_id=project.id, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="preview_generate_storyline_execution", command_args="双线叙事"),
    )

    assert result.handled is True
    assert result.output["status"] == "completed"
    assert result.output["target_type"] == "storyline"
    assert result.output["side_effects"] == {"executed": [], "skipped": ["generate_storyline"]}
    assert result.output["recommended_next_tools"] == ["prepare_generate_storyline_execution"]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_prepare_generate_storyline_execution(db_session):
    project = Project(name="Prepare Storyline Generation")
    db_session.add(project)
    db_session.commit()
    db_session.add(Setup(project_id=project.id, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="prepare_generate_storyline_execution", command_args="双线叙事"),
    )

    assert result.handled is True
    assert result.output["status"] == "approval_required"
    plan_step = result.output["agent_plan"]["steps"][0]
    assert plan_step["tool_name"] == "generate_storyline"
    assert plan_step["approval_executor_tool_name"] == "execute_generate_storyline_with_approval"
    assert result.output["agent_plan_approval_contract_hash"]
    assert result.output["agent_plan_approval_contract"]["write_steps"][0]["tool_name"] == "generate_storyline"
    assert result.output["required_confirmation"]["confirm_execute"] is True
    assert result.output["recommended_next_tools"] == ["execute_generate_storyline_with_approval"]


@pytest.mark.asyncio
async def test_tool_executor_blocks_execute_generate_storyline_without_confirmation(db_session):
    project = Project(name="Blocked Storyline Generation")
    db_session.add(project)
    db_session.commit()
    db_session.add(Setup(project_id=project.id, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="execute_generate_storyline_with_approval"),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "confirmation_required"
    assert result.output["side_effects"] == {"executed": [], "skipped": ["generate_storyline"]}


@pytest.mark.asyncio
async def test_tool_executor_executes_generate_storyline_with_approval(db_session, monkeypatch):
    project = Project(name="Execute Storyline Generation")
    db_session.add(project)
    db_session.commit()
    db_session.add(Setup(project_id=project.id, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.commit()
    prepare = prepare_generate_storyline_execution(db_session, project.id, command_args="双线叙事")
    calls: list[dict] = []

    async def fake_generate_storyline(project_id: str, db, command_args=None):
        calls.append({"project_id": project_id, "command_args": command_args})

    monkeypatch.setattr("app.api.storylines.generate_storyline", fake_generate_storyline)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_generate_storyline_with_approval",
            command_args="双线叙事",
            params={
                "confirm_execute": True,
                "approval_contract_hash": prepare["agent_plan_approval_contract_hash"],
                "approval_contract": prepare["agent_plan_approval_contract"],
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "success"
    assert result.output["execute_version"]
    assert result.output["agent_plan_approval_verification"]["status"] == "ready"
    assert result.output["execution_resource_binding"]["status"] == "ready"
    assert result.output["execution_resource_binding"]["expected"]["tool_name"] == "generate_storyline"
    assert result.output["side_effects"] == {"executed": ["generate_storyline"], "skipped": []}
    assert calls == [{"project_id": project.id, "command_args": "双线叙事"}]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_preview_generate_outline_execution(db_session):
    project = Project(name="Preview Outline Generation")
    db_session.add(project)
    db_session.commit()
    db_session.add(Setup(project_id=project.id, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=project.id, status="generated", plotlines=[], foreshadowing=[]))
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="preview_generate_outline_execution", command_args="每章留钩子"),
    )

    assert result.handled is True
    assert result.output["status"] == "completed"
    assert result.output["target_type"] == "outline"
    assert result.output["side_effects"] == {"executed": [], "skipped": ["generate_outline"]}
    assert result.output["recommended_next_tools"] == ["prepare_generate_outline_execution"]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_prepare_generate_outline_execution(db_session):
    project = Project(name="Prepare Outline Generation")
    db_session.add(project)
    db_session.commit()
    db_session.add(Setup(project_id=project.id, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=project.id, status="generated", plotlines=[], foreshadowing=[]))
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="prepare_generate_outline_execution", command_args="每章留钩子"),
    )

    assert result.handled is True
    assert result.output["status"] == "approval_required"
    plan_step = result.output["agent_plan"]["steps"][0]
    assert plan_step["tool_name"] == "generate_outline"
    assert plan_step["approval_executor_tool_name"] == "execute_generate_outline_with_approval"
    assert result.output["agent_plan_approval_contract_hash"]
    assert result.output["agent_plan_approval_contract"]["write_steps"][0]["tool_name"] == "generate_outline"
    assert result.output["required_confirmation"]["confirm_execute"] is True
    assert result.output["recommended_next_tools"] == ["execute_generate_outline_with_approval"]


@pytest.mark.asyncio
async def test_tool_executor_blocks_execute_generate_outline_without_confirmation(db_session):
    project = Project(name="Blocked Outline Generation")
    db_session.add(project)
    db_session.commit()
    db_session.add(Setup(project_id=project.id, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=project.id, status="generated", plotlines=[], foreshadowing=[]))
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="execute_generate_outline_with_approval"),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "confirmation_required"
    assert result.output["side_effects"] == {"executed": [], "skipped": ["generate_outline"]}


@pytest.mark.asyncio
async def test_tool_executor_executes_generate_outline_with_approval(db_session, monkeypatch):
    project = Project(name="Execute Outline Generation")
    db_session.add(project)
    db_session.commit()
    db_session.add(Setup(project_id=project.id, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=project.id, status="generated", plotlines=[], foreshadowing=[]))
    db_session.commit()
    prepare = prepare_generate_outline_execution(db_session, project.id, command_args="每章留钩子")
    calls: list[dict] = []

    async def fake_generate_outline(project_id: str, db, command_args=None):
        calls.append({"project_id": project_id, "command_args": command_args})

    monkeypatch.setattr("app.api.outlines.generate_outline", fake_generate_outline)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_generate_outline_with_approval",
            command_args="每章留钩子",
            params={
                "confirm_execute": True,
                "approval_contract_hash": prepare["agent_plan_approval_contract_hash"],
                "approval_contract": prepare["agent_plan_approval_contract"],
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "success"
    assert result.output["execute_version"]
    assert result.output["agent_plan_approval_verification"]["status"] == "ready"
    assert result.output["execution_resource_binding"]["status"] == "ready"
    assert result.output["execution_resource_binding"]["expected"]["tool_name"] == "generate_outline"
    assert result.output["side_effects"] == {"executed": ["generate_outline"], "skipped": []}
    assert calls == [{"project_id": project.id, "command_args": "每章留钩子"}]


@pytest.mark.asyncio
async def test_tool_executor_redirects_direct_pre_chapter_generation_tools_to_approval(db_session):
    project = Project(name="Executor Legacy")
    db_session.add(project)
    db_session.commit()

    setup_result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="generate_setup", command_args="城市悬疑"),
    )
    storyline_result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="generate_storyline", command_args="双线叙事"),
    )
    outline_result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="generate_outline", command_args="每章留钩子"),
    )

    assert setup_result.handled is True
    assert setup_result.output["status"] == "blocked"
    assert setup_result.output["reason"] == "approval_required_before_write"
    assert setup_result.output["side_effects"] == {"executed": [], "skipped": ["generate_setup"]}
    assert setup_result.output["recommended_next_tools"] == ["prepare_generate_setup_execution"]
    assert setup_result.output["required_approval"]["prepare_tool"] == "prepare_generate_setup_execution"

    assert storyline_result.handled is True
    assert storyline_result.output["status"] == "blocked"
    assert storyline_result.output["reason"] == "approval_required_before_write"
    assert storyline_result.output["side_effects"] == {"executed": [], "skipped": ["generate_storyline"]}
    assert storyline_result.output["recommended_next_tools"] == ["prepare_generate_storyline_execution"]
    assert storyline_result.output["required_approval"]["prepare_tool"] == "prepare_generate_storyline_execution"

    assert outline_result.handled is True
    assert outline_result.output["status"] == "blocked"
    assert outline_result.output["reason"] == "approval_required_before_write"
    assert outline_result.output["side_effects"] == {"executed": [], "skipped": ["generate_outline"]}
    assert outline_result.output["recommended_next_tools"] == ["prepare_generate_outline_execution"]
    assert outline_result.output["required_approval"]["prepare_tool"] == "prepare_generate_outline_execution"


def _seed_profile_scope_project(db_session) -> Project:
    project = Project(name="Profile Scoped Tool Plan", genre="都市悬疑", target_chapter_count=600)
    db_session.add(project)
    db_session.flush()
    db_session.add(
        Setup(
            project_id=project.id,
            status="generated",
            world_building={"background": "雾港被记忆异常影响。"},
            characters=[{"name": "林深"}],
            core_concept={"hook": "雾会回放记忆"},
        )
    )
    db_session.add(
        Storyline(
            project_id=project.id,
            status="generated",
            plotlines=[{"name": "主线", "type": "main", "summary": "追查记忆异常"}],
            foreshadowing=[],
        )
    )
    db_session.add(
        Outline(
            project_id=project.id,
            total_chapters=600,
            status="generated",
            chapters=[
                {
                    "chapter_index": 2,
                    "title": "雾港线索2",
                    "summary": "林深追查第二条线索。",
                    "scenes": ["诊所追问"],
                    "characters": ["林深"],
                    "purpose": "推进主线",
                }
            ],
            plotlines=[],
            foreshadowing=[],
        )
    )
    for index in (1, 2):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"雾港线索{index}",
                content=f"林深在第{index}章发现雾港记忆异常的新证据。",
                word_count=2200,
                status="generated",
            )
        )
    db_session.commit()
    db_session.refresh(project)
    return project


def test_tool_executor_static_adapter_names_are_report_or_agent_native_tools():
    names = static_writing_agent_tool_adapter_names()

    assert {
        "describe_agent_tools",
        "inspect_agent_health_projection",
        "inspect_agent_control_plane_readiness",
        "generate_chapter",
        "prepare_generate_chapter_execution",
        "execute_generate_chapter_with_approval",
        "plan_writing_agent_run",
        "plan_dialog_intent_agent_run",
        "preview_agent_plan_approval_contract",
        "verify_agent_plan_approval_contract",
        "plan_longform_chapter_batch",
        "enqueue_longform_chapter_batch",
        "prepare_enqueue_longform_chapter_batch",
        "execute_enqueue_longform_chapter_batch_with_approval",
        "inspect_longform_chapter_batch",
        "inspect_agent_job_projection",
        "inspect_agent_tool_contracts",
        "inspect_agent_command_contracts",
        "inspect_agent_write_gate_coverage",
        "inspect_agent_route_preference_projection",
        "plan_agent_route_approval_opt_in",
        "preview_pending_action_route_approval_opt_in_apply",
        "preview_pending_action_route_approval_opt_in_apply_contract",
        "apply_pending_action_route_approval_opt_in",
        "inspect_agent_knowledge_base_route",
        "record_agent_knowledge_base_candidate",
        "import_setup_world_model",
        "seed_continuity_anchor_proposals",
        "prepare_seed_continuity_anchor_proposals_execution",
        "execute_seed_continuity_anchor_proposals_with_approval",
        "analyze_chapter_world_model",
        "expand_outline_window",
        "prepare_expand_outline_window_execution",
        "execute_expand_outline_window_with_approval",
        "execute_longform_chapter_batch_preflight",
        "prepare_longform_chapter_batch_preflight",
        "execute_longform_chapter_batch_preflight_with_approval",
        "prepare_longform_chapter_batch_execution",
        "prepare_longform_chapter_batch_execution_prepare",
        "execute_longform_chapter_batch_execution_prepare_with_approval",
        "execute_longform_chapter_batch",
        "review_longform_chapter_batch_execution",
        "prepare_longform_chapter_batch_execution_review",
        "execute_longform_chapter_batch_execution_review_with_approval",
        "route_longform_chapter_batch_after_review",
        "prepare_longform_chapter_batch_after_review_route",
        "execute_longform_chapter_batch_after_review_route_with_approval",
        "inspect_agent_trace_audit",
        "inspect_agent_memory_route",
        "summarize_longform_context",
        "inspect_agent_world_model_route",
        "review_chapter_quality",
        "review_chapter_continuity",
        "plan_chapter_revision",
        "create_revision_draft",
        "prepare_create_revision_draft_execution",
        "execute_create_revision_draft_with_approval",
        "apply_planner_revision_patch",
        "expand_chapter_to_target",
        "compress_chapter_to_target",
        "repair_longform_maintenance",
        "review_world_model_proposals",
        "plan_world_model_proposal_resolution",
        "preview_world_model_proposal_resolution",
        "apply_world_model_proposal_resolution",
        "prepare_apply_world_model_proposal_resolution",
        "execute_apply_world_model_proposal_resolution_with_approval",
        "draft_world_model_proposal_resolution_decisions",
        "generate_setup",
        "preview_generate_storyline_execution",
        "prepare_generate_storyline_execution",
        "execute_generate_storyline_with_approval",
        "generate_storyline",
        "preview_generate_outline_execution",
        "prepare_generate_outline_execution",
        "execute_generate_outline_with_approval",
        "generate_outline",
    }.issubset(names)


def test_tool_executor_exposes_adapter_metadata_for_trace():
    review_metadata = writing_agent_tool_adapter_metadata("review_chapter_quality")
    preflight_metadata = writing_agent_tool_adapter_metadata("preflight_writing")

    assert review_metadata == {
        "tool_name": "review_chapter_quality",
        "adapter_type": "static",
        "category": "review",
        "mutability": "read",
        "handler_name": "_review_chapter_quality",
    }
    assert preflight_metadata == {
        "tool_name": "preflight_writing",
        "adapter_type": "injected",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "preflight_writing",
    }
    assert writing_agent_tool_adapter_metadata_by_name()["preflight_writing"] == preflight_metadata
    assert writing_agent_tool_adapter_metadata("generate_chapter") == {
        "tool_name": "generate_chapter",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "guarded_write",
        "handler_name": "_generate_chapter",
        "write_policy": "approval_required_redirect",
    }


def test_tool_executor_exposes_inspect_agent_route_preference_projection_adapter_metadata():
    assert writing_agent_tool_adapter_metadata("inspect_agent_route_preference_projection") == {
        "tool_name": "inspect_agent_route_preference_projection",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "_inspect_agent_route_preference_projection",
    }


def test_tool_executor_exposes_inspect_agent_health_projection_adapter_metadata():
    assert writing_agent_tool_adapter_metadata("inspect_agent_health_projection") == {
        "tool_name": "inspect_agent_health_projection",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "_inspect_agent_health_projection",
    }


def test_tool_executor_exposes_route_approval_opt_in_plan_adapter_metadata():
    assert writing_agent_tool_adapter_metadata("plan_agent_route_approval_opt_in") == {
        "tool_name": "plan_agent_route_approval_opt_in",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "_plan_agent_route_approval_opt_in",
    }


def test_tool_executor_exposes_route_opt_in_apply_preview_adapter_metadata():
    assert writing_agent_tool_adapter_metadata("preview_pending_action_route_approval_opt_in_apply") == {
        "tool_name": "preview_pending_action_route_approval_opt_in_apply",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "_preview_pending_action_route_approval_opt_in_apply",
    }


def test_tool_executor_exposes_route_opt_in_apply_contract_adapter_metadata():
    assert writing_agent_tool_adapter_metadata("preview_pending_action_route_approval_opt_in_apply_contract") == {
        "tool_name": "preview_pending_action_route_approval_opt_in_apply_contract",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "_preview_pending_action_route_approval_opt_in_apply_contract",
    }


def test_tool_executor_exposes_apply_route_opt_in_approval_adapter_metadata():
    assert writing_agent_tool_adapter_metadata("apply_pending_action_route_approval_opt_in") == {
        "tool_name": "apply_pending_action_route_approval_opt_in",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "guarded_write",
        "handler_name": "_apply_pending_action_route_approval_opt_in",
        "write_policy": "approval_required_redirect",
    }
    assert writing_agent_tool_adapter_metadata("prepare_apply_pending_action_route_approval_opt_in") == {
        "tool_name": "prepare_apply_pending_action_route_approval_opt_in",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "_prepare_apply_pending_action_route_approval_opt_in",
    }
    assert writing_agent_tool_adapter_metadata("execute_apply_pending_action_route_approval_opt_in_with_approval") == {
        "tool_name": "execute_apply_pending_action_route_approval_opt_in_with_approval",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "write",
        "handler_name": "_execute_apply_pending_action_route_approval_opt_in_with_approval",
    }


def test_tool_executor_exposes_dialog_control_plane_projection_adapter_metadata():
    assert writing_agent_tool_adapter_metadata("inspect_agent_dialog_control_plane_projection") == {
        "tool_name": "inspect_agent_dialog_control_plane_projection",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "_inspect_agent_dialog_control_plane_projection",
    }


def test_tool_executor_exposes_approved_direct_chapter_generation_adapter_metadata():
    assert writing_agent_tool_adapter_metadata("prepare_generate_chapter_execution") == {
        "tool_name": "prepare_generate_chapter_execution",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "read",
        "handler_name": "_prepare_generate_chapter_execution",
    }
    assert writing_agent_tool_adapter_metadata("execute_generate_chapter_with_approval") == {
        "tool_name": "execute_generate_chapter_with_approval",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "write",
        "handler_name": "_execute_generate_chapter_with_approval",
    }


def test_tool_executor_exposes_approved_setup_generation_adapter_metadata():
    assert writing_agent_tool_adapter_metadata("generate_setup") == {
        "tool_name": "generate_setup",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "guarded_write",
        "handler_name": "_generate_setup",
        "write_policy": "approval_required_redirect",
    }
    assert writing_agent_tool_adapter_metadata("preview_generate_setup_execution") == {
        "tool_name": "preview_generate_setup_execution",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "read",
        "handler_name": "_preview_generate_setup_execution",
    }
    assert writing_agent_tool_adapter_metadata("prepare_generate_setup_execution") == {
        "tool_name": "prepare_generate_setup_execution",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "read",
        "handler_name": "_prepare_generate_setup_execution",
    }
    assert writing_agent_tool_adapter_metadata("execute_generate_setup_with_approval") == {
        "tool_name": "execute_generate_setup_with_approval",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "write",
        "handler_name": "_execute_generate_setup_with_approval",
    }


def test_tool_executor_exposes_approved_storyline_generation_adapter_metadata():
    assert writing_agent_tool_adapter_metadata("generate_storyline") == {
        "tool_name": "generate_storyline",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "guarded_write",
        "handler_name": "_generate_storyline",
        "write_policy": "approval_required_redirect",
    }
    assert writing_agent_tool_adapter_metadata("preview_generate_storyline_execution") == {
        "tool_name": "preview_generate_storyline_execution",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "read",
        "handler_name": "_preview_generate_storyline_execution",
    }
    assert writing_agent_tool_adapter_metadata("prepare_generate_storyline_execution") == {
        "tool_name": "prepare_generate_storyline_execution",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "read",
        "handler_name": "_prepare_generate_storyline_execution",
    }
    assert writing_agent_tool_adapter_metadata("execute_generate_storyline_with_approval") == {
        "tool_name": "execute_generate_storyline_with_approval",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "write",
        "handler_name": "_execute_generate_storyline_with_approval",
    }


def test_tool_executor_exposes_approved_outline_generation_adapter_metadata():
    assert writing_agent_tool_adapter_metadata("generate_outline") == {
        "tool_name": "generate_outline",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "guarded_write",
        "handler_name": "_generate_outline",
        "write_policy": "approval_required_redirect",
    }
    assert writing_agent_tool_adapter_metadata("preview_generate_outline_execution") == {
        "tool_name": "preview_generate_outline_execution",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "read",
        "handler_name": "_preview_generate_outline_execution",
    }
    assert writing_agent_tool_adapter_metadata("prepare_generate_outline_execution") == {
        "tool_name": "prepare_generate_outline_execution",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "read",
        "handler_name": "_prepare_generate_outline_execution",
    }
    assert writing_agent_tool_adapter_metadata("execute_generate_outline_with_approval") == {
        "tool_name": "execute_generate_outline_with_approval",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "write",
        "handler_name": "_execute_generate_outline_with_approval",
    }


def test_tool_executor_lists_unhandled_internal_tools_for_migration_tracking():
    names = unhandled_internal_writing_agent_tool_names()

    assert "create_revision_draft" not in names
    assert "apply_planner_revision_patch" not in names
    assert "expand_chapter_to_target" not in names
    assert "prepare_generate_chapter_execution" not in names
    assert "execute_generate_chapter_with_approval" not in names
    assert "preview_generate_setup_execution" not in names
    assert "prepare_generate_setup_execution" not in names
    assert "execute_generate_setup_with_approval" not in names
    assert "preview_generate_storyline_execution" not in names
    assert "prepare_generate_storyline_execution" not in names
    assert "execute_generate_storyline_with_approval" not in names
    assert "preview_generate_outline_execution" not in names
    assert "prepare_generate_outline_execution" not in names
    assert "execute_generate_outline_with_approval" not in names
    assert "compress_chapter_to_target" not in names
    assert "backfill_outline_gaps" not in names
    assert "repair_longform_maintenance" not in names
    assert "prepare_repair_longform_maintenance" not in names
    assert "execute_repair_longform_maintenance_with_approval" not in names
    assert "expand_outline_window" not in names
    assert "inspect_agent_trace_audit" not in names
    assert "inspect_agent_memory_route" not in names
    assert "summarize_longform_context" not in names
    assert "inspect_agent_world_model_route" not in names
    assert "review_chapter_quality" not in names
    assert "plan_writing_agent_run" not in names
    assert "plan_dialog_intent_agent_run" not in names
    assert "preview_agent_plan_approval_contract" not in names
    assert "verify_agent_plan_approval_contract" not in names
    assert "inspect_agent_control_plane_readiness" not in names
    assert "import_setup_world_model" not in names
    assert "seed_continuity_anchor_proposals" not in names
    assert "analyze_chapter_world_model" not in names
    assert "apply_world_model_proposal_resolution" not in names
    assert "prepare_apply_world_model_proposal_resolution" not in names
    assert "execute_apply_world_model_proposal_resolution_with_approval" not in names
    assert "plan_longform_chapter_batch" not in names
    assert "enqueue_longform_chapter_batch" not in names
    assert "inspect_longform_chapter_batch" not in names
    assert "inspect_agent_job_projection" not in names
    assert "inspect_agent_tool_contracts" not in names
    assert "inspect_agent_command_contracts" not in names
    assert "inspect_agent_write_gate_coverage" not in names
    assert "inspect_agent_route_preference_projection" not in names
    assert "plan_agent_route_approval_opt_in" not in names
    assert "preview_pending_action_route_approval_opt_in_apply" not in names
    assert "preview_pending_action_route_approval_opt_in_apply_contract" not in names
    assert "apply_pending_action_route_approval_opt_in" not in names
    assert "inspect_agent_knowledge_base_route" not in names
    assert "record_agent_knowledge_base_candidate" not in names
    assert "prepare_record_agent_knowledge_base_candidate" not in names
    assert "execute_record_agent_knowledge_base_candidate_with_approval" not in names
    assert "execute_longform_chapter_batch_preflight" not in names
    assert "prepare_longform_chapter_batch_preflight" not in names
    assert "execute_longform_chapter_batch_preflight_with_approval" not in names
    assert "prepare_longform_chapter_batch_execution" not in names
    assert "prepare_longform_chapter_batch_execution_prepare" not in names
    assert "execute_longform_chapter_batch_execution_prepare_with_approval" not in names
    assert "execute_longform_chapter_batch" not in names
    assert "review_longform_chapter_batch_execution" not in names
    assert "prepare_longform_chapter_batch_execution_review" not in names
    assert "execute_longform_chapter_batch_execution_review_with_approval" not in names
    assert "route_longform_chapter_batch_after_review" not in names
    assert "prepare_longform_chapter_batch_after_review_route" not in names
    assert "execute_longform_chapter_batch_after_review_route_with_approval" not in names
    assert "preflight_writing" not in names


def test_tool_executor_exposes_inspect_agent_memory_route_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_memory_route")

    assert metadata == {
        "tool_name": "inspect_agent_memory_route",
        "adapter_type": "static",
        "category": "longform_memory",
        "mutability": "read",
        "handler_name": "_inspect_agent_memory_route",
    }


def test_tool_executor_exposes_search_agent_retrieval_context_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("search_agent_retrieval_context")

    assert metadata == {
        "tool_name": "search_agent_retrieval_context",
        "adapter_type": "static",
        "category": "retrieval",
        "mutability": "read",
        "handler_name": "_search_agent_retrieval_context",
    }


def test_tool_executor_exposes_summarize_longform_context_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("summarize_longform_context")

    assert metadata == {
        "tool_name": "summarize_longform_context",
        "adapter_type": "static",
        "category": "longform_memory",
        "mutability": "read",
        "handler_name": "_summarize_longform_context",
    }


def test_tool_executor_exposes_inspect_agent_tool_contracts_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_tool_contracts")

    assert metadata == {
        "tool_name": "inspect_agent_tool_contracts",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "_inspect_agent_tool_contracts",
    }


def test_tool_executor_exposes_inspect_agent_reference_alignment_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_reference_alignment")

    assert metadata == {
        "tool_name": "inspect_agent_reference_alignment",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "_inspect_agent_reference_alignment",
    }


def test_tool_executor_exposes_inspect_agent_dogfood_evidence_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_dogfood_evidence")

    assert metadata == {
        "tool_name": "inspect_agent_dogfood_evidence",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "_inspect_agent_dogfood_evidence",
    }


def test_tool_executor_exposes_inspect_agent_command_contracts_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_command_contracts")

    assert metadata == {
        "tool_name": "inspect_agent_command_contracts",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "_inspect_agent_command_contracts",
    }


def test_tool_executor_exposes_inspect_agent_control_plane_readiness_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_control_plane_readiness")

    assert metadata == {
        "tool_name": "inspect_agent_control_plane_readiness",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "_inspect_agent_control_plane_readiness",
    }


def test_tool_executor_exposes_legacy_hermes_migration_projection_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_legacy_hermes_action_migration")

    assert metadata == {
        "tool_name": "inspect_legacy_hermes_action_migration",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "_inspect_legacy_hermes_action_migration",
    }


def test_tool_executor_exposes_inspect_agent_write_gate_coverage_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_write_gate_coverage")

    assert metadata == {
        "tool_name": "inspect_agent_write_gate_coverage",
        "adapter_type": "static",
        "category": "preflight",
        "mutability": "read",
        "handler_name": "_inspect_agent_write_gate_coverage",
    }


def test_tool_executor_exposes_analyze_chapter_world_model_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("analyze_chapter_world_model")

    assert metadata == {
        "tool_name": "analyze_chapter_world_model",
        "adapter_type": "static",
        "category": "athena_world_model",
        "mutability": "guarded_write",
        "handler_name": "_analyze_chapter_world_model",
        "write_policy": "approval_required_redirect",
    }


@pytest.mark.asyncio
async def test_tool_executor_redirects_direct_analyze_chapter_world_model_to_approval(db_session, monkeypatch):
    project = Project(name="Direct Chapter World Model Analysis Redirect")
    db_session.add(project)
    db_session.commit()
    calls: list[int] = []

    def fake_analysis_tool(db, project_id: str, *, chapter_index: int, run_id=None):
        calls.append(chapter_index)
        return {"status": "completed"}

    monkeypatch.setattr(
        "app.services.writing_agent.world_model_analysis_tool.analyze_chapter_world_model_tool",
        fake_analysis_tool,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-direct"),
        WritingAgentToolRequest(tool_name="analyze_chapter_world_model", params={"chapter_index": 3}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["target_type"] == "world_model"
    assert result.output["chapter_index"] == 3
    assert result.output["recommended_next_tools"] == ["prepare_analyze_chapter_world_model_execution"]
    assert result.output["required_approval"]["execute_tool"] == "execute_analyze_chapter_world_model_with_approval"
    assert result.output["side_effects"]["executed"] == []
    assert result.output["side_effects"]["skipped"] == ["analyze_chapter_world_model"]
    assert calls == []


def test_tool_executor_exposes_expand_outline_window_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("expand_outline_window")

    assert metadata == {
        "tool_name": "expand_outline_window",
        "adapter_type": "static",
        "category": "generation",
        "mutability": "guarded_write",
        "handler_name": "_expand_outline_window",
        "write_policy": "approval_required_redirect",
    }


def test_tool_executor_exposes_import_setup_world_model_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("import_setup_world_model")

    assert metadata == {
        "tool_name": "import_setup_world_model",
        "adapter_type": "static",
        "category": "athena_world_model",
        "mutability": "guarded_write",
        "handler_name": "_import_setup_world_model",
        "write_policy": "approval_required_redirect",
    }


@pytest.mark.asyncio
async def test_tool_executor_redirects_direct_import_setup_world_model_to_approval(db_session, monkeypatch):
    project = Project(name="Direct Setup World Model Redirect")
    db_session.add(project)
    db_session.commit()
    calls: list[str] = []

    def fake_import_tool(db, project_id: str):
        calls.append(project_id)
        return {"status": "completed"}

    monkeypatch.setattr(
        "app.services.writing_agent.setup_world_model_import_tool.import_setup_world_model_tool",
        fake_import_tool,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="import_setup_world_model", params={}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["target_type"] == "world_model"
    assert result.output["recommended_next_tools"] == ["prepare_import_setup_world_model_execution"]
    assert result.output["required_approval"]["execute_tool"] == "execute_import_setup_world_model_with_approval"
    assert result.output["side_effects"]["executed"] == []
    assert result.output["side_effects"]["skipped"] == ["import_setup_world_model"]
    assert calls == []


def test_tool_executor_exposes_seed_continuity_anchor_proposals_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("seed_continuity_anchor_proposals")

    assert metadata == {
        "tool_name": "seed_continuity_anchor_proposals",
        "adapter_type": "static",
        "category": "maintenance",
        "mutability": "guarded_write",
        "handler_name": "_seed_continuity_anchor_proposals",
        "write_policy": "approval_required_redirect",
    }


def test_tool_executor_exposes_apply_world_model_proposal_resolution_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("apply_world_model_proposal_resolution")
    prepare_metadata = writing_agent_tool_adapter_metadata("prepare_apply_world_model_proposal_resolution")
    execute_metadata = writing_agent_tool_adapter_metadata(
        "execute_apply_world_model_proposal_resolution_with_approval"
    )

    assert metadata == {
        "tool_name": "apply_world_model_proposal_resolution",
        "adapter_type": "static",
        "category": "athena_world_model",
        "mutability": "guarded_write",
        "handler_name": "_apply_world_model_proposal_resolution",
        "write_policy": "approval_required_redirect",
    }
    assert prepare_metadata == {
        "tool_name": "prepare_apply_world_model_proposal_resolution",
        "adapter_type": "static",
        "category": "athena_world_model",
        "mutability": "read",
        "handler_name": "_prepare_apply_world_model_proposal_resolution",
    }
    assert execute_metadata == {
        "tool_name": "execute_apply_world_model_proposal_resolution_with_approval",
        "adapter_type": "static",
        "category": "athena_world_model",
        "mutability": "write",
        "handler_name": "_execute_apply_world_model_proposal_resolution_with_approval",
    }


def test_tool_executor_exposes_create_revision_draft_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("create_revision_draft")

    assert metadata == {
        "tool_name": "create_revision_draft",
        "adapter_type": "static",
        "category": "revision",
        "mutability": "guarded_write",
        "handler_name": "_create_revision_draft",
        "write_policy": "approval_required_redirect",
    }


def test_tool_executor_exposes_apply_planner_revision_patch_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("apply_planner_revision_patch")

    assert metadata == {
        "tool_name": "apply_planner_revision_patch",
        "adapter_type": "static",
        "category": "revision",
        "mutability": "guarded_write",
        "handler_name": "_apply_planner_revision_patch",
        "write_policy": "approval_required_redirect",
    }


def test_tool_executor_exposes_expand_chapter_to_target_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("expand_chapter_to_target")

    assert metadata == {
        "tool_name": "expand_chapter_to_target",
        "adapter_type": "static",
        "category": "revision",
        "mutability": "guarded_write",
        "handler_name": "_expand_chapter_to_target",
        "write_policy": "approval_required_redirect",
    }


def test_tool_executor_exposes_compress_chapter_to_target_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("compress_chapter_to_target")

    assert metadata == {
        "tool_name": "compress_chapter_to_target",
        "adapter_type": "static",
        "category": "revision",
        "mutability": "guarded_write",
        "handler_name": "_compress_chapter_to_target",
        "write_policy": "approval_required_redirect",
    }


@pytest.mark.asyncio
async def test_tool_executor_handles_legacy_hermes_migration_projection(db_session):
    project = Project(name="Legacy Hermes Migration")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="inspect_legacy_hermes_action_migration"),
    )

    assert result.handled is True
    assert result.output["status"] == "completed"
    assert result.output["summary"]["legacy_action_count"] == 3
    assert result.output["summary"]["agent_native_ready_count"] == 3
    tools_by_name = {item["tool_name"]: item for item in result.output["tools"]}
    assert set(tools_by_name) == {"generate_setup", "generate_storyline", "generate_outline"}
    expected_execute_tools = {
        "generate_setup": "execute_generate_setup_with_approval",
        "generate_storyline": "execute_generate_storyline_with_approval",
        "generate_outline": "execute_generate_outline_with_approval",
    }
    for tool_name, execute_tool in expected_execute_tools.items():
        item = tools_by_name[tool_name]
        assert item["current_execution_route"] == "static_adapter"
        assert item["migration_stage"] == "agent_native_ready"
        assert item["agent_native_execution_route"] == "static_adapter"
        assert item["approval_wrapper"]["execute_tool"] == execute_tool
        assert item["approval_wrapper"]["execute_adapter_exists"] is True
        assert "confirm_execute" in item["required_guards"]
    assert "inspect_agent_tool_contracts" in result.output["recommended_next_tools"]


@pytest.mark.asyncio
async def test_tool_executor_handles_inspect_agent_tool_contracts(db_session):
    project = Project(name="Tool Contract Snapshot")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-contract"),
        WritingAgentToolRequest(
            tool_name="inspect_agent_tool_contracts",
            params={"chapter_index": 1, "include_gap_details": True},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["summary"]["total_tools"] >= 1
    assert result.output["summary"]["internal_tools"] >= 1
    assert result.output["coverage"]["schema_coverage_ratio"] == 1.0
    assert result.output["coverage"]["adapter_coverage_ratio"] == 1.0
    assert "confirmation_contract_ratio" in result.output["coverage"]
    assert "tool_visibility_projection" in result.output["reference_alignment"]["patterns"]
    assert "runtime_policy_projection" in result.output["reference_alignment"]["patterns"]
    assert "recommendation_surface_normalization" in result.output["reference_alignment"]["patterns"]
    assert "permission_scope_category" in result.output["reference_alignment"]["patterns"]
    assert "references/agent-projects/openclaw" in result.output["reference_alignment"]["source_refs"]
    tools_by_name = {tool["name"]: tool for tool in result.output["tools"]}
    assert tools_by_name["generate_setup"]["execution_route"] == "static_adapter"
    assert tools_by_name["generate_setup"]["mutability"] == "guarded_write"
    assert tools_by_name["generate_setup"]["permission_level"] == "confirm_required"
    assert "requires_confirmation" in tools_by_name["generate_setup"]["side_effects"]
    assert tools_by_name["generate_chapter"]["execution_route"] == "static_adapter"
    assert tools_by_name["preflight_writing"]["execution_route"] == "injected_adapter"
    assert tools_by_name["describe_agent_tools"]["mutability"] == "read"
    assert tools_by_name["describe_agent_tools"]["parallel_safe"] is True
    assert tools_by_name["inspect_agent_knowledge_base_route"]["memory_boundary"] == "knowledge_base"
    assert tools_by_name["search_agent_retrieval_context"]["capability_area"] == "retrieval"
    assert tools_by_name["search_agent_retrieval_context"]["resource_scope"] == "retrieval_index"
    assert tools_by_name["inspect_agent_tool_contracts"]["contract_status"] == "ready"
    assert tools_by_name["enqueue_longform_chapter_batch"]["mutability"] == "guarded_write"
    assert tools_by_name["enqueue_longform_chapter_batch"]["permission_level"] == "confirm_required"
    assert "requires_confirmation" in tools_by_name["enqueue_longform_chapter_batch"]["side_effects"]
    assert tools_by_name["route_longform_chapter_batch_after_review"]["mutability"] == "guarded_write"
    assert tools_by_name["execute_longform_chapter_batch"]["requires_confirmation"] is True
    assert tools_by_name["execute_longform_chapter_batch"]["mutability"] == "guarded_write"
    assert tools_by_name["execute_longform_chapter_batch"]["permission_level"] == "confirm_required"
    assert tools_by_name["execute_longform_chapter_batch"]["parallel_safe"] is False
    assert tools_by_name["execute_longform_chapter_batch"]["recovery_tools"] == [
        "inspect_agent_job_projection",
        "plan_recovery_tools",
    ]
    assert tools_by_name["generate_chapter"]["resource_scope"] == "manuscript"
    assert tools_by_name["generate_chapter"]["report_policy"] == {
        "stop_check_required": False,
        "stop_condition": None,
        "allowed_followups": [],
        "block_message": None,
    }
    assert tools_by_name["generate_chapter"]["recommendation_contract"] == {
        "output_fields": ["recommended_next_tools"],
        "canonical_output_field": "recommended_next_tools",
        "legacy_output_fields": [],
        "policy_followups": [],
        "recovery_followups": ["plan_recovery_tools", "inspect_agent_trace_audit"],
        "deterministic_followups": ["plan_recovery_tools", "inspect_agent_trace_audit"],
    }
    assert tools_by_name["generate_chapter"]["adapter_type"] == "static"
    assert "missing_agent_native_adapter" not in tools_by_name["generate_chapter"]["gap_codes"]
    assert "output_schema_too_generic" not in tools_by_name["generate_chapter"]["gap_codes"]
    assert tools_by_name["analyze_chapter_world_model"]["adapter_type"] == "static"
    assert tools_by_name["analyze_chapter_world_model"]["mutability"] == "guarded_write"
    assert tools_by_name["analyze_chapter_world_model"]["permission_level"] == "confirm_required"
    assert "missing_agent_native_adapter" not in tools_by_name["analyze_chapter_world_model"]["gap_codes"]
    assert tools_by_name["expand_outline_window"]["adapter_type"] == "static"
    assert tools_by_name["expand_outline_window"]["mutability"] == "guarded_write"
    assert tools_by_name["expand_outline_window"]["permission_level"] == "confirm_required"
    assert "requires_confirmation" in tools_by_name["expand_outline_window"]["side_effects"]
    assert "missing_agent_native_adapter" not in tools_by_name["expand_outline_window"]["gap_codes"]
    assert "output_schema_too_generic" not in tools_by_name["expand_outline_window"]["gap_codes"]
    assert tools_by_name["import_setup_world_model"]["adapter_type"] == "static"
    assert tools_by_name["import_setup_world_model"]["mutability"] == "guarded_write"
    assert tools_by_name["import_setup_world_model"]["permission_level"] == "confirm_required"
    assert "missing_agent_native_adapter" not in tools_by_name["import_setup_world_model"]["gap_codes"]
    assert "output_schema_too_generic" not in tools_by_name["import_setup_world_model"]["gap_codes"]
    assert tools_by_name["seed_continuity_anchor_proposals"]["adapter_type"] == "static"
    assert tools_by_name["seed_continuity_anchor_proposals"]["mutability"] == "guarded_write"
    assert tools_by_name["seed_continuity_anchor_proposals"]["permission_level"] == "confirm_required"
    assert tools_by_name["seed_continuity_anchor_proposals"]["report_policy"] == {
        "stop_check_required": True,
        "stop_condition": "non_terminal_step_and_should_generate_next_chapter_false_without_allowed_followup",
        "allowed_followups": [
            "apply_world_model_proposal_resolution",
            "execute_apply_world_model_proposal_resolution_with_approval",
        ],
        "block_message": "稳定连续性锚点提案尚未审批，已停止后续写作工具。",
    }
    assert tools_by_name["seed_continuity_anchor_proposals"]["recommendation_contract"] == {
        "output_fields": ["recommended_actions"],
        "canonical_output_field": "recommended_actions",
        "legacy_output_fields": ["recommended_actions"],
            "policy_followups": [
                "apply_world_model_proposal_resolution",
                "execute_apply_world_model_proposal_resolution_with_approval",
            ],
            "recovery_followups": ["plan_recovery_tools", "inspect_agent_trace_audit"],
            "deterministic_followups": [
                "apply_world_model_proposal_resolution",
                "execute_apply_world_model_proposal_resolution_with_approval",
                "plan_recovery_tools",
                "inspect_agent_trace_audit",
            ],
        }
    assert "missing_agent_native_adapter" not in tools_by_name["seed_continuity_anchor_proposals"]["gap_codes"]
    assert "output_schema_too_generic" not in tools_by_name["seed_continuity_anchor_proposals"]["gap_codes"]
    assert tools_by_name["apply_world_model_proposal_resolution"]["adapter_type"] == "static"
    assert tools_by_name["apply_world_model_proposal_resolution"]["mutability"] == "guarded_write"
    assert tools_by_name["apply_world_model_proposal_resolution"]["requires_confirmation"] is True
    assert tools_by_name["review_world_model_proposals"]["recommendation_contract"] == {
        "output_fields": [],
        "canonical_output_field": None,
        "legacy_output_fields": [],
        "policy_followups": ["plan_world_model_proposal_resolution"],
        "recovery_followups": ["review_world_model_proposals", "plan_world_model_proposal_resolution"],
        "deterministic_followups": ["plan_world_model_proposal_resolution", "review_world_model_proposals"],
    }
    assert "missing_agent_native_adapter" not in tools_by_name["apply_world_model_proposal_resolution"]["gap_codes"]
    assert "output_schema_too_generic" not in tools_by_name["apply_world_model_proposal_resolution"]["gap_codes"]
    assert tools_by_name["create_revision_draft"]["adapter_type"] == "static"
    assert tools_by_name["create_revision_draft"]["mutability"] == "guarded_write"
    assert "missing_agent_native_adapter" not in tools_by_name["create_revision_draft"]["gap_codes"]
    assert tools_by_name["apply_planner_revision_patch"]["adapter_type"] == "static"
    assert tools_by_name["apply_planner_revision_patch"]["mutability"] == "guarded_write"
    assert "missing_agent_native_adapter" not in tools_by_name["apply_planner_revision_patch"]["gap_codes"]
    assert "output_schema_too_generic" not in tools_by_name["apply_planner_revision_patch"]["gap_codes"]
    assert tools_by_name["apply_pending_action_route_approval_opt_in"]["adapter_type"] == "static"
    assert tools_by_name["apply_pending_action_route_approval_opt_in"]["mutability"] == "guarded_write"
    assert tools_by_name["apply_pending_action_route_approval_opt_in"]["requires_confirmation"] is True
    assert "missing_agent_native_adapter" not in tools_by_name["apply_pending_action_route_approval_opt_in"]["gap_codes"]
    assert "output_schema_too_generic" not in tools_by_name["apply_pending_action_route_approval_opt_in"]["gap_codes"]
    assert tools_by_name["expand_chapter_to_target"]["adapter_type"] == "static"
    assert tools_by_name["expand_chapter_to_target"]["mutability"] == "guarded_write"
    assert "missing_agent_native_adapter" not in tools_by_name["expand_chapter_to_target"]["gap_codes"]
    assert "output_schema_too_generic" not in tools_by_name["expand_chapter_to_target"]["gap_codes"]
    assert tools_by_name["compress_chapter_to_target"]["adapter_type"] == "static"
    assert tools_by_name["compress_chapter_to_target"]["mutability"] == "guarded_write"
    assert "missing_agent_native_adapter" not in tools_by_name["compress_chapter_to_target"]["gap_codes"]
    assert "output_schema_too_generic" not in tools_by_name["compress_chapter_to_target"]["gap_codes"]
    assert internal_tool_names().issubset(set(tools_by_name))


@pytest.mark.asyncio
async def test_tool_executor_handles_inspect_agent_reference_alignment(db_session):
    project = Project(name="Reference Alignment Projection")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-reference"),
        WritingAgentToolRequest(tool_name="inspect_agent_reference_alignment"),
    )

    assert result.handled is True
    assert result.output["status"] == "completed"
    assert result.output["summary"]["source_count"] == 3
    assert result.output["summary"]["decision_count"] >= 9
    assert result.output["summary"]["capability_area_count"] >= 9
    assert result.output["source_refs"] == [
        "references/agent-projects/hermes-agent",
        "references/agent-projects/openhuman",
        "references/agent-projects/openclaw",
    ]
    pattern_ids = {pattern["pattern_id"] for pattern in result.output["patterns"]}
    assert {
        "tool_registry_visible_surface",
        "subagent_worker_boundary",
        "permission_audit_gate",
        "long_memory_context_resume",
    }.issubset(pattern_ids)
    worker_pattern = next(
        pattern for pattern in result.output["patterns"] if pattern["pattern_id"] == "subagent_worker_boundary"
    )
    worker_decision_ids = {decision["decision_id"] for decision in worker_pattern["novelv3_decisions"]}
    assert "yaml_worker_definition_registry" in worker_decision_ids
    assert "story_asset_worker_chain" in worker_decision_ids
    story_asset_decision = next(
        decision for decision in worker_pattern["novelv3_decisions"] if decision["decision_id"] == "story_asset_worker_chain"
    )
    assert story_asset_decision["status"] == "implemented"
    assert {
        "preview_generate_setup_execution",
        "prepare_generate_storyline_execution",
        "execute_generate_outline_with_approval",
        "inspect_agent_worker_dispatch",
    }.issubset(set(story_asset_decision["evidence_tools"]))
    assert "inspect_agent_worker_dispatch" in worker_pattern["recommended_next_tools"]
    capability_areas = {item["area"] for item in result.output["capability_alignment"]}
    assert {
        "Hermes/dialog",
        "Athena/world_model",
        "story_assets",
        "retrieval",
        "knowledge_base",
        "review",
        "task_queue",
        "trace",
        "frontend",
        "long_memory",
    }.issubset(capability_areas)
    story_asset_area = next(
        item for item in result.output["capability_alignment"] if item["area"] == "story_assets"
    )
    assert story_asset_area["status"] == "implemented"
    assert {
        "preview_generate_setup_execution",
        "prepare_generate_storyline_execution",
        "execute_generate_outline_with_approval",
    }.issubset(set(story_asset_area["adapter_backed_tools"]))
    assert "inspect_agent_tool_contracts" in result.output["recommended_next_tools"]
    assert "inspect_agent_write_gate_coverage" in result.output["recommended_next_tools"]
    assert result.output["trace"]["adapter_backed_tool_count"] >= 1


@pytest.mark.asyncio
async def test_tool_executor_handles_inspect_agent_dogfood_evidence(db_session):
    project = Project(name="Dogfood Evidence Projection")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-dogfood"),
        WritingAgentToolRequest(tool_name="inspect_agent_dogfood_evidence"),
    )

    assert result.handled is True
    assert result.output["status"] == "ready"
    assert result.output["summary"]["covered_capability_count"] == result.output["summary"]["required_capability_count"]
    assert "full_agent_native_loop_20260526" in {item["evidence_id"] for item in result.output["evidence"]}
    assert "inspect_agent_health_projection" in result.output["recommended_next_tools"]
    assert result.output["trace"]["mutability"] == "read"


@pytest.mark.asyncio
async def test_tool_executor_handles_inspect_agent_command_contracts(db_session):
    project = Project(name="Command Contract Snapshot")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-command-contract"),
        WritingAgentToolRequest(tool_name="inspect_agent_command_contracts"),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["version"] == "phase38.agent_command_contracts.v1"
    assert result.output["summary"]["total_commands"] >= 4
    assert result.output["summary"]["commands_with_control_projection"] == 2
    commands_by_name = {command["name"]: command for command in result.output["commands"]}
    assert commands_by_name["continue"]["contract_status"] == "ready"
    assert commands_by_name["continue"]["control_projection_type"] == "continue_agent_control"
    assert commands_by_name["continue"]["required_agent_tools"] == [
        "inspect_agent_health_projection",
        "inspect_agent_command_contracts",
        "plan_recovery_tools",
        "plan_recommended_followups",
        "prepare_generate_chapter_execution",
    ]
    assert commands_by_name["status"]["control_projection_type"] == "agent_health_projection"
    assert commands_by_name["clear"]["contract_status"] == "ready"
    assert commands_by_name["clear"]["control_projection_type"] == ""
    assert result.output["gaps"] == []
    assert "inspect_agent_tool_contracts" in result.output["recommended_next_tools"]


@pytest.mark.asyncio
async def test_tool_executor_handles_inspect_agent_control_plane_readiness(db_session):
    project = Project(name="Control Plane Readiness")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-control-plane"),
        WritingAgentToolRequest(tool_name="inspect_agent_control_plane_readiness"),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] in {"ready", "degraded"}
    assert result.output["summary"]["agent_control_commands"] == 2
    assert "tool_contracts" in result.output["control_surfaces"]
    assert "command_contracts" in result.output["control_surfaces"]
    assert "inspect_agent_health_projection" in result.output["recommended_next_tools"]


@pytest.mark.asyncio
async def test_tool_executor_handles_inspect_agent_write_gate_coverage(db_session):
    project = Project(name="Write Gate Coverage")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-gate-coverage"),
        WritingAgentToolRequest(tool_name="inspect_agent_write_gate_coverage", params={}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    tools_by_name = {tool["tool_name"]: tool for tool in result.output["write_tools"]}
    assert tools_by_name["execute_longform_chapter_batch"]["agent_plan_gate_status"] == "enforced"
    assert tools_by_name["execute_generate_chapter_with_approval"]["agent_plan_gate_status"] == "enforced"
    assert tools_by_name["generate_chapter"]["agent_plan_gate_status"] == "indirect_agent_gate_available"
    assert tools_by_name["generate_chapter"]["direct_write_policy"] == "approval_required_redirect"
    assert tools_by_name["generate_chapter"]["direct_write_blocked"] is True
    assert tools_by_name["generate_chapter"]["risk_level"] == "low"
    assert result.output["recommended_next_targets"]


@pytest.mark.asyncio
async def test_tool_executor_hides_contract_gap_details_when_requested(db_session):
    project = Project(name="Tool Contract Snapshot Compact")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-contract-compact"),
        WritingAgentToolRequest(
            tool_name="inspect_agent_tool_contracts",
            params={"chapter_index": 1, "include_gap_details": False},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["gaps"] == []
    assert all("gaps" not in tool for tool in result.output["tools"])


def test_tool_executor_exposes_inspect_agent_trace_audit_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_trace_audit")

    assert metadata == {
        "tool_name": "inspect_agent_trace_audit",
        "adapter_type": "static",
        "category": "trace",
        "mutability": "read",
        "handler_name": "_inspect_agent_trace_audit",
    }


def test_tool_executor_exposes_inspect_agent_world_model_route_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_world_model_route")

    assert metadata == {
        "tool_name": "inspect_agent_world_model_route",
        "adapter_type": "static",
        "category": "athena_world_model",
        "mutability": "read",
        "handler_name": "_inspect_agent_world_model_route",
    }


def test_tool_executor_exposes_backfill_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("backfill_outline_gaps")

    assert metadata == {
        "tool_name": "backfill_outline_gaps",
        "adapter_type": "static",
        "category": "maintenance",
        "mutability": "guarded_write",
        "handler_name": "_backfill_outline_gaps",
        "write_policy": "approval_required_redirect",
    }


@pytest.mark.asyncio
async def test_tool_executor_redirects_direct_backfill_outline_gaps_to_approval(db_session, monkeypatch):
    project = Project(name="Direct Backfill Redirect")
    db_session.add(project)
    db_session.commit()
    calls: list[int | None] = []

    def fake_backfill(db, project_id: str, *, before_chapter: int | None):
        calls.append(before_chapter)
        return {"status": "completed"}

    monkeypatch.setattr(
        "app.core.outline_lookup.backfill_missing_outline_chapters_from_content",
        fake_backfill,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="backfill_outline_gaps", params={"before_chapter": "4"}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["target_type"] == "outline"
    assert result.output["before_chapter"] == 4
    assert result.output["recommended_next_tools"] == ["prepare_backfill_outline_gaps_execution"]
    assert result.output["required_approval"]["execute_tool"] == "execute_backfill_outline_gaps_with_approval"
    assert result.output["side_effects"]["executed"] == []
    assert result.output["side_effects"]["skipped"] == ["backfill_outline_gaps"]
    assert calls == []


def test_tool_executor_exposes_repair_longform_maintenance_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("repair_longform_maintenance")

    assert metadata == {
        "tool_name": "repair_longform_maintenance",
        "adapter_type": "static",
        "category": "maintenance",
        "mutability": "guarded_write",
        "handler_name": "_repair_longform_maintenance",
        "write_policy": "approval_required_redirect",
    }


def test_tool_executor_exposes_repair_longform_maintenance_approval_chain_adapter_metadata():
    prepare_metadata = writing_agent_tool_adapter_metadata("prepare_repair_longform_maintenance")
    execute_metadata = writing_agent_tool_adapter_metadata("execute_repair_longform_maintenance_with_approval")

    assert prepare_metadata == {
        "tool_name": "prepare_repair_longform_maintenance",
        "adapter_type": "static",
        "category": "maintenance",
        "mutability": "read",
        "handler_name": "_prepare_repair_longform_maintenance",
    }
    assert execute_metadata == {
        "tool_name": "execute_repair_longform_maintenance_with_approval",
        "adapter_type": "static",
        "category": "maintenance",
        "mutability": "write",
        "handler_name": "_execute_repair_longform_maintenance_with_approval",
    }


def test_tool_executor_exposes_plan_longform_chapter_batch_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("plan_longform_chapter_batch")

    assert metadata == {
        "tool_name": "plan_longform_chapter_batch",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "read",
        "handler_name": "_plan_longform_chapter_batch",
    }


def test_tool_executor_exposes_enqueue_longform_chapter_batch_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("enqueue_longform_chapter_batch")

    assert metadata == {
        "tool_name": "enqueue_longform_chapter_batch",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "guarded_write",
        "handler_name": "_enqueue_longform_chapter_batch",
        "write_policy": "approval_required_redirect",
    }


def test_tool_executor_exposes_enqueue_longform_chapter_batch_approval_chain_adapter_metadata():
    prepare_metadata = writing_agent_tool_adapter_metadata("prepare_enqueue_longform_chapter_batch")
    execute_metadata = writing_agent_tool_adapter_metadata("execute_enqueue_longform_chapter_batch_with_approval")

    assert prepare_metadata == {
        "tool_name": "prepare_enqueue_longform_chapter_batch",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "read",
        "handler_name": "_prepare_enqueue_longform_chapter_batch",
    }
    assert execute_metadata == {
        "tool_name": "execute_enqueue_longform_chapter_batch_with_approval",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "write",
        "handler_name": "_execute_enqueue_longform_chapter_batch_with_approval",
    }


def test_tool_executor_exposes_inspect_longform_chapter_batch_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_longform_chapter_batch")

    assert metadata == {
        "tool_name": "inspect_longform_chapter_batch",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "read",
        "handler_name": "_inspect_longform_chapter_batch",
    }


def test_tool_executor_exposes_inspect_agent_job_projection_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_job_projection")

    assert metadata == {
        "tool_name": "inspect_agent_job_projection",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "read",
        "handler_name": "_inspect_agent_job_projection",
    }


def test_tool_executor_exposes_inspect_agent_knowledge_base_route_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_knowledge_base_route")

    assert metadata == {
        "tool_name": "inspect_agent_knowledge_base_route",
        "adapter_type": "static",
        "category": "knowledge_base",
        "mutability": "read",
        "handler_name": "_inspect_agent_knowledge_base_route",
    }


def test_tool_executor_exposes_plan_post_chapter_memory_capture_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("plan_post_chapter_memory_capture")

    assert metadata == {
        "tool_name": "plan_post_chapter_memory_capture",
        "adapter_type": "static",
        "category": "knowledge_base",
        "mutability": "read",
        "handler_name": "_plan_post_chapter_memory_capture",
    }


def test_tool_executor_exposes_record_agent_knowledge_base_candidate_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("record_agent_knowledge_base_candidate")

    assert metadata == {
        "tool_name": "record_agent_knowledge_base_candidate",
        "adapter_type": "static",
        "category": "knowledge_base",
        "mutability": "guarded_write",
        "handler_name": "_record_agent_knowledge_base_candidate",
        "write_policy": "approval_required_redirect",
    }


def test_tool_executor_exposes_knowledge_base_candidate_approval_chain_adapter_metadata():
    prepare_metadata = writing_agent_tool_adapter_metadata("prepare_record_agent_knowledge_base_candidate")
    execute_metadata = writing_agent_tool_adapter_metadata("execute_record_agent_knowledge_base_candidate_with_approval")

    assert prepare_metadata == {
        "tool_name": "prepare_record_agent_knowledge_base_candidate",
        "adapter_type": "static",
        "category": "knowledge_base",
        "mutability": "read",
        "handler_name": "_prepare_record_agent_knowledge_base_candidate",
    }
    assert execute_metadata == {
        "tool_name": "execute_record_agent_knowledge_base_candidate_with_approval",
        "adapter_type": "static",
        "category": "knowledge_base",
        "mutability": "write",
        "handler_name": "_execute_record_agent_knowledge_base_candidate_with_approval",
    }


@pytest.mark.asyncio
async def test_tool_executor_handles_plan_post_chapter_memory_capture(db_session):
    project = Project(name="Post Chapter Memory Capture")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=2,
            title="雾港追踪",
            content="林深在黑市追查雾晶钥匙，结尾发现灯塔旧案的新证据。",
            word_count=2200,
            status="generated",
        )
    )
    run = WritingAgentRun(project_id=project.id, goal="审稿第2章", status="success", entrypoint="api")
    db_session.add(run)
    db_session.flush()
    db_session.add_all(
        [
            WritingAgentStep(
                run_id=run.id,
                project_id=project.id,
                step_index=1,
                tool_name="review_chapter_quality",
                status="success",
                chapter_index=2,
                output={
                    "status": "completed",
                    "warning_count": 1,
                    "findings": [
                        {
                            "severity": "warning",
                            "code": "thin_scene_action",
                            "message": "黑市场景动作偏少。",
                        }
                    ],
                },
            ),
            WritingAgentStep(
                run_id=run.id,
                project_id=project.id,
                step_index=2,
                tool_name="review_chapter_continuity",
                status="success",
                chapter_index=2,
                output={"status": "completed", "findings": []},
            ),
        ]
    )
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id=run.id),
        WritingAgentToolRequest(tool_name="plan_post_chapter_memory_capture", params={"chapter_index": 2}),
    )

    assert result.handled is True
    assert result.output["status"] == "completed"
    assert result.output["capture_status"] == "ready"
    assert result.output["chapter_index"] == 2
    assert result.output["summary"]["candidate_count"] >= 2
    assert result.output["recommended_next_tools"] == ["prepare_record_agent_knowledge_base_candidate"]
    candidates = result.output["candidates"]
    assert {candidate["memory_type"] for candidate in candidates} >= {
        "writing_pattern",
        "self_optimization_lesson",
    }
    assert candidates[0]["source_refs"] == [f"chapter_content:{candidates[0]['evidence']['chapter_content_id']}"]
    lesson = next(candidate for candidate in candidates if candidate["memory_type"] == "self_optimization_lesson")
    assert "thin_scene_action" in lesson["summary"]
    assert any(ref.startswith("writing_agent_step:") for ref in lesson["source_refs"])
    assert lesson["next_tool_call"]["tool_name"] == "prepare_record_agent_knowledge_base_candidate"
    assert result.output["memory_provenance"]["recovery"]["next_tools"] == [
        "prepare_record_agent_knowledge_base_candidate"
    ]


def test_tool_executor_exposes_execute_longform_chapter_batch_preflight_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("execute_longform_chapter_batch_preflight")

    assert metadata == {
        "tool_name": "execute_longform_chapter_batch_preflight",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "guarded_write",
        "handler_name": "_execute_longform_chapter_batch_preflight",
        "write_policy": "approval_required_redirect",
    }


def test_tool_executor_exposes_longform_chapter_batch_preflight_approval_chain_adapter_metadata():
    prepare_metadata = writing_agent_tool_adapter_metadata("prepare_longform_chapter_batch_preflight")
    execute_metadata = writing_agent_tool_adapter_metadata("execute_longform_chapter_batch_preflight_with_approval")

    assert prepare_metadata == {
        "tool_name": "prepare_longform_chapter_batch_preflight",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "read",
        "handler_name": "_prepare_longform_chapter_batch_preflight",
    }
    assert execute_metadata == {
        "tool_name": "execute_longform_chapter_batch_preflight_with_approval",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "write",
        "handler_name": "_execute_longform_chapter_batch_preflight_with_approval",
    }


def test_tool_executor_exposes_prepare_longform_chapter_batch_execution_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("prepare_longform_chapter_batch_execution")

    assert metadata == {
        "tool_name": "prepare_longform_chapter_batch_execution",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "guarded_write",
        "handler_name": "_prepare_longform_chapter_batch_execution",
        "write_policy": "approval_required_redirect",
    }


def test_tool_executor_exposes_longform_chapter_batch_execution_prepare_approval_chain_adapter_metadata():
    prepare_metadata = writing_agent_tool_adapter_metadata("prepare_longform_chapter_batch_execution_prepare")
    execute_metadata = writing_agent_tool_adapter_metadata(
        "execute_longform_chapter_batch_execution_prepare_with_approval"
    )

    assert prepare_metadata == {
        "tool_name": "prepare_longform_chapter_batch_execution_prepare",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "read",
        "handler_name": "_prepare_longform_chapter_batch_execution_prepare",
    }
    assert execute_metadata == {
        "tool_name": "execute_longform_chapter_batch_execution_prepare_with_approval",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "write",
        "handler_name": "_execute_longform_chapter_batch_execution_prepare_with_approval",
    }


def test_tool_executor_exposes_execute_longform_chapter_batch_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("execute_longform_chapter_batch")

    assert metadata == {
        "tool_name": "execute_longform_chapter_batch",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "write",
        "handler_name": "_execute_longform_chapter_batch",
    }


def test_tool_executor_exposes_review_longform_chapter_batch_execution_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("review_longform_chapter_batch_execution")

    assert metadata == {
        "tool_name": "review_longform_chapter_batch_execution",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "guarded_write",
        "handler_name": "_review_longform_chapter_batch_execution",
        "write_policy": "approval_required_redirect",
    }


def test_tool_executor_exposes_longform_chapter_batch_execution_review_approval_chain_adapter_metadata():
    prepare_metadata = writing_agent_tool_adapter_metadata("prepare_longform_chapter_batch_execution_review")
    execute_metadata = writing_agent_tool_adapter_metadata(
        "execute_longform_chapter_batch_execution_review_with_approval"
    )

    assert prepare_metadata == {
        "tool_name": "prepare_longform_chapter_batch_execution_review",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "read",
        "handler_name": "_prepare_longform_chapter_batch_execution_review",
    }
    assert execute_metadata == {
        "tool_name": "execute_longform_chapter_batch_execution_review_with_approval",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "write",
        "handler_name": "_execute_longform_chapter_batch_execution_review_with_approval",
    }


def test_tool_executor_exposes_route_longform_chapter_batch_after_review_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("route_longform_chapter_batch_after_review")
    prepare_metadata = writing_agent_tool_adapter_metadata("prepare_longform_chapter_batch_after_review_route")
    execute_metadata = writing_agent_tool_adapter_metadata(
        "execute_longform_chapter_batch_after_review_route_with_approval"
    )

    assert metadata == {
        "tool_name": "route_longform_chapter_batch_after_review",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "guarded_write",
        "handler_name": "_route_longform_chapter_batch_after_review",
        "write_policy": "approval_required_redirect",
    }
    assert prepare_metadata == {
        "tool_name": "prepare_longform_chapter_batch_after_review_route",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "read",
        "handler_name": "_prepare_longform_chapter_batch_after_review_route",
    }
    assert execute_metadata == {
        "tool_name": "execute_longform_chapter_batch_after_review_route_with_approval",
        "adapter_type": "static",
        "category": "task_queue",
        "mutability": "write",
        "handler_name": "_execute_longform_chapter_batch_after_review_route_with_approval",
    }


@pytest.mark.asyncio
async def test_tool_executor_dispatches_plan_longform_chapter_batch_adapter(db_session, monkeypatch):
    project = Project(name="Executor Batch Plan")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, int | None, int | None]] = []

    def fake_plan(db, project_id: str, *, source_run_id: str | None, start_chapter: int | None, batch_size: int | None):
        calls.append((project_id, source_run_id, start_chapter, batch_size))
        return {"status": "completed", "batch": {"chapter_indexes": [start_chapter]}}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_planner.build_longform_chapter_batch_plan",
        fake_plan,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="plan_longform_chapter_batch",
            params={"source_run_id": "run-1", "start_chapter": "7", "batch_size": "2"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "batch": {"chapter_indexes": [7]}}
    assert calls == [(project.id, "run-1", 7, 2)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_enqueue_longform_chapter_batch_adapter_to_approval_redirect(
    db_session,
    monkeypatch,
):
    project = Project(name="Executor Batch Enqueue")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, int | None, int | None, bool, str | None]] = []

    def fake_enqueue(
        db,
        project_id: str,
        *,
        source_run_id: str | None,
        start_chapter: int | None,
        batch_size: int | None,
        confirm_enqueue: bool,
        plan_hash: str | None,
    ):
        calls.append((project_id, source_run_id, start_chapter, batch_size, confirm_enqueue, plan_hash))
        return {"status": "queued", "task": {"id": "task-1"}}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_enqueue.build_longform_chapter_batch_enqueue",
        fake_enqueue,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="enqueue_longform_chapter_batch",
            params={
                "source_run_id": "run-1",
                "start_chapter": "7",
                "batch_size": "2",
                "confirm_enqueue": True,
                "plan_hash": "hash-1",
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["target_type"] == "background_task_enqueue"
    assert result.output["recommended_next_tools"] == ["prepare_enqueue_longform_chapter_batch"]
    assert result.output["required_approval"] == {
        "prepare_tool": "prepare_enqueue_longform_chapter_batch",
        "execute_tool": "execute_enqueue_longform_chapter_batch_with_approval",
        "approval_scope": "agent_plan_approval",
    }
    assert result.output["source_run_id"] == "run-1"
    assert result.output["start_chapter"] == 7
    assert result.output["batch_size"] == 2
    assert result.output["side_effects"] == {"executed": [], "skipped": ["enqueue_longform_chapter_batch"]}
    assert calls == []


@pytest.mark.asyncio
async def test_tool_executor_dispatches_enqueue_longform_chapter_batch_approval_executor(
    db_session,
    monkeypatch,
):
    from app.services.writing_agent.batch_enqueue_execution import prepare_enqueue_longform_chapter_batch

    project = Project(name="Executor Approved Batch Enqueue")
    db_session.add(project)
    db_session.commit()
    prepared = prepare_enqueue_longform_chapter_batch(db_session, project.id, start_chapter=7, batch_size=2)
    calls: list[tuple[str, int | None, int | None, bool, str | None]] = []

    def fake_enqueue(
        db,
        project_id: str,
        *,
        source_run_id: str | None,
        start_chapter: int | None,
        batch_size: int | None,
        confirm_enqueue: bool,
        plan_hash: str | None,
    ):
        calls.append((project_id, start_chapter, batch_size, confirm_enqueue, plan_hash))
        return {"status": "queued", "task": {"id": "task-1"}, "plan_hash": plan_hash}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_enqueue_execution.build_longform_chapter_batch_enqueue",
        fake_enqueue,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_enqueue_longform_chapter_batch_with_approval",
            params={
                "start_chapter": "7",
                "batch_size": "2",
                "plan_hash": prepared["plan_hash"],
                "confirm_execute": True,
                "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
                "approval_contract": prepared["agent_plan_approval_contract"],
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "queued"
    assert result.output["agent_plan_approval_verification"]["status"] == "ready"
    assert result.output["side_effects"]["executed"] == ["enqueue_longform_chapter_batch"]
    assert calls == [(project.id, 7, 2, True, prepared["plan_hash"])]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_inspect_longform_chapter_batch_adapter(db_session, monkeypatch):
    project = Project(name="Executor Batch Inspect")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, str | None, int | None]] = []

    def fake_inspect(db, project_id: str, *, task_id: str | None, plan_hash: str | None, limit: int | None):
        calls.append((project_id, task_id, plan_hash, limit))
        return {"status": "completed", "tasks": []}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_queue_inspector.inspect_longform_chapter_batch_queue",
        fake_inspect,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="inspect_longform_chapter_batch",
            params={"task_id": "task-1", "plan_hash": "hash-1", "limit": "2"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "tasks": []}
    assert calls == [(project.id, "task-1", "hash-1", 2)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_inspect_agent_job_projection_adapter(db_session, monkeypatch):
    project = Project(name="Executor Agent Job Projection")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, str | None, str | None, int | None, int | None]] = []

    def fake_projection(
        db,
        project_id: str,
        *,
        task_id: str | None,
        task_type: str | None,
        status: str | None,
        limit: int | None,
        chapter_index: int | None,
    ):
        calls.append((project_id, task_id, task_type, status, limit, chapter_index))
        return {"status": "completed", "queue": {"depth": 0}}

    monkeypatch.setattr(
        "app.services.writing_agent.agent_job_projection.inspect_agent_job_projection",
        fake_projection,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="inspect_agent_job_projection",
            params={"task_id": "task-1", "task_type": "generate_chapter", "status": "failed", "limit": "9"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "queue": {"depth": 0}}
    assert calls == [(project.id, "task-1", "generate_chapter", "failed", 9, None)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_inspect_agent_job_projection_with_chapter_index(db_session, monkeypatch):
    project = Project(name="Executor Agent Job Projection Chapter")
    db_session.add(project)
    db_session.commit()
    captured = {}

    def fake_projection(
        db,
        project_id: str,
        *,
        task_id: str | None,
        task_type: str | None,
        status: str | None,
        limit: int | None,
        chapter_index: int | None,
    ):
        captured.update(
            {
                "project_id": project_id,
                "task_id": task_id,
                "task_type": task_type,
                "status": status,
                "limit": limit,
                "chapter_index": chapter_index,
            }
        )
        return {"status": "completed"}

    monkeypatch.setattr(
        "app.services.writing_agent.agent_job_projection.inspect_agent_job_projection",
        fake_projection,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="inspect_agent_job_projection", params={"chapter_index": 3, "limit": 5}),
    )

    assert result.handled is True
    assert result.output == {"status": "completed"}
    assert captured == {
        "project_id": project.id,
        "task_id": None,
        "task_type": None,
        "status": None,
        "limit": 5,
        "chapter_index": 3,
    }


@pytest.mark.asyncio
async def test_tool_executor_dispatches_plan_chapter_conflict_recovery_adapter(db_session, monkeypatch):
    project = Project(name="Executor Chapter Conflict Recovery")
    db_session.add(project)
    db_session.commit()
    captured = {}

    def fake_plan(db, project_id: str, *, chapter_index: int | None):
        captured.update({"project_id": project_id, "chapter_index": chapter_index})
        return {"status": "completed", "chapter_index": chapter_index}

    monkeypatch.setattr(
        "app.services.writing_agent.chapter_conflict_recovery_planner.plan_chapter_conflict_recovery",
        fake_plan,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="plan_chapter_conflict_recovery", params={"chapter_index": "3"}),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "chapter_index": 3}
    assert captured == {"project_id": project.id, "chapter_index": 3}


@pytest.mark.asyncio
async def test_tool_executor_dispatches_inspect_agent_knowledge_base_route_adapter(db_session, monkeypatch):
    project = Project(name="Executor Knowledge Base Route")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int | None, str | None, int | None]] = []

    def fake_route(db, project_id: str, *, chapter_index: int | None, query: str | None, limit: int | None):
        calls.append((project_id, chapter_index, query, limit))
        return {"status": "completed", "route": {"status": "ready"}}

    monkeypatch.setattr(
        "app.services.writing_agent.agent_knowledge_base_route.inspect_agent_knowledge_base_route",
        fake_route,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="inspect_agent_knowledge_base_route",
            params={"chapter_index": "8", "query": "雾港节奏", "limit": "5"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "route": {"status": "ready"}}
    assert calls == [(project.id, 8, "雾港节奏", 5)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_record_agent_knowledge_base_candidate_adapter(db_session, monkeypatch):
    project = Project(name="Executor Knowledge Base Candidate")
    db_session.add(project)
    db_session.commit()
    calls: list[str] = []

    def fake_record(*args, **kwargs):
        calls.append("record")
        return {"status": "completed", "action": "created"}

    monkeypatch.setattr(
        "app.services.writing_agent.agent_knowledge_base_candidates.record_agent_knowledge_base_candidate",
        fake_record,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="record_agent_knowledge_base_candidate",
            params={
                "memory_type": "self_optimization_lesson",
                "title": "低细节续写可行",
                "summary": "Agent route 可以支撑续写。",
                "source_refs": ["phase77", "chapter:24"],
                "confidence": "0.8",
                "status": "candidate",
                "tags": ["dogfood"],
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["side_effects"] == {"executed": [], "skipped": ["record_agent_knowledge_base_candidate"]}
    assert result.output["recommended_next_tools"] == ["prepare_record_agent_knowledge_base_candidate"]
    assert result.output["required_approval"]["prepare_tool"] == "prepare_record_agent_knowledge_base_candidate"
    assert calls == []


@pytest.mark.asyncio
async def test_tool_executor_dispatches_prepare_record_agent_knowledge_base_candidate(db_session):
    project = Project(name="Prepare Knowledge Candidate")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="prepare_record_agent_knowledge_base_candidate",
            params={
                "memory_type": "self_optimization_lesson",
                "title": "低细节续写可行",
                "summary": "Agent route 可以支撑续写。",
                "source_refs": ["phase77", "chapter:24"],
                "confidence": "0.8",
                "status": "candidate",
                "tags": ["dogfood"],
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "approval_required"
    plan_step = result.output["agent_plan"]["steps"][0]
    assert plan_step["tool_name"] == "record_agent_knowledge_base_candidate"
    assert plan_step["approval_executor_tool_name"] == "execute_record_agent_knowledge_base_candidate_with_approval"
    assert plan_step["mutation_fingerprint"]["components"]["target_type"] == "agent_knowledge_base_candidate"
    assert result.output["agent_plan_approval_contract_hash"]
    assert result.output["agent_plan_approval_contract"]["write_steps"][0]["tool_name"] == (
        "record_agent_knowledge_base_candidate"
    )
    assert result.output["required_confirmation"]["confirm_execute"] is True
    assert result.output["side_effects"] == {"executed": [], "skipped": ["record_agent_knowledge_base_candidate"]}
    assert result.output["recommended_next_tools"] == ["execute_record_agent_knowledge_base_candidate_with_approval"]


@pytest.mark.asyncio
async def test_tool_executor_blocks_execute_record_knowledge_candidate_without_confirmation(db_session):
    project = Project(name="Blocked Knowledge Candidate")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_record_agent_knowledge_base_candidate_with_approval",
            params={
                "memory_type": "writing_pattern",
                "title": "章末钩子",
                "summary": "保持章节末尾的下一步行动压力。",
                "source_refs": ["chapter:24"],
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "confirmation_required"
    assert result.output["side_effects"] == {"executed": [], "skipped": ["record_agent_knowledge_base_candidate"]}


@pytest.mark.asyncio
async def test_tool_executor_executes_record_knowledge_candidate_with_approval(db_session):
    project = Project(name="Execute Knowledge Candidate", style_config={})
    db_session.add(project)
    db_session.commit()
    candidate_params = {
        "memory_type": "self_optimization_lesson",
        "title": "低细节续写可行",
        "summary": "Agent route 可以支撑续写。",
        "source_refs": ["phase77", "chapter:24"],
        "confidence": "0.8",
        "status": "candidate",
        "tags": ["dogfood"],
    }
    prepare = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="prepare_record_agent_knowledge_base_candidate", params=candidate_params),
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_record_agent_knowledge_base_candidate_with_approval",
            params={
                **candidate_params,
                "confirm_execute": True,
                "approval_contract_hash": prepare.output["agent_plan_approval_contract_hash"],
                "approval_contract": prepare.output["agent_plan_approval_contract"],
                "post_approval_continuation_tools": [
                    {"tool_name": "summarize_longform_context", "params": {"chapter_index": 2}},
                    {"tool_name": "preflight_writing", "params": {"chapter_index": 2}},
                ],
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "success"
    assert result.output["agent_plan_approval_verification"]["status"] == "ready"
    assert result.output["approval_verification_event"]["reason"] == "approval_contract_verified"
    assert result.output["execution_resource_binding"]["status"] == "ready"
    assert result.output["execution_resource_binding"]["expected"]["tool_name"] == "record_agent_knowledge_base_candidate"
    assert result.output["side_effects"] == {"executed": ["record_agent_knowledge_base_candidate"], "skipped": []}
    assert result.output["recommended_next_tools"] == ["summarize_longform_context", "preflight_writing"]
    assert result.output["post_approval_continuation_tools"][0]["params"] == {"chapter_index": 2}
    assert result.output["candidate"]["title"] == "低细节续写可行"

    db_session.refresh(project)
    candidates = project.style_config["knowledge_base_candidates"]
    assert len(candidates) == 1
    assert candidates[0]["title"] == "低细节续写可行"


@pytest.mark.asyncio
async def test_tool_executor_dispatches_execute_longform_chapter_batch_preflight_adapter(db_session):
    project = Project(name="Executor Batch Preflight")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_longform_chapter_batch_preflight",
            params={"task_id": "task-1", "max_chapters": "2", "confirm_checkpoint": True},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["required_approval"]["prepare_tool"] == "prepare_longform_chapter_batch_preflight"
    assert result.output["required_approval"]["execute_tool"] == "execute_longform_chapter_batch_preflight_with_approval"
    assert result.output["side_effects"] == {
        "executed": [],
        "skipped": ["execute_longform_chapter_batch_preflight"],
    }


@pytest.mark.asyncio
async def test_tool_executor_dispatches_approved_longform_chapter_batch_preflight_adapter(db_session, monkeypatch):
    project = Project(name="Executor Approved Batch Preflight")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, int | None, bool, str | None, dict | None]] = []

    def fake_execute(
        db,
        project_id: str,
        *,
        task_id: str | None,
        max_chapters: int | None,
        confirm_execute: bool,
        approval_contract_hash: str | None,
        approval_contract: dict | None,
        approval_tool_metadata_provider,
    ):
        calls.append((project_id, task_id, max_chapters, confirm_execute, approval_contract_hash, approval_contract))
        assert approval_tool_metadata_provider is not None
        return {"status": "ready", "checkpoint": {"task_id": task_id}}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_preflight_execution.execute_longform_chapter_batch_preflight_with_approval",
        fake_execute,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_longform_chapter_batch_preflight_with_approval",
            params={
                "task_id": "task-1",
                "max_chapters": "2",
                "confirm_execute": True,
                "approval_contract_hash": "approval:1",
                "approval_contract": {"status": "requires_confirmation"},
            },
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "ready", "checkpoint": {"task_id": "task-1"}}
    assert calls == [
        (project.id, "task-1", 2, True, "approval:1", {"status": "requires_confirmation"}),
    ]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_prepare_longform_chapter_batch_execution_adapter(db_session):
    project = Project(name="Executor Batch Prepare")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="prepare_longform_chapter_batch_execution",
            params={"task_id": "task-1", "confirm_prepare": True},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["required_approval"]["prepare_tool"] == "prepare_longform_chapter_batch_execution_prepare"
    assert result.output["required_approval"]["execute_tool"] == (
        "execute_longform_chapter_batch_execution_prepare_with_approval"
    )
    assert result.output["side_effects"] == {
        "executed": [],
        "skipped": ["prepare_longform_chapter_batch_execution"],
    }


@pytest.mark.asyncio
async def test_tool_executor_dispatches_approved_longform_chapter_batch_execution_prepare_adapter(
    db_session,
    monkeypatch,
):
    project = Project(name="Executor Approved Batch Prepare")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, bool, str | None, dict | None]] = []

    def fake_execute(
        db,
        project_id: str,
        *,
        task_id: str | None,
        confirm_execute: bool,
        approval_contract_hash: str | None,
        approval_contract: dict | None,
        approval_tool_metadata_provider,
    ):
        calls.append((project_id, task_id, confirm_execute, approval_contract_hash, approval_contract))
        assert approval_tool_metadata_provider is not None
        return {"status": "approval_required", "attempt_manifest": {"task_id": task_id}}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_execution_prepare_approval."
        "execute_longform_chapter_batch_execution_prepare_with_approval",
        fake_execute,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_longform_chapter_batch_execution_prepare_with_approval",
            params={
                "task_id": "task-1",
                "confirm_execute": True,
                "approval_contract_hash": "approval:1",
                "approval_contract": {"status": "requires_confirmation"},
            },
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "approval_required", "attempt_manifest": {"task_id": "task-1"}}
    assert calls == [(project.id, "task-1", True, "approval:1", {"status": "requires_confirmation"})]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_execute_longform_chapter_batch_adapter(db_session, monkeypatch):
    project = Project(name="Executor Batch Execute")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, bool, str | None, str | None, bool]] = []

    async def fake_execute(
        db,
        project_id: str,
        *,
        task_id: str | None,
        confirm_execute: bool,
        attempt_manifest_hash: str | None,
        approval_contract_hash: str | None,
        approval_tool_metadata_provider,
    ):
        metadata = approval_tool_metadata_provider(
            {"steps": [{"tool_name": "generate_chapter", "mutability": "write", "requires_confirmation": True}]}
        )
        calls.append(
            (
                project_id,
                task_id,
                confirm_execute,
                attempt_manifest_hash,
                approval_contract_hash,
                metadata["generate_chapter"]["tool_exists"],
            )
        )
        return {"status": "completed", "chapter_index": 2}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_execution.execute_longform_chapter_batch",
        fake_execute,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_longform_chapter_batch",
            params={
                "task_id": "task-1",
                "confirm_execute": True,
                "attempt_manifest_hash": "attempt-hash",
                "approval_contract_hash": "contract-hash",
            },
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "chapter_index": 2}
    assert calls == [(project.id, "task-1", True, "attempt-hash", "contract-hash", True)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_review_longform_chapter_batch_execution_adapter(db_session, monkeypatch):
    project = Project(name="Executor Batch Review")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="review_longform_chapter_batch_execution",
            params={"task_id": "task-1", "lookback": "12", "confirm_review": True},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["required_approval"]["prepare_tool"] == "prepare_longform_chapter_batch_execution_review"
    assert result.output["required_approval"]["execute_tool"] == (
        "execute_longform_chapter_batch_execution_review_with_approval"
    )
    assert result.output["side_effects"] == {
        "executed": [],
        "skipped": ["review_longform_chapter_batch_execution"],
    }


@pytest.mark.asyncio
async def test_tool_executor_dispatches_approved_longform_chapter_batch_execution_review_adapter(
    db_session,
    monkeypatch,
):
    project = Project(name="Executor Approved Batch Review")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, int | None, bool, str | None, dict | None]] = []

    def fake_review(
        db,
        project_id: str,
        *,
        task_id: str | None,
        lookback: int | None,
        confirm_execute: bool,
        approval_contract_hash: str | None,
        approval_contract: dict | None,
        approval_tool_metadata_provider,
    ):
        calls.append((project_id, task_id, lookback, confirm_execute, approval_contract_hash, approval_contract))
        assert approval_tool_metadata_provider is not None
        return {"status": "completed", "chapter_index": 2}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_execution_review_approval."
        "execute_longform_chapter_batch_execution_review_with_approval",
        fake_review,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_longform_chapter_batch_execution_review_with_approval",
            params={
                "task_id": "task-1",
                "lookback": "12",
                "confirm_execute": True,
                "approval_contract_hash": "approval:review",
                "approval_contract": {"status": "requires_confirmation"},
            },
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "chapter_index": 2}
    assert calls == [
        (project.id, "task-1", 12, True, "approval:review", {"status": "requires_confirmation"})
    ]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_route_longform_chapter_batch_after_review_adapter(
    db_session,
):
    project = Project(name="Executor Batch Route")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="route_longform_chapter_batch_after_review",
            params={
                "task_id": "task-1",
                "expected_post_generation_review_hash": "review-hash",
                "next_batch_size": "2",
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["target_type"] == "background_task_post_review_route"
    assert result.output["required_approval"]["prepare_tool"] == "prepare_longform_chapter_batch_after_review_route"
    assert result.output["required_approval"]["execute_tool"] == (
        "execute_longform_chapter_batch_after_review_route_with_approval"
    )
    assert result.output["side_effects"] == {
        "executed": [],
        "skipped": ["route_longform_chapter_batch_after_review"],
    }


@pytest.mark.asyncio
async def test_tool_executor_dispatches_prepare_longform_chapter_batch_after_review_route_adapter(
    db_session,
    monkeypatch,
):
    project = Project(name="Executor Batch Route Prepare")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, str | None, int | None]] = []

    def fake_prepare(
        db,
        project_id: str,
        *,
        task_id: str | None,
        expected_post_generation_review_hash: str | None,
        next_batch_size: int | None,
    ):
        calls.append((project_id, task_id, expected_post_generation_review_hash, next_batch_size))
        return {"status": "approval_required", "task": {"id": task_id}}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_execution_route_approval."
        "prepare_longform_chapter_batch_after_review_route",
        fake_prepare,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="prepare_longform_chapter_batch_after_review_route",
            params={
                "task_id": "task-1",
                "expected_post_generation_review_hash": "review-hash",
                "next_batch_size": "2",
            },
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "approval_required", "task": {"id": "task-1"}}
    assert calls == [(project.id, "task-1", "review-hash", 2)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_approved_longform_chapter_batch_after_review_route_adapter(
    db_session,
    monkeypatch,
):
    project = Project(name="Executor Approved Batch Route")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, str | None, int | None, bool, str | None, dict | None]] = []

    def fake_route(
        db,
        project_id: str,
        *,
        task_id: str | None,
        expected_post_generation_review_hash: str | None,
        next_batch_size: int | None,
        confirm_execute: bool,
        approval_contract_hash: str | None,
        approval_contract: dict | None,
        approval_tool_metadata_provider,
    ):
        calls.append(
            (
                project_id,
                task_id,
                expected_post_generation_review_hash,
                next_batch_size,
                confirm_execute,
                approval_contract_hash,
                approval_contract,
            )
        )
        assert approval_tool_metadata_provider is not None
        return {"status": "completed", "route_decision": {"decision": "continue_to_next_batch"}}

    monkeypatch.setattr(
        "app.services.writing_agent.batch_execution_route_approval."
        "execute_longform_chapter_batch_after_review_route_with_approval",
        fake_route,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_longform_chapter_batch_after_review_route_with_approval",
            params={
                "task_id": "task-1",
                "expected_post_generation_review_hash": "review-hash",
                "next_batch_size": "2",
                "confirm_execute": True,
                "approval_contract_hash": "approval:route",
                "approval_contract": {"status": "requires_confirmation"},
            },
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "route_decision": {"decision": "continue_to_next_batch"}}
    assert calls == [
        (
            project.id,
            "task-1",
            "review-hash",
            2,
            True,
            "approval:route",
            {"status": "requires_confirmation"},
        )
    ]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_backfill_approval_adapter_with_normalized_params(db_session, monkeypatch):
    project = Project(name="Executor Backfill")
    db_session.add(project)
    db_session.commit()
    from app.services.writing_agent.outline_backfill_execution import prepare_backfill_outline_gaps_execution

    calls: list[tuple[str, int | None]] = []

    def fake_backfill(db, project_id: str, *, before_chapter: int | None):
        calls.append((project_id, before_chapter))
        return {"status": "completed", "before_chapter": before_chapter}

    monkeypatch.setattr(
        "app.services.writing_agent.outline_backfill_execution.backfill_missing_outline_chapters_from_content",
        fake_backfill,
    )
    context = WritingAgentToolContext(db=db_session, project_id=project.id)

    def approved_tool_params(before_chapter: int | None) -> dict:
        prepared = prepare_backfill_outline_gaps_execution(db_session, project.id, before_chapter=before_chapter)
        params = {
            "confirm_execute": True,
            "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
            "approval_contract": prepared["agent_plan_approval_contract"],
        }
        if before_chapter is not None:
            params["before_chapter"] = str(before_chapter)
        return params

    from_before = await execute_writing_agent_tool(
        context,
        WritingAgentToolRequest(
            tool_name="execute_backfill_outline_gaps_with_approval",
            params=approved_tool_params(7),
        ),
    )
    without_bound = await execute_writing_agent_tool(
        context,
        WritingAgentToolRequest(
            tool_name="execute_backfill_outline_gaps_with_approval",
            params=approved_tool_params(None),
        ),
    )

    assert from_before.handled is True
    assert from_before.output["status"] == "completed"
    assert from_before.output["before_chapter"] == 7
    assert from_before.output["agent_plan_approval_verification"]["status"] == "ready"
    assert without_bound.output["status"] == "completed"
    assert without_bound.output["before_chapter"] is None
    assert calls == [(project.id, 7), (project.id, None)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_repair_longform_maintenance_adapter(db_session, monkeypatch):
    project = Project(name="Executor Longform Repair")
    db_session.add(project)
    db_session.commit()
    calls: list[str] = []

    def fake_repair(*args, **kwargs):
        calls.append("repair")
        return {"status": "completed", "unexpected_direct_call": True}

    monkeypatch.setattr("app.core.longform_memory.repair_longform_maintenance", fake_repair)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="repair_longform_maintenance",
            params={"limit": "9", "repair_limit": "11"},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["side_effects"] == {"executed": [], "skipped": ["repair_longform_maintenance"]}
    assert result.output["recommended_next_tools"] == ["prepare_repair_longform_maintenance"]
    assert result.output["required_approval"]["prepare_tool"] == "prepare_repair_longform_maintenance"
    assert calls == []


@pytest.mark.asyncio
async def test_tool_executor_dispatches_repair_longform_maintenance_with_json_safe_output(db_session, monkeypatch):
    project = Project(name="Executor Longform Repair JSON Safe")
    db_session.add(project)
    db_session.commit()

    def fake_repair(db, project_id: str, *, limit: int, repair_limit: int):
        return {"status": "completed", "repaired_at": datetime(2026, 5, 23, 10, 30)}

    monkeypatch.setattr("app.core.longform_memory.repair_longform_maintenance", fake_repair)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="repair_longform_maintenance", params={}),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["required_approval"]["execute_tool"] == "execute_repair_longform_maintenance_with_approval"


@pytest.mark.asyncio
async def test_tool_executor_dispatches_prepare_repair_longform_maintenance(db_session):
    project = Project(name="Prepare Longform Repair")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="prepare_repair_longform_maintenance",
            params={"limit": "9", "repair_limit": "11"},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "approval_required"
    plan_step = result.output["agent_plan"]["steps"][0]
    assert plan_step["tool_name"] == "repair_longform_maintenance"
    assert plan_step["approval_executor_tool_name"] == "execute_repair_longform_maintenance_with_approval"
    assert plan_step["params"] == {"limit": 9, "repair_limit": 11}
    assert plan_step["mutation_fingerprint"]["components"]["target_type"] == "longform_maintenance"
    assert result.output["agent_plan_approval_contract_hash"]
    assert result.output["side_effects"] == {"executed": [], "skipped": ["repair_longform_maintenance"]}
    assert result.output["recommended_next_tools"] == ["execute_repair_longform_maintenance_with_approval"]


@pytest.mark.asyncio
async def test_tool_executor_blocks_execute_repair_longform_maintenance_without_confirmation(db_session):
    project = Project(name="Blocked Longform Repair")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_repair_longform_maintenance_with_approval",
            params={"limit": "9", "repair_limit": "11"},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "confirmation_required"
    assert result.output["side_effects"] == {"executed": [], "skipped": ["repair_longform_maintenance"]}


@pytest.mark.asyncio
async def test_tool_executor_executes_repair_longform_maintenance_with_approval(db_session, monkeypatch):
    project = Project(name="Execute Longform Repair")
    db_session.add(project)
    db_session.commit()
    prepare = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="prepare_repair_longform_maintenance",
            params={"limit": "9", "repair_limit": "11"},
        ),
    )
    calls: list[tuple[str, int, int]] = []

    def fake_repair(db, project_id: str, *, limit: int, repair_limit: int):
        calls.append((project_id, limit, repair_limit))
        return {
            "status": "completed",
            "repaired_memory_count": 2,
            "repaired_retrieval_count": 3,
            "remaining": {"ready_for_writing": True, "issue_count": 0},
        }

    monkeypatch.setattr("app.core.longform_memory.repair_longform_maintenance", fake_repair)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_repair_longform_maintenance_with_approval",
            params={
                "limit": "9",
                "repair_limit": "11",
                "confirm_execute": True,
                "approval_contract_hash": prepare.output["agent_plan_approval_contract_hash"],
                "approval_contract": prepare.output["agent_plan_approval_contract"],
                "post_approval_continuation_tools": [
                    {"tool_name": "summarize_longform_context", "params": {"chapter_index": 2}},
                    {"tool_name": "preflight_writing", "params": {"chapter_index": 2}},
                ],
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "success"
    assert result.output["repaired_memory_count"] == 2
    assert result.output["repaired_retrieval_count"] == 3
    assert result.output["agent_plan_approval_verification"]["status"] == "ready"
    assert result.output["approval_verification_event"]["reason"] == "approval_contract_verified"
    assert result.output["execution_resource_binding"]["expected"]["tool_name"] == "repair_longform_maintenance"
    assert result.output["side_effects"] == {"executed": ["repair_longform_maintenance"], "skipped": []}
    assert result.output["recommended_next_tools"] == ["summarize_longform_context", "preflight_writing"]
    assert result.output["post_approval_continuation_tools"][0]["params"] == {"chapter_index": 2}
    assert calls == [(project.id, 9, 11)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_inspect_agent_memory_route_adapter(db_session, monkeypatch):
    project = Project(name="Executor Memory Route")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int | None, str | None, bool]] = []

    def fake_route(db, project_id: str, *, chapter_index: int | None, query: str | None, include_context_summary: bool):
        calls.append((project_id, chapter_index, query, include_context_summary))
        return {"status": "completed", "route": {"status": "ready"}}

    monkeypatch.setattr("app.services.writing_agent.agent_memory_route.inspect_agent_memory_route", fake_route)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="inspect_agent_memory_route",
            params={"chapter_index": "12", "query": "父亲失踪", "include_context_summary": True},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "route": {"status": "ready"}}
    assert calls == [(project.id, 12, "父亲失踪", True)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_search_agent_retrieval_context_adapter(db_session, monkeypatch):
    project = Project(name="Executor Retrieval Context")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str, int, str | None, int | None, int | None]] = []

    def fake_search(
        db,
        project_id: str,
        query: str,
        *,
        limit: int,
        source_type: str | None,
        max_chapter_index: int | None,
        candidate_limit: int | None,
    ):
        calls.append((project_id, query, limit, source_type, max_chapter_index, candidate_limit))
        return {
            "query": query,
            "total": 1,
            "items": [
                {
                    "source_type": "chapter",
                    "source_ref": "chapter:2",
                    "title": "雾港追踪",
                    "chapter_index": 2,
                    "score": 0.91,
                    "snippet": "雾晶钥匙与灯塔旧案有关。",
                }
            ],
        }

    monkeypatch.setattr("app.core.athena_retrieval.search_retrieval", fake_search)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="search_agent_retrieval_context",
            command_args="灯塔旧案",
            params={"limit": "3", "source_type": "chapter", "max_chapter_index": "8", "candidate_limit": "20"},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "completed"
    assert result.output["summary"] == {"total": 1, "returned": 1}
    assert result.output["items"][0]["source_ref"] == "chapter:2"
    assert result.output["memory_provenance"]["sources"][0]["source_ref"] == "chapter:2"
    assert result.output["trace"]["mutability"] == "read"
    assert calls == [(project.id, "灯塔旧案", 3, "chapter", 8, 20)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_summarize_longform_context_adapter(db_session, monkeypatch):
    project = Project(name="Executor Context Summary")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int | None, str | None, int | None, bool]] = []

    def fake_summary(
        db,
        project_id: str,
        *,
        chapter_index: int | None,
        query: str | None,
        max_chars: int | None,
        include_prompt_context: bool,
    ):
        calls.append((project_id, chapter_index, query, max_chars, include_prompt_context))
        return {"status": "completed", "chapter_index": chapter_index, "sections": []}

    monkeypatch.setattr("app.services.writing_agent.longform_context_summary.summarize_longform_context", fake_summary)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="summarize_longform_context",
            command_args="灯塔记忆",
            params={"chapter_index": "14", "max_chars": "1500", "include_prompt_context": True},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "chapter_index": 14, "sections": []}
    assert calls == [(project.id, 14, "灯塔记忆", 1500, True)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_build_agent_context_compression_payload_adapter(db_session, monkeypatch):
    project = Project(name="Executor Context Compression Payload")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int | None, int | None, int]] = []

    def fake_payload(db, project_id: str, *, chapter_index: int | None, max_chars: int | None, context_guard_failure_count: int):
        calls.append((project_id, chapter_index, max_chars, context_guard_failure_count))
        return {"status": "ready", "compression_payload": {"execution_mode": "dry_run"}}

    monkeypatch.setattr(
        "app.services.writing_agent.agent_context_compression_projection.build_agent_context_compression_payload",
        fake_payload,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="build_agent_context_compression_payload",
            params={"chapter_index": "14", "max_chars": "1500", "context_guard_failure_count": "2"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "ready", "compression_payload": {"execution_mode": "dry_run"}}
    assert calls == [(project.id, 14, 1500, 2)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_inspect_agent_trace_audit_adapter(db_session, monkeypatch):
    project = Project(name="Executor Trace Audit")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, int | None, str | None, int | None]] = []

    def fake_audit(
        db,
        project_id: str,
        *,
        run_id: str | None,
        chapter_index: int | None,
        task_id: str | None,
        limit: int | None,
    ):
        calls.append((project_id, run_id, chapter_index, task_id, limit))
        return {"status": "completed", "audit": {"status": "completed"}}

    monkeypatch.setattr("app.services.writing_agent.agent_trace_audit.inspect_agent_trace_audit", fake_audit)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="inspect_agent_trace_audit",
            params={"run_id": "run-1", "chapter_index": "12", "task_id": "task-1", "limit": "7"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "audit": {"status": "completed"}}
    assert calls == [(project.id, "run-1", 12, "task-1", 7)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_inspect_agent_health_projection_adapter(db_session, monkeypatch):
    project = Project(name="Executor Agent Health")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str | None, str | None, int | None]] = []

    def fake_health(
        db,
        project_id: str,
        *,
        run_id: str | None,
        source: str | None,
        chapter_index: int | None,
        adapter_metadata_by_name,
        static_adapter_tool_names,
        action_execution_tool_names,
    ):
        calls.append((project_id, run_id, source, chapter_index))
        assert "inspect_agent_health_projection" in adapter_metadata_by_name
        assert "inspect_agent_health_projection" in static_adapter_tool_names
        assert isinstance(action_execution_tool_names, set)
        return {"status": "ready", "version": "phase218.agent_health_projection.v1"}

    monkeypatch.setattr("app.services.writing_agent.agent_health_projection.inspect_agent_health_projection", fake_health)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="inspect_agent_health_projection",
            params={"run_id": "run-1", "source": "text_intent", "chapter_index": "12"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "ready", "version": "phase218.agent_health_projection.v1"}
    assert calls == [(project.id, "run-1", "text_intent", 12)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_inspect_agent_world_model_route_adapter(db_session, monkeypatch):
    project = Project(name="Executor World Model Route")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int | None, str | None, int | None]] = []

    def fake_route(db, project_id: str, *, chapter_index: int | None, subject_ref: str | None, limit: int | None):
        calls.append((project_id, chapter_index, subject_ref, limit))
        return {"status": "completed", "route": {"status": "ready"}}

    monkeypatch.setattr("app.services.writing_agent.agent_world_model_route.inspect_agent_world_model_route", fake_route)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="inspect_agent_world_model_route",
            params={"chapter_index": "12", "subject_ref": "char.hero", "limit": "9"},
        ),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "route": {"status": "ready"}}
    assert calls == [(project.id, 12, "char.hero", 9)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_inspect_agent_mutation_fingerprints_adapter(db_session):
    project = Project(name="Executor Mutation Fingerprints")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="inspect_agent_mutation_fingerprints",
            params={"tools": [{"tool_name": "generate_chapter", "params": {"chapter_index": "4"}}]},
        ),
    )
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_mutation_fingerprints")

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["fingerprints"][0]["components"]["target_id"] == "chapter:4"
    assert metadata is not None
    assert metadata["mutability"] == "read"
    assert metadata["handler_name"] == "_inspect_agent_mutation_fingerprints"


@pytest.mark.asyncio
async def test_tool_executor_dispatches_chapter_report_adapters(db_session, monkeypatch):
    import app.core.chapter_revision_planner as revision_planner

    project = Project(name="Executor Chapter Reports")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str, int, int | None]] = []

    def fake_quality(db, project_id: str, chapter_index: int):
        calls.append(("quality", project_id, chapter_index, None))
        return {"status": "quality", "chapter_index": chapter_index}

    def fake_continuity(db, project_id: str, chapter_index: int, *, lookback: int):
        calls.append(("continuity", project_id, chapter_index, lookback))
        return {"status": "continuity", "chapter_index": chapter_index, "lookback": lookback}

    def fake_revision(db, project_id: str, chapter_index: int):
        calls.append(("revision", project_id, chapter_index, None))
        return {"status": "revision", "chapter_index": chapter_index}

    monkeypatch.setattr("app.core.chapter_quality_review.review_chapter_quality", fake_quality)
    monkeypatch.setattr("app.core.chapter_continuity_review.review_chapter_continuity", fake_continuity)
    monkeypatch.setattr(revision_planner, "plan_chapter_revision", fake_revision)
    context = WritingAgentToolContext(db=db_session, project_id=project.id)

    quality = await execute_writing_agent_tool(
        context,
        WritingAgentToolRequest(tool_name="review_chapter_quality", params={"chapter_index": 4}),
    )
    continuity = await execute_writing_agent_tool(
        context,
        WritingAgentToolRequest(tool_name="review_chapter_continuity", params={"chapter_index": 5}),
    )
    revision = await execute_writing_agent_tool(
        context,
        WritingAgentToolRequest(tool_name="plan_chapter_revision", params={"chapter_index": 6}),
    )

    assert quality.handled is True
    assert quality.output == {"status": "quality", "chapter_index": 4}
    assert continuity.output == {"status": "continuity", "chapter_index": 5, "lookback": 20}
    assert revision.output == {"status": "revision", "chapter_index": 6}
    assert calls == [
        ("quality", project.id, 4, None),
        ("continuity", project.id, 5, 20),
        ("revision", project.id, 6, None),
    ]


@pytest.mark.asyncio
async def test_tool_executor_redirects_direct_create_revision_draft_to_approval(db_session, monkeypatch):
    project = Project(name="Executor Revision Draft")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int]] = []

    def fake_revision_draft_tool(db, project_id: str, *, chapter_index: int):
        calls.append((project_id, chapter_index))
        return {"status": "drafted", "chapter_index": chapter_index, "revision_id": "rev-1"}

    monkeypatch.setattr(
        "app.services.writing_agent.revision_draft_tool.create_revision_draft_tool",
        fake_revision_draft_tool,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="create_revision_draft", params={"chapter_index": "7"}),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["chapter_index"] == 7
    assert result.output["required_approval"]["prepare_tool"] == "prepare_create_revision_draft_execution"
    assert result.output["required_approval"]["execute_tool"] == "execute_create_revision_draft_with_approval"
    assert result.output["side_effects"]["executed"] == []
    assert result.output["side_effects"]["skipped"] == ["create_revision_draft"]
    assert calls == []


@pytest.mark.asyncio
async def test_tool_executor_dispatches_create_revision_draft_approval_adapter(db_session, monkeypatch):
    from app.services.writing_agent.revision_draft_execution import prepare_create_revision_draft_execution

    project = Project(name="Executor Approved Revision Draft")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int]] = []

    def fake_revision_draft_tool(db, project_id: str, *, chapter_index: int):
        calls.append((project_id, chapter_index))
        return {"status": "drafted", "chapter_index": chapter_index, "revision_id": "rev-1"}

    monkeypatch.setattr(
        "app.services.writing_agent.revision_draft_execution.create_revision_draft_tool",
        fake_revision_draft_tool,
    )
    prepared = prepare_create_revision_draft_execution(db_session, project.id, chapter_index=7)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_create_revision_draft_with_approval",
            params={
                "chapter_index": "7",
                "confirm_execute": True,
                "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
                "approval_contract": prepared["agent_plan_approval_contract"],
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "drafted"
    assert result.output["chapter_index"] == 7
    assert result.output["revision_id"] == "rev-1"
    assert result.output["agent_plan_approval_verification"]["status"] == "ready"
    assert calls == [(project.id, 7)]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_apply_planner_revision_patch_adapter_to_approval_redirect(db_session):
    project = Project(name="Executor Revision Patch")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="apply_planner_revision_patch",
            params={"chapter_index": "8", "revision_id": " rev-8 "},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["revision_id"] == "rev-8"
    assert result.output["recommended_next_tools"] == ["prepare_apply_planner_revision_patch_execution"]
    assert result.output["required_approval"] == {
        "prepare_tool": "prepare_apply_planner_revision_patch_execution",
        "execute_tool": "execute_apply_planner_revision_patch_with_approval",
        "approval_scope": "agent_plan_approval",
    }
    assert result.output["side_effects"] == {"executed": [], "skipped": ["apply_planner_revision_patch"]}


@pytest.mark.asyncio
async def test_tool_executor_dispatches_approved_apply_planner_revision_patch_adapter(db_session, monkeypatch):
    from app.services.writing_agent.revision_patch_execution import prepare_apply_planner_revision_patch_execution

    project = Project(name="Executor Approved Revision Patch")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int, str | None]] = []

    def fake_revision_patch_tool(db, project_id: str, *, chapter_index: int, revision_id: str | None):
        calls.append((project_id, chapter_index, revision_id))
        return {"status": "completed", "chapter_index": chapter_index, "revision_id": revision_id}

    monkeypatch.setattr(
        "app.services.writing_agent.revision_patch_execution.apply_planner_revision_patch_tool",
        fake_revision_patch_tool,
    )
    prepared = prepare_apply_planner_revision_patch_execution(
        db_session,
        project.id,
        chapter_index=8,
        revision_id="rev-8",
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_apply_planner_revision_patch_with_approval",
            params={
                "chapter_index": "8",
                "revision_id": " rev-8 ",
                "confirm_execute": True,
                "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
                "approval_contract": prepared["agent_plan_approval_contract"],
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "completed"
    assert result.output["chapter_index"] == 8
    assert result.output["revision_id"] == "rev-8"
    assert result.output["agent_plan_approval_verification"]["status"] == "ready"
    assert calls == [(project.id, 8, "rev-8")]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_expand_chapter_to_target_adapter_to_approval_redirect(db_session):
    project = Project(name="Executor Chapter Expansion")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="expand_chapter_to_target",
            params={"chapter_index": "9", "min_word_count": "2100", "extra_instruction": "补足动作细节"},
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["recommended_next_tools"] == ["prepare_expand_chapter_to_target_execution"]
    assert result.output["required_approval"] == {
        "prepare_tool": "prepare_expand_chapter_to_target_execution",
        "execute_tool": "execute_expand_chapter_to_target_with_approval",
        "approval_scope": "agent_plan_approval",
    }
    assert result.output["side_effects"] == {"executed": [], "skipped": ["expand_chapter_to_target"]}


@pytest.mark.asyncio
async def test_tool_executor_dispatches_approved_expand_chapter_to_target_adapter(db_session, monkeypatch):
    from app.services.writing_agent.chapter_revision_execution import prepare_expand_chapter_to_target_execution

    project = Project(name="Executor Approved Chapter Expansion")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int, int | None, str]] = []

    async def fake_expansion_tool(
        db,
        project_id: str,
        *,
        chapter_index: int,
        min_word_count: int | None,
        extra_instruction: str,
    ):
        calls.append((project_id, chapter_index, min_word_count, extra_instruction))
        return {"status": "completed", "chapter_index": chapter_index, "word_count": 2200}

    monkeypatch.setattr(
        "app.services.writing_agent.chapter_revision_execution.expand_chapter_to_target_tool",
        fake_expansion_tool,
    )
    prepared = prepare_expand_chapter_to_target_execution(
        db_session,
        project.id,
        chapter_index=9,
        min_word_count=2100,
        extra_instruction="补足动作细节",
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_expand_chapter_to_target_with_approval",
            params={
                "chapter_index": "9",
                "min_word_count": "2100",
                "extra_instruction": "补足动作细节",
                "confirm_execute": True,
                "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
                "approval_contract": prepared["agent_plan_approval_contract"],
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "completed"
    assert result.output["chapter_index"] == 9
    assert result.output["word_count"] == 2200
    assert result.output["agent_plan_approval_verification"]["status"] == "ready"
    assert calls == [(project.id, 9, 2100, "补足动作细节")]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_expand_outline_window_adapter(db_session, monkeypatch):
    project = Project(name="Executor Outline Window")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int, int, str | None]] = []

    async def fake_outline_window_tool(
        db,
        project_id: str,
        *,
        start_chapter: int,
        end_chapter: int,
        command_args: str | None,
    ):
        calls.append((project_id, start_chapter, end_chapter, command_args))
        return {
            "status": "completed",
            "start_chapter": start_chapter,
            "end_chapter": end_chapter,
            "outline_id": "outline-3",
            "total_chapters": 600,
            "added_chapter_count": 1,
            "merge": {"added_chapter_count": 1},
            "trace_id": "trace-3",
            "recommended_next_tools": ["preflight_writing"],
        }

    monkeypatch.setattr(
        "app.services.writing_agent.outline_window_expansion_execution.expand_outline_window_tool",
        fake_outline_window_tool,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="expand_outline_window",
            command_args="补齐第3章",
            params={"chapter_index": "3"},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["required_approval"]["prepare_tool"] == "prepare_expand_outline_window_execution"
    assert result.output["required_approval"]["execute_tool"] == "execute_expand_outline_window_with_approval"
    assert result.output["side_effects"] == {"executed": [], "skipped": ["expand_outline_window"]}
    assert calls == []

    prepared = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="prepare_expand_outline_window_execution",
            params={"chapter_index": "3"},
        ),
    )

    assert prepared.handled is True
    assert prepared.output["status"] == "approval_required"

    confirmed = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_expand_outline_window_with_approval",
            command_args="补齐第3章",
            params={
                "chapter_index": "3",
                "confirm_execute": True,
                "approval_contract_hash": prepared.output["agent_plan_approval_contract_hash"],
                "approval_contract": prepared.output["agent_plan_approval_contract"],
            },
        ),
    )

    assert confirmed.handled is True
    assert confirmed.output is not None
    assert confirmed.output["status"] == "completed"
    assert confirmed.output["start_chapter"] == 3
    assert confirmed.output["end_chapter"] == 3
    assert confirmed.output["agent_plan_approval_verification"]["status"] == "ready"
    assert calls == [(project.id, 3, 3, "补齐第3章")]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_import_setup_world_model_approval_adapter(db_session, monkeypatch):
    project = Project(name="Executor Setup Import")
    db_session.add(project)
    db_session.commit()
    from app.services.writing_agent.setup_world_model_import_execution import (
        prepare_import_setup_world_model_execution,
    )

    calls: list[str] = []

    def fake_import_tool(db, project_id: str):
        calls.append(project_id)
        return {
            "status": "completed",
            "profile_version": 1,
            "project_profile_version_id": "profile-1",
            "created": {
                "profile": 1,
                "characters": 2,
                "locations": 1,
                "factions": 0,
                "artifacts": 0,
                "rules": 1,
            },
            "should_generate_next_chapter": False,
            "recommended_next_tools": ["preflight_writing", "inspect_agent_world_model_route"],
        }

    monkeypatch.setattr(
        "app.services.writing_agent.setup_world_model_import_execution.import_setup_world_model_tool",
        fake_import_tool,
    )
    prepared = prepare_import_setup_world_model_execution(db_session, project.id)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_import_setup_world_model_with_approval",
            params={
                "confirm_execute": True,
                "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
                "approval_contract": prepared["agent_plan_approval_contract"],
            },
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["profile_version"] == 1
    assert result.output["agent_plan_approval_verification"]["status"] == "ready"
    assert result.output["recommended_next_tools"] == ["preflight_writing", "inspect_agent_world_model_route"]
    assert calls == [project.id]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_seed_continuity_anchor_proposals_adapter_to_approval_redirect(
    db_session,
    monkeypatch,
):
    project = Project(name="Executor Continuity Anchor Seed")
    db_session.add(project)
    db_session.commit()
    calls: list[str] = []

    def fake_seed_tool(db, project_id: str):
        calls.append(project_id)
        return {
            "status": "blocked",
            "project_id": project_id,
            "profile_version": 1,
            "proposal_bundle_id": "bundle-1",
            "created_item_count": 2,
            "created_items": [
                {
                    "proposal_item_id": "item-1",
                    "claim_id": "claim-1",
                    "subject_ref": "林深",
                    "predicate": "father_name",
                }
            ],
            "pending_anchor_count": 2,
            "should_generate_next_chapter": False,
            "recommended_actions": ["apply_world_model_proposal_resolution"],
        }

    monkeypatch.setattr(
        "app.services.writing_agent.continuity_anchor_seed_tool.seed_continuity_anchor_proposals_tool",
        fake_seed_tool,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="seed_continuity_anchor_proposals", params={}),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["target_type"] == "world_model_continuity_anchor_seed"
    assert result.output["recommended_next_tools"] == ["prepare_seed_continuity_anchor_proposals_execution"]
    assert result.output["required_approval"] == {
        "prepare_tool": "prepare_seed_continuity_anchor_proposals_execution",
        "execute_tool": "execute_seed_continuity_anchor_proposals_with_approval",
        "approval_scope": "agent_plan_approval",
    }
    assert result.output["side_effects"] == {"executed": [], "skipped": ["seed_continuity_anchor_proposals"]}
    assert calls == []


@pytest.mark.asyncio
async def test_tool_executor_dispatches_seed_continuity_anchor_proposals_approval_executor(
    db_session,
    monkeypatch,
):
    from app.services.writing_agent.continuity_anchor_seed_execution import (
        prepare_seed_continuity_anchor_proposals_execution,
    )

    project = Project(name="Executor Approved Continuity Anchor Seed")
    db_session.add(project)
    db_session.commit()
    calls: list[str] = []

    def fake_seed_tool(db, project_id: str):
        calls.append(project_id)
        return {
            "status": "blocked",
            "project_id": project_id,
            "profile_version": 1,
            "proposal_bundle_id": "bundle-1",
            "created_item_count": 2,
            "created_items": [
                {
                    "proposal_item_id": "item-1",
                    "claim_id": "claim-1",
                    "subject_ref": "林深",
                    "predicate": "father_name",
                }
            ],
            "pending_anchor_count": 2,
            "should_generate_next_chapter": False,
            "recommended_actions": ["apply_world_model_proposal_resolution"],
        }

    monkeypatch.setattr(
        "app.services.writing_agent.continuity_anchor_seed_execution.seed_continuity_anchor_proposals_tool",
        fake_seed_tool,
    )
    prepared = prepare_seed_continuity_anchor_proposals_execution(db_session, project.id)

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_seed_continuity_anchor_proposals_with_approval",
            params={
                "confirm_execute": True,
                "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
                "approval_contract": prepared["agent_plan_approval_contract"],
            },
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "blocked"
    assert result.output["created_item_count"] == 2
    assert result.output["recommended_actions"] == ["apply_world_model_proposal_resolution"]
    assert result.output["agent_plan_approval_verification"]["status"] == "ready"
    assert calls == [project.id]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_compress_chapter_to_target_adapter_to_approval_redirect(db_session):
    project = Project(name="Executor Chapter Compression")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="compress_chapter_to_target",
            params={
                "chapter_index": "10",
                "target_max_word_count": "2300",
                "extra_instruction": "保留悬念",
                "forbidden_terms": ["  啰嗦  ", "", "重复"],
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "blocked"
    assert result.output["reason"] == "approval_required_before_write"
    assert result.output["recommended_next_tools"] == ["prepare_compress_chapter_to_target_execution"]
    assert result.output["required_approval"] == {
        "prepare_tool": "prepare_compress_chapter_to_target_execution",
        "execute_tool": "execute_compress_chapter_to_target_with_approval",
        "approval_scope": "agent_plan_approval",
    }
    assert result.output["forbidden_terms"] == ["啰嗦", "重复"]
    assert result.output["side_effects"] == {"executed": [], "skipped": ["compress_chapter_to_target"]}


@pytest.mark.asyncio
async def test_tool_executor_dispatches_approved_compress_chapter_to_target_adapter(db_session, monkeypatch):
    from app.services.writing_agent.chapter_revision_execution import prepare_compress_chapter_to_target_execution

    project = Project(name="Executor Approved Chapter Compression")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, int, int | None, str, list[str]]] = []

    async def fake_compression_tool(
        db,
        project_id: str,
        *,
        chapter_index: int,
        target_max_word_count: int | None,
        extra_instruction: str,
        forbidden_terms: list[str],
    ):
        calls.append((project_id, chapter_index, target_max_word_count, extra_instruction, forbidden_terms))
        return {"status": "completed", "chapter_index": chapter_index, "word_count": 2200}

    monkeypatch.setattr(
        "app.services.writing_agent.chapter_revision_execution.compress_chapter_to_target_tool",
        fake_compression_tool,
    )
    prepared = prepare_compress_chapter_to_target_execution(
        db_session,
        project.id,
        chapter_index=10,
        target_max_word_count=2300,
        extra_instruction="保留悬念",
        forbidden_terms=["啰嗦", "重复"],
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(
            tool_name="execute_compress_chapter_to_target_with_approval",
            params={
                "chapter_index": "10",
                "target_max_word_count": "2300",
                "extra_instruction": "保留悬念",
                "forbidden_terms": ["  啰嗦  ", "", "重复"],
                "confirm_execute": True,
                "approval_contract_hash": prepared["agent_plan_approval_contract_hash"],
                "approval_contract": prepared["agent_plan_approval_contract"],
            },
        ),
    )

    assert result.handled is True
    assert result.output["status"] == "completed"
    assert result.output["chapter_index"] == 10
    assert result.output["word_count"] == 2200
    assert result.output["agent_plan_approval_verification"]["status"] == "ready"
    assert calls == [(project.id, 10, 2300, "保留悬念", ["啰嗦", "重复"])]


@pytest.mark.asyncio
async def test_tool_executor_dispatches_world_proposal_report_adapters(db_session, monkeypatch):
    import app.core.world_proposal_resolution_plan as resolution_plan

    project = Project(name="Executor World Reports")
    db_session.add(project)
    db_session.commit()
    calls: list[tuple[str, str, object, object]] = []

    def fake_queue_report(db, project_id: str, *, offset: int, limit: int):
        calls.append(("queue", project_id, offset, limit))
        return {"status": "queue", "offset": offset, "limit": limit}

    def fake_resolution_plan(db, project_id: str, *, offset: int, limit: int):
        calls.append(("plan", project_id, offset, limit))
        return {"status": "plan", "offset": offset, "limit": limit}

    def fake_preview(db, project_id: str, decisions: list):
        calls.append(("preview", project_id, list(decisions), None))
        return {"status": "preview", "decision_count": len(decisions)}

    def fake_draft(db, project_id: str, *, limit: int, predicate_policies, include_unclassified: bool):
        calls.append(("draft", project_id, predicate_policies, include_unclassified))
        return {"status": "draft", "limit": limit, "predicate_policies": predicate_policies}

    monkeypatch.setattr("app.core.world_proposal_agent_report.build_world_proposal_agent_report", fake_queue_report)
    monkeypatch.setattr(resolution_plan, "build_world_proposal_resolution_plan", fake_resolution_plan)
    monkeypatch.setattr("app.core.world_proposal_resolution_preview.preview_world_model_proposal_resolution", fake_preview)
    monkeypatch.setattr(
        "app.core.world_proposal_resolution_draft.draft_world_model_proposal_resolution_decisions",
        fake_draft,
    )
    context = WritingAgentToolContext(db=db_session, project_id=project.id)

    queue = await execute_writing_agent_tool(context, WritingAgentToolRequest(tool_name="review_world_model_proposals"))
    plan = await execute_writing_agent_tool(
        context,
        WritingAgentToolRequest(tool_name="plan_world_model_proposal_resolution", params={"offset": "2", "limit": "7"}),
    )
    preview = await execute_writing_agent_tool(
        context,
        WritingAgentToolRequest(tool_name="preview_world_model_proposal_resolution", params={"decisions": "bad"}),
    )
    draft = await execute_writing_agent_tool(
        context,
        WritingAgentToolRequest(
            tool_name="draft_world_model_proposal_resolution_decisions",
            params={"limit": 20, "predicate_policies": ["bad"], "include_unclassified": True},
        ),
    )

    assert queue.handled is True
    assert queue.output == {"status": "queue", "offset": 0, "limit": 50}
    assert plan.output == {"status": "plan", "offset": 2, "limit": 7}
    assert preview.output == {"status": "preview", "decision_count": 0}
    assert draft.output == {"status": "draft", "limit": 20, "predicate_policies": None}
    assert calls == [
        ("queue", project.id, 0, 50),
        ("plan", project.id, 2, 7),
        ("preview", project.id, [], None),
        ("draft", project.id, None, True),
    ]

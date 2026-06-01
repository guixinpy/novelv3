from app.models import ChapterContent, Outline, Project, Setup, Storyline
from app.services.writing_agent.agent_core_tool_descriptors import AGENT_CORE_TOOL_DESCRIPTORS
from app.services.writing_agent.agent_generation_tool_descriptors import AGENT_GENERATION_TOOL_DESCRIPTORS
from app.services.writing_agent.agent_memory_trace_tool_descriptors import AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS
from app.services.writing_agent.agent_task_queue_tool_descriptors import AGENT_TASK_QUEUE_TOOL_DESCRIPTORS
from app.services.writing_agent.agent_tool_surface_policy import build_agent_profile_policy_audit
from app.services.writing_agent.hermes_action_tool_descriptors import HERMES_ACTION_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.knowledge_base_tool_descriptors import KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.longform_tool_descriptors import LONGFORM_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.outline_generation_tool_descriptors import OUTLINE_GENERATION_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.review_revision_tool_descriptors import REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.setup_generation_tool_descriptors import SETUP_GENERATION_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.storyline_generation_tool_descriptors import STORYLINE_GENERATION_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.tool_registry import (
    allowed_tool_names,
    build_agent_tool_plan,
    get_agent_tool_descriptor,
    list_agent_tool_descriptors,
    non_blocking_report_tool_names,
    target_type_for_tool,
)
from app.services.writing_agent.world_model_tool_descriptors import WORLD_MODEL_AGENT_TOOL_DESCRIPTORS


def test_agent_core_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in AGENT_CORE_TOOL_DESCRIPTORS]

    assert names == [
        "describe_agent_tools",
        "plan_writing_agent_run",
        "plan_dialog_intent_agent_run",
        "preview_agent_plan_approval_contract",
        "verify_agent_plan_approval_contract",
        "inspect_agent_health_projection",
        "inspect_agent_control_plane_readiness",
        "plan_recovery_tools",
        "plan_recommended_followups",
        "inspect_agent_worker_dispatch",
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
        "preflight_writing",
    ]
    assert {descriptor.category for descriptor in AGENT_CORE_TOOL_DESCRIPTORS} == {"preflight"}
    assert {descriptor.module for descriptor in AGENT_CORE_TOOL_DESCRIPTORS} == {"writing_agent"}
    assert all(descriptor.internal for descriptor in AGENT_CORE_TOOL_DESCRIPTORS)
    assert target_type_for_tool("preview_agent_plan_approval_contract") == "agent_plan_approval_contract"
    assert target_type_for_tool("inspect_agent_write_gate_coverage") == "agent_write_gate_coverage"
    assert target_type_for_tool("inspect_agent_worker_dispatch") == "agent_worker_dispatch"
    assert "plan_writing_agent_run" in non_blocking_report_tool_names()
    assert "preflight_writing" not in non_blocking_report_tool_names()


def test_agent_memory_trace_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS]

    assert names == [
        "inspect_agent_trace_audit",
        "inspect_agent_memory_route",
        "search_agent_retrieval_context",
        "summarize_longform_context",
        "inspect_agent_context_compression_projection",
        "inspect_agent_memory_activation_plan",
        "repair_longform_maintenance",
        "prepare_repair_longform_maintenance",
        "execute_repair_longform_maintenance_with_approval",
    ]
    assert {descriptor.category for descriptor in AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS} == {
        "trace",
        "longform_memory",
        "retrieval",
        "maintenance",
    }
    assert all(descriptor.internal for descriptor in AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS)
    assert target_type_for_tool("inspect_agent_trace_audit") == "agent_trace_audit"
    assert target_type_for_tool("inspect_agent_memory_route") == "agent_memory_route"
    assert target_type_for_tool("search_agent_retrieval_context") == "agent_retrieval_context"
    assert target_type_for_tool("summarize_longform_context") == "longform_context_summary"
    assert target_type_for_tool("inspect_agent_context_compression_projection") == "agent_context_compression_projection"
    assert target_type_for_tool("inspect_agent_memory_activation_plan") == "agent_memory_activation_plan"
    assert target_type_for_tool("repair_longform_maintenance") == "longform_maintenance"
    assert target_type_for_tool("prepare_repair_longform_maintenance") == "longform_maintenance_approval"
    assert target_type_for_tool("execute_repair_longform_maintenance_with_approval") == "longform_maintenance"
    assert "inspect_agent_trace_audit" in non_blocking_report_tool_names()
    assert "search_agent_retrieval_context" in non_blocking_report_tool_names()
    assert "inspect_agent_context_compression_projection" in non_blocking_report_tool_names()
    assert "inspect_agent_memory_activation_plan" in non_blocking_report_tool_names()
    assert "prepare_repair_longform_maintenance" in non_blocking_report_tool_names()
    assert "repair_longform_maintenance" not in non_blocking_report_tool_names()


def test_agent_generation_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in AGENT_GENERATION_TOOL_DESCRIPTORS]

    assert names == [
        "expand_outline_window",
        "prepare_expand_outline_window_execution",
        "execute_expand_outline_window_with_approval",
        "generate_chapter",
        "prepare_generate_chapter_execution",
        "execute_generate_chapter_with_approval",
        "backfill_outline_gaps",
        "prepare_backfill_outline_gaps_execution",
        "execute_backfill_outline_gaps_with_approval",
    ]
    assert {descriptor.category for descriptor in AGENT_GENERATION_TOOL_DESCRIPTORS} == {"generation", "maintenance"}
    assert target_type_for_tool("expand_outline_window") == "outline"
    assert target_type_for_tool("prepare_expand_outline_window_execution") == "outline_window_expansion_approval"
    assert target_type_for_tool("execute_expand_outline_window_with_approval") == "outline"
    assert target_type_for_tool("generate_chapter") == "chapter"
    assert target_type_for_tool("prepare_generate_chapter_execution") == "chapter_generation_approval"
    assert target_type_for_tool("execute_generate_chapter_with_approval") == "chapter"
    assert target_type_for_tool("backfill_outline_gaps") == "outline"
    assert target_type_for_tool("prepare_backfill_outline_gaps_execution") == "outline_backfill_approval"
    assert target_type_for_tool("execute_backfill_outline_gaps_with_approval") == "outline"
    assert "prepare_generate_chapter_execution" in non_blocking_report_tool_names()
    assert "prepare_expand_outline_window_execution" in non_blocking_report_tool_names()
    assert "prepare_backfill_outline_gaps_execution" in non_blocking_report_tool_names()
    assert "execute_generate_chapter_with_approval" not in non_blocking_report_tool_names()


def test_setup_generation_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in SETUP_GENERATION_AGENT_TOOL_DESCRIPTORS]

    assert names == [
        "preview_generate_setup_execution",
        "prepare_generate_setup_execution",
        "execute_generate_setup_with_approval",
    ]
    assert {descriptor.category for descriptor in SETUP_GENERATION_AGENT_TOOL_DESCRIPTORS} == {"generation"}
    assert all(descriptor.internal for descriptor in SETUP_GENERATION_AGENT_TOOL_DESCRIPTORS)
    assert target_type_for_tool("preview_generate_setup_execution") == "setup_generation_preview"
    assert target_type_for_tool("prepare_generate_setup_execution") == "setup_generation_approval"
    assert target_type_for_tool("execute_generate_setup_with_approval") == "setup"
    assert "prepare_generate_setup_execution" in non_blocking_report_tool_names()
    assert "execute_generate_setup_with_approval" not in non_blocking_report_tool_names()


def test_storyline_generation_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in STORYLINE_GENERATION_AGENT_TOOL_DESCRIPTORS]

    assert names == [
        "preview_generate_storyline_execution",
        "prepare_generate_storyline_execution",
        "execute_generate_storyline_with_approval",
    ]
    assert {descriptor.category for descriptor in STORYLINE_GENERATION_AGENT_TOOL_DESCRIPTORS} == {"generation"}
    assert all(descriptor.internal for descriptor in STORYLINE_GENERATION_AGENT_TOOL_DESCRIPTORS)
    assert target_type_for_tool("preview_generate_storyline_execution") == "storyline_generation_preview"
    assert target_type_for_tool("prepare_generate_storyline_execution") == "storyline_generation_approval"
    assert target_type_for_tool("execute_generate_storyline_with_approval") == "storyline"
    assert "prepare_generate_storyline_execution" in non_blocking_report_tool_names()
    assert "execute_generate_storyline_with_approval" not in non_blocking_report_tool_names()


def test_outline_generation_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in OUTLINE_GENERATION_AGENT_TOOL_DESCRIPTORS]

    assert names == [
        "preview_generate_outline_execution",
        "prepare_generate_outline_execution",
        "execute_generate_outline_with_approval",
    ]
    assert {descriptor.category for descriptor in OUTLINE_GENERATION_AGENT_TOOL_DESCRIPTORS} == {"generation"}
    assert all(descriptor.internal for descriptor in OUTLINE_GENERATION_AGENT_TOOL_DESCRIPTORS)
    assert target_type_for_tool("preview_generate_outline_execution") == "outline_generation_preview"
    assert target_type_for_tool("prepare_generate_outline_execution") == "outline_generation_approval"
    assert target_type_for_tool("execute_generate_outline_with_approval") == "outline"
    assert "prepare_generate_outline_execution" in non_blocking_report_tool_names()
    assert "execute_generate_outline_with_approval" not in non_blocking_report_tool_names()


def test_agent_task_queue_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in AGENT_TASK_QUEUE_TOOL_DESCRIPTORS]

    assert names == [
        "inspect_agent_event_projection",
        "inspect_agent_job_projection",
        "plan_chapter_conflict_recovery",
    ]
    assert {descriptor.category for descriptor in AGENT_TASK_QUEUE_TOOL_DESCRIPTORS} == {"task_queue"}
    assert {descriptor.module for descriptor in AGENT_TASK_QUEUE_TOOL_DESCRIPTORS} == {"writing_agent"}
    assert all(descriptor.internal for descriptor in AGENT_TASK_QUEUE_TOOL_DESCRIPTORS)
    assert all(descriptor.non_blocking_report for descriptor in AGENT_TASK_QUEUE_TOOL_DESCRIPTORS)
    assert target_type_for_tool("inspect_agent_event_projection") == "agent_event_projection"
    assert target_type_for_tool("inspect_agent_job_projection") == "agent_job_projection"
    assert target_type_for_tool("plan_chapter_conflict_recovery") == "agent_tool_plan"


def test_hermes_action_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in HERMES_ACTION_AGENT_TOOL_DESCRIPTORS]

    assert names == [
        "generate_setup",
        "generate_storyline",
        "generate_outline",
    ]
    assert {descriptor.module for descriptor in HERMES_ACTION_AGENT_TOOL_DESCRIPTORS} == {"hermes"}
    assert {descriptor.category for descriptor in HERMES_ACTION_AGENT_TOOL_DESCRIPTORS} == {"generation"}
    assert all(not descriptor.internal for descriptor in HERMES_ACTION_AGENT_TOOL_DESCRIPTORS)
    assert target_type_for_tool("generate_setup") == "setup"
    assert target_type_for_tool("generate_storyline") == "storyline"
    assert target_type_for_tool("generate_outline") == "outline"
    assert "generate_setup" in allowed_tool_names()


def test_review_revision_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS]

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
    assert {descriptor.category for descriptor in REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS} == {"review", "revision"}
    assert all(descriptor.internal for descriptor in REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS)
    assert target_type_for_tool("plan_chapter_revision") == "revision_plan"
    assert target_type_for_tool("prepare_create_revision_draft_execution") == "revision_draft_approval"
    assert "prepare_create_revision_draft_execution" in non_blocking_report_tool_names()
    assert target_type_for_tool("apply_planner_revision_patch") == "revision"
    assert target_type_for_tool("prepare_apply_planner_revision_patch_execution") == "revision_patch_approval"
    assert target_type_for_tool("execute_apply_planner_revision_patch_with_approval") == "revision"
    assert "prepare_apply_planner_revision_patch_execution" in non_blocking_report_tool_names()
    assert target_type_for_tool("prepare_expand_chapter_to_target_execution") == "revision_adjustment_approval"
    assert target_type_for_tool("execute_expand_chapter_to_target_with_approval") == "revision"
    assert target_type_for_tool("prepare_compress_chapter_to_target_execution") == "revision_adjustment_approval"
    assert target_type_for_tool("execute_compress_chapter_to_target_with_approval") == "revision"
    assert "prepare_expand_chapter_to_target_execution" in non_blocking_report_tool_names()
    assert "prepare_compress_chapter_to_target_execution" in non_blocking_report_tool_names()
    assert "review_chapter_quality" in non_blocking_report_tool_names()


def test_world_model_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in WORLD_MODEL_AGENT_TOOL_DESCRIPTORS]

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
    assert {descriptor.category for descriptor in WORLD_MODEL_AGENT_TOOL_DESCRIPTORS} == {
        "athena_world_model",
        "maintenance",
    }
    assert all(descriptor.internal for descriptor in WORLD_MODEL_AGENT_TOOL_DESCRIPTORS)
    assert target_type_for_tool("inspect_agent_world_model_route") == "agent_world_model_route"
    assert target_type_for_tool("apply_world_model_proposal_resolution") == "world_model"
    assert target_type_for_tool("prepare_apply_world_model_proposal_resolution") == (
        "world_model_proposal_resolution_approval"
    )
    assert target_type_for_tool("execute_apply_world_model_proposal_resolution_with_approval") == (
        "world_model_proposal_resolution"
    )
    assert target_type_for_tool("execute_import_setup_world_model_with_approval") == "world_model"
    assert target_type_for_tool("execute_analyze_chapter_world_model_with_approval") == "world_model"
    assert target_type_for_tool("seed_continuity_anchor_proposals") == "world_model_continuity_anchor_seed"
    assert (
        target_type_for_tool("prepare_seed_continuity_anchor_proposals_execution")
        == "world_model_continuity_anchor_seed_approval"
    )
    assert (
        target_type_for_tool("execute_seed_continuity_anchor_proposals_with_approval")
        == "world_model_continuity_anchor_seed"
    )
    assert "prepare_seed_continuity_anchor_proposals_execution" in non_blocking_report_tool_names()
    assert "prepare_apply_world_model_proposal_resolution" in non_blocking_report_tool_names()


def test_knowledge_base_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS]

    assert names == [
        "inspect_agent_knowledge_base_route",
        "plan_post_chapter_memory_capture",
        "record_agent_knowledge_base_candidate",
        "prepare_record_agent_knowledge_base_candidate",
        "execute_record_agent_knowledge_base_candidate_with_approval",
    ]
    assert {descriptor.category for descriptor in KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS} == {"knowledge_base"}
    assert {descriptor.module for descriptor in KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS} == {"writing_agent"}
    assert all(descriptor.internal for descriptor in KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS)
    assert target_type_for_tool("inspect_agent_knowledge_base_route") == "agent_knowledge_base_route"


def test_longform_tool_descriptors_live_in_dedicated_module():
    names = [descriptor.name for descriptor in LONGFORM_AGENT_TOOL_DESCRIPTORS]

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
    assert {descriptor.category for descriptor in LONGFORM_AGENT_TOOL_DESCRIPTORS} == {"task_queue"}
    assert {descriptor.module for descriptor in LONGFORM_AGENT_TOOL_DESCRIPTORS} == {"writing_agent"}
    assert all(descriptor.internal for descriptor in LONGFORM_AGENT_TOOL_DESCRIPTORS)
    assert target_type_for_tool("enqueue_longform_chapter_batch") == "background_task"
    assert target_type_for_tool("prepare_enqueue_longform_chapter_batch") == "background_task_enqueue_approval"
    assert target_type_for_tool("execute_enqueue_longform_chapter_batch_with_approval") == "background_task_enqueue"
    assert target_type_for_tool("prepare_longform_chapter_batch_preflight") == "background_task_checkpoint_approval"
    assert target_type_for_tool("execute_longform_chapter_batch_preflight_with_approval") == "background_task_checkpoint"
    assert target_type_for_tool("execute_longform_chapter_batch") == "background_task"
    assert target_type_for_tool("prepare_longform_chapter_batch_after_review_route") == (
        "background_task_post_review_route_approval"
    )
    assert target_type_for_tool("execute_longform_chapter_batch_after_review_route_with_approval") == (
        "background_task_post_review_route"
    )


def test_agent_tool_registry_has_unique_names_and_contracts():
    descriptors = list_agent_tool_descriptors()
    names = [descriptor.name for descriptor in descriptors]

    assert len(names) == len(set(names))
    assert {
        "generate_chapter",
        "prepare_generate_chapter_execution",
        "execute_generate_chapter_with_approval",
        "preflight_writing",
        "describe_agent_tools",
        "plan_writing_agent_run",
        "preview_agent_plan_approval_contract",
        "verify_agent_plan_approval_contract",
        "plan_recovery_tools",
        "plan_longform_chapter_batch",
        "enqueue_longform_chapter_batch",
        "prepare_enqueue_longform_chapter_batch",
        "execute_enqueue_longform_chapter_batch_with_approval",
        "inspect_longform_chapter_batch",
        "prepare_longform_chapter_batch_preflight",
        "execute_longform_chapter_batch_preflight_with_approval",
        "inspect_agent_job_projection",
        "inspect_agent_reference_alignment",
        "inspect_agent_tool_contracts",
        "inspect_agent_write_gate_coverage",
        "inspect_agent_mutation_fingerprints",
        "inspect_agent_route_preference_projection",
        "inspect_agent_knowledge_base_route",
        "plan_post_chapter_memory_capture",
        "record_agent_knowledge_base_candidate",
        "execute_longform_chapter_batch_preflight",
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
        "search_agent_retrieval_context",
        "inspect_agent_world_model_route",
        "summarize_longform_context",
        "repair_longform_maintenance",
    }.issubset(set(names))
    assert allowed_tool_names() == set(names)
    assert target_type_for_tool("describe_agent_tools") == "agent_tool_plan"
    assert target_type_for_tool("prepare_generate_chapter_execution") == "chapter_generation_approval"
    assert target_type_for_tool("execute_generate_chapter_with_approval") == "chapter"
    assert target_type_for_tool("plan_writing_agent_run") == "agent_tool_plan"
    assert target_type_for_tool("preview_agent_plan_approval_contract") == "agent_plan_approval_contract"
    assert target_type_for_tool("verify_agent_plan_approval_contract") == "agent_plan_approval_verification"
    assert target_type_for_tool("plan_recovery_tools") == "agent_tool_plan"
    assert target_type_for_tool("plan_longform_chapter_batch") == "longform_batch_plan"
    assert target_type_for_tool("enqueue_longform_chapter_batch") == "background_task"
    assert target_type_for_tool("prepare_enqueue_longform_chapter_batch") == "background_task_enqueue_approval"
    assert target_type_for_tool("execute_enqueue_longform_chapter_batch_with_approval") == "background_task_enqueue"
    assert target_type_for_tool("inspect_longform_chapter_batch") == "background_task"
    assert target_type_for_tool("prepare_longform_chapter_batch_preflight") == "background_task_checkpoint_approval"
    assert target_type_for_tool("execute_longform_chapter_batch_preflight_with_approval") == "background_task_checkpoint"
    assert target_type_for_tool("inspect_agent_job_projection") == "agent_job_projection"
    assert target_type_for_tool("inspect_agent_reference_alignment") == "agent_reference_alignment"
    assert target_type_for_tool("inspect_agent_tool_contracts") == "agent_tool_contracts"
    assert target_type_for_tool("inspect_agent_write_gate_coverage") == "agent_write_gate_coverage"
    assert target_type_for_tool("inspect_agent_mutation_fingerprints") == "agent_mutation_fingerprint"
    assert target_type_for_tool("inspect_agent_route_preference_projection") == "agent_route_preference_projection"
    assert target_type_for_tool("inspect_agent_knowledge_base_route") == "agent_knowledge_base_route"
    assert target_type_for_tool("plan_post_chapter_memory_capture") == "agent_post_chapter_memory_capture_plan"
    assert target_type_for_tool("record_agent_knowledge_base_candidate") == "agent_knowledge_base_candidate"
    assert target_type_for_tool("execute_longform_chapter_batch_preflight") == "background_task"
    assert target_type_for_tool("prepare_longform_chapter_batch_execution") == "background_task"
    assert target_type_for_tool("prepare_longform_chapter_batch_execution_prepare") == (
        "background_task_execution_prepare_approval"
    )
    assert target_type_for_tool("execute_longform_chapter_batch_execution_prepare_with_approval") == (
        "background_task_execution_prepare"
    )
    assert target_type_for_tool("execute_longform_chapter_batch") == "background_task"
    assert target_type_for_tool("review_longform_chapter_batch_execution") == "background_task"
    assert target_type_for_tool("prepare_longform_chapter_batch_execution_review") == (
        "background_task_post_generation_review_approval"
    )
    assert target_type_for_tool("execute_longform_chapter_batch_execution_review_with_approval") == (
        "background_task_post_generation_review"
    )
    assert target_type_for_tool("route_longform_chapter_batch_after_review") == "background_task"
    assert target_type_for_tool("prepare_longform_chapter_batch_after_review_route") == (
        "background_task_post_review_route_approval"
    )
    assert target_type_for_tool("execute_longform_chapter_batch_after_review_route_with_approval") == (
        "background_task_post_review_route"
    )
    assert target_type_for_tool("inspect_agent_trace_audit") == "agent_trace_audit"
    assert target_type_for_tool("inspect_agent_memory_route") == "agent_memory_route"
    assert target_type_for_tool("search_agent_retrieval_context") == "agent_retrieval_context"
    assert target_type_for_tool("inspect_agent_world_model_route") == "agent_world_model_route"
    assert target_type_for_tool("summarize_longform_context") == "longform_context_summary"
    assert target_type_for_tool("repair_longform_maintenance") == "longform_maintenance"
    assert "review_chapter_quality" in non_blocking_report_tool_names()
    assert "prepare_generate_chapter_execution" in non_blocking_report_tool_names()
    assert "plan_recovery_tools" in non_blocking_report_tool_names()
    assert "plan_longform_chapter_batch" in non_blocking_report_tool_names()
    assert "prepare_enqueue_longform_chapter_batch" in non_blocking_report_tool_names()
    assert "inspect_longform_chapter_batch" in non_blocking_report_tool_names()
    assert "inspect_agent_job_projection" in non_blocking_report_tool_names()
    assert "inspect_agent_tool_contracts" in non_blocking_report_tool_names()
    assert "inspect_agent_write_gate_coverage" in non_blocking_report_tool_names()
    assert "inspect_agent_mutation_fingerprints" in non_blocking_report_tool_names()
    assert "inspect_agent_route_preference_projection" in non_blocking_report_tool_names()
    assert "preview_agent_plan_approval_contract" in non_blocking_report_tool_names()
    assert "verify_agent_plan_approval_contract" in non_blocking_report_tool_names()
    assert "inspect_agent_knowledge_base_route" in non_blocking_report_tool_names()
    assert "summarize_longform_context" in non_blocking_report_tool_names()
    assert "prepare_longform_chapter_batch_after_review_route" in non_blocking_report_tool_names()

    for descriptor in descriptors:
        assert descriptor.category
        assert descriptor.module
        assert descriptor.description
        assert descriptor.input_schema["type"] == "object"
        assert descriptor.output_schema["type"] == "object"
        assert get_agent_tool_descriptor(descriptor.name) == descriptor


def test_agent_tool_registry_generate_chapter_has_structured_output_contract():
    descriptor = get_agent_tool_descriptor("generate_chapter")

    assert descriptor is not None
    properties = descriptor.output_schema["properties"]
    assert {
        "status",
        "chapter_index",
        "trace_id",
        "athena_analysis",
        "agent_continuity_feedback",
        "agent_generation_feedback",
        "recommended_next_tools",
    }.issubset(properties)
    assert properties["chapter_index"]["type"] == "integer"
    assert properties["recommended_next_tools"]["type"] == "array"


def test_agent_tool_registry_includes_approved_direct_chapter_generation_tools():
    prepare_descriptor = get_agent_tool_descriptor("prepare_generate_chapter_execution")
    execute_descriptor = get_agent_tool_descriptor("execute_generate_chapter_with_approval")

    assert prepare_descriptor is not None
    assert prepare_descriptor.internal is True
    assert prepare_descriptor.non_blocking_report is True
    assert prepare_descriptor.category == "generation"
    assert prepare_descriptor.target_type == "chapter_generation_approval"
    assert set(prepare_descriptor.input_schema["required"]) == {"chapter_index"}
    assert prepare_descriptor.output_schema["properties"]["mutation_fingerprint"]["type"] == "object"
    assert prepare_descriptor.output_schema["properties"]["tool_call_id"]["type"] == "string"
    assert prepare_descriptor.output_schema["properties"]["resource_binding"]["type"] == "object"
    assert prepare_descriptor.output_schema["properties"]["agent_plan_approval_contract_hash"]["type"] == "string"

    assert execute_descriptor is not None
    assert execute_descriptor.internal is True
    assert execute_descriptor.non_blocking_report is False
    assert execute_descriptor.category == "generation"
    assert execute_descriptor.target_type == "chapter"
    assert set(execute_descriptor.input_schema["required"]) == {
        "chapter_index",
        "confirm_execute",
        "approval_contract_hash",
        "approval_contract",
    }
    assert execute_descriptor.output_schema["properties"]["agent_plan_approval_verification"]["type"] == "object"
    assert execute_descriptor.output_schema["properties"]["execution_resource_binding"]["type"] == "object"


def test_agent_tool_registry_includes_approved_setup_generation_tools():
    preview_descriptor = get_agent_tool_descriptor("preview_generate_setup_execution")
    prepare_descriptor = get_agent_tool_descriptor("prepare_generate_setup_execution")
    execute_descriptor = get_agent_tool_descriptor("execute_generate_setup_with_approval")

    assert preview_descriptor is not None
    assert preview_descriptor.internal is True
    assert preview_descriptor.non_blocking_report is True
    assert preview_descriptor.category == "generation"
    assert preview_descriptor.target_type == "setup_generation_preview"

    assert prepare_descriptor is not None
    assert prepare_descriptor.internal is True
    assert prepare_descriptor.non_blocking_report is True
    assert prepare_descriptor.category == "generation"
    assert prepare_descriptor.target_type == "setup_generation_approval"
    assert prepare_descriptor.output_schema["properties"]["agent_plan_approval_contract_hash"]["type"] == "string"

    assert execute_descriptor is not None
    assert execute_descriptor.internal is True
    assert execute_descriptor.non_blocking_report is False
    assert execute_descriptor.category == "generation"
    assert execute_descriptor.target_type == "setup"
    assert set(execute_descriptor.input_schema["required"]) == {
        "confirm_execute",
        "approval_contract_hash",
        "approval_contract",
    }
    assert execute_descriptor.input_schema["properties"]["confirm_execute"]["type"] == "boolean"
    assert execute_descriptor.output_schema["properties"]["agent_plan_approval_verification"]["type"] == "object"
    assert execute_descriptor.output_schema["properties"]["execution_resource_binding"]["type"] == "object"


def test_agent_tool_registry_includes_approved_storyline_generation_tools():
    preview_descriptor = get_agent_tool_descriptor("preview_generate_storyline_execution")
    prepare_descriptor = get_agent_tool_descriptor("prepare_generate_storyline_execution")
    execute_descriptor = get_agent_tool_descriptor("execute_generate_storyline_with_approval")

    assert preview_descriptor is not None
    assert preview_descriptor.internal is True
    assert preview_descriptor.non_blocking_report is True
    assert preview_descriptor.category == "generation"
    assert preview_descriptor.target_type == "storyline_generation_preview"

    assert prepare_descriptor is not None
    assert prepare_descriptor.internal is True
    assert prepare_descriptor.non_blocking_report is True
    assert prepare_descriptor.category == "generation"
    assert prepare_descriptor.target_type == "storyline_generation_approval"
    assert prepare_descriptor.output_schema["properties"]["agent_plan_approval_contract_hash"]["type"] == "string"

    assert execute_descriptor is not None
    assert execute_descriptor.internal is True
    assert execute_descriptor.non_blocking_report is False
    assert execute_descriptor.category == "generation"
    assert execute_descriptor.target_type == "storyline"
    assert set(execute_descriptor.input_schema["required"]) == {
        "confirm_execute",
        "approval_contract_hash",
        "approval_contract",
    }
    assert execute_descriptor.input_schema["properties"]["confirm_execute"]["type"] == "boolean"
    assert execute_descriptor.output_schema["properties"]["agent_plan_approval_verification"]["type"] == "object"
    assert execute_descriptor.output_schema["properties"]["execution_resource_binding"]["type"] == "object"


def test_agent_tool_registry_includes_approved_outline_generation_tools():
    preview_descriptor = get_agent_tool_descriptor("preview_generate_outline_execution")
    prepare_descriptor = get_agent_tool_descriptor("prepare_generate_outline_execution")
    execute_descriptor = get_agent_tool_descriptor("execute_generate_outline_with_approval")

    assert preview_descriptor is not None
    assert preview_descriptor.internal is True
    assert preview_descriptor.non_blocking_report is True
    assert preview_descriptor.category == "generation"
    assert preview_descriptor.target_type == "outline_generation_preview"

    assert prepare_descriptor is not None
    assert prepare_descriptor.internal is True
    assert prepare_descriptor.non_blocking_report is True
    assert prepare_descriptor.category == "generation"
    assert prepare_descriptor.target_type == "outline_generation_approval"
    assert prepare_descriptor.output_schema["properties"]["agent_plan_approval_contract_hash"]["type"] == "string"

    assert execute_descriptor is not None
    assert execute_descriptor.internal is True
    assert execute_descriptor.non_blocking_report is False
    assert execute_descriptor.category == "generation"
    assert execute_descriptor.target_type == "outline"
    assert set(execute_descriptor.input_schema["required"]) == {
        "confirm_execute",
        "approval_contract_hash",
        "approval_contract",
    }
    assert execute_descriptor.input_schema["properties"]["confirm_execute"]["type"] == "boolean"
    assert execute_descriptor.output_schema["properties"]["agent_plan_approval_verification"]["type"] == "object"
    assert execute_descriptor.output_schema["properties"]["execution_resource_binding"]["type"] == "object"


def test_agent_tool_registry_includes_approved_outline_window_expansion_tools():
    prepare_descriptor = get_agent_tool_descriptor("prepare_expand_outline_window_execution")
    execute_descriptor = get_agent_tool_descriptor("execute_expand_outline_window_with_approval")

    assert prepare_descriptor is not None
    assert prepare_descriptor.internal is True
    assert prepare_descriptor.non_blocking_report is True
    assert prepare_descriptor.category == "generation"
    assert prepare_descriptor.target_type == "outline_window_expansion_approval"
    assert prepare_descriptor.output_schema["properties"]["agent_plan_approval_contract_hash"]["type"] == "string"

    assert execute_descriptor is not None
    assert execute_descriptor.internal is True
    assert execute_descriptor.non_blocking_report is False
    assert execute_descriptor.category == "generation"
    assert execute_descriptor.target_type == "outline"
    assert set(execute_descriptor.input_schema["required"]) == {
        "confirm_execute",
        "approval_contract_hash",
        "approval_contract",
    }
    assert execute_descriptor.input_schema["properties"]["confirm_execute"]["type"] == "boolean"
    assert execute_descriptor.output_schema["properties"]["agent_plan_approval_verification"]["type"] == "object"
    assert execute_descriptor.output_schema["properties"]["execution_resource_binding"]["type"] == "object"


def test_agent_tool_registry_expand_outline_window_has_structured_output_contract():
    descriptor = get_agent_tool_descriptor("expand_outline_window")

    assert descriptor is not None
    input_properties = descriptor.input_schema["properties"]
    output_properties = descriptor.output_schema["properties"]
    assert {"chapter_index", "start_chapter", "end_chapter", "command_args"}.issubset(input_properties)
    assert {
        "status",
        "start_chapter",
        "end_chapter",
        "outline_id",
        "total_chapters",
        "added_chapter_count",
        "merge",
        "trace_id",
        "recommended_next_tools",
    }.issubset(output_properties)
    assert output_properties["merge"]["type"] == "object"
    assert output_properties["trace_id"]["type"] == ["string", "null"]
    assert output_properties["recommended_next_tools"]["type"] == "array"


def test_agent_tool_registry_import_setup_world_model_has_structured_output_contract():
    descriptor = get_agent_tool_descriptor("import_setup_world_model")

    assert descriptor is not None
    properties = descriptor.output_schema["properties"]
    assert {
        "status",
        "profile_version",
        "project_profile_version_id",
        "created",
        "should_generate_next_chapter",
        "recommended_next_tools",
    }.issubset(properties)
    assert properties["created"]["type"] == "object"
    assert properties["recommended_next_tools"]["type"] == "array"


def test_agent_tool_registry_seed_continuity_anchor_proposals_has_structured_output_contract():
    descriptor = get_agent_tool_descriptor("seed_continuity_anchor_proposals")

    assert descriptor is not None
    properties = descriptor.output_schema["properties"]
    assert {
        "status",
        "project_id",
        "profile_version",
        "proposal_bundle_id",
        "created_item_count",
        "created_items",
        "pending_anchor_count",
        "should_generate_next_chapter",
        "recommended_actions",
    }.issubset(properties)
    assert properties["created_items"]["type"] == "array"
    assert properties["recommended_actions"]["type"] == "array"


def test_agent_tool_registry_apply_world_model_resolution_has_structured_output_contract():
    descriptor = get_agent_tool_descriptor("apply_world_model_proposal_resolution")
    prepare_descriptor = get_agent_tool_descriptor("prepare_apply_world_model_proposal_resolution")
    execute_descriptor = get_agent_tool_descriptor("execute_apply_world_model_proposal_resolution_with_approval")

    assert descriptor is not None
    assert descriptor.non_blocking_report is False
    input_properties = descriptor.input_schema["properties"]
    assert input_properties["confirm_apply"]["type"] == "boolean"
    assert input_properties["approval_contract_hash"]["type"] == "string"
    assert input_properties["approval_contract"]["type"] == "object"
    properties = descriptor.output_schema["properties"]
    assert {"status", "required_approval", "side_effects"}.issubset(properties)

    assert prepare_descriptor is not None
    assert prepare_descriptor.non_blocking_report is True
    assert prepare_descriptor.output_schema["properties"]["agent_plan_approval_contract"]["type"] == "object"

    assert execute_descriptor is not None
    assert execute_descriptor.non_blocking_report is True
    execute_properties = execute_descriptor.output_schema["properties"]
    assert {
        "status",
        "profile_version",
        "before_actionable_items",
        "after_actionable_items",
        "applied_count",
        "applied_reviews",
        "invalid_decision_count",
        "invalid_decisions",
        "requires_confirmation",
        "should_generate_next_chapter",
        "recommended_actions",
        "agent_plan_approval_verification",
        "execution_resource_binding",
    }.issubset(execute_properties)
    assert execute_properties["applied_reviews"]["type"] == "array"
    assert execute_properties["requires_confirmation"]["type"] == "boolean"
    assert execute_properties["profile_version"]["type"] == ["integer", "null"]
    assert "execute_apply_world_model_proposal_resolution_with_approval" in non_blocking_report_tool_names()


def test_agent_tool_registry_expand_chapter_has_structured_output_contract():
    descriptor = get_agent_tool_descriptor("expand_chapter_to_target")

    assert descriptor is not None
    input_properties = descriptor.input_schema["properties"]
    output_properties = descriptor.output_schema["properties"]
    assert {"chapter_index", "min_word_count", "extra_instruction"}.issubset(input_properties)
    assert {
        "status",
        "chapter_index",
        "chapter_id",
        "revision_id",
        "revision_index",
        "base_version_id",
        "result_version_id",
        "trace_id",
        "previous_word_count",
        "word_count",
        "target_min_word_count",
        "target_max_word_count",
        "change_summary",
        "warnings",
        "pending_world_model_proposal_count",
        "should_generate_next_chapter",
        "recommended_next_tools",
    }.issubset(output_properties)
    assert output_properties["warnings"]["type"] == "array"
    assert output_properties["recommended_next_tools"]["type"] == "array"
    assert output_properties["target_max_word_count"]["type"] == ["integer", "null"]


def test_agent_tool_registry_compress_chapter_has_structured_output_contract():
    descriptor = get_agent_tool_descriptor("compress_chapter_to_target")

    assert descriptor is not None
    input_properties = descriptor.input_schema["properties"]
    output_properties = descriptor.output_schema["properties"]
    assert {"chapter_index", "target_max_word_count", "extra_instruction", "forbidden_terms"}.issubset(
        input_properties
    )
    assert {
        "status",
        "reason",
        "message",
        "chapter_index",
        "chapter_id",
        "revision_id",
        "revision_index",
        "base_version_id",
        "result_version_id",
        "trace_id",
        "previous_word_count",
        "word_count",
        "target_min_word_count",
        "target_max_word_count",
        "forbidden_terms",
        "remaining_forbidden_terms",
        "postcondition_retry_count",
        "compression_attempt_count",
        "failed_attempts",
        "deterministic_repair_applied",
        "deterministic_trim_applied",
        "change_summary",
        "warnings",
        "pending_world_model_proposal_count",
        "should_generate_next_chapter",
        "recommended_next_tools",
    }.issubset(output_properties)
    assert output_properties["forbidden_terms"]["type"] == "array"
    assert output_properties["remaining_forbidden_terms"]["type"] == "array"
    assert output_properties["failed_attempts"]["type"] == "array"
    assert output_properties["recommended_next_tools"]["type"] == "array"


def test_agent_tool_registry_includes_plan_recovery_tools():
    descriptor = get_agent_tool_descriptor("plan_recovery_tools")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_tool_plan"
    assert "plan_recovery_tools" in allowed_tool_names()
    assert "plan_recovery_tools" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_agent_plan_approval_contract_preview():
    descriptor = get_agent_tool_descriptor("preview_agent_plan_approval_contract")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_plan_approval_contract"
    assert descriptor.input_schema["properties"]["plan"]["type"] == "object"
    assert descriptor.output_schema["properties"]["approval"]["type"] == "object"
    assert "preview_agent_plan_approval_contract" in allowed_tool_names()
    assert "preview_agent_plan_approval_contract" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_agent_plan_approval_contract_verification():
    descriptor = get_agent_tool_descriptor("verify_agent_plan_approval_contract")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_plan_approval_verification"
    assert descriptor.input_schema["properties"]["plan"]["type"] == "object"
    assert descriptor.input_schema["properties"]["approval_contract_hash"]["type"] == "string"
    assert descriptor.output_schema["properties"]["drift"]["type"] == "object"
    assert "verify_agent_plan_approval_contract" in allowed_tool_names()
    assert "verify_agent_plan_approval_contract" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_plan_longform_chapter_batch():
    descriptor = get_agent_tool_descriptor("plan_longform_chapter_batch")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "longform_batch_plan"
    assert descriptor.input_schema["properties"]["batch_size"]["minimum"] == 1
    assert "plan_longform_chapter_batch" in allowed_tool_names()
    assert "plan_longform_chapter_batch" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_enqueue_longform_chapter_batch():
    descriptor = get_agent_tool_descriptor("enqueue_longform_chapter_batch")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is False
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "background_task"
    assert descriptor.input_schema["properties"]["batch_size"]["minimum"] == 1
    assert descriptor.input_schema["properties"]["confirm_enqueue"]["type"] == "boolean"
    assert "enqueue_longform_chapter_batch" in allowed_tool_names()
    assert "enqueue_longform_chapter_batch" not in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_enqueue_longform_chapter_batch_approval_chain():
    prepare_descriptor = get_agent_tool_descriptor("prepare_enqueue_longform_chapter_batch")
    execute_descriptor = get_agent_tool_descriptor("execute_enqueue_longform_chapter_batch_with_approval")

    assert prepare_descriptor is not None
    assert prepare_descriptor.internal is True
    assert prepare_descriptor.non_blocking_report is True
    assert prepare_descriptor.target_type == "background_task_enqueue_approval"
    assert prepare_descriptor.input_schema["properties"]["batch_size"]["minimum"] == 1
    assert execute_descriptor is not None
    assert execute_descriptor.internal is True
    assert execute_descriptor.target_type == "background_task_enqueue"
    assert execute_descriptor.input_schema["properties"]["confirm_execute"]["type"] == "boolean"
    assert "approval_contract_hash" in execute_descriptor.input_schema["required"]
    assert "prepare_enqueue_longform_chapter_batch" in allowed_tool_names()
    assert "execute_enqueue_longform_chapter_batch_with_approval" in allowed_tool_names()
    assert "prepare_enqueue_longform_chapter_batch" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_longform_chapter_batch():
    descriptor = get_agent_tool_descriptor("inspect_longform_chapter_batch")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "background_task"
    assert descriptor.input_schema["properties"]["task_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["limit"]["minimum"] == 1
    assert "inspect_longform_chapter_batch" in allowed_tool_names()
    assert "inspect_longform_chapter_batch" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_job_projection():
    descriptor = get_agent_tool_descriptor("inspect_agent_job_projection")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "agent_job_projection"
    assert descriptor.input_schema["properties"]["task_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["limit"]["minimum"] == 1
    assert "inspect_agent_job_projection" in allowed_tool_names()
    assert "inspect_agent_job_projection" in non_blocking_report_tool_names()


def test_agent_tool_registry_inspect_agent_job_projection_accepts_chapter_index():
    descriptor = get_agent_tool_descriptor("inspect_agent_job_projection")
    properties = descriptor.input_schema["properties"]

    assert properties["chapter_index"] == {"type": "integer", "minimum": 1}


def test_agent_tool_registry_includes_plan_chapter_conflict_recovery():
    descriptor = get_agent_tool_descriptor("plan_chapter_conflict_recovery")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "agent_tool_plan"
    assert descriptor.input_schema["properties"]["chapter_index"] == {"type": "integer", "minimum": 1}
    assert "plan_chapter_conflict_recovery" in allowed_tool_names()
    assert "plan_chapter_conflict_recovery" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_tool_contracts():
    descriptor = get_agent_tool_descriptor("inspect_agent_tool_contracts")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_tool_contracts"
    assert descriptor.input_schema["properties"]["chapter_index"]["minimum"] == 1
    assert descriptor.input_schema["properties"]["include_gap_details"]["type"] == "boolean"
    assert "inspect_agent_tool_contracts" in allowed_tool_names()
    assert "inspect_agent_tool_contracts" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_reference_alignment():
    descriptor = get_agent_tool_descriptor("inspect_agent_reference_alignment")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_reference_alignment"
    assert descriptor.output_schema["properties"]["patterns"]["type"] == "array"
    assert descriptor.output_schema["properties"]["capability_alignment"]["type"] == "array"
    assert descriptor.output_schema["properties"]["recommended_next_tools"]["type"] == "array"
    assert "inspect_agent_reference_alignment" in allowed_tool_names()
    assert "inspect_agent_reference_alignment" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_worker_dispatch_definition_registry():
    descriptor = get_agent_tool_descriptor("inspect_agent_worker_dispatch")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_worker_dispatch"
    assert descriptor.output_schema["properties"]["definition_registry"]["type"] == "object"
    assert descriptor.output_schema["properties"]["route_registry"]["type"] == "object"
    assert "inspect_agent_worker_dispatch" in allowed_tool_names()
    assert "inspect_agent_worker_dispatch" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_command_contracts():
    descriptor = get_agent_tool_descriptor("inspect_agent_command_contracts")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_command_contracts"
    assert descriptor.output_schema["properties"]["commands"]["type"] == "array"
    assert descriptor.output_schema["properties"]["gaps"]["type"] == "array"
    assert "inspect_agent_command_contracts" in allowed_tool_names()
    assert "inspect_agent_command_contracts" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_control_plane_readiness():
    descriptor = get_agent_tool_descriptor("inspect_agent_control_plane_readiness")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_control_plane_readiness"
    assert descriptor.output_schema["properties"]["control_surfaces"]["type"] == "object"
    assert "inspect_agent_control_plane_readiness" in allowed_tool_names()
    assert "inspect_agent_control_plane_readiness" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_legacy_hermes_migration_projection():
    descriptor = get_agent_tool_descriptor("inspect_legacy_hermes_action_migration")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_tool_migration_projection"
    assert "inspect_legacy_hermes_action_migration" in allowed_tool_names()
    assert "inspect_legacy_hermes_action_migration" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_dialog_control_plane_projection():
    descriptor = get_agent_tool_descriptor("inspect_agent_dialog_control_plane_projection")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_dialog_control_plane_projection"
    assert descriptor.input_schema["properties"]["action_type"]["type"] == "string"
    assert descriptor.output_schema["properties"]["actions"]["type"] == "array"
    assert "inspect_agent_dialog_control_plane_projection" in allowed_tool_names()
    assert "inspect_agent_dialog_control_plane_projection" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_write_gate_coverage():
    descriptor = get_agent_tool_descriptor("inspect_agent_write_gate_coverage")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_write_gate_coverage"
    assert descriptor.output_schema["properties"]["write_tools"]["type"] == "array"
    assert descriptor.output_schema["properties"]["recommended_next_targets"]["type"] == "array"
    assert "inspect_agent_write_gate_coverage" in allowed_tool_names()
    assert "inspect_agent_write_gate_coverage" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_mutation_fingerprints():
    descriptor = get_agent_tool_descriptor("inspect_agent_mutation_fingerprints")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_mutation_fingerprint"
    assert descriptor.input_schema["properties"]["tools"]["type"] == "array"
    assert descriptor.output_schema["properties"]["fingerprints"]["type"] == "array"
    assert "inspect_agent_mutation_fingerprints" in allowed_tool_names()
    assert "inspect_agent_mutation_fingerprints" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_route_preference_projection():
    descriptor = get_agent_tool_descriptor("inspect_agent_route_preference_projection")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_route_preference_projection"
    assert descriptor.input_schema["properties"]["approval_chain_opt_in_action_types"]["type"] == "array"
    assert descriptor.output_schema["properties"]["routes"]["type"] == "array"
    assert descriptor.output_schema["properties"]["summary"]["type"] == "object"
    assert "inspect_agent_route_preference_projection" in allowed_tool_names()
    assert "inspect_agent_route_preference_projection" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_route_approval_opt_in_plan():
    descriptor = get_agent_tool_descriptor("plan_agent_route_approval_opt_in")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_route_approval_opt_in_plan"
    assert descriptor.input_schema["properties"]["pending_action_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["agent_route"]["type"] == "object"
    assert descriptor.input_schema["properties"]["action_type"]["type"] == "string"
    assert descriptor.output_schema["properties"]["metadata_patch"]["type"] == "object"
    assert "plan_agent_route_approval_opt_in" in allowed_tool_names()
    assert "plan_agent_route_approval_opt_in" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_route_opt_in_apply_preview():
    descriptor = get_agent_tool_descriptor("preview_pending_action_route_approval_opt_in_apply")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_route_approval_opt_in_apply_preview"
    assert descriptor.input_schema["properties"]["pending_action_id"]["type"] == "string"
    assert descriptor.output_schema["properties"]["params_diff"]["type"] == "object"
    assert "preview_pending_action_route_approval_opt_in_apply" in allowed_tool_names()
    assert "preview_pending_action_route_approval_opt_in_apply" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_route_opt_in_apply_contract_preview():
    descriptor = get_agent_tool_descriptor("preview_pending_action_route_approval_opt_in_apply_contract")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_route_approval_opt_in_apply_contract"
    assert descriptor.input_schema["properties"]["pending_action_id"]["type"] == "string"
    assert descriptor.output_schema["properties"]["approval_contract_hash"]["type"] == ["string", "null"]
    assert descriptor.output_schema["properties"]["approval_contract"]["type"] == ["object", "null"]
    assert descriptor.output_schema["properties"]["route_apply_preview"]["type"] == "object"
    assert "preview_pending_action_route_approval_opt_in_apply_contract" in allowed_tool_names()
    assert "preview_pending_action_route_approval_opt_in_apply_contract" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_apply_route_opt_in_approval():
    descriptor = get_agent_tool_descriptor("apply_pending_action_route_approval_opt_in")
    prepare_descriptor = get_agent_tool_descriptor("prepare_apply_pending_action_route_approval_opt_in")
    execute_descriptor = get_agent_tool_descriptor("execute_apply_pending_action_route_approval_opt_in_with_approval")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is False
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_route_approval_opt_in_apply"
    assert descriptor.input_schema["properties"]["pending_action_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["confirm_apply"]["type"] == "boolean"
    assert descriptor.input_schema["properties"]["approval_contract_hash"]["type"] == "string"
    assert descriptor.input_schema["properties"]["approval_contract"]["type"] == "object"
    assert set(descriptor.input_schema["required"]) == {
        "pending_action_id",
        "confirm_apply",
        "approval_contract_hash",
        "approval_contract",
    }
    assert descriptor.output_schema["properties"]["write_performed"]["type"] == "boolean"
    assert "apply_pending_action_route_approval_opt_in" in allowed_tool_names()
    assert "apply_pending_action_route_approval_opt_in" not in non_blocking_report_tool_names()

    assert prepare_descriptor is not None
    assert prepare_descriptor.internal is True
    assert prepare_descriptor.non_blocking_report is True
    assert prepare_descriptor.category == "preflight"
    assert prepare_descriptor.target_type == "agent_route_approval_opt_in_apply_approval"
    assert prepare_descriptor.output_schema["properties"]["agent_plan_approval_contract_hash"]["type"] == "string"
    assert prepare_descriptor.output_schema["properties"]["route_apply_approval_contract_hash"]["type"] == "string"

    assert execute_descriptor is not None
    assert execute_descriptor.internal is True
    assert execute_descriptor.non_blocking_report is False
    assert execute_descriptor.category == "preflight"
    assert execute_descriptor.target_type == "agent_route_approval_opt_in_apply"
    assert set(execute_descriptor.input_schema["required"]) == {
        "pending_action_id",
        "confirm_execute",
        "route_apply_approval_contract_hash",
        "route_apply_approval_contract",
        "agent_plan_approval_contract_hash",
        "agent_plan_approval_contract",
    }
    assert execute_descriptor.output_schema["properties"]["agent_plan_approval_verification"]["type"] == "object"
    assert execute_descriptor.output_schema["properties"]["execution_resource_binding"]["type"] == "object"


def test_agent_tool_registry_includes_inspect_agent_knowledge_base_route():
    descriptor = get_agent_tool_descriptor("inspect_agent_knowledge_base_route")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "knowledge_base"
    assert descriptor.target_type == "agent_knowledge_base_route"
    assert descriptor.input_schema["properties"]["chapter_index"]["minimum"] == 1
    assert descriptor.input_schema["properties"]["limit"]["minimum"] == 1
    assert "inspect_agent_knowledge_base_route" in allowed_tool_names()
    assert "inspect_agent_knowledge_base_route" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_plan_post_chapter_memory_capture():
    descriptor = get_agent_tool_descriptor("plan_post_chapter_memory_capture")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "knowledge_base"
    assert descriptor.target_type == "agent_post_chapter_memory_capture_plan"
    assert descriptor.input_schema["properties"]["chapter_index"]["minimum"] == 1
    assert descriptor.output_schema["properties"]["candidates"]["type"] == "array"
    assert descriptor.output_schema["properties"]["memory_provenance"]["type"] == "object"
    assert "plan_post_chapter_memory_capture" in allowed_tool_names()
    assert "plan_post_chapter_memory_capture" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_record_agent_knowledge_base_candidate():
    descriptor = get_agent_tool_descriptor("record_agent_knowledge_base_candidate")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is False
    assert descriptor.category == "knowledge_base"
    assert descriptor.target_type == "agent_knowledge_base_candidate"
    assert descriptor.input_schema["properties"]["memory_type"]["type"] == "string"
    assert descriptor.input_schema["properties"]["source_refs"]["type"] == "array"
    assert set(descriptor.input_schema["required"]) == {"memory_type", "title", "summary", "source_refs"}
    assert "record_agent_knowledge_base_candidate" in allowed_tool_names()
    assert "record_agent_knowledge_base_candidate" not in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_knowledge_base_candidate_approval_chain():
    prepare_descriptor = get_agent_tool_descriptor("prepare_record_agent_knowledge_base_candidate")
    execute_descriptor = get_agent_tool_descriptor("execute_record_agent_knowledge_base_candidate_with_approval")

    assert prepare_descriptor is not None
    assert prepare_descriptor.internal is True
    assert prepare_descriptor.non_blocking_report is True
    assert prepare_descriptor.target_type == "agent_knowledge_base_candidate_approval"
    assert prepare_descriptor.input_schema["properties"]["memory_type"]["type"] == "string"
    assert prepare_descriptor.output_schema["properties"]["agent_plan_approval_contract_hash"]["type"] == "string"
    assert "prepare_record_agent_knowledge_base_candidate" in allowed_tool_names()
    assert "prepare_record_agent_knowledge_base_candidate" in non_blocking_report_tool_names()

    assert execute_descriptor is not None
    assert execute_descriptor.internal is True
    assert execute_descriptor.non_blocking_report is False
    assert execute_descriptor.target_type == "agent_knowledge_base_candidate"
    assert execute_descriptor.input_schema["properties"]["confirm_execute"]["type"] == "boolean"
    assert execute_descriptor.input_schema["properties"]["approval_contract_hash"]["type"] == "string"
    assert execute_descriptor.input_schema["properties"]["approval_contract"]["type"] == "object"
    assert set(execute_descriptor.input_schema["required"]) == {
        "memory_type",
        "title",
        "summary",
        "source_refs",
        "confirm_execute",
        "approval_contract_hash",
        "approval_contract",
    }
    assert execute_descriptor.output_schema["properties"]["agent_plan_approval_verification"]["type"] == "object"
    assert "execute_record_agent_knowledge_base_candidate_with_approval" in allowed_tool_names()
    assert "execute_record_agent_knowledge_base_candidate_with_approval" not in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_execute_longform_chapter_batch_preflight():
    descriptor = get_agent_tool_descriptor("execute_longform_chapter_batch_preflight")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is False
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "background_task"
    assert descriptor.input_schema["properties"]["task_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["max_chapters"]["minimum"] == 1
    assert descriptor.input_schema["properties"]["confirm_checkpoint"]["type"] == "boolean"
    assert set(descriptor.input_schema["required"]) == {"task_id"}
    assert "execute_longform_chapter_batch_preflight" in allowed_tool_names()
    assert "execute_longform_chapter_batch_preflight" not in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_longform_chapter_batch_preflight_approval_chain():
    prepare_descriptor = get_agent_tool_descriptor("prepare_longform_chapter_batch_preflight")
    execute_descriptor = get_agent_tool_descriptor("execute_longform_chapter_batch_preflight_with_approval")

    assert prepare_descriptor is not None
    assert prepare_descriptor.internal is True
    assert prepare_descriptor.non_blocking_report is True
    assert prepare_descriptor.target_type == "background_task_checkpoint_approval"
    assert prepare_descriptor.input_schema["properties"]["task_id"]["type"] == "string"
    assert prepare_descriptor.output_schema["properties"]["agent_plan_approval_contract_hash"]["type"] == "string"
    assert execute_descriptor is not None
    assert execute_descriptor.internal is True
    assert execute_descriptor.target_type == "background_task_checkpoint"
    assert execute_descriptor.input_schema["properties"]["confirm_execute"]["type"] == "boolean"
    assert "approval_contract_hash" in execute_descriptor.input_schema["required"]
    assert "approval_contract" in execute_descriptor.input_schema["required"]
    assert execute_descriptor.output_schema["properties"]["agent_plan_approval_verification"]["type"] == "object"
    assert "prepare_longform_chapter_batch_preflight" in allowed_tool_names()
    assert "execute_longform_chapter_batch_preflight_with_approval" in allowed_tool_names()
    assert "prepare_longform_chapter_batch_preflight" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_prepare_longform_chapter_batch_execution():
    descriptor = get_agent_tool_descriptor("prepare_longform_chapter_batch_execution")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is False
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "background_task"
    assert descriptor.input_schema["properties"]["task_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["confirm_prepare"]["type"] == "boolean"
    assert set(descriptor.input_schema["required"]) == {"task_id"}
    assert "prepare_longform_chapter_batch_execution" in allowed_tool_names()
    assert "prepare_longform_chapter_batch_execution" not in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_longform_batch_execution_prepare_approval_chain():
    prepare_descriptor = get_agent_tool_descriptor("prepare_longform_chapter_batch_execution_prepare")
    execute_descriptor = get_agent_tool_descriptor("execute_longform_chapter_batch_execution_prepare_with_approval")

    assert prepare_descriptor is not None
    assert prepare_descriptor.internal is True
    assert prepare_descriptor.non_blocking_report is True
    assert prepare_descriptor.category == "task_queue"
    assert prepare_descriptor.target_type == "background_task_execution_prepare_approval"
    assert set(prepare_descriptor.input_schema["required"]) == {"task_id"}
    assert prepare_descriptor.output_schema["properties"]["agent_plan_approval_contract"]["type"] == "object"

    assert execute_descriptor is not None
    assert execute_descriptor.internal is True
    assert execute_descriptor.non_blocking_report is False
    assert execute_descriptor.category == "task_queue"
    assert execute_descriptor.target_type == "background_task_execution_prepare"
    assert set(execute_descriptor.input_schema["required"]) == {
        "task_id",
        "confirm_execute",
        "approval_contract_hash",
        "approval_contract",
    }
    assert execute_descriptor.output_schema["properties"]["agent_plan_approval_verification"]["type"] == "object"
    assert "prepare_longform_chapter_batch_execution_prepare" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_execute_longform_chapter_batch():
    descriptor = get_agent_tool_descriptor("execute_longform_chapter_batch")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is False
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "background_task"
    assert descriptor.input_schema["properties"]["task_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["confirm_execute"]["type"] == "boolean"
    assert descriptor.input_schema["properties"]["attempt_manifest_hash"]["type"] == "string"
    assert descriptor.input_schema["properties"]["approval_contract_hash"]["type"] == "string"
    assert set(descriptor.input_schema["required"]) == {
        "task_id",
        "confirm_execute",
        "attempt_manifest_hash",
        "approval_contract_hash",
    }
    assert descriptor.output_schema["properties"]["agent_plan_approval_verification"]["type"] == "object"
    assert descriptor.output_schema["properties"]["execution_resource_binding"]["type"] == "object"
    assert "execute_longform_chapter_batch" in allowed_tool_names()
    assert "execute_longform_chapter_batch" not in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_review_longform_chapter_batch_execution():
    descriptor = get_agent_tool_descriptor("review_longform_chapter_batch_execution")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is False
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "background_task"
    assert descriptor.input_schema["properties"]["task_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["lookback"]["minimum"] == 1
    assert descriptor.input_schema["properties"]["confirm_review"]["type"] == "boolean"
    assert set(descriptor.input_schema["required"]) == {"task_id"}
    assert "review_longform_chapter_batch_execution" in allowed_tool_names()
    assert "review_longform_chapter_batch_execution" not in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_longform_batch_execution_review_approval_chain():
    prepare_descriptor = get_agent_tool_descriptor("prepare_longform_chapter_batch_execution_review")
    execute_descriptor = get_agent_tool_descriptor("execute_longform_chapter_batch_execution_review_with_approval")

    assert prepare_descriptor is not None
    assert prepare_descriptor.internal is True
    assert prepare_descriptor.non_blocking_report is True
    assert prepare_descriptor.category == "task_queue"
    assert prepare_descriptor.target_type == "background_task_post_generation_review_approval"
    assert set(prepare_descriptor.input_schema["required"]) == {"task_id"}
    assert prepare_descriptor.output_schema["properties"]["agent_plan_approval_contract"]["type"] == "object"

    assert execute_descriptor is not None
    assert execute_descriptor.internal is True
    assert execute_descriptor.non_blocking_report is False
    assert execute_descriptor.category == "task_queue"
    assert execute_descriptor.target_type == "background_task_post_generation_review"
    assert set(execute_descriptor.input_schema["required"]) == {
        "task_id",
        "confirm_execute",
        "approval_contract_hash",
        "approval_contract",
    }
    assert execute_descriptor.output_schema["properties"]["agent_plan_approval_verification"]["type"] == "object"
    assert "prepare_longform_chapter_batch_execution_review" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_route_longform_chapter_batch_after_review():
    descriptor = get_agent_tool_descriptor("route_longform_chapter_batch_after_review")
    prepare_descriptor = get_agent_tool_descriptor("prepare_longform_chapter_batch_after_review_route")
    execute_descriptor = get_agent_tool_descriptor("execute_longform_chapter_batch_after_review_route_with_approval")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is False
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "background_task"
    assert descriptor.input_schema["properties"]["task_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["expected_post_generation_review_hash"]["type"] == "string"
    assert descriptor.input_schema["properties"]["next_batch_size"]["minimum"] == 1
    assert set(descriptor.input_schema["required"]) == {"task_id"}
    assert "route_longform_chapter_batch_after_review" in allowed_tool_names()
    assert "route_longform_chapter_batch_after_review" not in non_blocking_report_tool_names()

    assert prepare_descriptor is not None
    assert prepare_descriptor.internal is True
    assert prepare_descriptor.non_blocking_report is True
    assert prepare_descriptor.category == "task_queue"
    assert prepare_descriptor.target_type == "background_task_post_review_route_approval"
    assert set(prepare_descriptor.input_schema["required"]) == {"task_id"}
    assert prepare_descriptor.output_schema["properties"]["agent_plan_approval_contract"]["type"] == "object"

    assert execute_descriptor is not None
    assert execute_descriptor.internal is True
    assert execute_descriptor.non_blocking_report is False
    assert execute_descriptor.category == "task_queue"
    assert execute_descriptor.target_type == "background_task_post_review_route"
    assert set(execute_descriptor.input_schema["required"]) == {
        "task_id",
        "confirm_execute",
        "approval_contract_hash",
        "approval_contract",
    }
    assert execute_descriptor.output_schema["properties"]["agent_plan_approval_verification"]["type"] == "object"
    assert "prepare_longform_chapter_batch_after_review_route" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_memory_route():
    descriptor = get_agent_tool_descriptor("inspect_agent_memory_route")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "longform_memory"
    assert descriptor.target_type == "agent_memory_route"
    assert descriptor.input_schema["properties"]["chapter_index"]["minimum"] == 1
    assert descriptor.input_schema["properties"]["include_context_summary"]["type"] == "boolean"
    assert descriptor.output_schema["properties"]["recommended_next_tools"]["type"] == "array"
    assert "inspect_agent_memory_route" in allowed_tool_names()
    assert "inspect_agent_memory_route" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_trace_audit():
    descriptor = get_agent_tool_descriptor("inspect_agent_trace_audit")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "trace"
    assert descriptor.target_type == "agent_trace_audit"
    assert descriptor.input_schema["properties"]["run_id"]["type"] == "string"
    assert descriptor.input_schema["properties"]["chapter_index"]["minimum"] == 1
    assert descriptor.output_schema["properties"]["profile_policy_audit"]["type"] == ["object", "null"]
    assert "inspect_agent_trace_audit" in allowed_tool_names()
    assert "inspect_agent_trace_audit" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_search_agent_retrieval_context():
    descriptor = get_agent_tool_descriptor("search_agent_retrieval_context")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "retrieval"
    assert descriptor.target_type == "agent_retrieval_context"
    assert descriptor.input_schema["properties"]["query"]["type"] == "string"
    assert descriptor.input_schema["properties"]["limit"]["minimum"] == 1
    assert descriptor.output_schema["properties"]["items"]["type"] == "array"
    assert descriptor.output_schema["properties"]["memory_provenance"]["type"] == "object"
    assert "search_agent_retrieval_context" in allowed_tool_names()
    assert "search_agent_retrieval_context" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_health_projection():
    descriptor = get_agent_tool_descriptor("inspect_agent_health_projection")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_health_projection"
    assert descriptor.input_schema["properties"]["run_id"]["type"] == "string"
    assert descriptor.output_schema["properties"]["profile_policy"]["type"] == ["object", "null"]
    assert descriptor.output_schema["properties"]["agent_definition_registry"]["type"] == "object"
    assert descriptor.output_schema["properties"]["agent_worker_route_registry"]["type"] == "object"
    assert descriptor.output_schema["properties"]["dogfood_evidence"]["type"] == "object"
    assert descriptor.output_schema["properties"]["post_chapter_memory_capture"]["type"] == ["object", "null"]
    assert descriptor.output_schema["properties"]["recommended_next_tools"]["type"] == "array"
    assert "inspect_agent_health_projection" in allowed_tool_names()
    assert "inspect_agent_health_projection" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_dogfood_evidence():
    descriptor = get_agent_tool_descriptor("inspect_agent_dogfood_evidence")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "preflight"
    assert descriptor.target_type == "agent_dogfood_evidence"
    assert descriptor.output_schema["properties"]["capability_coverage"]["type"] == "array"
    assert descriptor.output_schema["properties"]["evidence"]["type"] == "array"
    assert descriptor.output_schema["properties"]["diagnostics"]["type"] == "array"
    assert "inspect_agent_dogfood_evidence" in allowed_tool_names()
    assert "inspect_agent_dogfood_evidence" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_inspect_agent_world_model_route():
    descriptor = get_agent_tool_descriptor("inspect_agent_world_model_route")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "athena_world_model"
    assert descriptor.target_type == "agent_world_model_route"
    assert descriptor.input_schema["properties"]["chapter_index"]["minimum"] == 1
    assert descriptor.input_schema["properties"]["subject_ref"]["type"] == "string"
    assert "inspect_agent_world_model_route" in allowed_tool_names()
    assert "inspect_agent_world_model_route" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_summarize_longform_context():
    descriptor = get_agent_tool_descriptor("summarize_longform_context")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "longform_memory"
    assert descriptor.target_type == "longform_context_summary"
    assert descriptor.input_schema["properties"]["chapter_index"]["minimum"] == 1
    assert "summarize_longform_context" in allowed_tool_names()
    assert "summarize_longform_context" in non_blocking_report_tool_names()


def test_agent_tool_registry_includes_repair_longform_maintenance():
    descriptor = get_agent_tool_descriptor("repair_longform_maintenance")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is False
    assert descriptor.category == "maintenance"
    assert descriptor.target_type == "longform_maintenance"
    assert descriptor.input_schema["properties"]["repair_limit"]["minimum"] == 1
    assert "repair_longform_maintenance" in allowed_tool_names()


def test_agent_tool_registry_includes_repair_longform_maintenance_approval_chain():
    prepare_descriptor = get_agent_tool_descriptor("prepare_repair_longform_maintenance")
    execute_descriptor = get_agent_tool_descriptor("execute_repair_longform_maintenance_with_approval")

    assert prepare_descriptor is not None
    assert prepare_descriptor.internal is True
    assert prepare_descriptor.non_blocking_report is True
    assert prepare_descriptor.category == "maintenance"
    assert prepare_descriptor.target_type == "longform_maintenance_approval"
    assert prepare_descriptor.output_schema["properties"]["agent_plan_approval_contract_hash"]["type"] == "string"
    assert "prepare_repair_longform_maintenance" in allowed_tool_names()
    assert "prepare_repair_longform_maintenance" in non_blocking_report_tool_names()

    assert execute_descriptor is not None
    assert execute_descriptor.internal is True
    assert execute_descriptor.non_blocking_report is False
    assert execute_descriptor.category == "maintenance"
    assert execute_descriptor.target_type == "longform_maintenance"
    assert execute_descriptor.input_schema["properties"]["confirm_execute"]["type"] == "boolean"
    assert execute_descriptor.input_schema["properties"]["approval_contract_hash"]["type"] == "string"
    assert execute_descriptor.input_schema["properties"]["approval_contract"]["type"] == "object"
    assert set(execute_descriptor.input_schema["required"]) == {
        "confirm_execute",
        "approval_contract_hash",
        "approval_contract",
    }
    assert execute_descriptor.output_schema["properties"]["agent_plan_approval_verification"]["type"] == "object"
    assert "execute_repair_longform_maintenance_with_approval" in allowed_tool_names()
    assert "execute_repair_longform_maintenance_with_approval" not in non_blocking_report_tool_names()


def test_agent_tool_plan_hides_chapter_generation_until_dependencies_are_ready(db_session):
    project = Project(name="Tool Plan Missing Dependencies")
    db_session.add(project)
    db_session.commit()

    plan = build_agent_tool_plan(db_session, project.id, chapter_index=2)

    assert plan["status"] == "completed"
    assert _tool_names(plan["visible_tools"]) >= {"generate_setup", "preflight_writing"}
    assert "generate_chapter" in _tool_names(plan["hidden_tools"])
    chapter_diagnostics = _diagnostic_codes(plan, "generate_chapter")
    assert {"missing_setup", "missing_outline_chapter", "missing_previous_chapter"}.issubset(chapter_diagnostics)


def test_agent_tool_plan_shows_chapter_generation_when_required_inputs_are_ready(db_session):
    project = _seed_ready_project(db_session)

    plan = build_agent_tool_plan(db_session, project.id, chapter_index=2)

    assert "generate_chapter" in _tool_names(plan["visible_tools"])
    assert "review_chapter_quality" in _tool_names(plan["hidden_tools"])
    assert "missing_generated_chapter" in _diagnostic_codes(plan, "review_chapter_quality")
    chapter_diagnostics = [item for item in plan["diagnostics"] if item["tool_name"] == "generate_chapter"]
    assert any(item["code"] == "missing_world_model_profile" and item["severity"] == "warning" for item in chapter_diagnostics)


def test_agent_tool_plan_exposes_agent_tool_surface_for_visible_tools(db_session):
    project = _seed_ready_project(db_session)

    plan = build_agent_tool_plan(db_session, project.id, chapter_index=2)
    visible = {tool["name"]: tool for tool in plan["visible_tools"]}

    describe_surface = visible["describe_agent_tools"]["agent_tool_surface"]
    assert describe_surface == {
        "visibility": "internal_only",
        "tool_scope": "agent_only",
        "mutability": "read",
        "permission_level": "read",
        "requires_confirmation": False,
        "parallel_safe": True,
    }
    preflight_surface = visible["preflight_writing"]["agent_tool_surface"]
    assert preflight_surface["mutability"] == "read"
    assert preflight_surface["permission_level"] == "read"

    generate_surface = visible["generate_chapter"]["agent_tool_surface"]
    assert generate_surface["visibility"] == "agent_visible"
    assert generate_surface["tool_scope"] == "agent_and_legacy_action"
    assert generate_surface["mutability"] == "write"
    assert generate_surface["permission_level"] == "write"
    assert generate_surface["requires_confirmation"] is False
    assert generate_surface["parallel_safe"] is False


def test_agent_tool_plan_exposes_guarded_write_surface_for_hidden_tools(db_session):
    project = _seed_ready_project(db_session)

    plan = build_agent_tool_plan(db_session, project.id, chapter_index=2)
    tools = {tool["name"]: tool for tool in [*plan["visible_tools"], *plan["hidden_tools"]]}

    execute_surface = tools["apply_world_model_proposal_resolution"]["agent_tool_surface"]
    assert execute_surface["mutability"] == "guarded_write"
    assert execute_surface["permission_level"] == "confirm_required"
    assert execute_surface["requires_confirmation"] is True
    assert execute_surface["parallel_safe"] is False
    assert tools["verify_agent_plan_approval_contract"]["agent_tool_surface"]["mutability"] == "read"
    assert tools["inspect_longform_chapter_batch"]["agent_tool_surface"]["mutability"] == "read"


def test_agent_tool_plan_uses_adapter_metadata_for_surface_classification(db_session):
    project = _seed_ready_project(db_session)

    plan = build_agent_tool_plan(
        db_session,
        project.id,
        chapter_index=2,
        adapter_metadata_by_name={
            "verify_agent_plan_approval_contract": {"mutability": "read", "adapter_type": "static"},
            "inspect_longform_chapter_batch": {"mutability": "read", "adapter_type": "static"},
            "seed_continuity_anchor_proposals": {
                "mutability": "guarded_write",
                "adapter_type": "static",
                "write_policy": "approval_required_redirect",
            },
            "review_longform_chapter_batch_execution": {"mutability": "write", "adapter_type": "static"},
        },
    )
    tools = {tool["name"]: tool for tool in [*plan["visible_tools"], *plan["hidden_tools"]]}

    assert tools["verify_agent_plan_approval_contract"]["agent_tool_surface"]["mutability"] == "read"
    assert tools["verify_agent_plan_approval_contract"]["agent_tool_surface"]["requires_confirmation"] is False
    assert tools["inspect_longform_chapter_batch"]["agent_tool_surface"]["mutability"] == "read"
    assert tools["seed_continuity_anchor_proposals"]["agent_tool_surface"]["mutability"] == "guarded_write"
    assert tools["seed_continuity_anchor_proposals"]["agent_tool_surface"]["permission_level"] == "confirm_required"
    assert tools["review_longform_chapter_batch_execution"]["agent_tool_surface"]["mutability"] == "guarded_write"
    assert tools["review_longform_chapter_batch_execution"]["agent_tool_surface"]["permission_level"] == "confirm_required"


def test_agent_tool_plan_exposes_tool_policy_projection(db_session):
    project = _seed_ready_project(db_session)

    plan = build_agent_tool_plan(db_session, project.id, chapter_index=2)
    projection = plan["tool_policy_projection"]

    assert projection["version"] == "phase206.agent_tool_surface_policy.v1"
    assert projection["summary"]["visible_tools"] == len(plan["visible_tools"])
    assert projection["summary"]["hidden_tools"] == len(plan["hidden_tools"])
    assert projection["summary"]["read_tools"] >= 1
    assert projection["summary"]["write_tools"] >= 1
    assert projection["summary"]["guarded_write_tools"] >= 1
    assert projection["summary"]["unclassified_tools"] == len(projection["unclassified_tools"])
    assert "describe_agent_tools" in projection["parallel_read_tools"]
    assert "generate_chapter" in projection["approval_required_tools"]
    assert "apply_world_model_proposal_resolution" in projection["approval_required_tools"]
    assert "apply_world_model_proposal_resolution" in projection["explicit_confirmation_tools"]
    assert "describe_agent_tools" in projection["agent_only_tools"]
    assert "generate_chapter" in projection["legacy_action_bridge_tools"]
    policy_codes = {rule["code"] for rule in projection["policy_rules"]}
    assert {
        "read_tools_are_parallel_safe",
        "guarded_writes_require_confirmation",
        "unclassified_tools_require_review",
    }.issubset(policy_codes)


def test_agent_tool_plan_exposes_agent_profile_tool_projection(db_session):
    project = _seed_ready_project(db_session)

    plan = build_agent_tool_plan(db_session, project.id, chapter_index=2)
    projection = plan["agent_profile_tool_projection"]

    assert projection["version"] == "phase207.agent_profile_tool_policy.v1"
    definitions = projection["profile_definitions"]
    assert definitions["version"] == "phase212.agent_profile_definition.v1"
    assert definitions["profiles"]["orchestrator"]["role"] == "orchestrator"
    assert definitions["profiles"]["orchestrator"]["tier"] == "reasoning"
    assert definitions["profiles"]["orchestrator"]["delegation_allowed"] is True
    assert "drafting_worker" in definitions["profiles"]["orchestrator"]["delegate_to_profiles"]
    assert definitions["profiles"]["drafting_worker"]["tier"] == "worker"
    assert definitions["profiles"]["drafting_worker"]["delegation_allowed"] is False
    profiles = projection["profiles"]
    assert set(profiles) >= {
        "orchestrator",
        "drafting_worker",
        "reviewer_worker",
        "memory_worker",
        "retrieval_worker",
        "world_model_worker",
        "revision_worker",
        "recovery_worker",
    }
    assert "describe_agent_tools" in profiles["orchestrator"]["allowed_visible_tools"]
    assert "generate_chapter" not in profiles["orchestrator"]["allowed_visible_tools"]
    assert "generate_chapter" in profiles["orchestrator"]["blocked_visible_tools"]
    assert "generate_chapter" in profiles["drafting_worker"]["allowed_visible_tools"]
    assert "search_agent_retrieval_context" in profiles["retrieval_worker"]["allowed_visible_tools"]
    assert "inspect_agent_memory_activation_plan" in profiles["memory_worker"]["allowed_visible_tools"]
    assert "plan_chapter_revision" in profiles["revision_worker"]["allowed_hidden_tools"]
    assert "analyze_chapter_world_model" in profiles["drafting_worker"]["allowed_hidden_tools"]
    assert "apply_world_model_proposal_resolution" not in profiles["drafting_worker"]["allowed_hidden_tools"]
    assert "review_chapter_quality" in profiles["reviewer_worker"]["allowed_hidden_tools"]
    assert "generate_chapter" not in profiles["reviewer_worker"]["allowed_visible_tools"]
    assert "apply_pending_action_route_approval_opt_in" in profiles["reviewer_worker"]["blocked_visible_tools"]
    assert "review_world_model_proposals" in profiles["world_model_worker"]["allowed_hidden_tools"]
    assert profiles["drafting_worker"]["summary"]["allowed_visible_tools"] >= 1
    assert profiles["orchestrator"]["summary"]["blocked_visible_tools"] >= 1
    audit = projection["consistency_audit"]
    assert audit["version"] == "phase215.agent_profile_policy_audit.v1"
    assert audit["status"] == "passed"
    assert audit["summary"]["issues"] == 0
    assert audit["summary"]["delegate_edges"] == 7
    assert {"source": "orchestrator", "target": "drafting_worker"} in audit["delegate_edges"]
    assert {"source": "orchestrator", "target": "retrieval_worker"} in audit["delegate_edges"]
    audit_rule_codes = {rule["code"] for rule in audit["rules"]}
    assert {
        "profile_definitions_have_tool_rules",
        "profile_tool_rules_have_definitions",
        "delegate_targets_have_definitions",
        "delegate_targets_have_tool_rules",
        "non_delegating_profiles_have_no_delegate_targets",
        "delegated_profiles_are_leaf_profiles",
    }.issubset(audit_rule_codes)


def test_agent_profile_policy_audit_flags_unknown_delegate_targets():
    audit = build_agent_profile_policy_audit(
        {
            "version": "test",
            "profiles": {
                "orchestrator": {
                    "profile": "orchestrator",
                    "delegation_allowed": True,
                    "delegate_to_profiles": ["ghost_worker"],
                }
            },
        },
        {"orchestrator": {"profile": "orchestrator"}},
    )

    assert audit["status"] == "needs_attention"
    assert audit["summary"]["issues"] == 2
    assert {"source": "orchestrator", "target": "ghost_worker"} in audit["delegate_edges"]
    assert any(issue["code"] == "delegate_target_missing_definition" for issue in audit["issues"])
    assert any(issue["code"] == "delegate_target_missing_tool_rule" for issue in audit["issues"])


def test_agent_profile_projection_does_not_change_tool_visibility(db_session):
    project = _seed_ready_project(db_session)

    baseline = build_agent_tool_plan(db_session, project.id, chapter_index=2)
    projected = build_agent_tool_plan(db_session, project.id, chapter_index=2)

    assert _tool_names(projected["visible_tools"]) == _tool_names(baseline["visible_tools"])
    assert _tool_names(projected["hidden_tools"]) == _tool_names(baseline["hidden_tools"])


def _seed_ready_project(db_session) -> Project:
    project = Project(name="Tool Plan Ready", genre="都市悬疑", target_chapter_count=600, target_word_count=1200000)
    db_session.add(project)
    db_session.flush()
    db_session.add(
        Setup(
            project_id=project.id,
            status="generated",
            world_building={"background": "雾港被记忆异常影响。"},
            characters=[{"name": "林深", "goals": "查明真相"}],
            core_concept={"hook": "雾会回放记忆"},
        )
    )
    db_session.add(
        Storyline(
            project_id=project.id,
            status="generated",
            plotlines=[{"name": "主线", "type": "main", "summary": "追查记忆异常", "milestones": []}],
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
                    "summary": "林深继续调查记忆异常。",
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
            content="林深在雾港旧灯塔发现记忆异常的第一条线索。",
            word_count=60,
            status="generated",
        )
    )
    db_session.commit()
    db_session.refresh(project)
    return project


def _tool_names(items: list[dict]) -> set[str]:
    return {str(item["name"]) for item in items}


def _diagnostic_codes(plan: dict, tool_name: str) -> set[str]:
    return {str(item["code"]) for item in plan["diagnostics"] if item["tool_name"] == tool_name}

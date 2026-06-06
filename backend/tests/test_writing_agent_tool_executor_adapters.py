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
from app.services.writing_agent.memory_tree_tool_adapters import build_memory_tree_tool_adapters
from app.services.writing_agent.outline_generation_tool_adapters import build_outline_generation_agent_tool_adapters
from app.services.writing_agent.review_revision_tool_adapters import REVIEW_REVISION_AGENT_TOOL_ADAPTERS
from app.services.writing_agent.setup_generation_tool_adapters import build_setup_generation_agent_tool_adapters
from app.services.writing_agent.storyline_generation_tool_adapters import build_storyline_generation_agent_tool_adapters
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
        "inspect_agent_trace_anomaly_trends",
        "inspect_agent_trace_anomaly_long_run_samples",
        "inspect_agent_trace_anomaly_threshold_review",
        "record_agent_trace_anomaly_threshold_config",
        "inspect_agent_memory_route",
        "inspect_agent_retrieval_strategy",
        "inspect_agent_retrieval_strategy_quality",
        "inspect_agent_retrieval_prefetch_plan",
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
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["inspect_agent_trace_anomaly_trends"].mutability == "read"
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["inspect_agent_trace_anomaly_long_run_samples"].mutability == "read"
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["inspect_agent_trace_anomaly_threshold_review"].mutability == "read"
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["record_agent_trace_anomaly_threshold_config"].mutability == (
        "guarded_write"
    )
    assert (
        AGENT_MEMORY_TRACE_TOOL_ADAPTERS["record_agent_trace_anomaly_threshold_config"].write_policy
        == "approval_required_redirect"
    )
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["search_agent_retrieval_context"].mutability == "read"
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["inspect_agent_retrieval_strategy"].mutability == "read"
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["inspect_agent_retrieval_strategy_quality"].mutability == "read"
    assert AGENT_MEMORY_TRACE_TOOL_ADAPTERS["inspect_agent_retrieval_prefetch_plan"].mutability == "read"
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
        AGENT_MEMORY_TRACE_TOOL_ADAPTERS["inspect_agent_retrieval_strategy"].handler.__name__
        == "_inspect_agent_retrieval_strategy"
    )
    assert (
        AGENT_MEMORY_TRACE_TOOL_ADAPTERS["inspect_agent_retrieval_strategy_quality"].handler.__name__
        == "_inspect_agent_retrieval_strategy_quality"
    )
    assert (
        AGENT_MEMORY_TRACE_TOOL_ADAPTERS["inspect_agent_retrieval_prefetch_plan"].handler.__name__
        == "_inspect_agent_retrieval_prefetch_plan"
    )
    assert (
        AGENT_MEMORY_TRACE_TOOL_ADAPTERS["repair_longform_maintenance"].handler.__name__
        == "_repair_longform_maintenance"
    )
    assert (
        AGENT_MEMORY_TRACE_TOOL_ADAPTERS["record_agent_trace_anomaly_threshold_config"].handler.__name__
        == "_record_agent_trace_anomaly_threshold_config"
    )
    assert (
        AGENT_MEMORY_TRACE_TOOL_ADAPTERS["inspect_agent_trace_anomaly_long_run_samples"].handler.__name__
        == "_inspect_agent_trace_anomaly_long_run_samples"
    )
    assert (
        AGENT_MEMORY_TRACE_TOOL_ADAPTERS["inspect_agent_trace_anomaly_threshold_review"].handler.__name__
        == "_inspect_agent_trace_anomaly_threshold_review"
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
        "inspect_agent_trace_anomaly_trends",
        "inspect_agent_trace_anomaly_long_run_samples",
        "inspect_agent_trace_anomaly_threshold_review",
        "record_agent_trace_anomaly_threshold_config",
        "inspect_agent_memory_route",
        "inspect_agent_retrieval_strategy",
        "inspect_agent_retrieval_strategy_quality",
        "inspect_agent_retrieval_prefetch_plan",
        "search_agent_retrieval_context",
        "summarize_longform_context",
        "inspect_agent_context_compression_projection",
        "build_agent_context_compression_payload",
        "record_agent_context_compression_summary",
        "inspect_agent_memory_activation_plan",
        "repair_longform_maintenance",
        "prepare_repair_longform_maintenance",
        "execute_repair_longform_maintenance_with_approval",
        "prepare_record_agent_trace_anomaly_threshold_config",
        "execute_record_agent_trace_anomaly_threshold_config_with_approval",
    ]
    assert adapters["prepare_repair_longform_maintenance"].mutability == "read"
    assert adapters["execute_repair_longform_maintenance_with_approval"].mutability == "write"
    assert adapters["prepare_record_agent_trace_anomaly_threshold_config"].mutability == "read"
    assert adapters["execute_record_agent_trace_anomaly_threshold_config_with_approval"].mutability == "write"
    assert (
        adapters["execute_repair_longform_maintenance_with_approval"].handler.__name__
        == "_execute_repair_longform_maintenance_with_approval"
    )
    assert (
        adapters["execute_record_agent_trace_anomaly_threshold_config_with_approval"].handler.__name__
        == "_execute_record_agent_trace_anomaly_threshold_config_with_approval"
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


def test_memory_tree_tool_adapter_builder_adds_summary_approval_chain():
    adapters = build_memory_tree_tool_adapters(approval_tool_metadata_provider=lambda plan: {})
    names = list(adapters)

    assert names == [
        "inspect_agent_memory_tree",
        "inspect_agent_memory_tree_quality",
        "build_agent_memory_tree_llm_summary_plan",
        "summarize_agent_memory_tree_llm_candidate",
        "inspect_agent_memory_tree_llm_candidates",
        "record_agent_memory_tree_llm_candidate_summary",
        "record_agent_memory_tree_summaries",
        "prepare_record_agent_memory_tree_llm_candidate_summary",
        "prepare_record_agent_memory_tree_llm_candidate_summaries_batch",
        "execute_record_agent_memory_tree_llm_candidate_summary_with_approval",
        "execute_record_agent_memory_tree_llm_candidate_summaries_batch_with_approval",
        "prepare_record_agent_memory_tree_summaries",
        "execute_record_agent_memory_tree_summaries_with_approval",
    ]
    assert adapters["inspect_agent_memory_tree"].mutability == "read"
    assert adapters["inspect_agent_memory_tree_quality"].mutability == "read"
    assert adapters["build_agent_memory_tree_llm_summary_plan"].mutability == "read"
    assert adapters["summarize_agent_memory_tree_llm_candidate"].mutability == "read"
    assert adapters["inspect_agent_memory_tree_llm_candidates"].mutability == "read"
    assert adapters["record_agent_memory_tree_llm_candidate_summary"].mutability == "guarded_write"
    assert (
        adapters["record_agent_memory_tree_llm_candidate_summary"].write_policy
        == "approval_required_redirect"
    )
    assert adapters["record_agent_memory_tree_summaries"].mutability == "guarded_write"
    assert adapters["record_agent_memory_tree_summaries"].write_policy == "approval_required_redirect"
    assert adapters["prepare_record_agent_memory_tree_llm_candidate_summary"].mutability == "read"
    assert adapters["prepare_record_agent_memory_tree_llm_candidate_summaries_batch"].mutability == "read"
    assert adapters["execute_record_agent_memory_tree_llm_candidate_summary_with_approval"].mutability == "write"
    assert (
        adapters["execute_record_agent_memory_tree_llm_candidate_summary_with_approval"].handler.__name__
        == "_execute_record_agent_memory_tree_llm_candidate_summary_with_approval"
    )
    assert adapters["prepare_record_agent_memory_tree_summaries"].mutability == "read"
    assert adapters["execute_record_agent_memory_tree_summaries_with_approval"].mutability == "write"
    assert (
        adapters["execute_record_agent_memory_tree_summaries_with_approval"].handler.__name__
        == "_execute_record_agent_memory_tree_summaries_with_approval"
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
        "inspect_agent_world_model_semantic_check",
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
    assert WORLD_MODEL_AGENT_TOOL_ADAPTERS["inspect_agent_world_model_semantic_check"].mutability == "read"
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

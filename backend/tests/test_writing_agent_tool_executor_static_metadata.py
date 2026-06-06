from app.services.writing_agent.tool_executor import (
    static_writing_agent_tool_adapter_names,
    unhandled_internal_writing_agent_tool_names,
    writing_agent_tool_adapter_metadata,
    writing_agent_tool_adapter_metadata_by_name,
)


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
        "inspect_agent_world_model_semantic_check",
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

def test_tool_executor_exposes_inspect_agent_retrieval_strategy_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_retrieval_strategy")

    assert metadata == {
        "tool_name": "inspect_agent_retrieval_strategy",
        "adapter_type": "static",
        "category": "retrieval",
        "mutability": "read",
        "handler_name": "_inspect_agent_retrieval_strategy",
    }

def test_tool_executor_exposes_inspect_agent_retrieval_prefetch_plan_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_retrieval_prefetch_plan")

    assert metadata == {
        "tool_name": "inspect_agent_retrieval_prefetch_plan",
        "adapter_type": "static",
        "category": "retrieval",
        "mutability": "read",
        "handler_name": "_inspect_agent_retrieval_prefetch_plan",
    }

def test_tool_executor_exposes_inspect_agent_world_model_semantic_check_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_world_model_semantic_check")

    assert metadata == {
        "tool_name": "inspect_agent_world_model_semantic_check",
        "adapter_type": "static",
        "category": "athena_world_model",
        "mutability": "read",
        "handler_name": "_inspect_agent_world_model_semantic_check",
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

def test_tool_executor_exposes_inspect_agent_trace_anomaly_trends_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_trace_anomaly_trends")

    assert metadata == {
        "tool_name": "inspect_agent_trace_anomaly_trends",
        "adapter_type": "static",
        "category": "trace",
        "mutability": "read",
        "handler_name": "_inspect_agent_trace_anomaly_trends",
    }

def test_tool_executor_exposes_inspect_agent_trace_anomaly_long_run_samples_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_trace_anomaly_long_run_samples")

    assert metadata == {
        "tool_name": "inspect_agent_trace_anomaly_long_run_samples",
        "adapter_type": "static",
        "category": "trace",
        "mutability": "read",
        "handler_name": "_inspect_agent_trace_anomaly_long_run_samples",
    }

def test_tool_executor_exposes_inspect_agent_trace_anomaly_threshold_review_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("inspect_agent_trace_anomaly_threshold_review")

    assert metadata == {
        "tool_name": "inspect_agent_trace_anomaly_threshold_review",
        "adapter_type": "static",
        "category": "trace",
        "mutability": "read",
        "handler_name": "_inspect_agent_trace_anomaly_threshold_review",
    }

def test_tool_executor_exposes_trace_anomaly_threshold_config_adapter_metadata():
    direct_metadata = writing_agent_tool_adapter_metadata("record_agent_trace_anomaly_threshold_config")
    prepare_metadata = writing_agent_tool_adapter_metadata("prepare_record_agent_trace_anomaly_threshold_config")
    execute_metadata = writing_agent_tool_adapter_metadata(
        "execute_record_agent_trace_anomaly_threshold_config_with_approval"
    )

    assert direct_metadata == {
        "tool_name": "record_agent_trace_anomaly_threshold_config",
        "adapter_type": "static",
        "category": "trace",
        "mutability": "guarded_write",
        "handler_name": "_record_agent_trace_anomaly_threshold_config",
        "write_policy": "approval_required_redirect",
    }
    assert prepare_metadata == {
        "tool_name": "prepare_record_agent_trace_anomaly_threshold_config",
        "adapter_type": "static",
        "category": "trace",
        "mutability": "read",
        "handler_name": "_prepare_record_agent_trace_anomaly_threshold_config",
    }
    assert execute_metadata == {
        "tool_name": "execute_record_agent_trace_anomaly_threshold_config_with_approval",
        "adapter_type": "static",
        "category": "trace",
        "mutability": "write",
        "handler_name": "_execute_record_agent_trace_anomaly_threshold_config_with_approval",
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

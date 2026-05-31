from __future__ import annotations

from app.services.writing_agent.write_gate_coverage import inspect_agent_write_gate_coverage


def test_write_gate_coverage_marks_batch_execute_as_agent_gate_enforced():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    tools_by_name = _tools_by_name(output)

    execute_tool = tools_by_name["execute_longform_chapter_batch"]
    assert execute_tool["agent_plan_gate_status"] == "enforced"
    assert execute_tool["gate_version"] == "phase111.agent_plan_approval_execution_gate.v1"
    assert execute_tool["risk_level"] == "low"
    assert output["summary"]["agent_plan_gate_enforced_count"] >= 1


def test_write_gate_coverage_marks_approved_direct_generate_as_agent_gate_enforced():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    tools_by_name = _tools_by_name(output)

    execute_tool = tools_by_name["execute_generate_chapter_with_approval"]
    assert execute_tool["agent_plan_gate_status"] == "enforced"
    assert execute_tool["gate_version"] == "phase114.direct_generate_agent_plan_approval.v1"
    assert execute_tool["risk_level"] == "low"


def test_write_gate_coverage_marks_pre_chapter_generation_approval_executors_as_enforced():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    tools_by_name = _tools_by_name(output)

    expected_gate_versions = {
        "execute_generate_setup_with_approval": "phase186.setup_agent_plan_approval.v1",
        "execute_generate_storyline_with_approval": "phase187.storyline_agent_plan_approval.v1",
        "execute_generate_outline_with_approval": "phase188.outline_agent_plan_approval.v1",
    }
    for tool_name, gate_version in expected_gate_versions.items():
        execute_tool = tools_by_name[tool_name]
        assert execute_tool["agent_plan_gate_status"] == "enforced"
        assert execute_tool["gate_version"] == gate_version
        assert execute_tool["gate_type"] == "stateless_agent_plan_approval"
        assert execute_tool["risk_level"] == "low"
        assert execute_tool["confirmation_fields"] == ["approval_contract_hash", "confirm_execute"]


def test_write_gate_coverage_marks_import_setup_world_model_direct_calls_as_approval_redirected():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    tools_by_name = _tools_by_name(output)

    execute_tool = tools_by_name["execute_import_setup_world_model_with_approval"]
    assert execute_tool["agent_plan_gate_status"] == "enforced"
    assert execute_tool["gate_version"] == "phase191.setup_world_model_import_agent_plan_approval.v1"
    assert execute_tool["risk_level"] == "low"

    import_tool = tools_by_name["import_setup_world_model"]
    assert import_tool["agent_plan_gate_status"] == "indirect_agent_gate_available"
    assert import_tool["direct_write_policy"] == "approval_required_redirect"
    assert import_tool["direct_write_blocked"] is True
    assert import_tool["risk_level"] == "low"
    assert {item["consumer_tool"] for item in import_tool["indirect_coverage"]} == {
        "execute_import_setup_world_model_with_approval"
    }
    assert import_tool["recommended_action"] == "route_direct_calls_to_approval_executor"


def test_write_gate_coverage_marks_analyze_chapter_world_model_direct_calls_as_approval_redirected():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    tools_by_name = _tools_by_name(output)

    execute_tool = tools_by_name["execute_analyze_chapter_world_model_with_approval"]
    assert execute_tool["agent_plan_gate_status"] == "enforced"
    assert execute_tool["gate_version"] == "phase192.world_model_analysis_agent_plan_approval.v1"
    assert execute_tool["risk_level"] == "low"

    analyze_tool = tools_by_name["analyze_chapter_world_model"]
    assert analyze_tool["agent_plan_gate_status"] == "indirect_agent_gate_available"
    assert analyze_tool["direct_write_policy"] == "approval_required_redirect"
    assert analyze_tool["direct_write_blocked"] is True
    assert analyze_tool["risk_level"] == "low"
    assert {item["consumer_tool"] for item in analyze_tool["indirect_coverage"]} == {
        "execute_analyze_chapter_world_model_with_approval"
    }
    assert analyze_tool["recommended_action"] == "route_direct_calls_to_approval_executor"


def test_write_gate_coverage_marks_backfill_outline_gaps_direct_calls_as_approval_redirected():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    tools_by_name = _tools_by_name(output)

    execute_tool = tools_by_name["execute_backfill_outline_gaps_with_approval"]
    assert execute_tool["agent_plan_gate_status"] == "enforced"
    assert execute_tool["gate_version"] == "phase193.outline_backfill_agent_plan_approval.v1"
    assert execute_tool["risk_level"] == "low"

    backfill_tool = tools_by_name["backfill_outline_gaps"]
    assert backfill_tool["agent_plan_gate_status"] == "indirect_agent_gate_available"
    assert backfill_tool["direct_write_policy"] == "approval_required_redirect"
    assert backfill_tool["direct_write_blocked"] is True
    assert backfill_tool["risk_level"] == "low"
    assert {item["consumer_tool"] for item in backfill_tool["indirect_coverage"]} == {
        "execute_backfill_outline_gaps_with_approval"
    }
    assert backfill_tool["recommended_action"] == "route_direct_calls_to_approval_executor"


def test_write_gate_coverage_marks_create_revision_draft_direct_calls_as_approval_redirected():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    tools_by_name = _tools_by_name(output)

    execute_tool = tools_by_name["execute_create_revision_draft_with_approval"]
    assert execute_tool["agent_plan_gate_status"] == "enforced"
    assert execute_tool["gate_version"] == "phase194.revision_draft_agent_plan_approval.v1"
    assert execute_tool["risk_level"] == "low"

    draft_tool = tools_by_name["create_revision_draft"]
    assert draft_tool["agent_plan_gate_status"] == "indirect_agent_gate_available"
    assert draft_tool["direct_write_policy"] == "approval_required_redirect"
    assert draft_tool["direct_write_blocked"] is True
    assert draft_tool["risk_level"] == "low"
    assert {item["consumer_tool"] for item in draft_tool["indirect_coverage"]} == {
        "execute_create_revision_draft_with_approval"
    }
    assert draft_tool["recommended_action"] == "route_direct_calls_to_approval_executor"


def test_write_gate_coverage_marks_chapter_revision_adjustments_as_approval_redirected():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    tools_by_name = _tools_by_name(output)

    expected = {
        "expand_chapter_to_target": (
            "execute_expand_chapter_to_target_with_approval",
            "phase196.chapter_expansion_agent_plan_approval.v1",
        ),
        "compress_chapter_to_target": (
            "execute_compress_chapter_to_target_with_approval",
            "phase197.chapter_compression_agent_plan_approval.v1",
        ),
    }
    for direct_tool_name, (execute_tool_name, gate_version) in expected.items():
        execute_tool = tools_by_name[execute_tool_name]
        assert execute_tool["agent_plan_gate_status"] == "enforced"
        assert execute_tool["gate_version"] == gate_version
        assert execute_tool["risk_level"] == "low"

        direct_tool = tools_by_name[direct_tool_name]
        assert direct_tool["agent_plan_gate_status"] == "indirect_agent_gate_available"
        assert direct_tool["direct_write_policy"] == "approval_required_redirect"
        assert direct_tool["direct_write_blocked"] is True
        assert direct_tool["risk_level"] == "low"
        assert {item["consumer_tool"] for item in direct_tool["indirect_coverage"]} == {execute_tool_name}


def test_write_gate_coverage_marks_continuity_anchor_seed_as_approval_redirected():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    tools_by_name = _tools_by_name(output)

    execute_tool = tools_by_name["execute_seed_continuity_anchor_proposals_with_approval"]
    assert execute_tool["agent_plan_gate_status"] == "enforced"
    assert execute_tool["gate_version"] == "phase198.continuity_anchor_seed_agent_plan_approval.v1"
    assert execute_tool["gate_type"] == "stateless_agent_plan_approval"
    assert execute_tool["risk_level"] == "low"
    assert execute_tool["confirmation_fields"] == ["approval_contract_hash", "confirm_execute"]

    seed_tool = tools_by_name["seed_continuity_anchor_proposals"]
    assert seed_tool["agent_plan_gate_status"] == "indirect_agent_gate_available"
    assert seed_tool["direct_write_policy"] == "approval_required_redirect"
    assert seed_tool["direct_write_blocked"] is True
    assert seed_tool["risk_level"] == "low"
    assert seed_tool["recommended_action"] == "route_direct_calls_to_approval_executor"
    assert {item["consumer_tool"] for item in seed_tool["indirect_coverage"]} == {
        "execute_seed_continuity_anchor_proposals_with_approval"
    }


def test_write_gate_coverage_marks_generate_chapter_direct_calls_as_approval_redirected():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    generate_tool = _tools_by_name(output)["generate_chapter"]

    assert generate_tool["agent_plan_gate_status"] == "indirect_agent_gate_available"
    assert generate_tool["direct_write_policy"] == "approval_required_redirect"
    assert generate_tool["direct_write_blocked"] is True
    assert generate_tool["direct_confirmation_guard"] is False
    assert generate_tool["risk_level"] == "low"
    assert {item["consumer_tool"] for item in generate_tool["indirect_coverage"]} >= {
        "execute_generate_chapter_with_approval",
        "execute_longform_chapter_batch",
    }
    assert generate_tool["recommended_action"] == "route_direct_calls_to_approval_executor"


def test_write_gate_coverage_marks_expand_outline_window_as_direct_confirmation_guarded():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    expand_tool = _tools_by_name(output)["expand_outline_window"]

    assert expand_tool["agent_plan_gate_status"] == "missing_agent_plan_gate"
    assert expand_tool["direct_confirmation_guard"] is True
    assert expand_tool["confirmation_fields"] == ["confirm_execute"]
    assert expand_tool["risk_level"] == "medium"
    assert expand_tool["recommended_action"] == "promote_confirm_guard_to_agent_plan_approval"


def test_write_gate_coverage_marks_pre_chapter_generate_tools_as_indirectly_covered_direct_gaps():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    tools_by_name = _tools_by_name(output)

    expected_consumers = {
        "generate_setup": "execute_generate_setup_with_approval",
        "generate_storyline": "execute_generate_storyline_with_approval",
        "generate_outline": "execute_generate_outline_with_approval",
    }
    for tool_name, consumer_tool in expected_consumers.items():
        generate_tool = tools_by_name[tool_name]
        assert generate_tool["agent_plan_gate_status"] == "indirect_agent_gate_available"
        assert generate_tool["direct_write_policy"] == "approval_required_redirect"
        assert generate_tool["direct_write_blocked"] is True
        assert generate_tool["direct_confirmation_guard"] is False
        assert generate_tool["risk_level"] == "low"
        assert {item["consumer_tool"] for item in generate_tool["indirect_coverage"]} == {consumer_tool}
        assert generate_tool["recommended_action"] == "route_direct_calls_to_approval_executor"


def test_write_gate_coverage_marks_knowledge_base_candidate_approval_executor_as_enforced():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    tools_by_name = _tools_by_name(output)

    execute_tool = tools_by_name["execute_record_agent_knowledge_base_candidate_with_approval"]
    assert execute_tool["agent_plan_gate_status"] == "enforced"
    assert execute_tool["gate_version"] == "phase189.knowledge_base_candidate_agent_plan_approval.v1"
    assert execute_tool["gate_type"] == "stateless_agent_plan_approval"
    assert execute_tool["risk_level"] == "low"
    assert execute_tool["confirmation_fields"] == ["approval_contract_hash", "confirm_execute"]

    record_tool = tools_by_name["record_agent_knowledge_base_candidate"]
    assert record_tool["agent_plan_gate_status"] == "indirect_agent_gate_available"
    assert record_tool["direct_write_policy"] == "approval_required_redirect"
    assert record_tool["direct_write_blocked"] is True
    assert record_tool["direct_confirmation_guard"] is False
    assert record_tool["risk_level"] == "low"
    assert record_tool["recommended_action"] == "route_direct_calls_to_approval_executor"
    assert {item["consumer_tool"] for item in record_tool["indirect_coverage"]} == {
        "execute_record_agent_knowledge_base_candidate_with_approval"
    }


def test_write_gate_coverage_marks_longform_maintenance_approval_executor_as_enforced():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    tools_by_name = _tools_by_name(output)

    execute_tool = tools_by_name["execute_repair_longform_maintenance_with_approval"]
    assert execute_tool["agent_plan_gate_status"] == "enforced"
    assert execute_tool["gate_version"] == "phase190.longform_maintenance_agent_plan_approval.v1"
    assert execute_tool["gate_type"] == "stateless_agent_plan_approval"
    assert execute_tool["risk_level"] == "low"
    assert execute_tool["confirmation_fields"] == ["approval_contract_hash", "confirm_execute"]

    repair_tool = tools_by_name["repair_longform_maintenance"]
    assert repair_tool["agent_plan_gate_status"] == "indirect_agent_gate_available"
    assert repair_tool["direct_write_policy"] == "approval_required_redirect"
    assert repair_tool["direct_write_blocked"] is True
    assert repair_tool["direct_confirmation_guard"] is False
    assert repair_tool["risk_level"] == "low"
    assert repair_tool["recommended_action"] == "route_direct_calls_to_approval_executor"
    assert {item["consumer_tool"] for item in repair_tool["indirect_coverage"]} == {
        "execute_repair_longform_maintenance_with_approval"
    }


def test_write_gate_coverage_marks_longform_batch_enqueue_as_approval_redirected():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    tools_by_name = _tools_by_name(output)

    execute_tool = tools_by_name["execute_enqueue_longform_chapter_batch_with_approval"]
    assert execute_tool["agent_plan_gate_status"] == "enforced"
    assert execute_tool["gate_version"] == "phase199.longform_batch_enqueue_agent_plan_approval.v1"
    assert execute_tool["gate_type"] == "stateless_agent_plan_approval"
    assert execute_tool["risk_level"] == "low"
    assert execute_tool["confirmation_fields"] == ["approval_contract_hash", "confirm_execute", "plan_hash"]

    enqueue_tool = tools_by_name["enqueue_longform_chapter_batch"]
    assert enqueue_tool["agent_plan_gate_status"] == "indirect_agent_gate_available"
    assert enqueue_tool["direct_write_policy"] == "approval_required_redirect"
    assert enqueue_tool["direct_write_blocked"] is True
    assert enqueue_tool["direct_confirmation_guard"] is True
    assert enqueue_tool["risk_level"] == "low"
    assert enqueue_tool["recommended_action"] == "route_direct_calls_to_approval_executor"
    assert {item["consumer_tool"] for item in enqueue_tool["indirect_coverage"]} == {
        "execute_enqueue_longform_chapter_batch_with_approval"
    }


def test_write_gate_coverage_marks_confirm_guarded_tools_as_missing_agent_gate():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    apply_tool = _tools_by_name(output)["apply_world_model_proposal_resolution"]

    assert apply_tool["agent_plan_gate_status"] == "missing_agent_plan_gate"
    assert apply_tool["direct_confirmation_guard"] is True
    assert apply_tool["confirmation_fields"] == ["approval_contract_hash", "confirm_apply"]
    assert apply_tool["risk_level"] == "medium"
    assert apply_tool["recommended_action"] == "promote_confirm_guard_to_agent_plan_approval"


def test_write_gate_coverage_marks_apply_route_opt_in_as_direct_confirmation_guarded():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    apply_tool = _tools_by_name(output)["apply_pending_action_route_approval_opt_in"]

    assert apply_tool["mutability"] == "guarded_write"
    assert apply_tool["requires_confirmation"] is True
    assert apply_tool["direct_confirmation_guard"] is True
    assert apply_tool["confirmation_fields"] == ["approval_contract_hash", "confirm_apply"]
    assert apply_tool["risk_level"] == "medium"


def test_write_gate_coverage_marks_batch_checkpoint_writes_as_confirmation_guarded():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    tools_by_name = _tools_by_name(output)

    approved_preflight_tool = tools_by_name["execute_longform_chapter_batch_preflight_with_approval"]
    assert approved_preflight_tool["agent_plan_gate_status"] == "enforced"
    assert approved_preflight_tool["gate_version"] == "phase200.longform_batch_preflight_agent_plan_approval.v1"
    assert approved_preflight_tool["gate_type"] == "stateless_agent_plan_approval"
    assert approved_preflight_tool["confirmation_fields"] == ["approval_contract_hash", "confirm_execute"]
    assert approved_preflight_tool["risk_level"] == "low"

    preflight_tool = tools_by_name["execute_longform_chapter_batch_preflight"]
    assert preflight_tool["agent_plan_gate_status"] == "indirect_agent_gate_available"
    assert preflight_tool["direct_write_policy"] == "approval_required_redirect"
    assert preflight_tool["direct_write_blocked"] is True
    assert preflight_tool["direct_confirmation_guard"] is True
    assert preflight_tool["confirmation_fields"] == ["confirm_checkpoint"]
    assert preflight_tool["risk_level"] == "low"
    assert preflight_tool["recommended_action"] == "route_direct_calls_to_approval_executor"
    assert {item["consumer_tool"] for item in preflight_tool["indirect_coverage"]} == {
        "execute_longform_chapter_batch_preflight_with_approval"
    }

    approved_prepare_tool = tools_by_name["execute_longform_chapter_batch_execution_prepare_with_approval"]
    assert approved_prepare_tool["agent_plan_gate_status"] == "enforced"
    assert approved_prepare_tool["gate_version"] == "phase201.longform_batch_execution_prepare_agent_plan_approval.v1"
    assert approved_prepare_tool["gate_type"] == "stateless_agent_plan_approval"
    assert approved_prepare_tool["direct_confirmation_guard"] is True
    assert approved_prepare_tool["confirmation_fields"] == ["approval_contract_hash", "confirm_execute"]
    assert approved_prepare_tool["risk_level"] == "low"

    prepare_tool = tools_by_name["prepare_longform_chapter_batch_execution"]
    assert prepare_tool["agent_plan_gate_status"] == "indirect_agent_gate_available"
    assert prepare_tool["direct_write_policy"] == "approval_required_redirect"
    assert prepare_tool["direct_write_blocked"] is True
    assert prepare_tool["direct_confirmation_guard"] is True
    assert prepare_tool["confirmation_fields"] == ["confirm_prepare"]
    assert prepare_tool["risk_level"] == "low"
    assert prepare_tool["recommended_action"] == "route_direct_calls_to_approval_executor"
    assert {item["consumer_tool"] for item in prepare_tool["indirect_coverage"]} == {
        "execute_longform_chapter_batch_execution_prepare_with_approval"
    }

    approved_review_tool = tools_by_name["execute_longform_chapter_batch_execution_review_with_approval"]
    assert approved_review_tool["agent_plan_gate_status"] == "enforced"
    assert approved_review_tool["gate_version"] == "phase202.longform_batch_execution_review_agent_plan_approval.v1"
    assert approved_review_tool["gate_type"] == "stateless_agent_plan_approval"
    assert approved_review_tool["confirmation_fields"] == ["approval_contract_hash", "confirm_execute"]
    assert approved_review_tool["risk_level"] == "low"

    review_tool = tools_by_name["review_longform_chapter_batch_execution"]
    assert review_tool["agent_plan_gate_status"] == "indirect_agent_gate_available"
    assert review_tool["direct_write_policy"] == "approval_required_redirect"
    assert review_tool["direct_write_blocked"] is True
    assert review_tool["direct_confirmation_guard"] is True
    assert review_tool["confirmation_fields"] == ["confirm_review"]
    assert review_tool["risk_level"] == "low"
    assert review_tool["recommended_action"] == "route_direct_calls_to_approval_executor"
    assert {item["consumer_tool"] for item in review_tool["indirect_coverage"]} == {
        "execute_longform_chapter_batch_execution_review_with_approval"
    }


def test_write_gate_coverage_recommends_high_risk_targets_first():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())

    assert output["status"] == "completed"
    assert output["recommended_next_targets"]
    first_target = output["recommended_next_targets"][0]
    assert first_target["risk_level"] == "high"
    assert first_target["agent_plan_gate_status"] in {"missing_agent_plan_gate", "indirect_agent_gate_available"}


def _tools_by_name(output: dict) -> dict[str, dict]:
    return {str(tool["tool_name"]): tool for tool in output["write_tools"]}


def _adapter_metadata() -> dict[str, dict]:
    return {
        "generate_chapter": {
            "tool_name": "generate_chapter",
            "adapter_type": "static",
            "category": "generation",
            "mutability": "guarded_write",
            "handler_name": "_generate_chapter",
            "write_policy": "approval_required_redirect",
        },
        "execute_longform_chapter_batch": {
            "tool_name": "execute_longform_chapter_batch",
            "adapter_type": "static",
            "category": "task_queue",
            "mutability": "write",
            "handler_name": "_execute_longform_chapter_batch",
        },
        "enqueue_longform_chapter_batch": {
            "tool_name": "enqueue_longform_chapter_batch",
            "adapter_type": "static",
            "category": "task_queue",
            "mutability": "guarded_write",
            "handler_name": "_enqueue_longform_chapter_batch",
            "write_policy": "approval_required_redirect",
        },
        "execute_enqueue_longform_chapter_batch_with_approval": {
            "tool_name": "execute_enqueue_longform_chapter_batch_with_approval",
            "adapter_type": "static",
            "category": "task_queue",
            "mutability": "write",
            "handler_name": "_execute_enqueue_longform_chapter_batch_with_approval",
        },
        "execute_generate_chapter_with_approval": {
            "tool_name": "execute_generate_chapter_with_approval",
            "adapter_type": "static",
            "category": "generation",
            "mutability": "write",
            "handler_name": "_execute_generate_chapter_with_approval",
        },
        "generate_setup": {
            "tool_name": "generate_setup",
            "adapter_type": "static",
            "category": "generation",
            "mutability": "guarded_write",
            "handler_name": "_generate_setup",
            "write_policy": "approval_required_redirect",
        },
        "execute_generate_setup_with_approval": {
            "tool_name": "execute_generate_setup_with_approval",
            "adapter_type": "static",
            "category": "generation",
            "mutability": "write",
            "handler_name": "_execute_generate_setup_with_approval",
        },
        "generate_storyline": {
            "tool_name": "generate_storyline",
            "adapter_type": "static",
            "category": "generation",
            "mutability": "guarded_write",
            "handler_name": "_generate_storyline",
            "write_policy": "approval_required_redirect",
        },
        "execute_generate_storyline_with_approval": {
            "tool_name": "execute_generate_storyline_with_approval",
            "adapter_type": "static",
            "category": "generation",
            "mutability": "write",
            "handler_name": "_execute_generate_storyline_with_approval",
        },
        "generate_outline": {
            "tool_name": "generate_outline",
            "adapter_type": "static",
            "category": "generation",
            "mutability": "guarded_write",
            "handler_name": "_generate_outline",
            "write_policy": "approval_required_redirect",
        },
        "execute_generate_outline_with_approval": {
            "tool_name": "execute_generate_outline_with_approval",
            "adapter_type": "static",
            "category": "generation",
            "mutability": "write",
            "handler_name": "_execute_generate_outline_with_approval",
        },
        "import_setup_world_model": {
            "tool_name": "import_setup_world_model",
            "adapter_type": "static",
            "category": "athena_world_model",
            "mutability": "guarded_write",
            "handler_name": "_import_setup_world_model",
            "write_policy": "approval_required_redirect",
        },
        "execute_import_setup_world_model_with_approval": {
            "tool_name": "execute_import_setup_world_model_with_approval",
            "adapter_type": "static",
            "category": "athena_world_model",
            "mutability": "write",
            "handler_name": "_execute_import_setup_world_model_with_approval",
        },
        "analyze_chapter_world_model": {
            "tool_name": "analyze_chapter_world_model",
            "adapter_type": "static",
            "category": "athena_world_model",
            "mutability": "guarded_write",
            "handler_name": "_analyze_chapter_world_model",
            "write_policy": "approval_required_redirect",
        },
        "execute_analyze_chapter_world_model_with_approval": {
            "tool_name": "execute_analyze_chapter_world_model_with_approval",
            "adapter_type": "static",
            "category": "athena_world_model",
            "mutability": "write",
            "handler_name": "_execute_analyze_chapter_world_model_with_approval",
        },
        "backfill_outline_gaps": {
            "tool_name": "backfill_outline_gaps",
            "adapter_type": "static",
            "category": "maintenance",
            "mutability": "guarded_write",
            "handler_name": "_backfill_outline_gaps",
            "write_policy": "approval_required_redirect",
        },
        "execute_backfill_outline_gaps_with_approval": {
            "tool_name": "execute_backfill_outline_gaps_with_approval",
            "adapter_type": "static",
            "category": "maintenance",
            "mutability": "write",
            "handler_name": "_execute_backfill_outline_gaps_with_approval",
        },
        "create_revision_draft": {
            "tool_name": "create_revision_draft",
            "adapter_type": "static",
            "category": "revision",
            "mutability": "guarded_write",
            "handler_name": "_create_revision_draft",
            "write_policy": "approval_required_redirect",
        },
        "execute_create_revision_draft_with_approval": {
            "tool_name": "execute_create_revision_draft_with_approval",
            "adapter_type": "static",
            "category": "revision",
            "mutability": "write",
            "handler_name": "_execute_create_revision_draft_with_approval",
        },
        "expand_chapter_to_target": {
            "tool_name": "expand_chapter_to_target",
            "adapter_type": "static",
            "category": "revision",
            "mutability": "guarded_write",
            "handler_name": "_expand_chapter_to_target",
            "write_policy": "approval_required_redirect",
        },
        "execute_expand_chapter_to_target_with_approval": {
            "tool_name": "execute_expand_chapter_to_target_with_approval",
            "adapter_type": "static",
            "category": "revision",
            "mutability": "write",
            "handler_name": "_execute_expand_chapter_to_target_with_approval",
        },
        "compress_chapter_to_target": {
            "tool_name": "compress_chapter_to_target",
            "adapter_type": "static",
            "category": "revision",
            "mutability": "guarded_write",
            "handler_name": "_compress_chapter_to_target",
            "write_policy": "approval_required_redirect",
        },
        "execute_compress_chapter_to_target_with_approval": {
            "tool_name": "execute_compress_chapter_to_target_with_approval",
            "adapter_type": "static",
            "category": "revision",
            "mutability": "write",
            "handler_name": "_execute_compress_chapter_to_target_with_approval",
        },
        "seed_continuity_anchor_proposals": {
            "tool_name": "seed_continuity_anchor_proposals",
            "adapter_type": "static",
            "category": "maintenance",
            "mutability": "guarded_write",
            "handler_name": "_seed_continuity_anchor_proposals",
            "write_policy": "approval_required_redirect",
        },
        "execute_seed_continuity_anchor_proposals_with_approval": {
            "tool_name": "execute_seed_continuity_anchor_proposals_with_approval",
            "adapter_type": "static",
            "category": "maintenance",
            "mutability": "write",
            "handler_name": "_execute_seed_continuity_anchor_proposals_with_approval",
        },
        "apply_world_model_proposal_resolution": {
            "tool_name": "apply_world_model_proposal_resolution",
            "adapter_type": "static",
            "category": "athena_world_model",
            "mutability": "write",
            "handler_name": "_apply_world_model_proposal_resolution",
        },
        "apply_pending_action_route_approval_opt_in": {
            "tool_name": "apply_pending_action_route_approval_opt_in",
            "adapter_type": "static",
            "category": "preflight",
            "mutability": "write",
            "handler_name": "_apply_pending_action_route_approval_opt_in",
        },
        "record_agent_knowledge_base_candidate": {
            "tool_name": "record_agent_knowledge_base_candidate",
            "adapter_type": "static",
            "category": "knowledge_base",
            "mutability": "guarded_write",
            "handler_name": "_record_agent_knowledge_base_candidate",
            "write_policy": "approval_required_redirect",
        },
        "execute_record_agent_knowledge_base_candidate_with_approval": {
            "tool_name": "execute_record_agent_knowledge_base_candidate_with_approval",
            "adapter_type": "static",
            "category": "knowledge_base",
            "mutability": "write",
            "handler_name": "_execute_record_agent_knowledge_base_candidate_with_approval",
        },
        "repair_longform_maintenance": {
            "tool_name": "repair_longform_maintenance",
            "adapter_type": "static",
            "category": "maintenance",
            "mutability": "guarded_write",
            "handler_name": "_repair_longform_maintenance",
            "write_policy": "approval_required_redirect",
        },
        "execute_repair_longform_maintenance_with_approval": {
            "tool_name": "execute_repair_longform_maintenance_with_approval",
            "adapter_type": "static",
            "category": "maintenance",
            "mutability": "write",
            "handler_name": "_execute_repair_longform_maintenance_with_approval",
        },
        "execute_longform_chapter_batch_preflight": {
            "tool_name": "execute_longform_chapter_batch_preflight",
            "adapter_type": "static",
            "category": "task_queue",
            "mutability": "guarded_write",
            "handler_name": "_execute_longform_chapter_batch_preflight",
            "write_policy": "approval_required_redirect",
        },
        "execute_longform_chapter_batch_preflight_with_approval": {
            "tool_name": "execute_longform_chapter_batch_preflight_with_approval",
            "adapter_type": "static",
            "category": "task_queue",
            "mutability": "write",
            "handler_name": "_execute_longform_chapter_batch_preflight_with_approval",
        },
        "prepare_longform_chapter_batch_execution": {
            "tool_name": "prepare_longform_chapter_batch_execution",
            "adapter_type": "static",
            "category": "task_queue",
            "mutability": "guarded_write",
            "handler_name": "_prepare_longform_chapter_batch_execution",
            "write_policy": "approval_required_redirect",
        },
        "execute_longform_chapter_batch_execution_prepare_with_approval": {
            "tool_name": "execute_longform_chapter_batch_execution_prepare_with_approval",
            "adapter_type": "static",
            "category": "task_queue",
            "mutability": "write",
            "handler_name": "_execute_longform_chapter_batch_execution_prepare_with_approval",
        },
        "review_longform_chapter_batch_execution": {
            "tool_name": "review_longform_chapter_batch_execution",
            "adapter_type": "static",
            "category": "task_queue",
            "mutability": "guarded_write",
            "handler_name": "_review_longform_chapter_batch_execution",
            "write_policy": "approval_required_redirect",
        },
        "execute_longform_chapter_batch_execution_review_with_approval": {
            "tool_name": "execute_longform_chapter_batch_execution_review_with_approval",
            "adapter_type": "static",
            "category": "task_queue",
            "mutability": "write",
            "handler_name": "_execute_longform_chapter_batch_execution_review_with_approval",
        },
    }

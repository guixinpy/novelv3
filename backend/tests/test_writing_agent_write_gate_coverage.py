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


def test_write_gate_coverage_marks_generate_chapter_as_indirectly_covered_direct_gap():
    output = inspect_agent_write_gate_coverage(adapter_metadata_by_name=_adapter_metadata())
    generate_tool = _tools_by_name(output)["generate_chapter"]

    assert generate_tool["agent_plan_gate_status"] == "indirect_agent_gate_available"
    assert generate_tool["direct_confirmation_guard"] is False
    assert generate_tool["risk_level"] == "high"
    assert {item["consumer_tool"] for item in generate_tool["indirect_coverage"]} >= {
        "execute_generate_chapter_with_approval",
        "execute_longform_chapter_batch",
    }
    assert generate_tool["recommended_action"] == "add_direct_agent_plan_approval_gate"


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
        assert generate_tool["direct_confirmation_guard"] is False
        assert generate_tool["risk_level"] == "high"
        assert {item["consumer_tool"] for item in generate_tool["indirect_coverage"]} == {consumer_tool}
        assert generate_tool["recommended_action"] == "add_direct_agent_plan_approval_gate"


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

    preflight_tool = tools_by_name["execute_longform_chapter_batch_preflight"]
    assert preflight_tool["agent_plan_gate_status"] == "missing_agent_plan_gate"
    assert preflight_tool["direct_confirmation_guard"] is True
    assert preflight_tool["confirmation_fields"] == ["confirm_checkpoint"]
    assert preflight_tool["risk_level"] == "medium"

    prepare_tool = tools_by_name["prepare_longform_chapter_batch_execution"]
    assert prepare_tool["agent_plan_gate_status"] == "missing_agent_plan_gate"
    assert prepare_tool["direct_confirmation_guard"] is True
    assert prepare_tool["confirmation_fields"] == ["confirm_prepare"]
    assert prepare_tool["risk_level"] == "medium"

    review_tool = tools_by_name["review_longform_chapter_batch_execution"]
    assert review_tool["agent_plan_gate_status"] == "missing_agent_plan_gate"
    assert review_tool["direct_confirmation_guard"] is True
    assert review_tool["confirmation_fields"] == ["confirm_review"]
    assert review_tool["risk_level"] == "medium"


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
            "mutability": "write",
            "handler_name": "_generate_chapter",
        },
        "execute_longform_chapter_batch": {
            "tool_name": "execute_longform_chapter_batch",
            "adapter_type": "static",
            "category": "task_queue",
            "mutability": "write",
            "handler_name": "_execute_longform_chapter_batch",
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
            "mutability": "write",
            "handler_name": "_generate_setup",
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
            "mutability": "write",
            "handler_name": "_generate_storyline",
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
            "mutability": "write",
            "handler_name": "_generate_outline",
        },
        "execute_generate_outline_with_approval": {
            "tool_name": "execute_generate_outline_with_approval",
            "adapter_type": "static",
            "category": "generation",
            "mutability": "write",
            "handler_name": "_execute_generate_outline_with_approval",
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
            "mutability": "write",
            "handler_name": "_execute_longform_chapter_batch_preflight",
        },
        "prepare_longform_chapter_batch_execution": {
            "tool_name": "prepare_longform_chapter_batch_execution",
            "adapter_type": "static",
            "category": "task_queue",
            "mutability": "write",
            "handler_name": "_prepare_longform_chapter_batch_execution",
        },
        "review_longform_chapter_batch_execution": {
            "tool_name": "review_longform_chapter_batch_execution",
            "adapter_type": "static",
            "category": "task_queue",
            "mutability": "write",
            "handler_name": "_review_longform_chapter_batch_execution",
        },
    }

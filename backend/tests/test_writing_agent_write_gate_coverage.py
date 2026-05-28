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
    }

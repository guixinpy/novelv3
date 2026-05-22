from app.services.writing_agent.approval_contract import build_agent_plan_approval_contract


def test_approval_contract_requires_confirmation_for_write_steps():
    plan = {
        "trace": {
            "plan_id": "plan:abc",
            "source_projection_id": "projection:1",
            "planner_version": "phase53.context_gate.v1",
        },
        "steps": [
            {
                "step_index": 1,
                "step_id": "step:read",
                "tool_name": "describe_agent_tools",
                "params": {},
                "mutability": "read",
                "requires_confirmation": False,
            },
            {
                "step_index": 2,
                "step_id": "step:write",
                "tool_name": "generate_chapter",
                "params": {"chapter_index": 2},
                "mutability": "write",
                "requires_confirmation": True,
                "reason": "生成第2章。",
            },
        ],
    }

    contract = build_agent_plan_approval_contract(plan)

    assert contract["status"] == "requires_confirmation"
    assert contract["version"] == "phase108.agent_plan_approval_contract.v1"
    assert contract["plan_id"] == "plan:abc"
    assert contract["source_projection_id"] == "projection:1"
    assert contract["write_step_count"] == 1
    assert contract["write_steps"][0] == {
        "step_index": 2,
        "step_id": "step:write",
        "tool_name": "generate_chapter",
        "params": {"chapter_index": 2},
        "mutability": "write",
        "requires_confirmation": True,
        "reason": "生成第2章。",
    }
    assert contract["approval"]["required"] is True
    assert contract["approval"]["approval_contract_hash"].startswith("approval:")
    assert contract["approval"]["confirmation_param"] == "approval_contract_hash"


def test_approval_contract_is_not_required_for_read_only_plan():
    plan = {
        "trace": {
            "plan_id": "plan:read",
            "source_projection_id": None,
            "planner_version": "phase53.context_gate.v1",
        },
        "steps": [
            {
                "step_index": 1,
                "step_id": "step:read",
                "tool_name": "review_chapter_quality",
                "params": {"chapter_index": 2},
                "mutability": "read",
                "requires_confirmation": False,
            },
        ],
    }

    contract = build_agent_plan_approval_contract(plan)

    assert contract["status"] == "not_required"
    assert contract["write_steps"] == []
    assert contract["approval"]["required"] is False
    assert contract["approval"]["approval_contract_hash"].startswith("approval:")


def test_approval_contract_hash_changes_when_write_params_change():
    base_plan = {
        "trace": {"plan_id": "plan:abc", "source_projection_id": None, "planner_version": "phase53.context_gate.v1"},
        "steps": [
            {
                "step_index": 1,
                "step_id": "step:write",
                "tool_name": "generate_chapter",
                "params": {"chapter_index": 2},
                "mutability": "write",
                "requires_confirmation": True,
            },
        ],
    }
    changed_plan = {
        **base_plan,
        "steps": [{**base_plan["steps"][0], "params": {"chapter_index": 3}}],
    }

    base_contract = build_agent_plan_approval_contract(base_plan)
    changed_contract = build_agent_plan_approval_contract(changed_plan)

    assert base_contract["approval"]["approval_contract_hash"] != changed_contract["approval"]["approval_contract_hash"]


def test_approval_contract_rejects_invalid_plan():
    contract = build_agent_plan_approval_contract(None)

    assert contract["status"] == "invalid_plan"
    assert contract["approval"]["required"] is False
    assert contract["write_step_count"] == 0

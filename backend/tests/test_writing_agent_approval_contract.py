from app.services.writing_agent.approval_contract import (
    build_agent_plan_approval_contract,
    verify_agent_plan_approval_contract,
)


def test_approval_contract_requires_confirmation_for_write_steps():
    plan = {
        "project_id": "project-1",
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
    step = contract["write_steps"][0]
    assert {
        key: value for key, value in step.items() if key != "mutation_fingerprint"
    } == {
        "step_index": 2,
        "step_id": "step:write",
        "tool_name": "generate_chapter",
        "params": {"chapter_index": 2},
        "mutability": "write",
        "requires_confirmation": True,
        "reason": "生成第2章。",
    }
    assert step["mutation_fingerprint"]["components"]["project_id"] == "project-1"
    assert step["mutation_fingerprint"]["components"]["target_id"] == "chapter:2"
    assert contract["approval"]["required"] is True
    assert contract["approval"]["approval_contract_hash"].startswith("approval:")
    assert contract["approval"]["confirmation_param"] == "approval_contract_hash"


def test_approval_contract_attaches_mutation_fingerprint_to_write_steps():
    plan = _write_plan(project_id="project-1")

    contract = build_agent_plan_approval_contract(plan)

    fingerprint = contract["write_steps"][0]["mutation_fingerprint"]
    assert fingerprint["status"] == "ready"
    assert fingerprint["components"]["target_id"] == "chapter:2"
    assert len(fingerprint["fingerprint"]) == 64


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


def test_verify_approval_contract_accepts_matching_hash():
    plan = _write_plan(project_id="project-1")
    contract = build_agent_plan_approval_contract(plan)

    result = verify_agent_plan_approval_contract(
        plan,
        approval_contract_hash=contract["approval"]["approval_contract_hash"],
        approval_contract=contract,
        project_id="project-1",
    )

    assert result["status"] == "ready"
    assert result["reason"] == "approval_contract_verified"
    assert result["current_contract"] == contract
    assert result["drift"]["hash_matches"] is True
    assert result["drift"]["project_matches"] is True
    assert result["recommended_next_tools"] == []


def test_verify_approval_contract_checks_write_step_tool_contracts():
    plan = _write_plan(project_id="project-1")
    contract = build_agent_plan_approval_contract(plan)

    result = verify_agent_plan_approval_contract(
        plan,
        approval_contract_hash=contract["approval"]["approval_contract_hash"],
        approval_contract=contract,
        project_id="project-1",
        tool_metadata_by_name={
            "generate_chapter": {
                "tool_exists": True,
                "adapter_exists": True,
                "mutability": "write",
                "requires_confirmation": True,
                "required_fields": ["chapter_index"],
            }
        },
    )

    assert result["status"] == "ready"
    assert result["reason"] == "approval_contract_verified"
    assert result["drift"]["tool_contracts_checked"] is True
    assert result["drift"]["tool_contract_drift_count"] == 0
    assert result["drift"]["tool_contracts"] == [
        {
            "step_id": "step:write",
            "tool_name": "generate_chapter",
            "tool_exists": True,
            "adapter_exists": True,
            "current_mutability": "write",
            "current_requires_confirmation": True,
            "required_fields": ["chapter_index"],
            "missing_required_fields": [],
            "status": "ready",
            "reasons": [],
        }
    ]


def test_verify_approval_contract_blocks_missing_required_step_params():
    plan = _write_plan(project_id="project-1")
    plan["steps"][0]["params"] = {}
    contract = build_agent_plan_approval_contract(plan)

    result = verify_agent_plan_approval_contract(
        plan,
        approval_contract_hash=contract["approval"]["approval_contract_hash"],
        approval_contract=contract,
        project_id="project-1",
        tool_metadata_by_name={
            "generate_chapter": {
                "tool_exists": True,
                "adapter_exists": True,
                "mutability": "write",
                "requires_confirmation": True,
                "required_fields": ["chapter_index"],
            }
        },
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "tool_contract_drift"
    assert result["drift"]["tool_contract_drift_count"] == 1
    assert result["drift"]["tool_contracts"][0]["missing_required_fields"] == ["chapter_index"]
    assert "missing_required_fields" in result["drift"]["tool_contracts"][0]["reasons"]
    assert result["recommended_next_tools"] == ["inspect_agent_tool_contracts"]


def test_verify_approval_contract_blocks_when_mutation_fingerprint_not_ready():
    plan = _write_plan(project_id="project-1")
    plan["steps"][0]["params"] = {}
    contract = build_agent_plan_approval_contract(plan)

    result = verify_agent_plan_approval_contract(
        plan,
        approval_contract_hash=contract["approval"]["approval_contract_hash"],
        approval_contract=contract,
        project_id="project-1",
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "mutation_fingerprint_not_ready"
    assert result["drift"]["mutation_fingerprint_drift_count"] == 1
    assert result["recommended_next_tools"] == ["inspect_agent_mutation_fingerprints"]


def test_verify_approval_contract_blocks_missing_tool_or_adapter():
    plan = _write_plan(project_id="project-1")
    contract = build_agent_plan_approval_contract(plan)

    result = verify_agent_plan_approval_contract(
        plan,
        approval_contract_hash=contract["approval"]["approval_contract_hash"],
        approval_contract=contract,
        project_id="project-1",
        tool_metadata_by_name={},
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "tool_contract_drift"
    assert result["drift"]["tool_contract_drift_count"] == 1
    assert result["drift"]["tool_contracts"][0]["tool_exists"] is False
    assert result["drift"]["tool_contracts"][0]["adapter_exists"] is False
    assert "tool_missing" in result["drift"]["tool_contracts"][0]["reasons"]
    assert "adapter_missing" in result["drift"]["tool_contracts"][0]["reasons"]


def test_verify_approval_contract_blocks_when_tool_no_longer_requires_confirmation():
    plan = _write_plan(project_id="project-1")
    contract = build_agent_plan_approval_contract(plan)

    result = verify_agent_plan_approval_contract(
        plan,
        approval_contract_hash=contract["approval"]["approval_contract_hash"],
        approval_contract=contract,
        project_id="project-1",
        tool_metadata_by_name={
            "generate_chapter": {
                "tool_exists": True,
                "adapter_exists": True,
                "mutability": "read",
                "requires_confirmation": False,
                "required_fields": ["chapter_index"],
            }
        },
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "tool_contract_drift"
    assert result["drift"]["tool_contract_drift_count"] == 1
    assert result["drift"]["tool_contracts"][0]["current_mutability"] == "read"
    assert result["drift"]["tool_contracts"][0]["current_requires_confirmation"] is False
    assert result["drift"]["tool_contracts"][0]["reasons"] == ["mutability_no_longer_write", "confirmation_not_required"]


def test_verify_approval_contract_blocks_hash_mismatch():
    plan = _write_plan(project_id="project-1")

    result = verify_agent_plan_approval_contract(
        plan,
        approval_contract_hash="approval:bad",
        project_id="project-1",
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "approval_contract_hash_mismatch"
    assert result["drift"]["hash_matches"] is False
    assert result["recommended_next_tools"] == ["preview_agent_plan_approval_contract"]


def test_verify_approval_contract_blocks_snapshot_mismatch():
    plan = _write_plan(project_id="project-1")
    contract = build_agent_plan_approval_contract(plan)
    stale_contract = {
        **contract,
        "approval": {**contract["approval"], "approval_contract_hash": "approval:stale"},
    }

    result = verify_agent_plan_approval_contract(
        plan,
        approval_contract_hash=contract["approval"]["approval_contract_hash"],
        approval_contract=stale_contract,
        project_id="project-1",
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "approval_contract_snapshot_mismatch"
    assert result["drift"]["snapshot_hash_matches"] is False


def test_verify_approval_contract_returns_not_required_for_read_only_plan():
    plan = {
        "project_id": "project-1",
        "trace": {"plan_id": "plan:read", "source_projection_id": None, "planner_version": "phase53.context_gate.v1"},
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

    result = verify_agent_plan_approval_contract(plan, project_id="project-1")

    assert result["status"] == "not_required"
    assert result["reason"] == "approval_contract_not_required"
    assert result["drift"]["hash_matches"] is None


def _write_plan(project_id: str) -> dict:
    return {
        "project_id": project_id,
        "intent_class": "continue_next_chapter",
        "trace": {
            "plan_id": "plan:abc",
            "source_projection_id": "projection:1",
            "planner_version": "phase53.context_gate.v1",
        },
        "steps": [
            {
                "step_index": 1,
                "step_id": "step:write",
                "tool_name": "generate_chapter",
                "params": {"chapter_index": 2},
                "mutability": "write",
                "requires_confirmation": True,
                "reason": "生成第2章。",
            },
        ],
    }

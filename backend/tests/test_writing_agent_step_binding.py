from app.services.writing_agent.agent_step_binding import build_agent_step_binding, verify_resource_binding_target
from app.services.writing_agent.mutation_fingerprint import build_mutation_fingerprint


def _chapter_fingerprint(chapter_index: int = 2) -> dict:
    return build_mutation_fingerprint("project-1", "generate_chapter", {"chapter_index": chapter_index})


def test_agent_step_binding_is_stable_for_same_write_step():
    step = {
        "step_index": 1,
        "step_id": "step:write",
        "tool_name": "generate_chapter",
        "params": {"chapter_index": 2},
    }

    first = build_agent_step_binding(
        project_id="project-1",
        plan_id="plan:abc",
        source_projection_id="projection:1",
        step=step,
        mutation_fingerprint=_chapter_fingerprint(),
    )
    second = build_agent_step_binding(
        project_id="project-1",
        plan_id="plan:abc",
        source_projection_id="projection:1",
        step=step,
        mutation_fingerprint=_chapter_fingerprint(),
    )

    assert first["tool_call_id"] == second["tool_call_id"]
    assert first["tool_call_id"].startswith("toolcall:")
    assert first["resource_binding"] == second["resource_binding"]


def test_agent_step_binding_uses_mutation_target_for_chapter_resource():
    binding = build_agent_step_binding(
        project_id="project-1",
        plan_id="plan:abc",
        source_projection_id="projection:1",
        step={
            "step_index": 1,
            "step_id": "step:write",
            "tool_name": "generate_chapter",
            "params": {"chapter_index": 2},
        },
        mutation_fingerprint=_chapter_fingerprint(),
    )

    resource = binding["resource_binding"]
    assert resource["binding_source"] == "server_derived"
    assert resource["project_id"] == "project-1"
    assert resource["source_plan_id"] == "plan:abc"
    assert resource["source_projection_id"] == "projection:1"
    assert resource["source_step_id"] == "step:write"
    assert resource["tool_name"] == "generate_chapter"
    assert resource["target_type"] == "chapter"
    assert resource["target_id"] == "chapter:2"


def test_agent_step_binding_changes_when_step_identity_changes():
    base = {
        "step_index": 1,
        "step_id": "step:write",
        "tool_name": "generate_chapter",
        "params": {"chapter_index": 2},
    }
    changed = {**base, "step_id": "step:write:changed"}

    first = build_agent_step_binding(
        project_id="project-1",
        plan_id="plan:abc",
        source_projection_id="projection:1",
        step=base,
        mutation_fingerprint=_chapter_fingerprint(),
    )
    second = build_agent_step_binding(
        project_id="project-1",
        plan_id="plan:abc",
        source_projection_id="projection:1",
        step=changed,
        mutation_fingerprint=_chapter_fingerprint(),
    )

    assert first["tool_call_id"] != second["tool_call_id"]


def test_verify_resource_binding_target_accepts_matching_write_target():
    verification = _verification_with_bindings(
        [
            {
                "tool_call_id": "toolcall:test",
                "tool_name": "generate_chapter",
                "target_type": "chapter",
                "target_id": "chapter:2",
                "source_plan_id": "plan:abc",
                "source_step_id": "step:write",
                "binding_source": "server_derived",
            }
        ]
    )

    result = verify_resource_binding_target(
        verification,
        tool_name="generate_chapter",
        target_type="chapter",
        target_id="chapter:2",
    )

    assert result == {
        "status": "ready",
        "reason": "resource_binding_verified",
        "expected": {
            "tool_name": "generate_chapter",
            "target_type": "chapter",
            "target_id": "chapter:2",
        },
        "tool_call_id": "toolcall:test",
        "resource_binding": {
            "tool_call_id": "toolcall:test",
            "tool_name": "generate_chapter",
            "target_type": "chapter",
            "target_id": "chapter:2",
            "source_plan_id": "plan:abc",
            "source_step_id": "step:write",
            "binding_source": "server_derived",
        },
        "resource_bindings": [
            {
                "tool_call_id": "toolcall:test",
                "tool_name": "generate_chapter",
                "target_type": "chapter",
                "target_id": "chapter:2",
                "source_plan_id": "plan:abc",
                "source_step_id": "step:write",
                "binding_source": "server_derived",
            }
        ],
    }


def test_verify_resource_binding_target_blocks_mismatched_write_target():
    result = verify_resource_binding_target(
        _verification_with_bindings(
            [
                {
                    "tool_call_id": "toolcall:wrong",
                    "tool_name": "generate_chapter",
                    "target_type": "chapter",
                    "target_id": "chapter:3",
                    "source_plan_id": "plan:abc",
                    "source_step_id": "step:write",
                    "binding_source": "server_derived",
                }
            ]
        ),
        tool_name="generate_chapter",
        target_type="chapter",
        target_id="chapter:2",
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "resource_binding_target_mismatch"
    assert result["expected"]["target_id"] == "chapter:2"
    assert result["resource_bindings"][0]["target_id"] == "chapter:3"


def test_verify_resource_binding_target_blocks_missing_write_binding():
    result = verify_resource_binding_target(
        _verification_with_bindings([]),
        tool_name="generate_chapter",
        target_type="chapter",
        target_id="chapter:2",
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "resource_binding_missing"
    assert result["expected"] == {
        "tool_name": "generate_chapter",
        "target_type": "chapter",
        "target_id": "chapter:2",
    }


def _verification_with_bindings(resource_bindings: list[dict]) -> dict:
    return {
        "status": "ready",
        "drift": {
            "resource_bindings": resource_bindings,
        },
    }

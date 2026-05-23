from app.services.writing_agent.agent_step_binding import build_agent_step_binding
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

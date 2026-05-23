from app.services.writing_agent.mutation_fingerprint import (
    build_mutation_fingerprint,
    inspect_agent_mutation_fingerprints,
)


def test_build_mutation_fingerprint_is_stable_for_generate_chapter():
    first = build_mutation_fingerprint("project-1", "generate_chapter", {"chapter_index": "2"})
    second = build_mutation_fingerprint("project-1", "generate_chapter", {"chapter_index": 2})

    assert first["status"] == "ready"
    assert first["mutating"] is True
    assert first["fingerprint"] == second["fingerprint"]
    assert len(first["fingerprint"]) == 64
    assert first["components"]["action"] == "generate_chapter"
    assert first["components"]["target_type"] == "chapter"
    assert first["components"]["target_id"] == "chapter:2"


def test_build_mutation_fingerprint_distinguishes_chapter_targets():
    chapter_two = build_mutation_fingerprint("project-1", "generate_chapter", {"chapter_index": 2})
    chapter_three = build_mutation_fingerprint("project-1", "generate_chapter", {"chapter_index": 3})

    assert chapter_two["fingerprint"] != chapter_three["fingerprint"]
    assert chapter_three["components"]["target_id"] == "chapter:3"


def test_inspect_agent_mutation_fingerprints_reports_missing_range_target():
    output = inspect_agent_mutation_fingerprints(
        "project-1",
        [{"tool_name": "generate_chapter_range", "params": {"start_chapter": 5}}],
    )

    assert output["status"] == "blocked"
    assert output["fingerprints"][0]["status"] == "blocked"
    assert output["fingerprints"][0]["fingerprint"] is None
    assert output["fingerprints"][0]["diagnostics"][0]["code"] == "missing_target"


def test_build_mutation_fingerprint_covers_world_model_bundle():
    result = build_mutation_fingerprint(
        "project-1",
        "apply_world_model_proposal_resolution",
        {"proposal_bundle_id": "bundle-1"},
    )

    assert result["status"] == "ready"
    assert result["components"]["target_type"] == "world_model_proposal_bundle"
    assert result["components"]["target_id"] == "world_model_proposal_bundle:bundle-1"

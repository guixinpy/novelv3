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


def test_build_mutation_fingerprint_covers_planner_revision_patch():
    first = build_mutation_fingerprint(
        "project-1",
        "apply_planner_revision_patch",
        {"chapter_index": "2", "revision_id": "revision-1"},
    )
    second = build_mutation_fingerprint(
        "project-1",
        "apply_planner_revision_patch",
        {"chapter_index": 2, "revision_id": "revision-1"},
    )

    assert first["status"] == "ready"
    assert first["mutating"] is True
    assert first["fingerprint"] == second["fingerprint"]
    assert first["components"]["target_type"] == "chapter_revision_patch"
    assert first["components"]["target_id"] == "chapter_revision_patch:2:revision-1"


def test_build_mutation_fingerprint_covers_knowledge_base_candidate():
    first = build_mutation_fingerprint(
        "project-1",
        "record_agent_knowledge_base_candidate",
        {
            "memory_type": "self_optimization_lesson",
            "title": "低细节续写可行",
            "summary": "先读取知识库、长篇记忆、世界模型和 preflight 后，低细节目标也能续写。",
            "source_refs": ["chapter:24", "dogfood:phase77"],
        },
    )
    second = build_mutation_fingerprint(
        "project-1",
        "record_agent_knowledge_base_candidate",
        {
            "memory_type": "self_optimization_lesson",
            "title": "低细节续写可行",
            "summary": "先读取知识库、长篇记忆、世界模型和 preflight 后，低细节目标也能续写。",
            "source_refs": ["dogfood:phase77", "chapter:24"],
            "confidence": 0.91,
        },
    )

    assert first["status"] == "ready"
    assert first["mutating"] is True
    assert first["fingerprint"] == second["fingerprint"]
    assert first["components"]["target_type"] == "agent_knowledge_base_candidate"
    assert first["components"]["target_id"].startswith("agent_knowledge_base_candidate:")


def test_build_mutation_fingerprint_blocks_knowledge_base_candidate_without_sources():
    result = build_mutation_fingerprint(
        "project-1",
        "record_agent_knowledge_base_candidate",
        {
            "memory_type": "writing_pattern",
            "title": "章末钩子",
            "summary": "保持章节末尾的下一步行动压力。",
            "source_refs": [],
        },
    )

    assert result["status"] == "blocked"
    assert result["fingerprint"] is None
    assert result["components"]["target_type"] == "agent_knowledge_base_candidate"
    assert result["diagnostics"] == [
        {
            "code": "missing_target",
            "message": "record_agent_knowledge_base_candidate requires memory_type, title, summary, and source_refs",
        }
    ]


def test_build_mutation_fingerprint_blocks_planner_revision_patch_without_revision_id():
    result = build_mutation_fingerprint("project-1", "apply_planner_revision_patch", {"chapter_index": 2})

    assert result["status"] == "blocked"
    assert result["fingerprint"] is None
    assert result["components"]["target_type"] == "chapter_revision_patch"
    assert result["diagnostics"] == [
        {
            "code": "missing_target",
            "message": "apply_planner_revision_patch requires a positive chapter_index and revision_id",
        }
    ]

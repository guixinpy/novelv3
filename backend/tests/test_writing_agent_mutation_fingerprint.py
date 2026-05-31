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
    approved = build_mutation_fingerprint(
        "project-1",
        "execute_apply_world_model_proposal_resolution_with_approval",
        {"proposal_bundle_id": "bundle-1"},
    )

    assert result["status"] == "ready"
    assert result["components"]["target_type"] == "world_model_proposal_bundle"
    assert result["components"]["target_id"] == "world_model_proposal_bundle:bundle-1"
    assert approved["status"] == "ready"
    assert approved["components"]["target_id"] == result["components"]["target_id"]


def test_build_mutation_fingerprint_covers_continuity_anchor_seed():
    direct = build_mutation_fingerprint("project-1", "seed_continuity_anchor_proposals", {})
    approved = build_mutation_fingerprint("project-1", "execute_seed_continuity_anchor_proposals_with_approval", {})

    assert direct["status"] == "ready"
    assert direct["mutating"] is True
    assert direct["components"]["target_type"] == "world_model_continuity_anchor_seed"
    assert direct["components"]["target_id"] == "world_model_continuity_anchor_seed:project-1"
    assert approved["status"] == "ready"
    assert approved["components"]["target_id"] == direct["components"]["target_id"]


def test_build_mutation_fingerprint_covers_longform_batch_enqueue():
    direct = build_mutation_fingerprint(
        "project-1",
        "enqueue_longform_chapter_batch",
        {"plan_hash": "plan-1", "start_chapter": 2, "batch_size": 2},
    )
    approved = build_mutation_fingerprint(
        "project-1",
        "execute_enqueue_longform_chapter_batch_with_approval",
        {"plan_hash": "plan-1"},
    )

    assert direct["status"] == "ready"
    assert direct["mutating"] is True
    assert direct["components"]["target_type"] == "background_task_enqueue"
    assert direct["components"]["target_id"] == "background_task_enqueue:project-1:plan-1"
    assert approved["status"] == "ready"
    assert approved["components"]["target_id"] == direct["components"]["target_id"]


def test_build_mutation_fingerprint_covers_longform_batch_preflight_checkpoint():
    direct = build_mutation_fingerprint(
        "project-1",
        "execute_longform_chapter_batch_preflight",
        {"task_id": "task-1", "max_chapters": 1},
    )
    approved = build_mutation_fingerprint(
        "project-1",
        "execute_longform_chapter_batch_preflight_with_approval",
        {"task_id": "task-1"},
    )

    assert direct["status"] == "ready"
    assert direct["mutating"] is True
    assert direct["components"]["target_type"] == "background_task_checkpoint"
    assert direct["components"]["target_id"] == "background_task_checkpoint:task-1:preflight"
    assert approved["status"] == "ready"
    assert approved["components"]["target_id"] == direct["components"]["target_id"]


def test_build_mutation_fingerprint_covers_longform_batch_execution_prepare():
    direct = build_mutation_fingerprint(
        "project-1",
        "prepare_longform_chapter_batch_execution",
        {"task_id": "task-1"},
    )
    approved = build_mutation_fingerprint(
        "project-1",
        "execute_longform_chapter_batch_execution_prepare_with_approval",
        {"task_id": "task-1"},
    )

    assert direct["status"] == "ready"
    assert direct["mutating"] is True
    assert direct["components"]["target_type"] == "background_task_execution_prepare"
    assert direct["components"]["target_id"] == "background_task_execution_prepare:task-1"
    assert approved["status"] == "ready"
    assert approved["components"]["target_id"] == direct["components"]["target_id"]


def test_build_mutation_fingerprint_covers_longform_batch_execution_review():
    direct = build_mutation_fingerprint(
        "project-1",
        "review_longform_chapter_batch_execution",
        {"task_id": "task-1", "lookback": 12},
    )
    approved = build_mutation_fingerprint(
        "project-1",
        "execute_longform_chapter_batch_execution_review_with_approval",
        {"task_id": "task-1"},
    )

    assert direct["status"] == "ready"
    assert direct["mutating"] is True
    assert direct["components"]["target_type"] == "background_task_post_generation_review"
    assert direct["components"]["target_id"] == "background_task_post_generation_review:task-1"
    assert approved["status"] == "ready"
    assert approved["components"]["target_id"] == direct["components"]["target_id"]


def test_build_mutation_fingerprint_covers_longform_batch_after_review_route():
    direct = build_mutation_fingerprint(
        "project-1",
        "route_longform_chapter_batch_after_review",
        {"task_id": "task-1", "expected_post_generation_review_hash": "review-hash"},
    )
    approved = build_mutation_fingerprint(
        "project-1",
        "execute_longform_chapter_batch_after_review_route_with_approval",
        {"task_id": "task-1"},
    )

    assert direct["status"] == "ready"
    assert direct["mutating"] is True
    assert direct["components"]["target_type"] == "background_task_post_review_route"
    assert direct["components"]["target_id"] == "background_task_post_review_route:task-1"
    assert approved["status"] == "ready"
    assert approved["components"]["target_id"] == direct["components"]["target_id"]


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


def test_build_mutation_fingerprint_covers_chapter_revision_adjustments():
    expansion = build_mutation_fingerprint(
        "project-1",
        "expand_chapter_to_target",
        {"chapter_index": "2", "min_word_count": 2200},
    )
    approved_expansion = build_mutation_fingerprint(
        "project-1",
        "execute_expand_chapter_to_target_with_approval",
        {"chapter_index": "2", "min_word_count": 2200},
    )
    compression = build_mutation_fingerprint(
        "project-1",
        "compress_chapter_to_target",
        {"chapter_index": 3, "target_max_word_count": 2300},
    )

    assert expansion["status"] == "ready"
    assert expansion["components"]["target_type"] == "chapter_revision_adjustment"
    assert expansion["components"]["target_id"] == "chapter_revision_adjustment:expand_chapter_to_target:2"
    assert approved_expansion["components"]["target_id"] == expansion["components"]["target_id"]
    assert compression["status"] == "ready"
    assert compression["components"]["target_id"] == "chapter_revision_adjustment:compress_chapter_to_target:3"


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


def test_build_mutation_fingerprint_covers_longform_maintenance_repair():
    first = build_mutation_fingerprint("project-1", "repair_longform_maintenance", {"limit": "20"})
    second = build_mutation_fingerprint("project-1", "repair_longform_maintenance", {"repair_limit": 100})

    assert first["status"] == "ready"
    assert first["mutating"] is True
    assert first["fingerprint"] == second["fingerprint"]
    assert first["components"]["target_type"] == "longform_maintenance"
    assert first["components"]["target_id"] == "longform_maintenance:project-1"


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

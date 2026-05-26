from datetime import UTC, datetime, timedelta

from app.models import Project, PromptRule
from app.services.writing_agent.agent_knowledge_base_route import inspect_agent_knowledge_base_route
from app.services.writing_agent.agent_knowledge_base_candidates import record_agent_knowledge_base_candidate


def test_inspect_agent_knowledge_base_route_reports_sparse_project_memory(db_session):
    project = Project(name="Sparse Knowledge")
    db_session.add(project)
    db_session.commit()

    output = inspect_agent_knowledge_base_route(db_session, project.id, chapter_index=1)

    assert output["status"] == "completed"
    assert output["route"]["status"] == "sparse"
    assert output["route"]["reason"] == "knowledge_base_sparse"
    assert output["author_preferences"]["status"] == "empty"
    assert output["learned_rules"]["total"] == 0
    assert output["project_strategy"]["name"] == "Sparse Knowledge"
    assert "summarize_longform_context" in output["route"]["recommended_tools"]
    assert {"knowledge_base_sparse", "world_truth_boundary"}.issubset(
        {item["code"] for item in output["diagnostics"]}
    )
    assert output["memory_provenance"]["status"] == "sparse"
    _assert_memory_provenance_contract(output["memory_provenance"])
    assert output["memory_provenance"]["recovery"] == {
        "status": "none",
        "reason": "knowledge_base_sparse",
        "next_tools": [],
        "tools": [],
    }
    assert output["memory_provenance"]["boundaries"]["world_truth"]["status"] == "separated"
    assert output["memory_provenance"]["boundaries"]["world_truth"]["canonical_source"] == "Athena/world_model"
    assert output["memory_provenance"]["sources"][0]["source_ref"] == "Project"


def test_inspect_agent_knowledge_base_route_projects_preferences_rules_and_patterns(db_session):
    project = Project(
        name="Configured Knowledge",
        description="面向长篇连载的雾港记忆悬疑。",
        genre="末世悬疑",
        target_chapter_count=600,
        target_word_count=1_200_000,
        style="冷峻、克制、强钩子",
        complexity=4,
        style_config={
            "description_density": 4,
            "dialogue_ratio": 3,
            "pacing_speed": 4,
            "tone_preferences": ["冷峻", "悬疑"],
        },
    )
    db_session.add(project)
    db_session.flush()
    db_session.add_all(
        [
            PromptRule(
                project_id=project.id,
                rule_type="learned",
                condition="用户反馈章节像大纲",
                action="增加场景动作和角色即时反应",
                priority=90,
            ),
            PromptRule(
                project_id=project.id,
                rule_type="style",
                condition="always",
                action="保留短句",
                priority=10,
            ),
        ]
    )
    db_session.commit()

    output = inspect_agent_knowledge_base_route(
        db_session,
        project.id,
        chapter_index=8,
        query="下一章需要保持雾港悬疑节奏",
    )

    assert output["route"]["status"] == "ready"
    assert output["route"]["reason"] == "knowledge_base_available"
    assert output["author_preferences"]["status"] == "configured"
    assert output["author_preferences"]["style_config"]["description_density"] == 4
    assert output["project_strategy"]["target_chapter_count"] == 600
    assert output["learned_rules"]["total"] == 1
    assert output["learned_rules"]["items"][0]["condition"] == "用户反馈章节像大纲"
    assert output["reference_patterns"]["available"] is True
    assert output["reference_patterns"]["task_type"] == "chapter"
    assert output["reference_patterns"]["genre"] == "末世悬疑"
    provenance = output["memory_provenance"]
    _assert_memory_provenance_contract(provenance)
    assert provenance["status"] == "available"
    assert provenance["source_count"] >= 4
    assert {
        "Project.style_config",
        "Project",
        "PromptRule(rule_type=learned)",
        "FewShotExampleLibrary",
    }.issubset({source["source_ref"] for source in provenance["sources"]})
    assert provenance["windows"]["learned_rules"] == {
        "total": 1,
        "returned": 1,
        "limit": 20,
        "has_more": False,
    }
    assert output["trace"]["mutability"] == "read"


def test_inspect_agent_knowledge_base_route_bounds_learned_rule_window(db_session):
    project = Project(name="Bounded Knowledge", style_config={"description_density": 3})
    db_session.add(project)
    db_session.flush()
    base_time = datetime(2026, 1, 1, tzinfo=UTC)
    db_session.add_all(
        [
            PromptRule(
                project_id=project.id,
                rule_type="learned",
                condition=f"规则 {index}",
                action=f"动作 {index}",
                priority=index,
                created_at=base_time + timedelta(minutes=index),
            )
            for index in range(12)
        ]
    )
    db_session.commit()

    output = inspect_agent_knowledge_base_route(db_session, project.id, limit=3)

    assert output["learned_rules"]["total"] == 12
    assert output["learned_rules"]["returned"] == 3
    assert output["learned_rules"]["limit"] == 3
    assert output["learned_rules"]["has_more"] is True
    assert output["learned_rules"]["items"][0]["condition"] == "规则 11"
    assert "learned_rules_truncated" in {item["code"] for item in output["diagnostics"]}
    assert output["memory_provenance"]["windows"]["learned_rules"] == {
        "total": 12,
        "returned": 3,
        "limit": 3,
        "has_more": True,
    }


def _assert_memory_provenance_contract(provenance):
    assert {
        "version",
        "status",
        "sources",
        "windows",
        "recovery",
        "trace",
    }.issubset(provenance)
    assert isinstance(provenance["sources"], list)
    assert isinstance(provenance["windows"], dict)
    assert isinstance(provenance["recovery"], dict)
    assert isinstance(provenance["trace"], dict)


def test_record_agent_knowledge_base_candidate_persists_candidate_and_updates_route(db_session):
    project = Project(name="Candidate Knowledge", style_config={"description_density": 3})
    db_session.add(project)
    db_session.commit()

    result = record_agent_knowledge_base_candidate(
        db_session,
        project.id,
        memory_type="self_optimization_lesson",
        title="低细节续写可行",
        summary="当 Agent 先读取知识库、长篇记忆、世界模型和 preflight 时，可以从低细节目标生成下一章。",
        source_refs=["docs/superpowers/notes/long-memory-agent/2026-05-20-phase77-dogfood-pre-generation-route.md", "chapter:24"],
        confidence=0.86,
        tags=["dogfood", "agent-route"],
    )

    assert result["status"] == "completed"
    assert result["action"] == "created"
    assert result["candidate"]["memory_type"] == "self_optimization_lesson"
    assert result["candidate"]["observed_count"] == 1
    assert result["trace"]["mutability"] == "write"

    db_session.refresh(project)
    candidates = project.style_config["knowledge_base_candidates"]
    assert len(candidates) == 1
    assert candidates[0]["title"] == "低细节续写可行"

    route = inspect_agent_knowledge_base_route(db_session, project.id, chapter_index=25)
    assert route["route"]["status"] == "ready"
    assert route["knowledge_candidates"]["total"] == 1
    assert route["knowledge_candidates"]["items"][0]["source_refs"] == [
        "docs/superpowers/notes/long-memory-agent/2026-05-20-phase77-dogfood-pre-generation-route.md",
        "chapter:24",
    ]


def test_record_agent_knowledge_base_candidate_deduplicates_by_fingerprint(db_session):
    project = Project(name="Candidate Dedup", style_config={})
    db_session.add(project)
    db_session.commit()

    first = record_agent_knowledge_base_candidate(
        db_session,
        project.id,
        memory_type="writing_pattern",
        title="章末钩子",
        summary="保持章节末尾的下一步行动压力。",
        source_refs=["chapter:24"],
        confidence=0.75,
    )
    second = record_agent_knowledge_base_candidate(
        db_session,
        project.id,
        memory_type="writing_pattern",
        title="章末钩子",
        summary="保持章节末尾的下一步行动压力。",
        source_refs=["chapter:24"],
        confidence=0.9,
    )

    assert first["action"] == "created"
    assert second["action"] == "updated"
    assert second["candidate"]["id"] == first["candidate"]["id"]
    assert second["candidate"]["observed_count"] == 2
    assert second["candidate"]["confidence"] == 0.9
    db_session.refresh(project)
    assert len(project.style_config["knowledge_base_candidates"]) == 1


def test_record_agent_knowledge_base_candidate_requires_source_refs(db_session):
    project = Project(name="Candidate Validation")
    db_session.add(project)
    db_session.commit()

    result = record_agent_knowledge_base_candidate(
        db_session,
        project.id,
        memory_type="project_strategy",
        title="长篇目标",
        summary="保持六百章长期稳定推进。",
        source_refs=[],
    )

    assert result["status"] == "failed"
    assert result["error"]["code"] == "missing_source_refs"

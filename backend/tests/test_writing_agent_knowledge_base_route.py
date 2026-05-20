from datetime import UTC, datetime, timedelta

from app.models import Project, PromptRule
from app.services.writing_agent.agent_knowledge_base_route import inspect_agent_knowledge_base_route


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

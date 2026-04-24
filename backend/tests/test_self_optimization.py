from app.core.self_optimization import apply_revision_optimization
from app.models import Project, PromptRule


def test_revision_optimization_creates_learned_rule_and_adjusts_preferences(db_session):
    project = Project(name="Test", style_config={"description_density": 3, "dialogue_ratio": 3})
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    result = apply_revision_optimization(
        db_session,
        project,
        annotations=[{"comment": "节奏太慢，描写太多"}],
        corrections=[{"original_text": "寒风凛冽", "corrected_text": "夜风微凉"}],
    )

    assert result["created_rules"] >= 1
    rules = db_session.query(PromptRule).filter(PromptRule.project_id == project.id, PromptRule.rule_type == "learned").all()
    assert any("节奏" in rule.condition for rule in rules)
    assert project.style_config["description_density"] == 2


def test_revision_optimization_keeps_preference_bounds(db_session):
    project = Project(name="Test", style_config={"description_density": 1, "dialogue_ratio": 5})
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    apply_revision_optimization(
        db_session,
        project,
        annotations=[{"comment": "节奏太慢，描写太多，对话不足"}],
        corrections=[],
    )

    assert project.style_config["description_density"] == 1
    assert project.style_config["dialogue_ratio"] == 5


def test_athena_optimization_endpoint_returns_rules_and_learning_logs(client, db_session):
    project = Project(name="Test", style_config={"description_density": 2, "dialogue_ratio": 3})
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add(
        PromptRule(
            project_id=project.id,
            rule_type="learned",
            condition="用户反馈节奏太慢",
            action="减少铺垫，加快场景推进",
            priority=80,
        )
    )
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}/athena/optimization")

    assert response.status_code == 200
    data = response.json()
    assert data["style_config"]["description_density"] == 2
    assert data["rules"][0]["condition"] == "用户反馈节奏太慢"
    assert data["learning_logs"][0]["rule_id"] == data["rules"][0]["id"]

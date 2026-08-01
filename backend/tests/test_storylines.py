"""情节线 CRUD 测试（v1 绞杀：generate 端点已删除）。"""
from app.models import Project, Storyline


def test_get_storyline_returns_stored(client, db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add(Storyline(
        project_id=project.id,
        plotlines=[{"title": "林舟案"}],
        foreshadowing=[],
        status="generated",
    ))
    db_session.commit()

    r = client.get(f"/api/v1/projects/{project.id}/storyline")
    assert r.status_code == 200
    assert r.json()["status"] == "generated"


def test_get_storyline_not_found(client):
    r = client.get("/api/v1/projects/nonexistent/storyline")
    assert r.status_code == 404

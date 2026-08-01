"""设定 CRUD 测试（v1 绞杀：generate 端点已删除）。"""
from app.models import Project, Setup


def test_get_setup_returns_stored_setup(client, db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add(Setup(
        project_id=project.id,
        world_building={},
        characters=[],
        core_concept={},
        status="generated",
    ))
    db_session.commit()

    r = client.get(f"/api/v1/projects/{project.id}/setup")
    assert r.status_code == 200
    assert r.json()["status"] == "generated"


def test_get_setup_not_found(client):
    r = client.get("/api/v1/projects/nonexistent/setup")
    assert r.status_code == 404

from app.core.athena_retrieval import reindex_project_retrieval, search_retrieval
from app.core.longform_memory import rebuild_longform_memory
from app.models import ChapterContent, LongformMemory, Project
from app.models import Version
from sqlalchemy import event


def test_create_and_list_versions(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post(f"/api/v1/projects/{pid}/versions", json={
        "node_type": "setup",
        "node_id": "fake-id",
        "content": '{"world_building": {}}',
        "description": "initial",
    })
    assert r2.status_code == 200
    assert r2.json()["version_saved"] is True
    assert r2.json()["version_number"] == 1

    r3 = client.get(f"/api/v1/projects/{pid}/versions")
    assert r3.status_code == 200
    assert len(r3.json()["versions"]) == 1


def test_list_versions_returns_bounded_page_with_total(client, db_session):
    project = Project(name="Version History Scale")
    db_session.add(project)
    db_session.flush()
    db_session.add_all([
        Version(
            project_id=project.id,
            node_type="chapter",
            node_id="chapter-1",
            version_number=index,
            content=f"版本正文 {index}",
            description=f"v{index}",
        )
        for index in range(1, 13)
    ])
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}/versions?offset=5&limit=4")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 12
    assert data["offset"] == 5
    assert data["limit"] == 4
    assert data["has_more"] is True
    assert [item["version_number"] for item in data["versions"]] == [7, 6, 5, 4]


def test_list_versions_does_not_select_version_content(client, db_session):
    project = Project(name="Version Summary Projection")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        Version(
            project_id=project.id,
            node_type="chapter",
            node_id="chapter-1",
            version_number=1,
            content="列表不应读取的大段版本正文。" * 1000,
            description="initial",
        )
    )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/versions")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    assert response.json()["versions"][0]["description"] == "initial"
    version_select_clauses = [
        statement.split("from versions", 1)[0]
        for statement in statements
        if "from versions" in statement
    ]
    assert version_select_clauses
    assert all("versions.content" not in clause for clause in version_select_clauses)


def test_get_version(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post(f"/api/v1/projects/{pid}/versions", json={
        "node_type": "setup",
        "node_id": "fake-id",
        "content": '{"test": true}',
    })
    vid = r2.json()["version_id"]

    r3 = client.get(f"/api/v1/projects/{pid}/versions/{vid}")
    assert r3.status_code == 200
    assert r3.json()["content"] == '{"test": true}'


def test_rollback_version(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post(f"/api/v1/projects/{pid}/versions", json={
        "node_type": "setup",
        "node_id": "fake-id",
        "content": '{"v": 1}',
        "description": "v1",
    })
    vid = r2.json()["version_id"]

    client.post(f"/api/v1/projects/{pid}/versions", json={
        "node_type": "setup",
        "node_id": "fake-id",
        "content": '{"v": 2}',
        "description": "v2",
    })

    r4 = client.post(f"/api/v1/projects/{pid}/versions/{vid}/rollback")
    assert r4.status_code == 200
    assert r4.json()["version_number"] == 3


def test_delete_version(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post(f"/api/v1/projects/{pid}/versions", json={
        "node_type": "setup",
        "node_id": "fake-id",
        "content": '{}',
    })
    vid = r2.json()["version_id"]

    r3 = client.delete(f"/api/v1/projects/{pid}/versions/{vid}")
    assert r3.status_code == 200

    r4 = client.get(f"/api/v1/projects/{pid}/versions/{vid}")
    assert r4.status_code == 404


def test_chapter_version_apply_refreshes_longform_memory_and_retrieval(client, db_session):
    project = Project(name="Version Longform Refresh")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    chapter = ChapterContent(
        project_id=project.id,
        chapter_index=1,
        title="第一章",
        content="旧正文。星环钥匙第一形态。",
        word_count=12,
        status="generated",
    )
    db_session.add(chapter)
    db_session.commit()
    db_session.refresh(chapter)
    rebuild_longform_memory(db_session, project.id)
    reindex_project_retrieval(db_session, project.id)

    response = client.post(
        f"/api/v1/projects/{project.id}/versions",
        json={
            "node_type": "chapter",
            "node_id": chapter.id,
            "content": "新正文。星环钥匙第二形态启动。",
            "description": "apply edited chapter",
        },
    )

    assert response.status_code == 200
    db_session.expire_all()
    refreshed_chapter = db_session.query(ChapterContent).filter(ChapterContent.id == chapter.id).one()
    refreshed_memory = (
        db_session.query(LongformMemory)
        .filter(LongformMemory.project_id == project.id, LongformMemory.scope_key == "chapter:1")
        .one()
    )
    results = search_retrieval(db_session, project.id, "星环钥匙第二形态", source_type="longform_memory")

    assert refreshed_chapter.content == "新正文。星环钥匙第二形态启动。"
    assert refreshed_chapter.word_count == 13
    assert "星环钥匙第二形态" in refreshed_memory.summary
    assert any("星环钥匙第二形态" in item["snippet"] for item in results["items"])

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
    assert len(r3.json()) == 1


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

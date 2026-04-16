def test_create_and_get_project(client):
    r = client.post("/api/v1/projects", json={"name": "Test Novel"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Test Novel"
    pid = data["id"]

    r2 = client.get(f"/api/v1/projects/{pid}")
    assert r2.status_code == 200
    assert r2.json()["id"] == pid


def test_list_projects(client):
    client.post("/api/v1/projects", json={"name": "Novel A"})
    client.post("/api/v1/projects", json={"name": "Novel B"})

    r = client.get("/api/v1/projects")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["name"] in ("Novel A", "Novel B")


def test_update_project(client):
    r = client.post("/api/v1/projects", json={"name": "Original"})
    pid = r.json()["id"]

    r2 = client.patch(f"/api/v1/projects/{pid}", json={"name": "Updated"})
    assert r2.status_code == 200
    assert r2.json()["name"] == "Updated"


def test_delete_project(client):
    r = client.post("/api/v1/projects", json={"name": "To Delete"})
    pid = r.json()["id"]

    r2 = client.delete(f"/api/v1/projects/{pid}")
    assert r2.status_code == 200
    assert r2.json()["deleted"] is True

    r3 = client.get(f"/api/v1/projects/{pid}")
    assert r3.status_code == 404


def test_get_project_404(client):
    r = client.get("/api/v1/projects/nonexistent-id")
    assert r.status_code == 404

def test_writing_start(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post(f"/api/v1/projects/{pid}/writing/start")
    assert r2.status_code == 200
    assert r2.json()["status"] == "running"


def test_writing_pause_and_resume(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    client.post(f"/api/v1/projects/{pid}/writing/start")
    r2 = client.post(f"/api/v1/projects/{pid}/writing/pause")
    assert r2.json()["status"] == "paused"

    r3 = client.post(f"/api/v1/projects/{pid}/writing/resume")
    assert r3.json()["status"] == "running"

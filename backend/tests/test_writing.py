from unittest.mock import patch

from app.models import BackgroundTask
from app.services.writing.writing_state_service import WritingStateService


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


def test_writing_state_survives_service_recreation(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    WritingStateService(db_session).start(pid)
    db_session.expire_all()

    restored = WritingStateService(db_session).state(pid)
    assert restored.status == "running"
    assert restored.current_chapter == 1

    WritingStateService(db_session).pause(pid)
    db_session.expire_all()

    resumed = WritingStateService(db_session).resume(pid)
    assert resumed.status == "running"


def test_writing_retry_creates_background_task(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.writing.LocalTaskRunner.start") as start:
        response = client.post(f"/api/v1/projects/{pid}/writing/chapters/2/retry")

    assert response.status_code == 200
    task = (
        db_session.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == pid,
            BackgroundTask.task_type == "retry_chapter",
        )
        .one()
    )
    assert task.payload == {"chapter_index": 2}
    assert task.status == "pending"
    start.assert_called_once()

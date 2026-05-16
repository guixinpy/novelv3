from unittest.mock import patch

import pytest

from app.models import BackgroundTask, ChapterContent
from app.services.tasks.background_task_service import BackgroundTaskService
from app.services.writing.writing_state_service import WritingStateService


def test_writing_start(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post(f"/api/v1/projects/{pid}/writing/start")
    assert r2.status_code == 200
    assert r2.json()["status"] == "running"


def test_writing_start_continues_after_latest_generated_chapter(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Long Running Novel"})
    pid = r.json()["id"]
    db_session.add_all([
        ChapterContent(
            project_id=pid,
            chapter_index=index,
            title=f"第{index}章",
            content="正文" * 100,
            word_count=200,
            status="generated",
        )
        for index in range(1, 4)
    ])
    db_session.commit()

    response = client.post(f"/api/v1/projects/{pid}/writing/start")

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["current_chapter"] == 4


def test_writing_state_endpoint_returns_current_state(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Readable Writing State"})
    pid = r.json()["id"]
    WritingStateService(db_session).mark_error(pid, "chapter generation failed")

    response = client.get(f"/api/v1/projects/{pid}/writing/state")

    assert response.status_code == 200
    assert response.json() == {
        "project_id": pid,
        "current_chapter": 1,
        "status": "failed",
        "last_error": "chapter generation failed",
    }


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
    assert response.json()["status"] == "running"
    assert response.json()["current_chapter"] == 2
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


@pytest.mark.asyncio
async def test_retry_chapter_work_marks_state_idle_after_success(client, db_session, monkeypatch):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    WritingStateService(db_session).run_chapter(pid, 2)
    task = BackgroundTaskService(db_session).create(
        project_id=pid,
        task_type="retry_chapter",
        payload={"chapter_index": 2},
    )

    async def fake_generate(project_id, chapter_index, db):
        return {"chapter_index": chapter_index}

    monkeypatch.setattr("app.api.chapters.generate_chapter", fake_generate)
    from app.api.writing import build_retry_chapter_work

    result = await build_retry_chapter_work(pid, 2)(db_session, task)

    state = WritingStateService(db_session).state(pid)
    assert result == {"chapter_index": 2}
    assert state.status == "idle"
    assert state.current_chapter == 2
    assert state.last_error is None


@pytest.mark.asyncio
async def test_retry_chapter_work_marks_state_failed_after_error(client, db_session, monkeypatch):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    WritingStateService(db_session).run_chapter(pid, 2)
    task = BackgroundTaskService(db_session).create(
        project_id=pid,
        task_type="retry_chapter",
        payload={"chapter_index": 2},
    )

    async def fake_generate(project_id, chapter_index, db):
        raise RuntimeError("chapter generation failed")

    monkeypatch.setattr("app.api.chapters.generate_chapter", fake_generate)
    from app.api.writing import build_retry_chapter_work

    with pytest.raises(RuntimeError, match="chapter generation failed"):
        await build_retry_chapter_work(pid, 2)(db_session, task)

    state = WritingStateService(db_session).state(pid)
    assert state.status == "failed"
    assert state.current_chapter == 2
    assert state.last_error == "chapter generation failed"

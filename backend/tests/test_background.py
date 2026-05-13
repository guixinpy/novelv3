import pytest
from sqlalchemy.orm import sessionmaker

from app.core.local_diagnostics import format_kv_event
from app.models import BackgroundTask
from app.services.tasks.background_task_service import BackgroundTaskService
from app.services.tasks.local_task_runner import LocalTaskRunner


def test_list_background_tasks(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    r2 = client.get(f"/api/v1/projects/{pid}/background-tasks")
    assert r2.status_code == 200
    assert "tasks" in r2.json()


def test_get_background_task_with_ui_hint(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    task = BackgroundTask(
        project_id=pid,
        task_type="generate_outline",
        status="completed",
        result={"ok": True},
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    r2 = client.get(f"/api/v1/background-tasks/{task.id}")
    assert r2.status_code == 200
    assert r2.json()["ui_hint"]["dialog_state"] == "CHATTING"
    assert r2.json()["ui_hint"]["active_action"]["target_panel"] == "outline"
    assert r2.json()["ui_hint"]["active_action"]["status"] == "completed"
    assert r2.json()["refresh_targets"] == ["outline", "versions"]


def test_get_background_task_consistency_deep_check_ui_hint(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    task = BackgroundTask(
        project_id=pid,
        task_type="consistency_deep_check",
        status="completed",
        result={"ok": True},
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    r2 = client.get(f"/api/v1/background-tasks/{task.id}")
    assert r2.status_code == 200
    assert r2.json()["ui_hint"]["dialog_state"] == "CHATTING"
    assert r2.json()["ui_hint"]["active_action"]["target_panel"] == "content"
    assert r2.json()["ui_hint"]["active_action"]["status"] == "completed"
    assert r2.json()["refresh_targets"] == ["content"]


def test_get_background_task_includes_range_payload(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    service = BackgroundTaskService(db_session)
    task = service.create_chapter_range(
        project_id=pid,
        task_type="athena_reindex_range",
        start_chapter_index=10,
        end_chapter_index=20,
        idempotency_key="range:10-20",
    )

    response = client.get(f"/api/v1/background-tasks/{task.id}")

    assert response.status_code == 200
    assert response.json()["payload"]["chapter_range"] == {"start": 10, "end": 20}
    assert response.json()["payload"]["idempotency_key"] == "range:10-20"


def test_background_task_service_tracks_lifecycle(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    service = BackgroundTaskService(db_session)

    task = service.create(
        project_id=pid,
        task_type="generate_chapter",
        payload={"chapter_index": 1},
    )
    assert task.status == "pending"

    running = service.mark_running(task.id)
    assert running.status == "running"
    assert running.started_at is not None

    completed = service.mark_completed(task.id, {"chapter_index": 1})
    assert completed.status == "completed"
    assert completed.result == {"chapter_index": 1}
    assert completed.finished_at is not None


def test_background_task_service_tracks_chapter_range_progress(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    service = BackgroundTaskService(db_session)

    task = service.create_chapter_range(
        project_id=pid,
        task_type="athena_reindex_range",
        start_chapter_index=1,
        end_chapter_index=5,
        payload={"source": "longform_scale"},
        idempotency_key="range:1-5",
    )

    assert task.payload["chapter_range"] == {"start": 1, "end": 5}
    assert task.payload["idempotency_key"] == "range:1-5"

    service.mark_range_progress(task.id, completed_chapter_index=1)
    progressed = service.mark_range_progress(task.id, completed_chapter_index=2)

    assert progressed.result["progress"] == {
        "chapter_range": {"start": 1, "end": 5},
        "completed_chapter_indexes": [1, 2],
        "next_chapter_index": 3,
        "completed_count": 2,
        "total_count": 5,
        "can_resume": True,
    }


def test_background_task_service_compacts_large_sequential_range_progress(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    service = BackgroundTaskService(db_session)
    task = service.create_chapter_range(
        project_id=pid,
        task_type="athena_reindex_range",
        start_chapter_index=1,
        end_chapter_index=250,
    )

    progressed = task
    for chapter_index in range(1, 251):
        progressed = service.mark_range_progress(progressed.id, completed_chapter_index=chapter_index)

    progress = progressed.result["progress"]
    assert progress["chapter_range"] == {"start": 1, "end": 250}
    assert progress["completed_until_chapter_index"] == 250
    assert progress["first_completed_chapter_index"] == 1
    assert progress["last_completed_chapter_index"] == 250
    assert progress["next_chapter_index"] == 251
    assert progress["completed_count"] == 250
    assert progress["total_count"] == 250
    assert progress["can_resume"] is False
    assert "completed_chapter_indexes" not in progress


def test_background_task_service_retries_failed_range_from_checkpoint(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    service = BackgroundTaskService(db_session)
    task = service.create_chapter_range(
        project_id=pid,
        task_type="athena_reindex_range",
        start_chapter_index=1,
        end_chapter_index=5,
    )
    service.mark_range_progress(task.id, completed_chapter_index=1)
    service.mark_range_progress(task.id, completed_chapter_index=2)
    service.mark_failed(task.id, "network error")

    retry = service.create_retry_from_failed(task.id)

    assert retry.status == "pending"
    assert retry.task_type == "athena_reindex_range"
    assert retry.payload["chapter_range"] == {"start": 1, "end": 5}
    assert retry.payload["retry_of_task_id"] == task.id
    assert retry.payload["resume_from_chapter_index"] == 3


def test_background_task_service_marks_interrupted_running_tasks_failed(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    service = BackgroundTaskService(db_session)
    task = service.create(project_id=pid, task_type="consistency_deep_check")
    service.mark_running(task.id)

    count = service.fail_interrupted_running_tasks()

    saved = service.get(task.id)
    assert count == 1
    assert saved.status == "failed"
    assert saved.error == "Task interrupted by local process restart"


def test_local_diagnostics_formats_key_value_event():
    line = format_kv_event(
        "task_done",
        task_id="task-1",
        status="completed",
        duration_ms=12,
        error="has space",
    )

    assert line == 'event=task_done task_id=task-1 status=completed duration_ms=12 error="has space"'


@pytest.mark.asyncio
async def test_local_task_runner_marks_completed(client, db_session, capsys):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    service = BackgroundTaskService(db_session)
    task = service.create(project_id=pid, task_type="consistency_deep_check")
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind())
    runner = LocalTaskRunner(session_factory=session_factory)

    async def work(session, running_task):
        return {"task_id": running_task.id}

    result = await runner.run_now(task.id, work)

    db_session.expire_all()
    saved = service.get(task.id)
    assert result == {"task_id": task.id}
    assert saved.status == "completed"
    assert saved.result == {"task_id": task.id}
    assert "event=task_done" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_local_task_runner_marks_failed(client, db_session, capsys):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    service = BackgroundTaskService(db_session)
    task = service.create(project_id=pid, task_type="consistency_deep_check")
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind())
    runner = LocalTaskRunner(session_factory=session_factory)

    async def work(session, running_task):
        raise RuntimeError("deep check failed")

    with pytest.raises(RuntimeError, match="deep check failed"):
        await runner.run_now(task.id, work)

    db_session.expire_all()
    saved = service.get(task.id)
    assert saved.status == "failed"
    assert saved.error == "deep check failed"
    assert "event=task_failed" in capsys.readouterr().out


def test_cross_validator():
    from app.core.cross_validator import CrossValidator
    cv = CrossValidator()
    l1 = [{"type": "character_presence", "subject": "李明", "new_value": 3}]
    l2 = [{"type": "character_presence", "subject": "李明", "new_value": 5, "confidence": 0.9}]
    result = cv.validate(l1, l2)
    assert len(result["confirmed"]) == 1


def test_location_checker():
    from unittest.mock import MagicMock

    from app.core.checkers import LocationChecker
    chapter = MagicMock()
    chapter.project_id = "test"
    chapter.chapter_index = 1
    checker = LocationChecker()
    facts = [
        {"type": "location_presence", "subject": "李明", "new_value": "A城"},
        {"type": "location_presence", "subject": "李明", "new_value": "B城"},
    ]
    issues = checker.check(chapter, facts)
    assert len(issues) == 1
    assert issues[0]["checker_name"] == "LocationChecker"

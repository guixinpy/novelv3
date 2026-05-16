import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

from app.core.local_diagnostics import format_kv_event
from app.main import app
from app.models import BackgroundTask
from app.services.tasks.background_task_service import BackgroundTaskService
from app.services.tasks.local_task_runner import LocalTaskRunner


def test_list_background_tasks(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    r2 = client.get(f"/api/v1/projects/{pid}/background-tasks")
    assert r2.status_code == 200
    assert "tasks" in r2.json()


def test_list_background_tasks_paginates_large_project_history(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Task History"})
    pid = r.json()["id"]
    db_session.add_all([
        BackgroundTask(project_id=pid, task_type=f"task-{index}", status="completed")
        for index in range(30)
    ])
    db_session.commit()

    first_page = client.get(f"/api/v1/projects/{pid}/background-tasks?offset=0&limit=10")
    second_page = client.get(f"/api/v1/projects/{pid}/background-tasks?offset=10&limit=10")

    assert first_page.status_code == 200
    assert first_page.json()["total"] == 30
    assert first_page.json()["offset"] == 0
    assert first_page.json()["limit"] == 10
    assert first_page.json()["has_more"] is True
    assert len(first_page.json()["tasks"]) == 10

    assert second_page.status_code == 200
    assert second_page.json()["total"] == 30
    assert second_page.json()["offset"] == 10
    assert second_page.json()["limit"] == 10
    assert second_page.json()["has_more"] is True
    assert len(second_page.json()["tasks"]) == 10


def test_list_background_tasks_total_does_not_select_heavy_task_fields(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Task History Heavy"})
    pid = r.json()["id"]
    db_session.add_all([
        BackgroundTask(
            project_id=pid,
            task_type=f"task-{index}",
            status="completed",
            payload={"chapters": list(range(1000))},
            result={"summary": ["任务结果"] * 500},
            error="长错误信息" * 300,
        )
        for index in range(3)
    ])
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{pid}/background-tasks?limit=1")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    assert response.json()["total"] == 3
    count_statements = [
        statement for statement in statements
        if "count(" in statement and "background_tasks" in statement
    ]
    assert count_statements
    assert all("background_tasks.payload" not in statement for statement in count_statements)
    assert all("background_tasks.result" not in statement for statement in count_statements)
    assert all("background_tasks.error" not in statement for statement in count_statements)


def test_list_background_tasks_rows_do_not_select_heavy_task_fields(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Task History Row Projection"})
    pid = r.json()["id"]
    db_session.add_all([
        BackgroundTask(
            project_id=pid,
            task_type=f"task-{index}",
            status="completed",
            payload={"chapters": list(range(1000))},
            result={"summary": ["任务结果"] * 500},
            error="长错误信息" * 300,
        )
        for index in range(3)
    ])
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{pid}/background-tasks?limit=1")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    assert len(response.json()["tasks"]) == 1
    row_selects = [
        statement for statement in statements
        if statement.startswith("select")
        and "from background_tasks" in statement
        and "count(" not in statement
    ]
    assert row_selects
    assert all("background_tasks.payload" not in statement for statement in row_selects)
    assert all("background_tasks.result" not in statement for statement in row_selects)
    assert all("background_tasks.error" not in statement for statement in row_selects)


def test_get_background_task_compact_does_not_select_heavy_task_fields(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Task Detail Compact"})
    pid = r.json()["id"]
    task = BackgroundTask(
        project_id=pid,
        task_type="generate_outline",
        status="running",
        payload={"chapters": list(range(1000))},
        result={"summary": ["任务结果"] * 500},
        error="长错误信息" * 300,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/background-tasks/{task.id}?compact=true")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    assert response.json()["task_id"] == task.id
    assert response.json()["status"] == "running"
    assert response.json()["payload"] is None
    assert response.json()["result"] is None
    assert response.json()["error"] is None
    row_selects = [
        statement for statement in statements
        if statement.startswith("select") and "from background_tasks" in statement
    ]
    assert row_selects
    assert all("background_tasks.payload" not in statement for statement in row_selects)
    assert all("background_tasks.result" not in statement for statement in row_selects)
    assert all("background_tasks.error" not in statement for statement in row_selects)


def test_get_background_task_compact_returns_bounded_failure_error(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Task Detail Compact Error"})
    pid = r.json()["id"]
    long_error = "DeepSeek timeout " * 80
    task = BackgroundTask(
        project_id=pid,
        task_type="generate_chapter_range",
        status="failed",
        payload={"chapters": list(range(1000))},
        result={"summary": ["任务结果"] * 500},
        error=long_error,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/background-tasks/{task.id}?compact=true")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["error"] == long_error[:240]
    row_selects = [
        statement for statement in statements
        if statement.startswith("select") and "from background_tasks" in statement
    ]
    assert row_selects
    assert all("background_tasks.payload" not in statement for statement in row_selects)
    assert all("background_tasks.result" not in statement for statement in row_selects)
    assert any("substr(" in statement and "background_tasks.error" in statement for statement in row_selects)


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


def test_get_background_task_generate_chapter_refreshes_writing_state(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    task = BackgroundTask(
        project_id=pid,
        task_type="generate_chapter",
        status="completed",
        result={"chapter_index": 12},
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    response = client.get(f"/api/v1/background-tasks/{task.id}")

    assert response.status_code == 200
    assert response.json()["refresh_targets"] == ["project", "content", "versions", "writing_state"]


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


def test_background_task_service_reuses_active_range_task_by_idempotency_key(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    service = BackgroundTaskService(db_session)

    first = service.create_chapter_range(
        project_id=pid,
        task_type="athena_reindex_range",
        start_chapter_index=1,
        end_chapter_index=1000,
        idempotency_key="range:1-1000",
    )
    service.mark_running(first.id)

    duplicate = service.create_chapter_range(
        project_id=pid,
        task_type="athena_reindex_range",
        start_chapter_index=1,
        end_chapter_index=1000,
        idempotency_key="range:1-1000",
    )

    assert duplicate.id == first.id
    assert db_session.query(BackgroundTask).filter(BackgroundTask.project_id == pid).count() == 1


def test_background_task_service_filters_idempotency_key_at_source(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Task Idempotency Lookup"})
    pid = r.json()["id"]
    db_session.add_all([
        BackgroundTask(
            project_id=pid,
            task_type="athena_reindex_range",
            status="running",
            payload={
                "idempotency_key": f"range:other:{index}",
                "chapter_range": {"start": index + 1, "end": index + 1},
                "large": ["任务载荷"] * 500,
            },
        )
        for index in range(6)
    ])
    matching = BackgroundTask(
        project_id=pid,
        task_type="athena_reindex_range",
        status="pending",
        payload={
            "idempotency_key": "range:target",
            "chapter_range": {"start": 1, "end": 10},
            "large": ["目标任务载荷"] * 500,
        },
    )
    db_session.add(matching)
    db_session.commit()
    db_session.refresh(matching)
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        duplicate = BackgroundTaskService(db_session).create_chapter_range(
            project_id=pid,
            task_type="athena_reindex_range",
            start_chapter_index=1,
            end_chapter_index=10,
            idempotency_key="range:target",
        )
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert duplicate.id == matching.id
    assert db_session.query(BackgroundTask).filter(BackgroundTask.project_id == pid).count() == 7
    row_selects = [
        statement for statement in statements
        if statement.startswith("select") and "from background_tasks" in statement
    ]
    assert row_selects
    assert any("json_extract" in statement and "limit" in statement for statement in row_selects)


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


def test_background_task_service_extends_compacted_range_without_expanding_checkpoints(
    client,
    db_session,
    monkeypatch,
):
    import app.services.tasks.background_task_service as task_module

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
    for chapter_index in range(1, 202):
        progressed = service.mark_range_progress(progressed.id, completed_chapter_index=chapter_index)
    assert progressed.result["progress"]["completed_until_chapter_index"] == 201

    def fail_if_expanded(*args, **kwargs):
        raise AssertionError("compacted progress should not be expanded")

    monkeypatch.setattr(task_module, "_completed_chapter_index_set", fail_if_expanded)

    progressed = service.mark_range_progress(progressed.id, completed_chapter_index=202)

    progress = progressed.result["progress"]
    assert progress["completed_until_chapter_index"] == 202
    assert progress["first_completed_chapter_index"] == 1
    assert progress["last_completed_chapter_index"] == 202
    assert progress["next_chapter_index"] == 203
    assert progress["completed_count"] == 202
    assert progress["total_count"] == 250
    assert progress["can_resume"] is True
    assert "completed_chapter_indexes" not in progress


def test_background_task_service_marks_many_range_progress_entries_in_one_commit(client, db_session, monkeypatch):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    service = BackgroundTaskService(db_session)
    task = service.create_chapter_range(
        project_id=pid,
        task_type="athena_reindex_range",
        start_chapter_index=1,
        end_chapter_index=1000,
    )
    commit_count = {"calls": 0}
    original_commit = db_session.commit

    def count_commit(*args, **kwargs):
        commit_count["calls"] += 1
        return original_commit(*args, **kwargs)

    monkeypatch.setattr(db_session, "commit", count_commit)

    progressed = service.mark_range_progress_many(task.id, completed_chapter_indexes=range(1, 1001))

    progress = progressed.result["progress"]
    assert progress["completed_until_chapter_index"] == 1000
    assert progress["completed_count"] == 1000
    assert progress["total_count"] == 1000
    assert progress["next_chapter_index"] == 1001
    assert progress["can_resume"] is False
    assert "completed_chapter_indexes" not in progress
    assert commit_count["calls"] == 1


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


def test_background_task_service_retry_keeps_compact_failed_progress_snapshot(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Retry Progress Snapshot"})
    pid = r.json()["id"]
    service = BackgroundTaskService(db_session)
    task = service.create_chapter_range(
        project_id=pid,
        task_type="athena_reindex_range",
        start_chapter_index=1,
        end_chapter_index=1000,
    )
    service.mark_range_progress_many(task.id, completed_chapter_indexes=range(1, 251))
    service.mark_failed(task.id, "network error")

    retry = service.create_retry_from_failed(task.id)

    assert retry.payload["resume_from_chapter_index"] == 251
    assert retry.payload["previous_progress"] == {
        "chapter_range": {"start": 1, "end": 1000},
        "next_chapter_index": 251,
        "completed_count": 250,
        "total_count": 1000,
        "can_resume": True,
        "completed_until_chapter_index": 250,
        "first_completed_chapter_index": 1,
        "last_completed_chapter_index": 250,
        "checkpoint_count": 0,
    }
    assert "completed_chapter_indexes" not in retry.payload["previous_progress"]


def test_background_task_service_pending_chapter_indexes_skip_sparse_completed(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Pending Sparse Range"})
    pid = r.json()["id"]
    service = BackgroundTaskService(db_session)
    task = service.create_chapter_range(
        project_id=pid,
        task_type="athena_reindex_range",
        start_chapter_index=1,
        end_chapter_index=8,
    )
    service.mark_range_progress_many(task.id, completed_chapter_indexes=[1, 2, 5])

    assert service.pending_chapter_indexes(task.id) == [3, 4, 6, 7, 8]


def test_background_task_service_pending_chapter_indexes_resume_retry_from_checkpoint(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Pending Retry Range"})
    pid = r.json()["id"]
    service = BackgroundTaskService(db_session)
    task = service.create_chapter_range(
        project_id=pid,
        task_type="athena_reindex_range",
        start_chapter_index=1,
        end_chapter_index=1000,
    )
    service.mark_range_progress_many(task.id, completed_chapter_indexes=range(1, 251))
    service.mark_failed(task.id, "network error")
    retry = service.create_retry_from_failed(task.id)

    pending = service.pending_chapter_indexes(retry.id)

    assert pending[:3] == [251, 252, 253]
    assert pending[-1] == 1000
    assert len(pending) == 750


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


def test_background_task_service_marks_interrupted_pending_tasks_failed(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    service = BackgroundTaskService(db_session)
    task = service.create_chapter_range(
        project_id=pid,
        task_type="generate_chapter_range",
        start_chapter_index=1,
        end_chapter_index=5,
        idempotency_key="range-1-5",
    )

    count = service.fail_interrupted_running_tasks()
    retry = service.create_chapter_range(
        project_id=pid,
        task_type="generate_chapter_range",
        start_chapter_index=1,
        end_chapter_index=5,
        idempotency_key="range-1-5",
    )

    saved = service.get(task.id)
    assert count == 1
    assert saved.status == "failed"
    assert saved.error == "Task interrupted by local process restart"
    assert retry.id != task.id


def test_background_task_service_fails_interrupted_tasks_without_selecting_rows(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Task Restart Bulk"})
    pid = r.json()["id"]
    db_session.add_all([
        BackgroundTask(
            project_id=pid,
            task_type=f"active-{index}",
            status="running" if index % 2 else "pending",
            payload={"chapters": list(range(1000))},
            result={"summary": ["任务结果"] * 500},
            error="长错误信息" * 300,
        )
        for index in range(5)
    ])
    db_session.add(
        BackgroundTask(
            project_id=pid,
            task_type="completed",
            status="completed",
            payload={"chapters": list(range(1000))},
        )
    )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        count = BackgroundTaskService(db_session).fail_interrupted_running_tasks()
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert count == 5
    row_selects = [
        statement for statement in statements
        if statement.startswith("select") and "from background_tasks" in statement
    ]
    assert row_selects == []
    update_statements = [
        statement for statement in statements
        if statement.startswith("update background_tasks")
    ]
    assert update_statements
    assert (
        db_session.query(BackgroundTask)
        .filter(BackgroundTask.project_id == pid, BackgroundTask.status == "failed")
        .count()
        == 5
    )
    assert (
        db_session.query(BackgroundTask)
        .filter(BackgroundTask.project_id == pid, BackgroundTask.status == "completed")
        .count()
        == 1
    )


def test_app_startup_marks_interrupted_running_tasks_failed(monkeypatch):
    calls: list[str] = []

    class FakeDb:
        def close(self):
            calls.append("closed")

    class FakeBackgroundTaskService:
        def __init__(self, db):
            assert isinstance(db, FakeDb)

        def fail_interrupted_running_tasks(self):
            calls.append("failed-interrupted")
            return 2

    monkeypatch.setattr("app.main.SessionLocal", lambda: FakeDb(), raising=False)
    monkeypatch.setattr("app.main.BackgroundTaskService", FakeBackgroundTaskService, raising=False)

    with TestClient(app):
        pass

    assert calls == ["failed-interrupted", "closed"]


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

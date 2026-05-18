from unittest.mock import patch

import pytest
from sqlalchemy import event

from app.models import AIModelCallTrace, BackgroundTask, ChapterContent, Outline
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


def test_writing_start_creates_generate_chapter_task(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Continuous Writing"})
    pid = r.json()["id"]

    with patch("app.api.writing.LocalTaskRunner.start") as start:
        response = client.post(f"/api/v1/projects/{pid}/writing/start")

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["current_chapter"] == 1
    task = (
        db_session.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == pid,
            BackgroundTask.task_type == "generate_chapter",
        )
        .one()
    )
    assert task.payload == {"chapter_index": 1}
    assert task.status == "pending"
    assert response.json()["task_id"] == task.id
    start.assert_called_once()


def test_writing_start_creates_range_task_when_target_is_known(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Targeted Continuous Writing", "target_chapter_count": 3})
    pid = r.json()["id"]

    with patch("app.api.writing.LocalTaskRunner.start") as start:
        response = client.post(f"/api/v1/projects/{pid}/writing/start")

    assert response.status_code == 200
    task = (
        db_session.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == pid,
            BackgroundTask.task_type == "generate_chapter",
        )
        .one()
    )
    assert task.payload == {
        "chapter_index": 1,
        "chapter_range": {"start": 1, "end": 3},
    }
    assert response.json()["task_id"] == task.id
    start.assert_called_once()


@pytest.mark.asyncio
async def test_generate_chapter_work_continues_until_project_target(client, db_session, monkeypatch):
    r = client.post("/api/v1/projects", json={"name": "Continuous Range Work", "target_chapter_count": 3})
    pid = r.json()["id"]
    task = BackgroundTaskService(db_session).create_chapter_range(
        project_id=pid,
        task_type="generate_chapter",
        start_chapter_index=1,
        end_chapter_index=3,
        payload={"chapter_index": 1},
    )
    WritingStateService(db_session).run_chapter(pid, 1)
    generated: list[int] = []

    async def fake_generate_chapter(project_id: str, chapter_index: int, db):
        generated.append(chapter_index)
        WritingStateService(db).complete_chapter(project_id, chapter_index)
        return {"chapter_index": chapter_index}

    monkeypatch.setattr("app.api.chapters.generate_chapter", fake_generate_chapter)
    from app.api.writing import build_generate_chapter_work

    result = await build_generate_chapter_work(pid, 1)(db_session, task)

    assert generated == [1, 2, 3]
    assert result["chapter_index"] == 3
    assert result["progress"]["completed_count"] == 3
    assert result["progress"]["next_chapter_index"] == 4
    state = WritingStateService(db_session).state(pid)
    assert state.status == "completed"
    assert state.current_chapter == 4


@pytest.mark.asyncio
async def test_generate_chapter_work_summarizes_generation_diagnostics(client, db_session, monkeypatch):
    r = client.post("/api/v1/projects", json={"name": "Observable Range Work", "target_chapter_count": 3})
    pid = r.json()["id"]
    task = BackgroundTaskService(db_session).create_chapter_range(
        project_id=pid,
        task_type="generate_chapter",
        start_chapter_index=1,
        end_chapter_index=3,
        payload={"chapter_index": 1},
    )
    WritingStateService(db_session).run_chapter(pid, 1)

    statuses = {
        1: {"status": "under", "warning": None},
        2: {
            "status": "within",
            "warning": {
                "stage": "longform_memory_refresh",
                "error_type": "RuntimeError",
                "message": "maintenance failed",
            },
        },
        3: {"status": "over", "warning": None},
    }

    async def fake_generate_chapter(project_id: str, chapter_index: int, db):
        status = statuses[chapter_index]["status"]
        metadata = {
            "chapter_word_target": {
                "actual_word_count": 100,
                "status": status,
            },
        }
        warning = statuses[chapter_index]["warning"]
        if warning:
            metadata["post_generation_warning_count"] = 1
            metadata["post_generation_warnings"] = [warning]
        trace = AIModelCallTrace(
            project_id=project_id,
            trace_type="chapter_generation",
            status="success",
            chapter_index=chapter_index,
            trace_metadata=metadata,
        )
        db.add(trace)
        db.commit()
        WritingStateService(db).complete_chapter(project_id, chapter_index)
        return {"chapter_index": chapter_index, "last_generation_trace_id": trace.id}

    monkeypatch.setattr("app.api.chapters.generate_chapter", fake_generate_chapter)
    from app.api.writing import build_generate_chapter_work

    result = await build_generate_chapter_work(pid, 1)(db_session, task)

    diagnostics = result["generation_diagnostics"]
    assert diagnostics["word_target"] == {
        "under_count": 1,
        "within_count": 1,
        "over_count": 1,
        "untracked_count": 0,
        "under_chapter_indexes": [1],
        "over_chapter_indexes": [3],
    }
    assert diagnostics["post_generation_warning_count"] == 1
    assert diagnostics["post_generation_warnings"] == [
        {
            "chapter_index": 2,
            "stage": "longform_memory_refresh",
            "error_type": "RuntimeError",
            "message": "maintenance failed",
        }
    ]


@pytest.mark.asyncio
async def test_generate_chapter_work_status_check_skips_active_task_lookup(client, db_session, monkeypatch):
    r = client.post("/api/v1/projects", json={"name": "Range Worker Lightweight State", "target_chapter_count": 3})
    pid = r.json()["id"]
    task = BackgroundTaskService(db_session).create_chapter_range(
        project_id=pid,
        task_type="generate_chapter",
        start_chapter_index=1,
        end_chapter_index=3,
        payload={"chapter_index": 1},
    )
    WritingStateService(db_session).run_chapter(pid, 1)

    async def fake_generate_chapter(project_id: str, chapter_index: int, db):
        WritingStateService(db).complete_chapter(project_id, chapter_index)
        return {"chapter_index": chapter_index}

    monkeypatch.setattr("app.api.chapters.generate_chapter", fake_generate_chapter)
    from app.api.writing import build_generate_chapter_work

    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        await build_generate_chapter_work(pid, 1)(db_session, task)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    active_task_lookups = [
        statement for statement in statements
        if "from background_tasks" in statement
        and "background_tasks.task_type in" in statement
        and "background_tasks.status in" in statement
    ]
    assert active_task_lookups == []


@pytest.mark.asyncio
async def test_generate_chapter_work_stops_when_paused_mid_chapter(client, db_session, monkeypatch):
    r = client.post("/api/v1/projects", json={"name": "Pause Continuous Range", "target_chapter_count": 3})
    pid = r.json()["id"]
    task = BackgroundTaskService(db_session).create_chapter_range(
        project_id=pid,
        task_type="generate_chapter",
        start_chapter_index=1,
        end_chapter_index=3,
        payload={"chapter_index": 1},
    )
    WritingStateService(db_session).run_chapter(pid, 1)
    generated: list[int] = []

    async def fake_generate_chapter(project_id: str, chapter_index: int, db):
        generated.append(chapter_index)
        WritingStateService(db).pause(project_id)
        WritingStateService(db).complete_chapter(project_id, chapter_index)
        return {"chapter_index": chapter_index}

    monkeypatch.setattr("app.api.chapters.generate_chapter", fake_generate_chapter)
    from app.api.writing import build_generate_chapter_work

    result = await build_generate_chapter_work(pid, 1)(db_session, task)

    assert generated == [1]
    assert result["progress"]["completed_count"] == 1
    state = WritingStateService(db_session).state(pid)
    assert state.status == "paused"
    assert state.current_chapter == 2


def test_writing_start_reuses_active_generate_chapter_task(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "No Duplicate Writing Tasks"})
    pid = r.json()["id"]

    with patch("app.api.writing.LocalTaskRunner.start") as start:
        first = client.post(f"/api/v1/projects/{pid}/writing/start")
        second = client.post(f"/api/v1/projects/{pid}/writing/start")

    assert first.status_code == 200
    assert second.status_code == 200
    tasks = (
        db_session.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == pid,
            BackgroundTask.task_type == "generate_chapter",
        )
        .all()
    )
    assert len(tasks) == 1
    assert first.json()["task_id"] == tasks[0].id
    assert second.json()["task_id"] == tasks[0].id
    start.assert_called_once()


def test_writing_start_reuses_active_range_task_covering_current_chapter(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "No Duplicate Range Writing", "target_chapter_count": 10})
    pid = r.json()["id"]
    active = BackgroundTaskService(db_session).create_chapter_range(
        project_id=pid,
        task_type="generate_chapter",
        start_chapter_index=1,
        end_chapter_index=10,
        payload={"chapter_index": 1},
    )
    active.status = "running"
    db_session.commit()
    WritingStateService(db_session).run_chapter(pid, 5)

    with patch("app.api.writing.LocalTaskRunner.start") as start:
        response = client.post(f"/api/v1/projects/{pid}/writing/start")

    assert response.status_code == 200
    assert response.json()["task_id"] == active.id
    tasks = (
        db_session.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == pid,
            BackgroundTask.task_type == "generate_chapter",
        )
        .all()
    )
    assert len(tasks) == 1
    start.assert_not_called()


def test_writing_start_after_completed_chapter_queues_next_chapter(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Advance After Completion"})
    pid = r.json()["id"]
    WritingStateService(db_session).complete_chapter(pid, 1)

    with patch("app.api.writing.LocalTaskRunner.start") as start:
        response = client.post(f"/api/v1/projects/{pid}/writing/start")

    assert response.status_code == 200
    assert response.json()["current_chapter"] == 2
    task = (
        db_session.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == pid,
            BackgroundTask.task_type == "generate_chapter",
        )
        .one()
    )
    assert task.payload == {"chapter_index": 2}
    start.assert_called_once()


def test_writing_start_completes_without_task_after_project_target(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Targeted Novel", "target_chapter_count": 1})
    pid = r.json()["id"]
    WritingStateService(db_session).complete_chapter(pid, 1)

    with patch("app.api.writing.LocalTaskRunner.start") as start:
        response = client.post(f"/api/v1/projects/{pid}/writing/start")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["current_chapter"] == 2
    assert "task_id" not in response.json()
    project = client.get(f"/api/v1/projects/{pid}").json()
    assert project["status"] == "completed"
    assert project["current_phase"] == "content"
    task_count = (
        db_session.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == pid,
            BackgroundTask.task_type == "generate_chapter",
        )
        .count()
    )
    assert task_count == 0
    start.assert_not_called()


def test_writing_start_finish_project_syncs_project_status(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Target Drift", "target_chapter_count": 1})
    pid = r.json()["id"]
    WritingStateService(db_session).run_chapter(pid, 2)

    with patch("app.api.writing.LocalTaskRunner.start") as start:
        response = client.post(f"/api/v1/projects/{pid}/writing/start")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    project = client.get(f"/api/v1/projects/{pid}").json()
    assert project["status"] == "completed"
    assert project["current_phase"] == "content"
    start.assert_not_called()


def test_writing_resume_completes_without_task_after_outline_target(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Outline Targeted Novel"})
    pid = r.json()["id"]
    db_session.add(Outline(project_id=pid, status="generated", total_chapters=1, chapters=[{"chapter_index": 1}]))
    db_session.commit()
    WritingStateService(db_session).complete_chapter(pid, 1)
    WritingStateService(db_session).pause(pid)

    with patch("app.api.writing.LocalTaskRunner.start") as start:
        response = client.post(f"/api/v1/projects/{pid}/writing/resume")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["current_chapter"] == 2
    assert "task_id" not in response.json()
    task_count = (
        db_session.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == pid,
            BackgroundTask.task_type == "generate_chapter",
        )
        .count()
    )
    assert task_count == 0
    start.assert_not_called()


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


def test_writing_state_endpoint_returns_active_task_id(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Recover Running Writing", "target_chapter_count": 10})
    pid = r.json()["id"]
    task = BackgroundTaskService(db_session).create_chapter_range(
        project_id=pid,
        task_type="generate_chapter",
        start_chapter_index=1,
        end_chapter_index=10,
        payload={"chapter_index": 1},
    )
    task.status = "running"
    db_session.commit()
    WritingStateService(db_session).run_chapter(pid, 5)

    response = client.get(f"/api/v1/projects/{pid}/writing/state")

    assert response.status_code == 200
    assert response.json()["task_id"] == task.id


def test_writing_state_active_task_lookup_does_not_select_heavy_task_fields(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Recover Running Writing Heavy", "target_chapter_count": 10})
    pid = r.json()["id"]
    task = BackgroundTaskService(db_session).create_chapter_range(
        project_id=pid,
        task_type="generate_chapter",
        start_chapter_index=1,
        end_chapter_index=10,
        payload={"chapter_index": 1, "chapter_range": {"start": 1, "end": 10}},
    )
    task.status = "running"
    task.result = {"progress": {"completed_chapter_indexes": list(range(1, 1000))}}
    task.error = "large error" * 100
    db_session.commit()
    WritingStateService(db_session).run_chapter(pid, 5)
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{pid}/writing/state")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    assert response.json()["task_id"] == task.id
    task_selects = [
        statement for statement in statements
        if statement.startswith("select") and "from background_tasks" in statement
    ]
    assert task_selects
    assert all("background_tasks.result" not in statement for statement in task_selects)
    assert all("background_tasks.error" not in statement for statement in task_selects)


def test_writing_pause_and_resume(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    client.post(f"/api/v1/projects/{pid}/writing/start")
    r2 = client.post(f"/api/v1/projects/{pid}/writing/pause")
    assert r2.json()["status"] == "paused"

    r3 = client.post(f"/api/v1/projects/{pid}/writing/resume")
    assert r3.json()["status"] == "running"


def test_writing_resume_creates_generate_chapter_task(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Paused Continuous Writing"})
    pid = r.json()["id"]
    WritingStateService(db_session).run_chapter(pid, 5)
    WritingStateService(db_session).pause(pid)

    with patch("app.api.writing.LocalTaskRunner.start") as start:
        response = client.post(f"/api/v1/projects/{pid}/writing/resume")

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["current_chapter"] == 5
    task = (
        db_session.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == pid,
            BackgroundTask.task_type == "generate_chapter",
        )
        .one()
    )
    assert task.payload == {"chapter_index": 5}
    assert task.status == "pending"
    start.assert_called_once()


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


def test_writing_retry_rejects_chapter_after_project_target(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Retry Target Guard", "target_chapter_count": 1})
    pid = r.json()["id"]

    with patch("app.api.writing.LocalTaskRunner.start") as start:
        response = client.post(f"/api/v1/projects/{pid}/writing/chapters/2/retry")

    assert response.status_code == 400
    assert response.json()["detail"] == "Chapter index exceeds project target chapter count"
    task_count = (
        db_session.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == pid,
            BackgroundTask.task_type == "retry_chapter",
        )
        .count()
    )
    assert task_count == 0
    start.assert_not_called()


def test_writing_retry_rejects_non_positive_chapter_index(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Retry Invalid Index"})
    pid = r.json()["id"]

    with patch("app.api.writing.LocalTaskRunner.start") as start:
        response = client.post(f"/api/v1/projects/{pid}/writing/chapters/0/retry")

    assert response.status_code == 422
    task_count = (
        db_session.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == pid,
            BackgroundTask.task_type == "retry_chapter",
        )
        .count()
    )
    assert task_count == 0
    start.assert_not_called()


def test_writing_retry_reuses_active_task_for_same_chapter(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "No Duplicate Retry Tasks"})
    pid = r.json()["id"]

    with patch("app.api.writing.LocalTaskRunner.start") as start:
        first = client.post(f"/api/v1/projects/{pid}/writing/chapters/2/retry")
        second = client.post(f"/api/v1/projects/{pid}/writing/chapters/2/retry")

    assert first.status_code == 200
    assert second.status_code == 200
    tasks = (
        db_session.query(BackgroundTask)
        .filter(
            BackgroundTask.project_id == pid,
            BackgroundTask.task_type == "retry_chapter",
        )
        .all()
    )
    assert len(tasks) == 1
    assert first.json()["task_id"] == tasks[0].id
    assert second.json()["task_id"] == tasks[0].id
    start.assert_called_once()


def test_writing_retry_does_not_move_next_chapter_pointer_backward(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Retry Old Chapter Pointer"})
    pid = r.json()["id"]
    WritingStateService(db_session).run_chapter(pid, 100)

    with patch("app.api.writing.LocalTaskRunner.start"):
        response = client.post(f"/api/v1/projects/{pid}/writing/chapters/2/retry")

    assert response.status_code == 200
    assert response.json()["current_chapter"] == 100
    state = WritingStateService(db_session).state(pid)
    assert state.current_chapter == 100


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
    assert state.current_chapter == 3
    assert state.last_error is None


@pytest.mark.asyncio
async def test_retry_chapter_work_preserves_forward_pointer_after_old_chapter_success(client, db_session, monkeypatch):
    r = client.post("/api/v1/projects", json={"name": "Retry Old Chapter Success"})
    pid = r.json()["id"]
    WritingStateService(db_session).run_chapter(pid, 100)
    task = BackgroundTaskService(db_session).create(
        project_id=pid,
        task_type="retry_chapter",
        payload={"chapter_index": 2},
    )

    async def fake_generate(project_id, chapter_index, db):
        WritingStateService(db).complete_chapter(project_id, chapter_index)
        return {"chapter_index": chapter_index}

    monkeypatch.setattr("app.api.chapters.generate_chapter", fake_generate)
    from app.api.writing import build_retry_chapter_work

    result = await build_retry_chapter_work(pid, 2)(db_session, task)

    state = WritingStateService(db_session).state(pid)
    assert result == {"chapter_index": 2}
    assert state.status == "idle"
    assert state.current_chapter == 100
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

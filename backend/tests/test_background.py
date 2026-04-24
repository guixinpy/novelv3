from app.models import BackgroundTask


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

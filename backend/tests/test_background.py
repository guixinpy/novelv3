def test_list_background_tasks(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    r2 = client.get(f"/api/v1/projects/{pid}/background-tasks")
    assert r2.status_code == 200
    assert "tasks" in r2.json()


def test_cross_validator():
    from app.core.cross_validator import CrossValidator
    cv = CrossValidator()
    l1 = [{"type": "character_presence", "subject": "李明", "new_value": 3}]
    l2 = [{"type": "character_presence", "subject": "李明", "new_value": 5, "confidence": 0.9}]
    result = cv.validate(l1, l2)
    assert len(result["confirmed"]) == 1


def test_location_checker():
    from app.core.checkers import LocationChecker
    from unittest.mock import MagicMock
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

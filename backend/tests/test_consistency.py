from unittest.mock import AsyncMock, patch

from app.models import BackgroundTask, ChapterContent, Project


def test_consistency_check_detects_dead_character(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as ms, \
         patch("app.api.setups.ai_service.parse_json") as mp:
        ms.return_value.content = '{"world_building": {}, "characters": [{"name": "李明", "character_status": "dead"}], "core_concept": {}}'
        mp.return_value = {"world_building": {}, "characters": [{"name": "李明", "character_status": "dead"}], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    with patch("app.api.chapters.load_api_key", return_value="sk-test"), \
         patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock) as mc:
        mc.return_value.content = "李明冷冷地看着对方。"
        mc.return_value.model = "deepseek-chat"
        mc.return_value.prompt_tokens = 10
        mc.return_value.completion_tokens = 10
        client.post(f"/api/v1/projects/{pid}/chapters/1/generate")

    r2 = client.post(f"/api/v1/projects/{pid}/consistency/chapters/1/check")
    assert r2.status_code == 200
    issues = r2.json()["issues"]
    assert any(i["checker_name"] == "CharacterStateChecker" for i in issues)


def test_list_issues(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.get(f"/api/v1/projects/{pid}/consistency/issues")
    assert r2.status_code == 200
    assert isinstance(r2.json(), list)


def test_deep_check_creates_background_task(client, db_session):
    project = Project(name="Deep Check")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="第一章",
            content="内容",
            status="generated",
        )
    )
    db_session.commit()

    with patch("app.api.consistency.LocalTaskRunner.start") as start:
        response = client.post(f"/api/v1/projects/{project.id}/consistency/chapters/1/check?depth=l2")

    assert response.status_code == 200
    payload = response.json()
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == payload["task_id"]).one()
    assert payload == {"task_id": task.id, "status": "pending"}
    assert task.task_type == "consistency_deep_check"
    assert task.payload == {"chapter_index": 1}
    assert task.status == "pending"
    start.assert_called_once()

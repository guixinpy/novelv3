import asyncio
from unittest.mock import AsyncMock, patch

from app.api.chapters import create_or_replace_chapter


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_generate_chapter(mock_complete, mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as ms, \
         patch("app.api.setups.ai_service.parse_json") as mp:
        ms.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
        mp.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    mock_complete.return_value.content = "第一章正文内容"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200

    r2 = client.post(f"/api/v1/projects/{pid}/chapters/1/generate")
    assert r2.status_code == 200
    assert r2.json()["content"] == "第一章正文内容"
    assert r2.json()["status"] == "generated"


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_generate_chapter_updates_project_and_list_chapter_word_counts(mock_complete, mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as ms, \
         patch("app.api.setups.ai_service.parse_json") as mp:
        ms.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
        mp.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    mock_complete.return_value.content = "alpha beta 第一章"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200

    r2 = client.post(f"/api/v1/projects/{pid}/chapters/1/generate")
    assert r2.status_code == 200
    assert r2.json()["word_count"] == 6

    project = client.get(f"/api/v1/projects/{pid}").json()
    assert project["current_word_count"] == 6

    chapters = client.get(f"/api/v1/projects/{pid}/chapters").json()["chapters"]
    assert chapters[0]["word_count"] == 6


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_create_chapter_applies_user_word_range_to_prompt_and_token_limit(mock_complete, mock_key, client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as ms, \
         patch("app.api.setups.ai_service.parse_json") as mp:
        ms.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
        mp.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    mock_complete.return_value.content = "第一章正文内容"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200

    asyncio.run(create_or_replace_chapter(db_session, pid, 1, extra_feedback="每章约1800-2200字"))

    sent_messages = mock_complete.await_args.args[0]
    assert "正文长度控制在1800-2200字" in sent_messages[0]["content"]
    assert mock_complete.await_args.kwargs["max_tokens"] == 3000


@patch("app.api.chapters.load_api_key", return_value="sk-test")
def test_generate_chapter_project_not_found(mock_key, client):
    r = client.post("/api/v1/projects/nonexistent/chapters/1/generate")
    assert r.status_code == 404


@patch("app.api.chapters.load_api_key", return_value="sk-test")
def test_generate_chapter_without_setup(mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post(f"/api/v1/projects/{pid}/chapters/1/generate")
    assert r2.status_code == 400


@patch("app.api.chapters.load_api_key", return_value="sk-test")
def test_generate_chapter_invalid_index(mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post(f"/api/v1/projects/{pid}/chapters/2/generate")
    assert r2.status_code == 400


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_get_chapter(mock_complete, mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as ms, \
         patch("app.api.setups.ai_service.parse_json") as mp:
        ms.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
        mp.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    mock_complete.return_value.content = "第一章正文内容"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200

    client.post(f"/api/v1/projects/{pid}/chapters/1/generate")

    r2 = client.get(f"/api/v1/projects/{pid}/chapters/1")
    assert r2.status_code == 200
    assert r2.json()["content"] == "第一章正文内容"
    assert r2.json()["status"] == "generated"


def test_get_chapter_not_found(client):
    r = client.get("/api/v1/projects/nonexistent/chapters/1")
    assert r.status_code == 404

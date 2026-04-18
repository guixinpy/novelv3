import asyncio
from unittest.mock import AsyncMock, patch
from app.api.storylines import generate_storyline


@patch("app.api.storylines.load_api_key", return_value="sk-test")
@patch("app.api.storylines.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.storylines.ai_service.parse_json")
def test_generate_storyline(mock_parse, mock_complete, mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as ms, \
         patch("app.api.setups.ai_service.parse_json") as mp:
        ms.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
        mp.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    mock_complete.return_value.content = '{"plotlines": [], "foreshadowing": []}'
    mock_parse.return_value = {"plotlines": [], "foreshadowing": []}

    r2 = client.post(f"/api/v1/projects/{pid}/storyline/generate")
    assert r2.status_code == 200
    assert r2.json()["status"] == "generated"


@patch("app.api.storylines.load_api_key", return_value="sk-test")
def test_generate_storyline_without_setup(mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post(f"/api/v1/projects/{pid}/storyline/generate")
    assert r2.status_code == 400


def test_get_storyline_not_found(client):
    r = client.get("/api/v1/projects/nonexistent/storyline")
    assert r.status_code == 404


@patch("app.api.storylines.load_api_key", return_value="sk-test")
@patch("app.api.storylines.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.storylines.ai_service.parse_json")
@patch("app.api.storylines.PromptManager.load", return_value="BASE_PROMPT")
def test_generate_storyline_appends_command_args_to_prompt(mock_pm_load, mock_parse, mock_complete, mock_key, client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as setup_complete, \
         patch("app.api.setups.ai_service.parse_json") as setup_parse:
        setup_complete.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
        setup_parse.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    mock_complete.return_value.content = '{"plotlines": [], "foreshadowing": []}'
    mock_parse.return_value = {"plotlines": [], "foreshadowing": []}

    asyncio.run(generate_storyline(pid, db_session, command_args="冲突更强烈"))

    sent_messages = mock_complete.await_args.args[0]
    prompt = sent_messages[0]["content"]
    assert "BASE_PROMPT" in prompt
    assert "附加要求：冲突更强烈" in prompt

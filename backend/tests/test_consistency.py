from unittest.mock import AsyncMock, patch


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

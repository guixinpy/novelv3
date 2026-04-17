def test_patch_outline_chapter(client):
    from unittest.mock import AsyncMock, patch
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as ms, \
         patch("app.api.setups.ai_service.parse_json") as mp:
        ms.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
        mp.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    with patch("app.api.storylines.load_api_key", return_value="sk-test"), \
         patch("app.api.storylines.ai_service.complete", new_callable=AsyncMock) as ms2, \
         patch("app.api.storylines.ai_service.parse_json") as mp2:
        ms2.return_value.content = '{"plotlines": [], "foreshadowing": []}'
        mp2.return_value = {"plotlines": [], "foreshadowing": []}
        client.post(f"/api/v1/projects/{pid}/storyline/generate")

    with patch("app.api.outlines.load_api_key", return_value="sk-test"), \
         patch("app.api.outlines.ai_service.complete", new_callable=AsyncMock) as ms3, \
         patch("app.api.outlines.ai_service.parse_json") as mp3:
        ms3.return_value.content = '{"total_chapters": 1, "chapters": [{"chapter_index": 1, "title": "原标题", "summary": "原摘要"}], "plotlines": [], "foreshadowing": []}'
        mp3.return_value = {"total_chapters": 1, "chapters": [{"chapter_index": 1, "title": "原标题", "summary": "原摘要"}], "plotlines": [], "foreshadowing": []}
        client.post(f"/api/v1/projects/{pid}/outline/generate")

    r2 = client.patch(f"/api/v1/projects/{pid}/outline/chapters/1", json={"title": "新标题"})
    assert r2.status_code == 200
    assert r2.json()["updated"] is True

    r3 = client.get(f"/api/v1/projects/{pid}/outline")
    assert r3.json()["chapters"][0]["title"] == "新标题"


def test_update_state(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post(f"/api/v1/projects/{pid}/state", json={"current_view": "outline"})
    assert r2.status_code == 200
    assert r2.json()["ui_state"]["current_view"] == "outline"
    assert "project_diagnosis" in r2.json()

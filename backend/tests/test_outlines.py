from unittest.mock import AsyncMock, patch


@patch("app.api.outlines.load_api_key", return_value="sk-test")
@patch("app.api.outlines.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.outlines.ai_service.parse_json")
def test_generate_outline(mock_parse, mock_complete, mock_key, client):
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

    mock_complete.return_value.content = '{"total_chapters": 3, "chapters": [], "plotlines": [], "foreshadowing": []}'
    mock_parse.return_value = {"total_chapters": 3, "chapters": [], "plotlines": [], "foreshadowing": []}

    r2 = client.post(f"/api/v1/projects/{pid}/outline/generate")
    assert r2.status_code == 200
    assert r2.json()["status"] == "generated"


@patch("app.api.outlines.load_api_key", return_value="sk-test")
def test_generate_outline_without_storyline(mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post(f"/api/v1/projects/{pid}/outline/generate")
    assert r2.status_code == 400


def test_get_outline_not_found(client):
    r = client.get("/api/v1/projects/nonexistent/outline")
    assert r.status_code == 404

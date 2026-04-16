from unittest.mock import AsyncMock, patch


@patch("app.api.setups.AIService.complete", new_callable=AsyncMock)
@patch("app.api.setups.AIService.parse_json")
def test_generate_setup(mock_parse, mock_complete, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    mock_complete.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
    mock_parse.return_value = {"world_building": {}, "characters": [], "core_concept": {}}

    r2 = client.post(f"/api/v1/projects/{pid}/setup/generate")
    assert r2.status_code == 200
    assert r2.json()["status"] == "generated"

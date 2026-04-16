from unittest.mock import AsyncMock, patch


@patch("app.api.setups.load_api_key", return_value="sk-test")
@patch("app.api.setups.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.setups.ai_service.parse_json")
def test_generate_setup(mock_parse, mock_complete, mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    mock_complete.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
    mock_parse.return_value = {"world_building": {}, "characters": [], "core_concept": {}}

    r2 = client.post(f"/api/v1/projects/{pid}/setup/generate")
    assert r2.status_code == 200
    assert r2.json()["status"] == "generated"


@patch("app.api.setups.load_api_key", return_value="sk-test")
def test_generate_setup_project_not_found(mock_key, client):
    r = client.post("/api/v1/projects/nonexistent/setup/generate")
    assert r.status_code == 404


@patch("app.api.setups.load_api_key", return_value="sk-test")
@patch("app.api.setups.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.setups.ai_service.parse_json")
def test_get_setup(mock_parse, mock_complete, mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    mock_complete.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
    mock_parse.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
    client.post(f"/api/v1/projects/{pid}/setup/generate")

    r2 = client.get(f"/api/v1/projects/{pid}/setup")
    assert r2.status_code == 200
    assert r2.json()["status"] == "generated"


def test_get_setup_not_found(client):
    r = client.get("/api/v1/projects/nonexistent/setup")
    assert r.status_code == 404

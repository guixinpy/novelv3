from unittest.mock import AsyncMock, patch


def test_get_topology_creates_on_demand(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as ms, \
         patch("app.api.setups.ai_service.parse_json") as mp:
        ms.return_value.content = '{"world_building": {}, "characters": [{"name": "李明"}], "core_concept": {}}'
        mp.return_value = {"world_building": {}, "characters": [{"name": "李明"}], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    r2 = client.get(f"/api/v1/projects/{pid}/topology")
    assert r2.status_code == 200
    data = r2.json()
    assert any(n["label"] == "李明" for n in data["nodes"])


def test_character_graph(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as ms, \
         patch("app.api.setups.ai_service.parse_json") as mp:
        ms.return_value.content = '{"world_building": {}, "characters": [{"name": "李明"}], "core_concept": {}}'
        mp.return_value = {"world_building": {}, "characters": [{"name": "李明"}], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    r2 = client.get(f"/api/v1/projects/{pid}/topology/character-graph")
    assert r2.status_code == 200
    assert all(n["type"] == "CHARACTER" for n in r2.json()["nodes"])

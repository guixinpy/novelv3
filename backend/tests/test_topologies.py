from unittest.mock import AsyncMock, patch

from app.models import Project, Topology


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


def test_topology_endpoints_return_bounded_windows(client, db_session):
    project = Project(name="Large topology")
    db_session.add(project)
    db_session.commit()
    topology = Topology(
        project_id=project.id,
        nodes=[
            {"id": f"node-{index:03d}", "type": "EVENT", "label": f"Node {index:03d}", "meta": {}}
            for index in range(250)
        ],
        edges=[
            {
                "id": f"edge-{index:03d}",
                "source": f"node-{index % 250:03d}",
                "target": f"node-{(index + 1) % 250:03d}",
                "type": "sequence",
                "meta": {},
            }
            for index in range(620)
        ],
    )
    db_session.add(topology)
    db_session.commit()

    default_response = client.get(f"/api/v1/projects/{project.id}/topology")
    window_response = client.get(
        f"/api/v1/projects/{project.id}/athena/ontology/relations"
        "?node_offset=200&node_limit=25&edge_offset=500&edge_limit=50"
    )

    assert default_response.status_code == 200
    default_payload = default_response.json()
    assert len(default_payload["nodes"]) == 200
    assert len(default_payload["edges"]) == 500
    assert default_payload["nodes_total"] == 250
    assert default_payload["edges_total"] == 620
    assert default_payload["nodes_has_more"] is True
    assert default_payload["edges_has_more"] is True

    assert window_response.status_code == 200
    window_payload = window_response.json()
    assert [node["id"] for node in window_payload["nodes"]][:2] == ["node-200", "node-201"]
    assert len(window_payload["nodes"]) == 25
    assert [edge["id"] for edge in window_payload["edges"]][:2] == ["edge-500", "edge-501"]
    assert len(window_payload["edges"]) == 50
    assert window_payload["nodes_total"] == 250
    assert window_payload["edges_total"] == 620

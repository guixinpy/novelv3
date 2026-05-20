from unittest.mock import AsyncMock, patch

from app.models import WritingAgentRun, WritingAgentStep


@patch("app.api.setups.load_api_key", return_value="sk-test")
@patch("app.api.setups.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.setups.ai_service.parse_json")
def test_athena_ontology_generate_routes_through_writing_agent_run(
    mock_parse,
    mock_complete,
    mock_key,
    client,
    db_session,
):
    project_id = client.post("/api/v1/projects", json={"name": "Agent Setup Button"}).json()["id"]
    mock_complete.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
    mock_parse.return_value = {"world_building": {}, "characters": [], "core_concept": {}}

    response = client.post(f"/api/v1/projects/{project_id}/athena/ontology/generate")

    body = response.json()
    run = db_session.query(WritingAgentRun).filter_by(project_id=project_id).one()
    step = db_session.query(WritingAgentStep).filter_by(run_id=run.id).one()
    assert response.status_code == 200
    assert body["status"] == "generated"
    assert body["agent_run_id"] == run.id
    assert body["control_plane"]["source"] == "athena_ontology_generate"
    assert run.entrypoint == "athena_ontology_generate"
    assert run.status == "success"
    assert run.input["control_plane"]["source"] == "athena_ontology_generate"
    assert run.input["tools"][0]["tool_name"] == "generate_setup"
    assert step.tool_name == "generate_setup"
    assert step.status == "success"
    assert step.target_type == "setup"
    assert step.target_id == body["id"]


@patch("app.api.setups.load_api_key", return_value=None)
def test_athena_ontology_generate_preserves_missing_api_key_400(mock_key, client):
    project_id = client.post("/api/v1/projects", json={"name": "Missing Key Agent Setup"}).json()["id"]

    response = client.post(f"/api/v1/projects/{project_id}/athena/ontology/generate")

    assert response.status_code == 400
    assert response.json()["detail"] == "API key not configured"

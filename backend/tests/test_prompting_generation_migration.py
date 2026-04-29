from unittest.mock import AsyncMock, patch


def _trace_detail(client, project_id: str, trace_type: str) -> dict:
    traces = client.get(f"/api/v1/projects/{project_id}/model-call-traces?trace_type={trace_type}").json()
    assert traces["total"] == 1
    trace_id = traces["items"][0]["id"]
    return client.get(f"/api/v1/projects/{project_id}/model-call-traces/{trace_id}").json()


def _assert_prompt_metadata(trace: dict, *, prompt_id: str, template_name: str) -> None:
    metadata = trace["trace_metadata"]
    assert metadata["prompt_id"] == prompt_id
    assert metadata["prompt_version"]
    assert metadata["template_name"] == template_name
    assert metadata["template_hash"].startswith("sha256:")


@patch("app.api.setups.load_api_key", return_value="sk-test")
@patch("app.api.setups.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.setups.ai_service.parse_json")
def test_setup_generation_trace_metadata_and_context_blocks(mock_parse, mock_complete, mock_key, client):
    response = client.post("/api/v1/projects", json={"name": "潮汐门"})
    project_id = response.json()["id"]
    mock_complete.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
    mock_parse.return_value = {"world_building": {}, "characters": [], "core_concept": {}}

    generated = client.post(f"/api/v1/projects/{project_id}/setup/generate")

    assert generated.status_code == 200
    trace = _trace_detail(client, project_id, "setup_generation")
    _assert_prompt_metadata(trace, prompt_id="setup.generate", template_name="generate_setup")
    assert {block["key"] for block in trace["context_blocks"]} == {
        "project_profile",
        "generate_setup_template",
    }


@patch("app.api.storylines.load_api_key", return_value="sk-test")
@patch("app.api.storylines.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.storylines.ai_service.parse_json")
def test_storyline_generation_trace_metadata_and_context_blocks(mock_parse, mock_complete, mock_key, client):
    response = client.post("/api/v1/projects", json={"name": "雾港二十夜"})
    project_id = response.json()["id"]
    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as setup_complete, \
         patch("app.api.setups.ai_service.parse_json") as setup_parse:
        setup_complete.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
        setup_parse.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
        client.post(f"/api/v1/projects/{project_id}/setup/generate")
    mock_complete.return_value.content = '{"plotlines": [], "foreshadowing": []}'
    mock_parse.return_value = {"plotlines": [], "foreshadowing": []}

    generated = client.post(f"/api/v1/projects/{project_id}/storyline/generate")

    assert generated.status_code == 200
    trace = _trace_detail(client, project_id, "storyline_generation")
    _assert_prompt_metadata(trace, prompt_id="storyline.generate", template_name="generate_storyline")
    assert {block["key"] for block in trace["context_blocks"]} == {
        "setup_world_building",
        "setup_characters",
        "setup_core_concept",
        "generate_storyline_template",
    }


@patch("app.api.outlines.load_api_key", return_value="sk-test")
@patch("app.api.outlines.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.outlines.ai_service.parse_json")
def test_outline_generation_trace_metadata_and_context_blocks(mock_parse, mock_complete, mock_key, client):
    response = client.post("/api/v1/projects", json={"name": "十章项目", "target_chapter_count": 10})
    project_id = response.json()["id"]
    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as setup_complete, \
         patch("app.api.setups.ai_service.parse_json") as setup_parse:
        setup_complete.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
        setup_parse.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
        client.post(f"/api/v1/projects/{project_id}/setup/generate")
    with patch("app.api.storylines.load_api_key", return_value="sk-test"), \
         patch("app.api.storylines.ai_service.complete", new_callable=AsyncMock) as storyline_complete, \
         patch("app.api.storylines.ai_service.parse_json") as storyline_parse:
        storyline_complete.return_value.content = '{"plotlines": [], "foreshadowing": []}'
        storyline_parse.return_value = {"plotlines": [], "foreshadowing": []}
        client.post(f"/api/v1/projects/{project_id}/storyline/generate")
    mock_complete.return_value.content = '{"total_chapters": 10, "chapters": [], "plotlines": [], "foreshadowing": []}'
    mock_parse.return_value = {"total_chapters": 10, "chapters": [], "plotlines": [], "foreshadowing": []}

    generated = client.post(f"/api/v1/projects/{project_id}/outline/generate")

    assert generated.status_code == 200
    trace = _trace_detail(client, project_id, "outline_generation")
    _assert_prompt_metadata(trace, prompt_id="outline.generate", template_name="generate_outline")
    assert {block["key"] for block in trace["context_blocks"]} == {
        "setup_world_building",
        "setup_characters",
        "setup_core_concept",
        "storyline_context",
        "outline_target",
        "generate_outline_template",
    }

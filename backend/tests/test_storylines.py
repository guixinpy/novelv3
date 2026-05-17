import asyncio
from unittest.mock import AsyncMock, patch

from sqlalchemy import event

from app.api import storylines
from app.api.storylines import generate_storyline
from app.models import Project, Setup


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
    traces = client.get(f"/api/v1/projects/{pid}/model-call-traces?trace_type=storyline_generation").json()
    assert traces["total"] == 1
    trace = client.get(f"/api/v1/projects/{pid}/model-call-traces/{traces['items'][0]['id']}").json()
    assert trace["status"] == "success"
    assert {block["key"] for block in trace["context_blocks"]} >= {
        "setup_world_building",
        "setup_characters",
        "setup_core_concept",
        "generate_storyline_template",
    }


@patch("app.api.storylines.load_api_key", return_value="sk-test")
@patch("app.api.storylines.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.storylines.ai_service.parse_json")
def test_generate_storyline_uses_project_ai_model(mock_parse, mock_complete, mock_key, client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Model Routed Storyline"})
    pid = r.json()["id"]
    project = db_session.get(Project, pid)
    project.ai_model = "deepseek-reasoner"
    db_session.commit()

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as setup_complete, \
         patch("app.api.setups.ai_service.parse_json") as setup_parse:
        setup_complete.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
        setup_parse.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    mock_complete.return_value.content = '{"plotlines": [], "foreshadowing": []}'
    mock_parse.return_value = {"plotlines": [], "foreshadowing": []}

    r2 = client.post(f"/api/v1/projects/{pid}/storyline/generate")

    assert r2.status_code == 200
    assert mock_complete.await_args.kwargs["model"] == "deepseek-reasoner"


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
def test_generate_storyline_appends_command_args_to_prompt(mock_parse, mock_complete, mock_key, client, db_session):
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
    assert "Test" in prompt
    assert "附加要求：冲突更强烈" in prompt
    traces = client.get(f"/api/v1/projects/{pid}/model-call-traces?trace_type=storyline_generation").json()
    trace = client.get(f"/api/v1/projects/{pid}/model-call-traces/{traces['items'][0]['id']}").json()
    assert {block["key"] for block in trace["context_blocks"]} >= {"command_args"}
    command_args_block = next(block for block in trace["context_blocks"] if block["key"] == "command_args")
    assert command_args_block["kind"] == "user_feedback"


def test_storyline_prompt_bounds_oversized_setup_context(db_session):
    project = Project(name="长篇故事线预算", genre="硬科幻")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    world_mid_noise = "MID_STORYLINE_WORLD_NOISE_SHOULD_NOT_APPEAR"
    character_mid_noise = "MID_STORYLINE_CHARACTER_NOISE_SHOULD_NOT_APPEAR"
    concept_mid_noise = "MID_STORYLINE_CONCEPT_NOISE_SHOULD_NOT_APPEAR"
    setup = Setup(
        project_id=project.id,
        world_building={
            "city": "雾港",
            "lore": ("世界观噪音" * 700) + world_mid_noise + ("更多世界观噪音" * 10_000),
        },
        characters=[
            {
                "name": "林舟",
                "bio": ("角色噪音" * 700) + character_mid_noise + ("更多角色噪音" * 10_000),
            }
        ],
        core_concept={
            "hook": "旧灯塔记忆病毒",
            "long": ("核心概念噪音" * 700) + concept_mid_noise + ("更多核心噪音" * 10_000),
        },
    )

    payload = storylines._build_storyline_call_payload(project, setup)

    prompt = payload["messages"][0]["content"]
    assert "雾港" in prompt
    assert "林舟" in prompt
    assert "旧灯塔记忆病毒" in prompt
    assert world_mid_noise not in prompt
    assert character_mid_noise not in prompt
    assert concept_mid_noise not in prompt
    assert "truncated: original content exceeded trace limit" not in prompt
    assert len(prompt) <= 8_000


@patch("app.api.storylines.load_api_key", return_value="sk-test")
@patch("app.api.storylines.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.storylines.ai_service.parse_json")
def test_generate_storyline_uses_bounded_setup_context_without_selecting_full_json(
    mock_parse,
    mock_complete,
    mock_key,
    client,
    db_session,
):
    project = Project(name="Bounded Storyline Setup", genre="长篇悬疑")
    db_session.add(project)
    db_session.flush()
    world_mid_noise = "MID_STORYLINE_QUERY_WORLD_NOISE_SHOULD_NOT_APPEAR"
    character_mid_noise = "MID_STORYLINE_QUERY_CHARACTER_NOISE_SHOULD_NOT_APPEAR"
    concept_mid_noise = "MID_STORYLINE_QUERY_CONCEPT_NOISE_SHOULD_NOT_APPEAR"
    db_session.add(
        Setup(
            project_id=project.id,
            status="generated",
            world_building={
                "city": "雾港",
                "lore": ("世界观噪音" * 700) + world_mid_noise + ("更多世界观噪音" * 10_000),
            },
            characters=[
                {
                    "name": "林舟",
                    "bio": ("角色噪音" * 700) + character_mid_noise + ("更多角色噪音" * 10_000),
                }
            ],
            core_concept={
                "hook": "旧灯塔记忆病毒",
                "long": ("核心概念噪音" * 700) + concept_mid_noise + ("更多核心噪音" * 10_000),
            },
        )
    )
    db_session.commit()
    mock_complete.return_value.content = '{"plotlines": [], "foreshadowing": []}'
    mock_parse.return_value = {"plotlines": [], "foreshadowing": []}
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.post(f"/api/v1/projects/{project.id}/storyline/generate")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    sent_prompt = mock_complete.await_args.args[0][0]["content"]
    assert "雾港" in sent_prompt
    assert "林舟" in sent_prompt
    assert "旧灯塔记忆病毒" in sent_prompt
    assert world_mid_noise not in sent_prompt
    assert character_mid_noise not in sent_prompt
    assert concept_mid_noise not in sent_prompt

    setup_select_clauses = [
        statement.split(" from setups", 1)[0]
        for statement in statements
        if " from setups" in statement
    ]
    assert setup_select_clauses
    assert all("setups.world_building as setups_world_building" not in clause for clause in setup_select_clauses)
    assert all("setups.characters as setups_characters" not in clause for clause in setup_select_clauses)
    assert all("setups.core_concept as setups_core_concept" not in clause for clause in setup_select_clauses)

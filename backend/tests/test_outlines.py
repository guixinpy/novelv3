import asyncio
from unittest.mock import AsyncMock, patch

from sqlalchemy import event

from app.api.outlines import generate_outline
from app.models import Outline, Project, Setup, Storyline


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
    traces = client.get(f"/api/v1/projects/{pid}/model-call-traces?trace_type=outline_generation").json()
    assert traces["total"] == 1
    trace = client.get(f"/api/v1/projects/{pid}/model-call-traces/{traces['items'][0]['id']}").json()
    assert trace["status"] == "success"
    assert {block["key"] for block in trace["context_blocks"]} >= {
        "setup_world_building",
        "setup_characters",
        "setup_core_concept",
        "storyline_context",
        "outline_target",
        "generate_outline_template",
    }


@patch("app.api.outlines.load_api_key", return_value="sk-test")
def test_generate_outline_without_storyline(mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post(f"/api/v1/projects/{pid}/outline/generate")
    assert r2.status_code == 400


def test_get_outline_not_found(client):
    r = client.get("/api/v1/projects/nonexistent/outline")
    assert r.status_code == 404


@patch("app.api.outlines.load_api_key", return_value="sk-test")
@patch("app.api.outlines.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.outlines.ai_service.parse_json")
def test_generate_outline_appends_command_args_to_prompt(mock_parse, mock_complete, mock_key, client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as setup_complete, \
         patch("app.api.setups.ai_service.parse_json") as setup_parse:
        setup_complete.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
        setup_parse.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    with patch("app.api.storylines.load_api_key", return_value="sk-test"), \
         patch("app.api.storylines.ai_service.complete", new_callable=AsyncMock) as storyline_complete, \
         patch("app.api.storylines.ai_service.parse_json") as storyline_parse:
        storyline_complete.return_value.content = '{"plotlines": [], "foreshadowing": []}'
        storyline_parse.return_value = {"plotlines": [], "foreshadowing": []}
        client.post(f"/api/v1/projects/{pid}/storyline/generate")

    mock_complete.return_value.content = '{"total_chapters": 3, "chapters": [], "plotlines": [], "foreshadowing": []}'
    mock_parse.return_value = {"total_chapters": 3, "chapters": [], "plotlines": [], "foreshadowing": []}

    asyncio.run(generate_outline(pid, db_session, command_args="每章结尾留悬念"))

    sent_messages = mock_complete.await_args.args[0]
    prompt = sent_messages[0]["content"]
    assert "Test" in prompt
    assert "附加要求：每章结尾留悬念" in prompt
    traces = client.get(f"/api/v1/projects/{pid}/model-call-traces?trace_type=outline_generation").json()
    trace = client.get(f"/api/v1/projects/{pid}/model-call-traces/{traces['items'][0]['id']}").json()
    assert {block["key"] for block in trace["context_blocks"]} >= {"command_args"}
    command_args_block = next(block for block in trace["context_blocks"] if block["key"] == "command_args")
    assert command_args_block["kind"] == "user_feedback"


@patch("app.api.outlines.load_api_key", return_value="sk-test")
@patch("app.api.outlines.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.outlines.ai_service.parse_json")
def test_generate_outline_passes_setup_context_to_prompt(mock_parse, mock_complete, mock_key, client, db_session):
    r = client.post("/api/v1/projects", json={"name": "雾港二十夜"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as setup_complete, \
         patch("app.api.setups.ai_service.parse_json") as setup_parse:
        setup_complete.return_value.content = '{"world_building": {}, "characters": [{"name": "林舟"}, {"name": "沈聆"}], "core_concept": {"hook": "旧灯塔"}}'
        setup_parse.return_value = {
            "world_building": {},
            "characters": [{"name": "林舟"}, {"name": "沈聆"}],
            "core_concept": {"hook": "旧灯塔"},
        }
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    with patch("app.api.storylines.load_api_key", return_value="sk-test"), \
         patch("app.api.storylines.ai_service.complete", new_callable=AsyncMock) as storyline_complete, \
         patch("app.api.storylines.ai_service.parse_json") as storyline_parse:
        storyline_complete.return_value.content = '{"plotlines": [], "foreshadowing": []}'
        storyline_parse.return_value = {"plotlines": [], "foreshadowing": []}
        client.post(f"/api/v1/projects/{pid}/storyline/generate")

    mock_complete.return_value.content = '{"total_chapters": 3, "chapters": [], "plotlines": [], "foreshadowing": []}'
    mock_parse.return_value = {"total_chapters": 3, "chapters": [], "plotlines": [], "foreshadowing": []}

    asyncio.run(generate_outline(pid, db_session))

    sent_messages = mock_complete.await_args.args[0]
    prompt = sent_messages[0]["content"]
    assert "林舟" in prompt
    assert "沈聆" in prompt
    assert "旧灯塔" in prompt


@patch("app.api.outlines.load_api_key", return_value="sk-test")
@patch("app.api.outlines.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.outlines.ai_service.parse_json")
def test_generate_outline_prefers_project_target_chapter_count(mock_parse, mock_complete, mock_key, client):
    r = client.post(
        "/api/v1/projects",
        json={"name": "十章项目", "target_chapter_count": 10, "target_word_count": 60000},
    )
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as setup_complete, \
         patch("app.api.setups.ai_service.parse_json") as setup_parse:
        setup_complete.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
        setup_parse.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    with patch("app.api.storylines.load_api_key", return_value="sk-test"), \
         patch("app.api.storylines.ai_service.complete", new_callable=AsyncMock) as storyline_complete, \
         patch("app.api.storylines.ai_service.parse_json") as storyline_parse:
        storyline_complete.return_value.content = '{"plotlines": [], "foreshadowing": []}'
        storyline_parse.return_value = {"plotlines": [], "foreshadowing": []}
        client.post(f"/api/v1/projects/{pid}/storyline/generate")

    mock_complete.return_value.content = '{"total_chapters": 10, "chapters": [], "plotlines": [], "foreshadowing": []}'
    mock_parse.return_value = {"total_chapters": 10, "chapters": [], "plotlines": [], "foreshadowing": []}

    response = client.post(f"/api/v1/projects/{pid}/outline/generate")

    assert response.status_code == 200
    sent_messages = mock_complete.await_args.args[0]
    prompt = sent_messages[0]["content"]
    assert "十章项目" in prompt
    assert "10" in prompt


def test_patch_outline_chapter_updates_json_without_selecting_full_chapters(client, db_session):
    project = Project(name="Patch Large Outline")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        Outline(
            project_id=project.id,
            status="generated",
            total_chapters=1000,
            chapters=[
                {
                    "chapter_index": index,
                    "title": f"第{index}章",
                    "summary": "章节摘要" * 20,
                    "scenes": ["旧场景"],
                    "characters": ["旧角色"],
                    "purpose": "旧目的",
                }
                for index in range(1, 1001)
            ],
        )
    )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.patch(
            f"/api/v1/projects/{project.id}/outline/chapters/512",
            json={
                "title": "新的第512章",
                "scenes": ["新场景"],
                "characters": ["新角色"],
                "purpose": "新目的",
            },
        )
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    updated_outline = db_session.query(Outline).filter(Outline.project_id == project.id).one()
    updated = updated_outline.chapters[511]
    assert updated["chapter_index"] == 512
    assert updated["title"] == "新的第512章"
    assert updated["summary"] == "章节摘要" * 20
    assert updated["scenes"] == ["新场景"]
    assert updated["characters"] == ["新角色"]
    assert updated["purpose"] == "新目的"
    assert updated_outline.chapters[510]["title"] == "第511章"
    assert updated_outline.chapters[512]["title"] == "第513章"

    select_clauses = [
        statement.split(" from outlines", 1)[0]
        for statement in statements
        if " from outlines" in statement
    ]
    assert select_clauses
    assert any("json_each(outlines.chapters)" in statement for statement in statements)
    assert any("json_set" in statement for statement in statements)
    assert all("outlines.chapters as" not in clause for clause in select_clauses)


@patch("app.api.outlines.load_api_key", return_value="sk-test")
@patch("app.api.outlines.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.outlines.ai_service.parse_json")
def test_generate_outline_uses_bounded_storyline_context_without_selecting_full_json(
    mock_parse,
    mock_complete,
    mock_key,
    client,
    db_session,
):
    project = Project(name="Bounded Outline Prompt", target_chapter_count=1000)
    db_session.add(project)
    db_session.flush()
    db_session.add(
        Setup(
            project_id=project.id,
            status="generated",
            world_building={},
            characters=[],
            core_concept={},
        )
    )
    db_session.add(
        Storyline(
            project_id=project.id,
            status="generated",
            plotlines=[
                {
                    "name": f"故事线{index}",
                    "type": "sub",
                    "summary": "故事线摘要" * 20,
                    "milestones": [
                        {"chapter_index": chapter, "title": f"节点{chapter}"}
                        for chapter in range(1, 1001)
                    ],
                }
                for index in range(1, 61)
            ],
            foreshadowing=[
                {
                    "hint": f"伏笔{index}",
                    "planted_chapter": index,
                    "resolved_chapter": index + 100,
                    "status": "planted",
                }
                for index in range(1, 501)
            ],
        )
    )
    db_session.commit()
    mock_complete.return_value.content = "{}"
    mock_parse.return_value = {"total_chapters": 1000, "chapters": [], "plotlines": [], "foreshadowing": []}
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.post(f"/api/v1/projects/{project.id}/outline/generate")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    sent_prompt = mock_complete.await_args.args[0][0]["content"]
    assert "故事线总数" in sent_prompt
    assert "伏笔总数" in sent_prompt
    assert "故事线1" in sent_prompt
    assert "故事线21" not in sent_prompt
    assert "伏笔101" not in sent_prompt
    traces = client.get(f"/api/v1/projects/{project.id}/model-call-traces?trace_type=outline_generation").json()
    trace = client.get(f"/api/v1/projects/{project.id}/model-call-traces/{traces['items'][0]['id']}").json()
    storyline_block = next(block for block in trace["context_blocks"] if block["key"] == "storyline_context")
    assert "故事线总数" in storyline_block["content"]
    assert "伏笔总数" in storyline_block["content"]

    storyline_select_clauses = [
        statement.split(" from storylines", 1)[0]
        for statement in statements
        if " from storylines" in statement
    ]
    assert storyline_select_clauses
    assert any("json_each(storylines.plotlines)" in statement for statement in statements)
    assert any("json_each(storylines.foreshadowing)" in statement for statement in statements)
    assert all("storylines.plotlines as" not in clause for clause in storyline_select_clauses)
    assert all("storylines.foreshadowing as" not in clause for clause in storyline_select_clauses)

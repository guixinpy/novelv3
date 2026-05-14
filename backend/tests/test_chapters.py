import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import event

from app.api.chapters import create_or_replace_chapter
from app.models import (
    AIModelCallTrace,
    ChapterContent,
    GenreProfile,
    LongformMemory,
    Outline,
    Project,
    ProjectProfileVersion,
    RetrievalDocument,
    Setup,
    WorldFactClaim,
)


def _create_project_with_setup(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as ms, \
         patch("app.api.setups.ai_service.parse_json") as mp:
        ms.return_value.content = '{"world_building": {"city": "雾城"}, "characters": [{"name": "林舟"}], "core_concept": {"hook": "灯塔"}}'
        mp.return_value = {
            "world_building": {"city": "雾城"},
            "characters": [{"name": "林舟"}],
            "core_concept": {"hook": "灯塔"},
        }
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    return pid


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_generate_chapter(mock_complete, mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as ms, \
         patch("app.api.setups.ai_service.parse_json") as mp:
        ms.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
        mp.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    mock_complete.return_value.content = "第一章正文内容"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200

    r2 = client.post(f"/api/v1/projects/{pid}/chapters/1/generate")
    assert r2.status_code == 200
    assert r2.json()["content"] == "第一章正文内容"
    assert r2.json()["status"] == "generated"


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_generate_chapter_records_model_call_trace(mock_complete, mock_key, client):
    pid = _create_project_with_setup(client)
    mock_complete.return_value.content = "第一章正文内容"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 123
    mock_complete.return_value.completion_tokens = 456

    response = client.post(f"/api/v1/projects/{pid}/chapters/1/generate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["last_generation_trace_id"]

    trace_response = client.get(f"/api/v1/projects/{pid}/model-call-traces/{payload['last_generation_trace_id']}")
    assert trace_response.status_code == 200
    trace = trace_response.json()
    assert trace["trace_type"] == "chapter_generation"
    assert trace["chapter_index"] == 1
    assert trace["status"] == "success"
    assert trace["prompt_tokens"] == 123
    assert trace["trace_metadata"]["prompt_id"] == "chapter.generate"
    context_kinds = {block["kind"] for block in trace["context_blocks"]}
    assert "setup" in context_kinds
    assert "athena_context" in context_kinds
    assert "prompt_template" in context_kinds
    sent_messages = mock_complete.await_args.args[0]
    assert trace["messages"][0]["content"] == sent_messages[0]["content"]


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_generate_chapter_prompt_uses_requested_chapter_index(mock_complete, mock_key, client):
    pid = _create_project_with_setup(client)
    mock_complete.return_value.content = "第三章正文内容"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 123
    mock_complete.return_value.completion_tokens = 456

    response = client.post(f"/api/v1/projects/{pid}/chapters/3/generate")

    assert response.status_code == 200
    sent_messages = mock_complete.await_args.args[0]
    assert "创作第 3 章正文" in sent_messages[0]["content"]
    assert "创作第 1 章正文" not in sent_messages[0]["content"]


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_generate_chapter_trace_records_rendered_style_rules(mock_complete, mock_key, client, db_session):
    pid = _create_project_with_setup(client)
    project = db_session.get(Project, pid)
    project.style_config = {"description_density": 4}
    db_session.commit()
    mock_complete.return_value.content = "第一章正文内容"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 123
    mock_complete.return_value.completion_tokens = 456

    response = client.post(f"/api/v1/projects/{pid}/chapters/1/generate")

    assert response.status_code == 200
    trace_id = response.json()["last_generation_trace_id"]
    trace = client.get(f"/api/v1/projects/{pid}/model-call-traces/{trace_id}").json()
    assert "【用户偏好规则】" in trace["messages"][0]["content"]
    assert "增加环境描写和感官细节" in trace["messages"][0]["content"]
    style_rule_blocks = [
        block for block in trace["context_blocks"]
        if block["kind"] == "style_rule"
    ]
    assert style_rule_blocks
    assert "【用户偏好规则】" in style_rule_blocks[0]["content"]
    assert "增加环境描写和感官细节" in style_rule_blocks[0]["content"]


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_get_chapter_returns_last_generation_trace_id(mock_complete, mock_key, client):
    pid = _create_project_with_setup(client)
    mock_complete.return_value.content = "第一章正文内容"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200

    generated = client.post(f"/api/v1/projects/{pid}/chapters/1/generate").json()

    response = client.get(f"/api/v1/projects/{pid}/chapters/1")

    assert response.status_code == 200
    assert response.json()["last_generation_trace_id"] == generated["last_generation_trace_id"]


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_generate_chapter_model_failure_records_failed_trace_and_reraises(mock_complete, mock_key, client, db_session):
    pid = _create_project_with_setup(client)
    mock_complete.side_effect = RuntimeError("fake model outage")

    with pytest.raises(RuntimeError, match="fake model outage"):
        client.post(f"/api/v1/projects/{pid}/chapters/1/generate")

    trace = (
        db_session.query(AIModelCallTrace)
        .filter(
            AIModelCallTrace.project_id == pid,
            AIModelCallTrace.trace_type == "chapter_generation",
            AIModelCallTrace.chapter_index == 1,
        )
        .one()
    )
    assert trace.status == "failed"
    assert "fake model outage" in trace.error_message


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_generate_chapter_keeps_chapter_when_trace_success_mark_fails(mock_complete, mock_key, client, monkeypatch):
    pid = _create_project_with_setup(client)
    mock_complete.return_value.content = "第一章正文内容"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200
    monkeypatch.setattr(
        "app.api.chapters.mark_trace_success",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("trace mark failed")),
        raising=False,
    )

    response = client.post(f"/api/v1/projects/{pid}/chapters/1/generate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["content"] == "第一章正文内容"
    assert payload["last_generation_trace_id"] is None


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_generate_chapter_updates_project_and_list_chapter_word_counts(mock_complete, mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as ms, \
         patch("app.api.setups.ai_service.parse_json") as mp:
        ms.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
        mp.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    mock_complete.return_value.content = "alpha beta 第一章"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200

    r2 = client.post(f"/api/v1/projects/{pid}/chapters/1/generate")
    assert r2.status_code == 200
    assert r2.json()["word_count"] == 5

    project = client.get(f"/api/v1/projects/{pid}").json()
    assert project["current_word_count"] == 5
    assert project["current_phase"] == "content"
    assert project["status"] == "writing"

    chapters = client.get(f"/api/v1/projects/{pid}/chapters").json()["chapters"]
    assert chapters[0]["word_count"] == 5


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_generate_chapter_reconciles_word_count_with_aggregate_query(mock_complete, mock_key, client, db_session):
    pid = _create_project_with_setup(client)
    project = db_session.get(Project, pid)
    for index in range(1, 121):
        db_session.add(
            ChapterContent(
                project_id=pid,
                chapter_index=index,
                title=f"第{index}章",
                content="已有正文。",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    mock_complete.return_value.content = "新增章节正文"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement.lower())

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        chapter = asyncio.run(create_or_replace_chapter(db_session, pid, 121))
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    db_session.refresh(project)
    assert chapter.chapter_index == 121
    assert project.current_word_count == 120000 + chapter.word_count
    unbounded_chapter_row_selects = []
    for statement in statements:
        if "select chapter_contents.id" not in statement or "from chapter_contents" not in statement:
            continue
        where_index = statement.find("where")
        where_clause = statement[where_index:] if where_index >= 0 else ""
        if "chapter_contents.project_id" in where_clause and "chapter_contents.chapter_index =" not in where_clause:
            unbounded_chapter_row_selects.append(statement)
    assert not unbounded_chapter_row_selects


def test_chapter_prompt_outline_target_does_not_select_full_outline_json(db_session):
    from app.prompting.providers.chapter import _build_outline_chapter_target_block

    project = Project(name="千章生成上下文")
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
                    "summary": f"第{index}章目标摘要。",
                    "scenes": [f"场景{index}"],
                    "characters": [f"角色{index}"],
                }
                for index in range(1, 1001)
            ],
            plotlines=[{"name": f"支线{index}", "summary": "支线摘要" * 20} for index in range(1, 101)],
            foreshadowing=[{"name": f"伏笔{index}", "summary": "伏笔摘要" * 20} for index in range(1, 101)],
        )
    )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        block = _build_outline_chapter_target_block(db_session, project.id, 777)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert block is not None
    assert "第777章：第777章目标摘要。" in block["content"]
    assert "场景777" in block["content"]
    assert "角色777" in block["content"]

    outline_select_clauses = [
        statement.split("from outlines", 1)[0]
        for statement in statements
        if "from outlines" in statement
    ]
    assert outline_select_clauses
    assert all("outlines.chapters as" not in clause for clause in outline_select_clauses)
    assert all("outlines.plotlines as" not in clause for clause in outline_select_clauses)
    assert all("outlines.foreshadowing as" not in clause for clause in outline_select_clauses)


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_generate_chapter_does_not_select_full_outline_json_for_title_or_memory(
    mock_complete,
    mock_key,
    db_session,
):
    project = Project(name="千章生成维护")
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
        Outline(
            project_id=project.id,
            status="generated",
            total_chapters=1000,
            chapters=[
                {
                    "chapter_index": index,
                    "title": f"第{index}章",
                    "summary": f"第{index}章目标摘要。",
                    "scenes": [f"场景{index}"],
                    "characters": [f"角色{index}"],
                }
                for index in range(1, 1001)
            ],
            plotlines=[{"name": f"支线{index}", "summary": "支线摘要" * 20} for index in range(1, 101)],
            foreshadowing=[{"name": f"伏笔{index}", "summary": "伏笔摘要" * 20} for index in range(1, 101)],
        )
    )
    db_session.commit()
    mock_complete.return_value.content = "第777章正文。星环钥匙在本章完成校准。"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        chapter = asyncio.run(create_or_replace_chapter(db_session, project.id, 777))
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert chapter.title == "第777章"
    assert (
        db_session.query(LongformMemory)
        .filter(LongformMemory.project_id == project.id, LongformMemory.scope_key == "chapter:777")
        .one()
    )

    outline_select_clauses = [
        statement.split("from outlines", 1)[0]
        for statement in statements
        if "from outlines" in statement
    ]
    assert outline_select_clauses
    assert all("outlines.chapters as" not in clause for clause in outline_select_clauses)
    assert all("outlines.plotlines as" not in clause for clause in outline_select_clauses)
    assert all("outlines.foreshadowing as" not in clause for clause in outline_select_clauses)


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_generate_chapter_refreshes_longform_memory_and_retrieval(mock_complete, mock_key, client, db_session):
    from app.core.athena_retrieval import reindex_project_retrieval, search_retrieval
    from app.core.longform_memory import rebuild_longform_memory

    pid = _create_project_with_setup(client)
    for index in range(1, 4):
        db_session.add(
            ChapterContent(
                project_id=pid,
                chapter_index=index,
                title=f"第{index}章",
                content=f"第{index}章旧正文。星环钥匙第一形态。",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    rebuild_longform_memory(db_session, pid)
    reindex_project_retrieval(db_session, pid)
    chapter_1_doc_id = _longform_memory_doc_id(db_session, pid, "memory:chapter:1")
    chapter_2_doc_id = _longform_memory_doc_id(db_session, pid, "memory:chapter:2")
    mock_complete.return_value.content = "星环钥匙第四形态在第二章启动，陆辞确认雾灯失效。"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200

    response = client.post(f"/api/v1/projects/{pid}/chapters/2/generate")

    assert response.status_code == 200
    db_session.expire_all()
    chapter_memory = (
        db_session.query(LongformMemory)
        .filter(LongformMemory.project_id == pid, LongformMemory.scope_key == "chapter:2")
        .one()
    )
    assert "星环钥匙第四形态" in chapter_memory.summary
    assert _longform_memory_doc_id(db_session, pid, "memory:chapter:1") == chapter_1_doc_id
    assert _longform_memory_doc_id(db_session, pid, "memory:chapter:2") != chapter_2_doc_id
    results = search_retrieval(
        db_session,
        pid,
        "星环钥匙第四形态",
        source_type="longform_memory",
        max_chapter_index=3,
    )
    assert any(
        item["source_ref"] == "memory:chapter:2" and "星环钥匙第四形态" in item["snippet"]
        for item in results["items"]
    )


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_generate_chapter_does_not_fail_when_longform_maintenance_fails(mock_complete, mock_key, client, monkeypatch):
    pid = _create_project_with_setup(client)
    mock_complete.return_value.content = "第一章正文内容"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200
    monkeypatch.setattr(
        "app.api.chapters.refresh_longform_memory_for_chapter",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("maintenance failed")),
    )

    response = client.post(f"/api/v1/projects/{pid}/chapters/1/generate")

    assert response.status_code == 200
    assert response.json()["content"] == "第一章正文内容"


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_generate_chapter_rolls_back_when_retrieval_indexing_fails(
    mock_complete,
    mock_key,
    client,
    db_session,
    monkeypatch,
):
    pid = _create_project_with_setup(client)
    mock_complete.return_value.content = "第一章正文内容"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200
    rollback_calls = {"value": 0}
    original_rollback = db_session.rollback

    def count_rollback():
        rollback_calls["value"] += 1
        return original_rollback()

    def fail_indexing(*_args, **_kwargs):
        raise RuntimeError("retrieval indexing failed")

    monkeypatch.setattr(db_session, "rollback", count_rollback)
    monkeypatch.setattr("app.core.athena_retrieval.index_chapter_retrieval", fail_indexing)

    chapter = asyncio.run(create_or_replace_chapter(db_session, pid, 1))

    assert chapter.content == "第一章正文内容"
    assert rollback_calls["value"] >= 1


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_create_chapter_applies_user_word_range_to_prompt_and_token_limit(mock_complete, mock_key, client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as ms, \
         patch("app.api.setups.ai_service.parse_json") as mp:
        ms.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
        mp.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    mock_complete.return_value.content = "第一章正文内容"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200

    asyncio.run(create_or_replace_chapter(db_session, pid, 1, extra_feedback="每章约1800-2200字"))

    sent_messages = mock_complete.await_args.args[0]
    assert "正文长度控制在1800-2200字" in sent_messages[0]["content"]
    assert mock_complete.await_args.kwargs["max_tokens"] == 3000


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_create_chapter_injects_athena_context_when_profile_exists(mock_complete, mock_key, client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as ms, \
         patch("app.api.setups.ai_service.parse_json") as mp:
        ms.return_value.content = '{"world_building": {}, "characters": [{"name": "林舟"}], "core_concept": {}}'
        mp.return_value = {"world_building": {}, "characters": [{"name": "林舟"}], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    genre_profile = GenreProfile(
        canonical_id=f"chapter-athena-context-{pid}",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add(genre_profile)
    db_session.commit()
    profile = ProjectProfileVersion(
        project_id=pid,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add(profile)
    db_session.commit()
    db_session.add(
        WorldFactClaim(
            project_id=pid,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            claim_id="claim.chapter.1.char.林舟.presence_count",
            chapter_index=1,
            intra_chapter_seq=0,
            subject_ref="char.林舟",
            predicate="presence_count",
            object_ref_or_value={"count": 2, "chapter_index": 1},
            claim_layer="truth",
            claim_status="confirmed",
            authority_type="derived",
            confidence=0.9,
            contract_version="world.contract.v1",
        )
    )
    db_session.commit()

    mock_complete.return_value.content = "第二章正文内容"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200

    asyncio.run(create_or_replace_chapter(db_session, pid, 2))

    sent_messages = mock_complete.await_args.args[0]
    assert "【Athena 世界上下文】" in sent_messages[0]["content"]
    assert "presence_count" in sent_messages[0]["content"]


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_create_chapter_injects_longform_memory_without_future_leak(mock_complete, mock_key, client, db_session):
    from app.core.longform_memory import rebuild_longform_memory

    pid = _create_project_with_setup(client)
    for index in range(1, 9):
        db_session.add(
            ChapterContent(
                project_id=pid,
                chapter_index=index,
                title=f"第{index}章",
                content="未来秘密只在第8章揭露。" if index == 8 else f"第{index}章正文。秘银钥匙线索推进。",
                word_count=1000,
                status="generated",
            )
        )
    db_session.commit()
    rebuild_longform_memory(db_session, pid)

    mock_complete.return_value.content = "第6章正文内容"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200

    asyncio.run(create_or_replace_chapter(db_session, pid, 6))

    sent_messages = mock_complete.await_args.args[0]
    prompt = sent_messages[0]["content"]
    assert "【长篇上下文】目标章节：第6章" in prompt
    assert "【近期章节记忆】" in prompt
    assert "第5章正文" in prompt
    assert "未来秘密" not in prompt

    trace = (
        db_session.query(AIModelCallTrace)
        .filter(
            AIModelCallTrace.project_id == pid,
            AIModelCallTrace.trace_type == "chapter_generation",
            AIModelCallTrace.chapter_index == 6,
        )
        .order_by(AIModelCallTrace.created_at.desc())
        .first()
    )
    assert trace is not None
    assert any(block.get("kind") == "longform_context" for block in trace.context_blocks)


@patch("app.api.chapters.load_api_key", return_value="sk-test")
def test_generate_chapter_project_not_found(mock_key, client):
    r = client.post("/api/v1/projects/nonexistent/chapters/1/generate")
    assert r.status_code == 404


@patch("app.api.chapters.load_api_key", return_value="sk-test")
def test_generate_chapter_without_setup(mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post(f"/api/v1/projects/{pid}/chapters/1/generate")
    assert r2.status_code == 400


@patch("app.api.chapters.load_api_key", return_value="sk-test")
def test_generate_chapter_invalid_index(mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post(f"/api/v1/projects/{pid}/chapters/2/generate")
    assert r2.status_code == 400


@patch("app.api.chapters.load_api_key", return_value="sk-test")
@patch("app.api.chapters.ai_service.complete", new_callable=AsyncMock)
def test_get_chapter(mock_complete, mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    with patch("app.api.setups.load_api_key", return_value="sk-test"), \
         patch("app.api.setups.ai_service.complete", new_callable=AsyncMock) as ms, \
         patch("app.api.setups.ai_service.parse_json") as mp:
        ms.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
        mp.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    mock_complete.return_value.content = "第一章正文内容"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200

    client.post(f"/api/v1/projects/{pid}/chapters/1/generate")

    r2 = client.get(f"/api/v1/projects/{pid}/chapters/1")
    assert r2.status_code == 200
    assert r2.json()["content"] == "第一章正文内容"
    assert r2.json()["status"] == "generated"


def test_get_chapter_not_found(client):
    r = client.get("/api/v1/projects/nonexistent/chapters/1")
    assert r.status_code == 404


def _longform_memory_doc_id(db_session, project_id: str, source_ref: str) -> str:
    return (
        db_session.query(RetrievalDocument.id)
        .filter(
            RetrievalDocument.project_id == project_id,
            RetrievalDocument.source_type == "longform_memory",
            RetrievalDocument.source_ref == source_ref,
        )
        .scalar()
    )

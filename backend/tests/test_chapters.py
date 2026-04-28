import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.api.chapters import create_or_replace_chapter
from app.models import AIModelCallTrace, GenreProfile, ProjectProfileVersion, WorldFactClaim


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
    context_kinds = {block["kind"] for block in trace["context_blocks"]}
    assert "setup" in context_kinds
    assert "chapter_context" in context_kinds
    sent_messages = mock_complete.await_args.args[0]
    assert trace["messages"][0]["content"] == sent_messages[0]["content"]


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
    assert r2.json()["word_count"] == 6

    project = client.get(f"/api/v1/projects/{pid}").json()
    assert project["current_word_count"] == 6

    chapters = client.get(f"/api/v1/projects/{pid}/chapters").json()["chapters"]
    assert chapters[0]["word_count"] == 6


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

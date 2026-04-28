from app.api import dialogs
from app.core.model_call_trace import build_context_block, create_trace, sanitize_model_messages, truncate_text
from app.models import AIModelCallTrace, Dialog, DialogMessage, Project
from app.schemas.model_call_trace import ModelCallTraceDetail, PaginatedModelCallTraces


class _FakeAiResult:
    content = "灯塔还能继续作为主线隐喻。"
    prompt_tokens = 321
    completion_tokens = 45


async def _fake_complete(*args, **kwargs):
    return _FakeAiResult()


async def _fake_complete_failure(*args, **kwargs):
    raise RuntimeError("fake model outage")


def _enable_fake_ai(monkeypatch, complete=_fake_complete):
    monkeypatch.setattr(dialogs, "load_api_key", lambda: True)
    monkeypatch.setattr(dialogs.ai_service, "complete", complete)


def test_sanitize_model_messages_redacts_authorization_bearer_and_api_keys():
    messages = [
        {
            "role": "system",
            "content": "Authorization: Bearer sk-live-secret\napi_key=sk-test-secret",
        },
        {
            "role": "user",
            "content": "nested",
            "metadata": {"api_key": "sk-nested-secret"},
        },
    ]

    sanitized = sanitize_model_messages(messages)

    serialized = str(sanitized)
    assert "sk-live-secret" not in serialized
    assert "sk-test-secret" not in serialized
    assert "sk-nested-secret" not in serialized
    assert "Authorization: Bearer [REDACTED]" in sanitized[0]["content"]
    assert sanitized[1]["metadata"]["api_key"] == "[REDACTED]"


def test_truncate_text_reports_original_count_and_appends_truncation_notice():
    text = "0123456789" * 5

    result = truncate_text(text, max_chars=12)

    assert result["original_char_count"] == 50
    assert result["truncated"] is True
    assert result["content"].startswith("012345678901")
    assert "truncated" in result["content"]


def test_build_context_block_populates_trace_context_shape():
    block = build_context_block(
        key="retrieval",
        kind="athena_retrieval",
        title="检索证据",
        content="旧灯塔熄灭时，亡者不能被直接召回。",
        sources=[
            {
                "source_type": "chapter",
                "source_id": "chapter-2",
                "label": "第2章",
                "chapter_index": 2,
                "source_ref": "chapter:2",
                "title": "亡者契约",
            }
        ],
    )

    assert block["key"] == "retrieval"
    assert block["kind"] == "athena_retrieval"
    assert block["title"] == "检索证据"
    assert block["content"] == "旧灯塔熄灭时，亡者不能被直接召回。"
    assert block["sources"] == [
        {
            "source_type": "chapter",
            "source_id": "chapter-2",
            "label": "第2章",
            "chapter_index": 2,
            "source_ref": "chapter:2",
            "title": "亡者契约",
        }
    ]
    assert block["char_count"] == len("旧灯塔熄灭时，亡者不能被直接召回。")
    assert block["token_estimate"] > 0


def test_create_trace_sanitizes_context_blocks_and_trace_metadata(db_session):
    project = Project(name="Trace Audit", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()

    trace = create_trace(
        db_session,
        project_id=project.id,
        trace_type="chat",
        context_blocks=[
            build_context_block(
                key="retrieval",
                kind="manual",
                title="检索证据",
                content="api_key=sk-context-secret",
                sources=[
                    {
                        "source_type": "chapter",
                        "source_id": "chapter-1",
                        "metadata": {"authorization": "Bearer sk-source-secret"},
                    }
                ],
            )
        ],
        trace_metadata={"nested": {"api_key": "sk-metadata-secret"}},
    )
    db_session.commit()
    db_session.refresh(trace)

    serialized = str({"context_blocks": trace.context_blocks, "trace_metadata": trace.trace_metadata})
    assert "sk-context-secret" not in serialized
    assert "sk-source-secret" not in serialized
    assert "sk-metadata-secret" not in serialized
    assert trace.context_blocks[0]["content"] == "api_key=[REDACTED]"
    assert trace.context_blocks[0]["sources"][0]["metadata"]["authorization"] == "[REDACTED]"
    assert trace.trace_metadata["nested"]["api_key"] == "[REDACTED]"


def test_create_trace_defaults_to_running_status(db_session):
    project = Project(name="Trace Status", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()

    trace = create_trace(db_session, project_id=project.id, trace_type="chat")

    assert trace.status == "running"


def test_model_call_trace_detail_normalizes_null_json_fields_from_orm():
    trace = AIModelCallTrace(
        id="trace-1",
        project_id="project-1",
        trace_type="chat",
        status="success",
        messages=None,
        context_blocks=None,
        trace_metadata=None,
    )

    detail = ModelCallTraceDetail.model_validate(trace)

    assert detail.messages == []
    assert detail.context_blocks == []
    assert detail.trace_metadata == {}


def test_paginated_model_call_traces_accepts_total_and_items_only():
    payload = PaginatedModelCallTraces.model_validate({"total": 0, "items": []})

    assert payload.total == 0
    assert payload.items == []


def test_list_model_call_traces_filters_by_trace_type(client, db_session):
    project = Project(name="Trace API", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()

    matching_trace = create_trace(
        db_session,
        project_id=project.id,
        trace_type="hermes_chat",
        status="success",
    )
    create_trace(
        db_session,
        project_id=project.id,
        trace_type="athena_retrieval",
        status="success",
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/projects/{project.id}/model-call-traces",
        params={"trace_type": "hermes_chat"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [item["id"] for item in payload["items"]] == [matching_trace.id]


def test_get_model_call_trace_detail_returns_messages_and_context_sources(client, db_session):
    project = Project(name="Trace Detail API", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()
    trace = create_trace(
        db_session,
        project_id=project.id,
        trace_type="hermes_chat",
        messages=[{"role": "user", "content": "讲讲灯塔。"}],
        context_blocks=[
            build_context_block(
                key="retrieval",
                kind="athena_retrieval",
                title="检索证据",
                content="旧灯塔熄灭时，亡者不能被直接召回。",
                sources=[
                    {
                        "source_type": "chapter",
                        "source_id": "chapter-2",
                        "label": "第2章",
                    }
                ],
            )
        ],
        status="success",
    )
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}/model-call-traces/{trace.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == trace.id
    assert payload["messages"] == [{"role": "user", "content": "讲讲灯塔。"}]
    assert payload["context_blocks"][0]["sources"] == [
        {
            "source_type": "chapter",
            "source_id": "chapter-2",
            "label": "第2章",
            "chapter_index": None,
            "source_ref": None,
            "title": None,
            "metadata": {},
        }
    ]


def test_get_model_call_trace_detail_normalizes_loose_context_blocks(client, db_session):
    project = Project(name="Trace Loose Detail API", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.flush()
    trace = AIModelCallTrace(
        project_id=project.id,
        trace_type="hermes_chat",
        status="success",
        messages=[],
        context_blocks=[
            {
                "content": "loose block",
                "sources": [{"label": "orphan"}],
            }
        ],
        trace_metadata={},
    )
    db_session.add(trace)
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}/model-call-traces/{trace.id}")

    assert response.status_code == 200
    block = response.json()["context_blocks"][0]
    assert block["key"] == "block-0"
    assert block["kind"] == "unknown"
    assert block["content"] == "loose block"
    assert block["char_count"] == len("loose block")
    assert block["token_estimate"] == 0
    assert block["sources"][0]["source_type"] == "Unknown"
    assert block["sources"][0]["label"] == "orphan"


def test_get_model_call_trace_detail_rejects_cross_project_access(client, db_session):
    project = Project(name="Trace Owner", genre="东方奇幻悬疑")
    other_project = Project(name="Trace Intruder", genre="东方奇幻悬疑")
    db_session.add_all([project, other_project])
    db_session.commit()
    trace = create_trace(
        db_session,
        project_id=project.id,
        trace_type="hermes_chat",
        status="success",
    )
    db_session.commit()

    response = client.get(f"/api/v1/projects/{other_project.id}/model-call-traces/{trace.id}")

    assert response.status_code == 404


def test_delete_project_removes_traces_before_dialog_messages(client, db_session):
    project = Project(name="Trace Delete", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.flush()
    dialog = Dialog(project_id=project.id, dialog_type="hermes")
    db_session.add(dialog)
    db_session.flush()
    message = DialogMessage(
        dialog_id=dialog.id,
        role="assistant",
        message_type="plain",
        content="灯塔重新亮起。",
    )
    db_session.add(message)
    db_session.flush()
    trace = AIModelCallTrace(
        project_id=project.id,
        trace_type="hermes_chat",
        status="success",
        dialog_id=dialog.id,
        response_message_id=message.id,
        messages=[],
        context_blocks=[],
        trace_metadata={},
    )
    db_session.add(trace)
    db_session.commit()
    trace_id = trace.id
    message_id = message.id
    dialog_id = dialog.id

    response = client.delete(f"/api/v1/projects/{project.id}")

    assert response.status_code == 200
    db_session.expire_all()
    assert db_session.get(AIModelCallTrace, trace_id) is None
    assert db_session.get(DialogMessage, message_id) is None
    assert db_session.get(Dialog, dialog_id) is None


def test_hermes_chat_success_records_model_call_trace_and_message_trace_id(client, db_session, monkeypatch):
    _enable_fake_ai(monkeypatch)
    project = Project(name="Hermes Trace", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()

    response = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": project.id, "text": "聊聊灯塔主线。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trace_id"]

    detail_response = client.get(f"/api/v1/projects/{project.id}/model-call-traces/{payload['trace_id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["trace_type"] == "hermes_chat"
    assert detail["status"] == "success"
    assert detail["prompt_tokens"] == 321
    assert detail["messages"][0]["role"] == "system"
    assert detail["context_blocks"]

    messages_response = client.get(
        f"/api/v1/dialog/projects/{project.id}/messages",
        params={"dialog_type": "hermes"},
    )
    assert messages_response.status_code == 200
    assistant_messages = [item for item in messages_response.json() if item["role"] == "assistant"]
    assert assistant_messages[-1]["id"] == detail["response_message_id"]
    assert assistant_messages[-1]["trace_id"] == payload["trace_id"]


def test_hermes_chat_failure_records_failed_trace_and_returns_fallback(client, db_session, monkeypatch):
    _enable_fake_ai(monkeypatch, complete=_fake_complete_failure)
    project = Project(name="Hermes Failed Trace", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()

    response = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": project.id, "text": "聊聊失败场景。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "模型调用失败" in payload["message"]
    assert payload["trace_id"]

    trace = db_session.query(AIModelCallTrace).filter(AIModelCallTrace.id == payload["trace_id"]).one()
    assert trace.trace_type == "hermes_chat"
    assert trace.status == "failed"
    assert "fake model outage" in trace.error_message
    assert trace.response_message_id is not None

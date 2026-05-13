from app.api import chapters, dialogs
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


def test_sanitize_model_messages_redacts_common_secret_key_variants_without_redacting_token_counts():
    messages = [
        {
            "role": "system",
            "content": (
                "apiKey=plain-api-key accessToken: plain-access "
                "refresh_token=plain-refresh secretKey=plain-secret "
                "clientSecret: plain-client password=plain-password token=plain-token"
            ),
            "metadata": {
                "accessToken": "plain-access-token",
                "AccessToken": "plain-pascal-access-token",
                "refresh-token": "plain-refresh-token",
                "secret key": "plain-secret-key",
                "clientSecret": "plain-client-secret",
                "password": "plain-password",
                "token": "plain-token",
                "idToken": "plain-id-token",
                "session_token": "plain-session-token",
                "max_tokens": 900,
                "prompt_tokens": 12,
                "completion_tokens": 34,
            },
        },
    ]

    sanitized = sanitize_model_messages(messages)

    serialized = str(sanitized)
    for secret in [
        "plain-api-key",
        "plain-access",
        "plain-refresh",
        "plain-secret",
        "plain-client",
        "plain-password",
        "plain-token",
        "plain-access-token",
        "plain-pascal-access-token",
        "plain-refresh-token",
        "plain-secret-key",
        "plain-client-secret",
        "plain-id-token",
        "plain-session-token",
    ]:
        assert secret not in serialized
    content = sanitized[0]["content"]
    assert "apiKey=[REDACTED]" in content
    assert "accessToken: [REDACTED]" in content
    assert "refresh_token=[REDACTED]" in content
    assert "secretKey=[REDACTED]" in content
    assert "clientSecret: [REDACTED]" in content
    assert "password=[REDACTED]" in content
    assert "token=[REDACTED]" in content
    assert sanitized[0]["metadata"]["accessToken"] == "[REDACTED]"
    assert sanitized[0]["metadata"]["AccessToken"] == "[REDACTED]"
    assert sanitized[0]["metadata"]["refresh-token"] == "[REDACTED]"
    assert sanitized[0]["metadata"]["secret key"] == "[REDACTED]"
    assert sanitized[0]["metadata"]["clientSecret"] == "[REDACTED]"
    assert sanitized[0]["metadata"]["password"] == "[REDACTED]"
    assert sanitized[0]["metadata"]["token"] == "[REDACTED]"
    assert sanitized[0]["metadata"]["idToken"] == "[REDACTED]"
    assert sanitized[0]["metadata"]["session_token"] == "[REDACTED]"
    assert sanitized[0]["metadata"]["max_tokens"] == 900
    assert sanitized[0]["metadata"]["prompt_tokens"] == 12
    assert sanitized[0]["metadata"]["completion_tokens"] == 34


def test_sanitize_model_messages_redacts_quoted_json_style_secret_assignments():
    messages = [
        {
            "role": "system",
            "content": (
                '{"accessToken": "plain-json-access", "clientSecret": "plain-json-client", '
                "'secretKey': 'plain-single-secret', 'password': 'plain-single-password', "
                '"max_tokens": 900}'
            ),
        }
    ]

    sanitized = sanitize_model_messages(messages)

    content = sanitized[0]["content"]
    for secret in [
        "plain-json-access",
        "plain-json-client",
        "plain-single-secret",
        "plain-single-password",
    ]:
        assert secret not in content
    assert '"accessToken": "[REDACTED]"' in content
    assert '"clientSecret": "[REDACTED]"' in content
    assert "'secretKey': '[REDACTED]'" in content
    assert "'password': '[REDACTED]'" in content
    assert '"max_tokens": 900' in content


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


def test_safe_create_chat_trace_commits_before_model_call(db_session):
    project = Project(id="trace-chat-project", name="Trace Chat Commit", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()
    dialog = Dialog(id="trace-chat-dialog", project_id=project.id, dialog_type="hermes")
    db_session.add(dialog)
    db_session.commit()

    trace = dialogs._safe_create_chat_trace(
        db_session,
        project_id=project.id,
        trace_type="hermes_chat",
        messages=[{"role": "user", "content": "测试 trace 事务"}],
        context_blocks=[],
        model="deepseek-chat",
        temperature=0.7,
        max_tokens=900,
        dialog_id=dialog.id,
        request_message_id=None,
        trace_metadata={"dialog_type": "hermes"},
    )

    assert trace is not None
    assert db_session.in_transaction() is False


def test_safe_create_chapter_trace_commits_before_model_call(db_session):
    project = Project(id="trace-chapter-project", name="Trace Chapter Commit", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()

    trace = chapters._safe_create_chapter_trace(
        db_session,
        project=project,
        chapter_index=1,
        payload={
            "messages": [{"role": "user", "content": "生成第一章"}],
            "context_blocks": [],
            "max_tokens": 1200,
            "trace_metadata": {
                "prompt_id": "chapter.generate",
                "prompt_version": "1",
                "template_name": "generate_chapter",
                "template_hash": "sha256:test",
                "budget": None,
            },
        },
    )

    assert trace is not None
    assert db_session.in_transaction() is False


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


def test_model_call_trace_detail_normalizes_malformed_trace_metadata_from_orm():
    for malformed_metadata in ([], "bad"):
        trace = AIModelCallTrace(
            id=f"trace-malformed-{type(malformed_metadata).__name__}",
            project_id="project-1",
            trace_type="chat",
            status="success",
            messages=[],
            context_blocks=[],
            trace_metadata=malformed_metadata,
        )

        detail = ModelCallTraceDetail.model_validate(trace)

        assert detail.trace_metadata == {}
        assert detail.prompt_metadata is None
        assert detail.prompt_budget is None


def test_model_call_trace_detail_derives_prompt_metadata_and_budget_from_trace_metadata():
    trace = AIModelCallTrace(
        id="trace-prompt",
        project_id="project-1",
        trace_type="chapter.generate",
        status="success",
        messages=[],
        context_blocks=[],
        trace_metadata={
            "prompt_id": "chapter.generate",
            "prompt_version": "v1",
            "template_name": "generate_chapter",
            "template_hash": "sha256:abcdef1234567890",
            "budget": {
                "max_context_chars": 24000,
                "requested_context_chars": 30000,
                "used_context_chars": 24000,
                "remaining_context_chars": 0,
                "included_blocks": 3,
                "omitted_blocks": 2,
                "omitted_block_keys": ["world-history", "old-outline"],
                "truncated_blocks": ["chapter-target"],
            },
        },
    )

    detail = ModelCallTraceDetail.model_validate(trace)

    assert detail.prompt_metadata is not None
    assert detail.prompt_metadata.prompt_id == "chapter.generate"
    assert detail.prompt_metadata.prompt_version == "v1"
    assert detail.prompt_metadata.template_name == "generate_chapter"
    assert detail.prompt_metadata.template_hash == "sha256:abcdef1234567890"
    assert detail.prompt_budget is not None
    assert detail.prompt_budget.included_blocks == 3
    assert detail.prompt_budget.requested_context_chars == 30000
    assert detail.prompt_budget.used_context_chars == 24000
    assert detail.prompt_budget.remaining_context_chars == 0
    assert detail.prompt_budget.omitted_blocks == 2
    assert detail.prompt_budget.omitted_block_keys == ["world-history", "old-outline"]
    assert detail.prompt_budget.truncated_blocks == ["chapter-target"]
    assert detail.model_dump()["trace_metadata"]["prompt_id"] == "chapter.generate"


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


def test_clear_deletes_dialog_traces_before_removing_messages(client, db_session, monkeypatch):
    _enable_fake_ai(monkeypatch)
    project = Project(name="Trace Clear", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()
    project_id = project.id

    response = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": project_id, "text": "清空前先聊一句。"},
    )

    assert response.status_code == 200
    trace_id = response.json()["trace_id"]
    db_session.expire_all()
    trace = db_session.get(AIModelCallTrace, trace_id)
    assert trace is not None
    assert trace.request_message_id is not None
    assert trace.response_message_id is not None
    dialog_id = trace.dialog_id

    clear_response = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": project_id, "input_type": "command", "command_name": "clear"},
    )

    assert clear_response.status_code == 200
    assert "清空" in clear_response.json()["message"]
    db_session.expire_all()
    assert db_session.get(AIModelCallTrace, trace_id) is None
    assert (
        db_session.query(AIModelCallTrace)
        .filter(AIModelCallTrace.dialog_id == dialog_id)
        .count()
        == 0
    )


def test_compact_detaches_traces_from_deleted_plain_messages(client, db_session, monkeypatch):
    _enable_fake_ai(monkeypatch)
    project = Project(name="Trace Compact", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()
    project_id = project.id

    trace_ids = []
    for text in ("第一段普通对话。", "第二段普通对话。"):
        response = client.post(
            "/api/v1/dialog/chat",
            json={"project_id": project_id, "text": text},
        )
        assert response.status_code == 200
        trace_ids.append(response.json()["trace_id"])

    db_session.expire_all()
    dialog = db_session.query(Dialog).filter(Dialog.project_id == project_id).one()
    plain_message_ids = {
        message_id
        for (message_id,) in (
            db_session.query(DialogMessage.id)
            .filter(
                DialogMessage.dialog_id == dialog.id,
                DialogMessage.message_type == "plain",
            )
            .all()
        )
    }
    assert len(plain_message_ids) == 4
    traces_before = (
        db_session.query(AIModelCallTrace)
        .filter(AIModelCallTrace.id.in_(trace_ids))
        .all()
    )
    assert {trace.id for trace in traces_before} == set(trace_ids)
    assert all(trace.request_message_id in plain_message_ids for trace in traces_before)
    assert all(trace.response_message_id in plain_message_ids for trace in traces_before)

    compact_response = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": project_id, "input_type": "command", "command_name": "compact"},
    )

    assert compact_response.status_code == 200
    assert compact_response.json()["message"].startswith("已压缩")
    db_session.expire_all()
    remaining_message_ids = {
        message_id for (message_id,) in db_session.query(DialogMessage.id).all()
    }
    assert plain_message_ids.isdisjoint(remaining_message_ids)
    traces_after = (
        db_session.query(AIModelCallTrace)
        .filter(AIModelCallTrace.id.in_(trace_ids))
        .all()
    )
    assert {trace.id for trace in traces_after} == set(trace_ids)
    for trace in traces_after:
        assert trace.request_message_id is None
        assert trace.response_message_id is None


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


def test_hermes_chat_keeps_model_content_when_trace_success_mark_fails(client, db_session, monkeypatch):
    _enable_fake_ai(monkeypatch)
    monkeypatch.setattr(
        dialogs,
        "mark_trace_success",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("trace mark failed")),
    )
    project = Project(name="Hermes Trace Mark Failure", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()

    response = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": project.id, "text": "聊聊 trace 写入失败。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == _FakeAiResult.content
    assert "模型调用失败" not in payload["message"]

    assistant_message = (
        db_session.query(DialogMessage)
        .filter(DialogMessage.role == "assistant")
        .order_by(DialogMessage.created_at.desc())
        .first()
    )
    assert assistant_message is not None
    assert assistant_message.content == _FakeAiResult.content


def test_hermes_chat_keeps_model_content_when_trace_attach_fails(client, db_session, monkeypatch):
    _enable_fake_ai(monkeypatch)
    monkeypatch.setattr(
        dialogs,
        "attach_trace_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("trace attach failed")),
    )
    project = Project(name="Hermes Trace Attach Failure", genre="东方奇幻悬疑")
    db_session.add(project)
    db_session.commit()

    response = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": project.id, "text": "聊聊 trace attach 失败。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == _FakeAiResult.content
    assert payload["trace_id"] is None

    assistant_message = (
        db_session.query(DialogMessage)
        .filter(DialogMessage.role == "assistant")
        .order_by(DialogMessage.created_at.desc())
        .first()
    )
    assert assistant_message is not None
    assert assistant_message.content == _FakeAiResult.content

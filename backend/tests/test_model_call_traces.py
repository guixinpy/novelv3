from app.core.model_call_trace import build_context_block, create_trace, sanitize_model_messages, truncate_text
from app.models import AIModelCallTrace, Project
from app.schemas.model_call_trace import ModelCallTraceDetail, PaginatedModelCallTraces


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

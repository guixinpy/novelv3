from app.core.model_call_trace import build_context_block, sanitize_model_messages, truncate_text


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
        content="旧灯塔熄灭时，亡者不能被直接召回。",
        sources=[
            {
                "source_type": "chapter",
                "source_id": "chapter-2",
                "source_ref": "chapter:2",
                "title": "亡者契约",
            }
        ],
    )

    assert block["key"] == "retrieval"
    assert block["kind"] == "athena_retrieval"
    assert block["content"] == "旧灯塔熄灭时，亡者不能被直接召回。"
    assert block["sources"] == [
        {
            "source_type": "chapter",
            "source_id": "chapter-2",
            "source_ref": "chapter:2",
            "title": "亡者契约",
        }
    ]
    assert block["char_count"] == len("旧灯塔熄灭时，亡者不能被直接召回。")
    assert block["token_estimate"] > 0

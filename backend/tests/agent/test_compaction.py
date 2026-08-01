"""上下文压缩测试。"""
from __future__ import annotations

from app.agent.compaction import check_context_usage, compact_history, estimate_message_tokens


def _msg(role: str, content: str = "你好") -> dict:
    return {"role": role, "content": content}


def test_estimate_short_message():
    tokens = estimate_message_tokens({"role": "user", "content": "你好世界"})
    assert tokens > 0


def test_check_below_threshold():
    history = [_msg("user", "hi")] * 10
    result = check_context_usage(history, max_tokens=1_000_000, threshold=0.75)
    assert result is None


def test_check_above_threshold():
    # 用大量内容填充
    history = [_msg("user", "x" * 100_000)] * 3
    result = check_context_usage(history, max_tokens=128_000, threshold=0.1)
    assert result is not None
    pct, total = result
    assert pct >= 0.1
    assert total > 0


def test_compact_noop_when_small():
    history = [_msg("system"), _msg("user"), _msg("assistant")]
    result = compact_history(history, head_count=2, tail_token_budget=0.5)
    assert len(result) == len(history)


def test_compact_large_history():
    history = [_msg("system")] + [_msg("user", f"msg{i}") for i in range(20)]
    result = compact_history(history, head_count=2)
    assert len(result) < len(history)
    assert result[0] == history[0]  # system preserved
    assert result[-1] == history[-1]  # last message preserved
    # Has a summary message
    summaries = [m for m in result if m.get("content") and "压缩" in m["content"]]
    assert len(summaries) == 1


def test_summary_skips_previous_compression_summaries():
    """新摘要不应嵌套旧压缩摘要（M5 200 章实测：摘要互相嵌套导致上下文混乱）。"""
    from app.agent.compaction import _build_summary_text

    history = [
        {"role": "user", "content": "[上下文压缩] 中间 74 条消息被压缩。 包含 8 条用户消息。"},
        {"role": "user", "content": "请继续写第 50 章。"},
        {"role": "assistant", "content": "好", "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "write_chapter", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "c1", "content": '{"chapter_index": 50, "word_count": 1200, "status": "written"}'},
        {"role": "assistant", "content": "ok", "tool_calls": [{"id": "c2", "type": "function", "function": {"name": "check_chapter_quality", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "c2", "content": '{"chapter_index": 50, "quality": "pass"}'},
    ]
    summary = _build_summary_text(history, 0, len(history))
    assert "[上下文压缩] 中间 74 条" not in summary
    assert "Ch50:1200字" in summary
    assert "Ch50:pass" in summary

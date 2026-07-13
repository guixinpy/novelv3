"""上下文压缩：用量预检 + 头尾保护压缩（M3）。"""
from __future__ import annotations

from app.agent.providers.base import Usage


def estimate_tokens(text: str) -> int:
    """粗略令牌估算：中英文混合按 ~1.5 字符/token。"""
    return int(len(text) * 1.5 / 1)


def estimate_message_tokens(msg: dict) -> int:
    """估算一条消息的令牌数。"""
    total = 0
    content = msg.get("content", "")
    if content:
        total += estimate_tokens(str(content))
    tool_calls = msg.get("tool_calls")
    if tool_calls:
        for tc in tool_calls:
            func = tc.get("function", {}) if isinstance(tc, dict) else {}
            total += estimate_tokens(str(func.get("name", "")))
            total += estimate_tokens(str(func.get("arguments", "")))
    return total


def check_context_usage(
    history: list[dict],
    max_tokens: int = 128_000,
    threshold: float = 0.75,
) -> tuple[float, int] | None:
    """检查上下文用量。超过阈值返回 (usage_pct, total_tokens)，否则返回 None。

    集成到 harness 中，每次 LLM 调用前检查。
    """
    total = sum(estimate_message_tokens(m) for m in history)
    usage_pct = total / max_tokens
    if usage_pct >= threshold:
        return (usage_pct, total)
    return None


def compact_history(
    history: list[dict],
    head_count: int = 2,
    tail_count: int = 10,
    summary_text: str = "（中间内容已压缩，保留开头和最近的对话记录）",
) -> list[dict]:
    """压缩对话历史：保留系统提示+开头 N 条+结尾 N 条，中间摘要为一条 user 消息。

    Args:
        history: 完整消息列表（含 system 消息）。
        head_count: 开头保留条数（含 system）。
        tail_count: 结尾保留条数。
        summary_text: 中间摘要文本。

    Returns:
        压缩后的消息列表。
    """
    if len(history) <= head_count + tail_count:
        return list(history)

    head = history[:head_count]
    tail = history[-tail_count:]
    compacted = head + [{"role": "user", "content": summary_text}] + tail
    return compacted

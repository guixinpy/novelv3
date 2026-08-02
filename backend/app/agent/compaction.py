"""上下文压缩：用量预检 + Token-Budget 尾部保护 + 防抖（M5 增强版）。

参考 hermes-agent context_compressor.py 的核心模式：
1. Token-Budget Tail Protection — 尾部分配固定比例的 token 预算，自适应窗口大小
2. Anti-Thrashing Guard — 追踪最近压缩效果，低效时跳过
3. Deterministic fallback — 不确定性摘要，用结构化模板
"""
from __future__ import annotations

import json

# ── 防抖状态（模块级，跨 turn 保持） ──

_last_compression_stats: dict = {"count": 0, "last_savings": []}  # 最近两次节省比例


def reset_compaction_stats() -> None:
    """重置防抖计数器（新会话开始时调用）。"""
    global _last_compression_stats
    _last_compression_stats = {"count": 0, "last_savings": []}


# ── Token 估算 ──


def estimate_tokens(text: str) -> int:
    """粗略令牌估算：中英文混合按 ~2 字符/token。"""
    return max(1, len(text) // 2)


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


# ── 上下文用量预检 ──


def check_context_usage(
    history: list[dict],
    max_tokens: int = 128_000,
    threshold: float = 0.75,
) -> tuple[float, int] | None:
    """检查上下文用量。超过阈值返回 (usage_pct, total_tokens)，否则返回 None。"""
    total = sum(estimate_message_tokens(m) for m in history)
    usage_pct = total / max_tokens
    if usage_pct >= threshold:
        return (usage_pct, total)
    return None


# ── Token-Budget Tail Protection（hermes-agent 模式） ──


def compact_history(
    history: list[dict],
    head_count: int = 2,
    tail_token_budget: float = 0.20,  # 尾部占窗口 20%
    max_tokens: int = 128_000,
    force: bool = False,
    extra_context: str | None = None,
) -> list[dict]:
    """压缩对话历史：Token-Budget 尾部保护 + 防抖。

    与旧版的区别：
    - tail_count 改为 tail_token_budget（动态计算尾部保留条数）
    - 添加防抖保护：连续两次节省 <10% 时跳过压缩
    - 提高摘要信息量
    - extra_context（T6 R2）：追加「最近写作上下文」段，压缩后保住可行动的写作信息

    Args:
        history: 完整消息列表（含 system 消息）。
        head_count: 开头保留条数（含 system）。
        tail_token_budget: 尾部 token 预算比例（默认 20% 的 max_tokens）。
        max_tokens: 模型上下文窗口大小。
        force: 强制压缩（跳过防抖）。
        extra_context: 追加到摘要的写作上下文文本（如项目状态快照）。

    Returns:
        压缩后的消息列表。
    """
    global _last_compression_stats

    if len(history) <= head_count:
        return list(history)

    # ── 防抖保护 ──
    before_tokens = sum(estimate_message_tokens(m) for m in history)
    # 尾部预算基于当前总 token 量（小上下文用更小尾部，大上下文用更大尾部）
    tail_budget_tokens = max(int(before_tokens * tail_token_budget), 1)

    # 从末尾向前累加 token，动态计算 tail_count
    tail_count = 0
    accumulated = 0
    for msg in reversed(history[head_count:]):
        accumulated += estimate_message_tokens(msg)
        tail_count += 1
        if accumulated >= tail_budget_tokens:
            break
    # 最少保留 3 条
    tail_count = max(3, tail_count)

    if len(history) <= head_count + tail_count:
        return list(history)

    # ── 防抖：连续两次节省 <10% 则跳过 ──
    if not force:
        estimated_after = (
            sum(estimate_message_tokens(m) for m in history[:head_count])
            + estimate_tokens(_build_summary_text(
                history, head_count, len(history) - tail_count, extra_context=extra_context))
            + sum(estimate_message_tokens(m) for m in history[-tail_count:])
        )
        saving_ratio = 1.0 - (estimated_after / max(1, before_tokens))
        savings_history = _last_compression_stats.get("last_savings", [])
        if len(savings_history) >= 2:
            if all(s < 0.10 for s in savings_history[-2:]):
                return list(history)  # 跳过压缩，效果太差
        savings_history.append(saving_ratio)
        if len(savings_history) > 2:
            savings_history = savings_history[-2:]
        _last_compression_stats["last_savings"] = savings_history
        _last_compression_stats["count"] += 1

    head = history[:head_count]
    tail = history[-tail_count:]
    mid_end = len(history) - tail_count
    summary = _build_summary_text(history, head_count, mid_end, extra_context=extra_context)
    return head + [{"role": "user", "content": summary}] + tail


def _build_summary_text(
    history: list[dict], start: int, end: int, extra_context: str | None = None,
) -> str:
    """构建结构化中间摘要（确定性，不依赖 LLM）。

    extra_context（T6 R2）：追加「最近写作上下文」段，压缩后保住章节/人物/线索信息。
    """
    middle = history[start:end]
    user_msgs = []
    tool_names = set()
    assistant_count = 0
    error_count = 0
    recent_writes: list[tuple[int, int]] = []
    quality_checks: list[tuple[int, str]] = []

    for m in middle:
        role = m.get("role", "")
        content = str(m.get("content", ""))
        # 跳过旧压缩摘要，避免嵌套膨胀（M5 200 章实测：摘要内嵌上一轮摘要）
        if role == "user" and content and not content.startswith("[上下文压缩]"):
            user_msgs.append(content[:200])
        elif role == "assistant":
            assistant_count += 1
            if "tool_calls" in m:
                for tc in m.get("tool_calls", []):
                    n = tc.get("function", {}).get("name", "") if isinstance(tc, dict) else tc.get("name", "")
                    if n:
                        tool_names.add(n)
        elif role == "tool":
            c = str(m.get("content", ""))
            if "error" in c.lower() or "失败" in c or "不存在" in c:
                error_count += 1
            try:
                parsed = json.loads(c)
            except (ValueError, TypeError):
                parsed = None
            if isinstance(parsed, dict):
                if parsed.get("status") == "written" and "chapter_index" in parsed:
                    recent_writes.append(
                        (int(parsed["chapter_index"]), int(parsed.get("word_count") or 0))
                    )
                elif parsed.get("quality") in ("pass", "fail"):
                    quality_checks.append(
                        (parsed.get("chapter_index"), parsed["quality"])
                    )

    parts = [
        f"[上下文压缩] 中间 {len(middle)} 条消息被压缩。",
        f"包含 {len(user_msgs)} 条用户消息，{assistant_count} 次助手回复。",
    ]
    if tool_names:
        parts.append(f"调用的工具: {', '.join(sorted(tool_names))}。")
    if error_count:
        parts.append(f"⚠ 其中 {error_count} 次工具调用返回错误。")
    if recent_writes:
        writes = ", ".join(f"Ch{i}:{w}字" for i, w in recent_writes[-8:])
        parts.append(f"最近写入章节: {writes}。")
    if quality_checks:
        qs = ", ".join(f"Ch{i}:{q}" for i, q in quality_checks[-8:])
        parts.append(f"质量自检: {qs}。")
    if user_msgs:
        parts.append(f"用户关注点: {'; '.join(user_msgs[:5])}。")
    if extra_context:
        parts.append(f"最近写作上下文: {extra_context[:300]}。")

    return " ".join(parts)

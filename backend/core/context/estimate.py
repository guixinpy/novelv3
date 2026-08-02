"""CJK-aware 启发式 token 估算（hermes #2 + openclaw #4 综合）。

规则：
- CJK/假名/谚文 1 字 ≈ 1.5 token（保守系数：hermes 按 1、openclaw 按 4，
  取中值偏保守——估算用于触发压缩阈值，估高比估低安全）
- 其余字符 4 字符 ≈ 1 token
- 图片按固定 1500 token/张（Anthropic 定价模型，避免 base64 字符长度误触发压缩）
- 内容指纹缓存：相同文本 O(1) 命中（str 值相等共享缓存，无 id 回收风险）

用途：压缩阈值判定（不追求精确，追求稳定且不触发过晚）。
"""
from __future__ import annotations

from typing import Any

IMAGE_TOKEN_BUDGET = 1500

_CACHE_LIMIT = 10_000
_CACHE_MAX_CHARS = 2_000_000  # 缓存总字符数上限（code-review #14：长跑进程防内存滞留）
_cache: dict[str, int] = {}
_cache_chars = 0


def _is_dense(ch: str) -> bool:
    return (
        "一" <= ch <= "鿿"   # CJK 统一表意文字
        or "぀" <= ch <= "ヿ"  # 假名
        or "가" <= ch <= "힯"  # 谚文
    )


def estimate_tokens(text: str) -> int:
    cached = _cache.get(text)
    if cached is not None:
        return cached
    dense = sum(1 for ch in text if _is_dense(ch))
    sparse = len(text) - dense
    tokens = max(1, int(dense * 1.5) + (sparse + 3) // 4)
    global _cache_chars
    if len(_cache) >= _CACHE_LIMIT or _cache_chars + len(text) > _CACHE_MAX_CHARS:
        # 超限清空（简单淘汰：估算缓存重算成本低，防长跑进程滞留数百 MB）
        _cache.clear()
        _cache_chars = 0
    _cache[text] = tokens
    _cache_chars += len(text)
    return tokens


def _estimate_content(content: Any) -> int:
    """content 支持 str（纯文本）与 list（多模态，Anthropic 格式）。"""
    if isinstance(content, str):
        return estimate_tokens(content)
    if isinstance(content, list):
        total = 0
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "text":
                total += estimate_tokens(str(block.get("text", "")))
            elif btype == "image":
                total += IMAGE_TOKEN_BUDGET
            else:
                total += estimate_tokens(str(block))
        return total
    return estimate_tokens(str(content))


def estimate_message_tokens(msg: dict) -> int:
    """估算一条消息的令牌数。"""
    total = _estimate_content(msg.get("content", ""))
    tool_calls = msg.get("tool_calls")
    if tool_calls:
        for tc in tool_calls:
            func = tc.get("function", {}) if isinstance(tc, dict) else {}
            total += estimate_tokens(str(func.get("name", "")))
            total += estimate_tokens(str(func.get("arguments", "")))
    return total


def estimate_history_tokens(history: list[dict]) -> int:
    return sum(estimate_message_tokens(m) for m in history)

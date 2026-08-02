"""上下文预算截断纯函数（生成统一 v2：从 prompting/budget 迁移，行为不变）。

按 priority 排序 + max_chars 预算截断；放不下的块用「头尾保留 + ...」截断
（200 章实验的上下文管理关键，头尾保护语义必须保持）。
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from core.context.estimate import estimate_tokens


def apply_context_budget(
    blocks: list[dict[str, Any]],
    max_chars: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """按 priority 排序截断上下文块。

    Returns:
        kept_blocks: 保留的上下文块（原顺序）。
        report: {max_context_chars, included_blocks, omitted_blocks, requested_context_chars,
                 used_context_chars, remaining_context_chars, omitted_block_keys, truncated_blocks}
    """
    remaining = max(0, max_chars)
    requested_chars = sum(len(_block_content(block)) for block in blocks)
    selected: dict[int, dict[str, Any]] = {}
    omitted_keys: list[str] = []
    truncated_keys: list[str] = []

    ordered = sorted(
        enumerate(blocks),
        key=lambda item: (item[1].get("priority", 100), item[0]),
    )

    for index, block in ordered:
        key = _block_key(block, index)
        content = _block_content(block)

        if len(content) <= remaining:
            if remaining == 0:
                omitted_keys.append(key)
                continue
            selected[index] = _copy_block_with_content(block, content)
            remaining -= len(content)
            continue

        if remaining > 0:
            kept = _copy_block_with_content(
                block,
                _truncate_content(content, remaining),
                budget_truncated=True,
                original_char_count=len(content),
            )
            selected[index] = kept
            truncated_keys.append(key)
            remaining = 0
            continue

        omitted_keys.append(key)

    kept_blocks = [selected[index] for index in sorted(selected)]
    used_chars = sum(len(_block_content(block)) for block in kept_blocks)
    report = {
        "max_context_chars": max_chars,
        "included_blocks": len(kept_blocks),
        "omitted_blocks": len(omitted_keys),
        "requested_context_chars": requested_chars,
        "used_context_chars": used_chars,
        "remaining_context_chars": remaining,
        "omitted_block_keys": omitted_keys,
        "truncated_blocks": truncated_keys,
    }
    return kept_blocks, report


def _block_key(block: dict[str, Any], index: int) -> str:
    key = block.get("key", index)
    return str(key)


def _block_content(block: dict[str, Any]) -> str:
    if "content" not in block:
        return ""
    return str(block["content"])


def _truncate_content(content: str, max_chars: int) -> str:
    """头尾保留 + 分隔符截断（与旧版语义一致）。"""
    if len(content) <= max_chars:
        return content
    separator = "\n...\n"
    if max_chars <= len(separator) + 2:
        return content[:max_chars]
    available_chars = max_chars - len(separator)
    head_chars = available_chars // 2
    tail_chars = available_chars - head_chars
    return f"{content[:head_chars]}{separator}{content[-tail_chars:]}"


def _copy_block_with_content(
    block: dict[str, Any],
    content: str,
    *,
    budget_truncated: bool = False,
    original_char_count: int | None = None,
) -> dict[str, Any]:
    copied = deepcopy(block)
    copied["content"] = content
    if budget_truncated:
        copied["char_count"] = len(content)
        copied["token_estimate"] = estimate_tokens(content)
        copied["original_char_count"] = max(
            _safe_int(block.get("original_char_count")),
            original_char_count or len(content),
        )
        copied["truncated"] = True
    return copied


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

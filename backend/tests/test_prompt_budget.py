"""上下文预算截断纯函数测试（生成统一 v2：从 prompting/budget 迁移，行为不变）。"""
from __future__ import annotations

from app.core.prompt_budget import apply_context_budget


def _block(key: str, content: str, priority: int = 100) -> dict:
    return {"key": key, "content": content, "priority": priority}


def test_all_blocks_fit_kept_in_original_order():
    blocks = [_block("a", "x" * 10, priority=100), _block("b", "y" * 20, priority=100)]
    kept, report = apply_context_budget(blocks, max_chars=1000)
    assert [b["key"] for b in kept] == ["a", "b"]
    assert report["omitted_blocks"] == 0
    assert report["truncated_blocks"] == []


def test_priority_order_respected_and_tail_preserved():
    # 低 priority（值大）先被省略；剩余空间放不下的块用头尾截断
    blocks = [
        _block("low", "L" * 500, priority=200),
        _block("high", "H" * 300, priority=10),
        _block("mid", "M" * 400, priority=100),
    ]
    kept, report = apply_context_budget(blocks, max_chars=400)
    assert [b["key"] for b in kept] == ["high", "mid"]
    assert report["omitted_blocks"] == 1
    assert report["omitted_block_keys"] == ["low"]
    assert report["truncated_blocks"] == ["mid"]
    # 头尾保留截断：开头与结尾都应在
    mid = kept[1]["content"]
    assert mid.startswith("M") and mid.endswith("M")
    assert "..." in mid


def test_zero_budget_omits_all():
    blocks = [_block("a", "x"), _block("b", "y")]
    kept, report = apply_context_budget(blocks, max_chars=0)
    assert kept == []
    assert report["omitted_blocks"] == 2


def test_truncated_block_carries_markers():
    blocks = [_block("big", "Z" * 1000, priority=1)]
    kept, report = apply_context_budget(blocks, max_chars=100)
    assert kept[0]["truncated"] is True
    assert kept[0]["original_char_count"] == 1000
    assert report["used_context_chars"] <= 100

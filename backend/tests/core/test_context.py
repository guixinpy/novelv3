"""CJK 估算 + 压缩护栏测试（CompactionState 实例化 + 冷却/防抖/合理性校验）。"""
from __future__ import annotations

from core.context.compaction import CompactionState, check_context_usage, compact_history
from core.context.estimate import estimate_tokens

# ── estimate ──

def test_cjk_weights_higher_than_ascii():
    chinese = "这是中文测试文本" * 10
    english = "a" * len(chinese)
    assert estimate_tokens(chinese) > estimate_tokens(english)


def test_estimate_cache_returns_same():
    text = "同一段文本" * 50
    assert estimate_tokens(text) == estimate_tokens(text)


def test_empty_text_min_one():
    assert estimate_tokens("") == 1


def test_history_usage_threshold():
    history = [{"role": "user", "content": "测试内容" * 1000}]
    result = check_context_usage(history, max_tokens=1000)
    assert result is not None
    pct, total = result
    assert pct > 1.0 and total > 0


# ── compaction ──

def _history(n: int, per: int = 100) -> list[dict]:
    return [{"role": "system", "content": "s"}] + [
        {"role": "user", "content": f"消息{i}" * per} for i in range(n)
    ]


def test_compaction_state_is_per_instance():
    """修旧缺陷 #1：多会话并发不互相污染（实例级状态）。"""
    s1 = CompactionState()
    s2 = CompactionState()
    h = _history(30)
    # s1 压缩多次，s2 不受影响
    for _ in range(3):
        compact_history(h, state=s1)
    assert s1.compaction_count >= 1
    assert s2.compaction_count == 0


def test_failure_cooldown_blocks_auto_compaction():
    state = CompactionState(failure_cooldown_seconds=60)
    state.record_failure()
    h = _history(30)
    result = compact_history(h, state=state)
    assert len(result) == len(h)  # 冷却期跳过
    # force 绕过冷却
    forced = compact_history(h, state=state, force=True)
    assert len(forced) < len(h)


def test_ineffective_compaction_stops_thrashing():
    """无效压缩计数：压缩不生效时止住空转（hermes #3）。

    第 4 次无效尝试被拦（max_ineffective_count=3 内允许尝试，之后跳过）。
    """
    state = CompactionState(max_ineffective_count=3)
    for _ in range(3):
        assert state._record_saving(0.01, was_effective=False) is True
    assert state._record_saving(0.01, was_effective=False) is False


def test_compaction_keeps_tail_and_summary():
    state = CompactionState()
    h = _history(30, per=500)
    result = compact_history(h, state=state)
    assert len(result) < len(h)
    # 摘要带固定前缀
    assert any(
        isinstance(m.get("content"), str) and m["content"].startswith("[上下文压缩]")
        for m in result
    )
    # 尾部保留（最后一条消息在）
    assert result[-1] == h[-1]


def test_compaction_injection_provider():
    """状态重注入（hermes #4）：压缩后保留设定/大纲等跨压缩状态。"""
    state = CompactionState()
    h = _history(30, per=500)
    result = compact_history(h, state=state, injection_provider=lambda: "大纲：主角是林舟")
    joined = " ".join(str(m.get("content", "")) for m in result)
    assert "写作状态已保留" in joined
    assert "林舟" in joined


def test_summary_includes_reference_only_semantics():
    """压缩摘要权威语义（hermes REFERENCE ONLY）：只响应摘要后的最新消息。

    防止模型把压缩摘要当当前任务续写（历史事故：摘要后 7 轮纯叙述不调工具）。
    """
    state = CompactionState()
    h = _history(30, per=500)
    result = compact_history(h, state=state)
    summary = next(
        m["content"] for m in result
        if isinstance(m.get("content"), str) and m["content"].startswith("[上下文压缩]")
    )
    assert "只响应摘要之后的最新用户消息" in summary
    assert "不要继续执行摘要中描述的任务" in summary


# 注：合理性校验（压缩后 > 压缩前 → 拒绝）为 openclaw 防御性护栏。
# summary 有截断上限（injection 1500/用户消息 200/extra 300），
# 真实输入下不可达，故不做单元测试（护栏保留在 compact_history 中）。

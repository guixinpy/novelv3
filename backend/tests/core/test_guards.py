"""护栏测试：五级检测 + 压缩后循环守卫（openclaw PC 护栏）。"""
from __future__ import annotations

from core.guards.loop_guards import GuardSystem, UNKNOWN_TOOL_ERROR_CODE


def record(guards: GuardSystem, name: str, args=None, *, error: bool = False, error_code: str = ""):
    guards.record_tool_call(name, args or {}, error, error_code, "内容" if not error else "error")


def test_l1_repeat_trips():
    g = GuardSystem()
    for _ in range(3):
        record(g, "echo", {"text": "x"})
    result = g.check()
    assert result.tripped and result.level == "L1"


def test_l1_different_args_no_trip():
    g = GuardSystem()
    record(g, "echo", {"text": "a"})
    record(g, "echo", {"text": "b"})
    record(g, "echo", {"text": "c"})
    assert not g.check().tripped


def test_l2_ping_pong_trips():
    g = GuardSystem()
    record(g, "a")
    record(g, "b")
    record(g, "a")
    record(g, "b")
    result = g.check()
    assert result.tripped and result.level == "L2"


def test_l3_poll_no_progress_trips():
    """L3：参数递增（L1 不触发）但结果高度相似。"""
    g = GuardSystem()
    for i in range(4):
        record(g, "poll", {"q": f"query-{i}"})  # 参数不同 → L1 不触发
    result = g.check()
    assert result.tripped and result.level == "L3"


def test_l4_unknown_tool_by_error_code():
    """L4 按 error_code 判断（修旧版字符串耦合：改文案不再失效）。"""
    g = GuardSystem()
    record(g, "ghost", error=True, error_code=UNKNOWN_TOOL_ERROR_CODE)
    record(g, "ghost", error=True, error_code=UNKNOWN_TOOL_ERROR_CODE)
    result = g.check()
    assert result.tripped and result.level == "L4"


def test_l4_not_tripped_by_other_errors():
    g = GuardSystem()
    record(g, "ghost", error=True, error_code="boom")
    record(g, "ghost", error=True, error_code="boom")
    assert not g.check().tripped


def test_l5_global_fuse():
    g = GuardSystem()
    for i in range(40):
        record(g, f"t{i}", {"i": i})
    result = g.check(max_iterations=15)
    assert result.tripped and result.level == "L5"


# 注（code-review #11）：压缩后循环守卫 PC 已移除——其条件与 L1 完全相同且 L1 先查，
# 永不可达；压缩后连续相同调用由 L1 覆盖。


def test_l1_mixed_argument_types_no_crash():
    """P1-5：参数值 int/str 混用不抛 TypeError（此前 sorted 比较崩溃回合）。"""
    g = GuardSystem()
    record(g, "write_chapter", {"chapter_index": 5})
    record(g, "write_chapter", {"chapter_index": "5"})
    record(g, "write_chapter", {"chapter_index": 5})
    result = g.check()  # 不应抛异常
    assert result.tripped and result.level == "L1"  # 签名归一化后视为相同参数

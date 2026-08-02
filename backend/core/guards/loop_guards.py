"""五级循环风险检测（迁移旧 agent/guards.py）+ 压缩后循环守卫。

改进（对照旧版）：
- L4 幻觉工具检测从 `"不存在" in result_text` 字符串耦合改为按 error_code=="unknown_tool"
  （工具框架失败分类学，修旧缺陷 #3）
- 新增 check_post_compaction：压缩后立刻死循环检测（openclaw 护栏）
"""
from __future__ import annotations

from dataclasses import dataclass, field

UNKNOWN_TOOL_ERROR_CODE = "unknown_tool"


@dataclass
class GuardResult:
    tripped: bool = False
    level: str = ""
    reason: str = ""
    diagnosis: dict = field(default_factory=dict)


@dataclass
class ToolRecord:
    name: str
    arguments: dict | None
    is_error: bool
    error_code: str
    result_text: str


def _result_similar(a: str, b: str) -> float:
    """简单的字符串相似度（用于 L3 poll 检测）。"""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    longer = max(len(a), len(b))
    if longer == 0:
        return 1.0
    matches = sum(1 for ca, cb in zip(a, b) if ca == cb)
    return matches / longer


class GuardSystem:
    """五级风险检测器 + 压缩后循环守卫。每个回合新建一个实例。"""

    def __init__(self) -> None:
        self._history: list[ToolRecord] = []
        self._post_compaction_history: list[ToolRecord] = []

    def record_tool_call(
        self,
        name: str,
        arguments: dict | None,
        is_error: bool,
        error_code: str,
        result_text: str,
    ) -> None:
        record = ToolRecord(
            name=name, arguments=arguments, is_error=is_error,
            error_code=error_code, result_text=result_text,
        )
        self._history.append(record)
        self._post_compaction_history.append(record)

    def reset_post_compaction(self) -> None:
        """压缩发生时清空压缩后窗口（避免把压缩前的调用计入守卫）。"""
        self._post_compaction_history.clear()

    def check(self, max_iterations: int = 30) -> GuardResult:
        result = self._check_l1_generic_repeat()
        if result.tripped:
            return result
        result = self._check_l2_ping_pong()
        if result.tripped:
            return result
        result = self._check_l3_poll_no_progress()
        if result.tripped:
            return result
        result = self._check_l4_unknown_repeat()
        if result.tripped:
            return result
        result = self._check_l5_global_fuse(max_iterations)
        if result.tripped:
            return result
        return GuardResult()

    def check_post_compaction(self, min_calls: int = 3) -> GuardResult:
        """压缩后立即死循环检测（openclaw post-compaction-loop-guard）：
        压缩后的新窗口内出现 ≥min_calls 次完全相同调用则熔断。"""
        if len(self._post_compaction_history) < min_calls:
            return GuardResult()
        recent = self._post_compaction_history[-min_calls:]
        names = {r.name for r in recent}
        if len(names) != 1:
            return GuardResult()
        args = {str(sorted((r.arguments or {}).items())) for r in recent}
        if len(args) != 1:
            return GuardResult()
        return GuardResult(
            tripped=True,
            level="PC",
            reason=f"压缩后连续 {min_calls} 次调用相同工具「{recent[0].name}」且参数相同，疑似压缩引发死循环。",
            diagnosis={"level": "PC", "tool_name": recent[0].name, "repeat_count": min_calls},
        )

    # ---- 五级检测 ----

    def _check_l1_generic_repeat(self) -> GuardResult:
        """L1: 连续 N 次相同工具 + 相同参数。"""
        if len(self._history) < 3:
            return GuardResult()
        last3 = self._history[-3:]
        names = [r.name for r in last3]
        if len(set(names)) != 1:
            return GuardResult()
        args = [str(sorted((r.arguments or {}).items())) for r in last3]
        if len(set(args)) != 1:
            return GuardResult()
        return GuardResult(
            tripped=True,
            level="L1",
            reason=f"连续 3 次调用相同工具「{names[0]}」且参数完全相同，疑似死循环。",
            diagnosis={"level": "L1", "tool_name": names[0], "repeat_count": 3},
        )

    def _check_l2_ping_pong(self) -> GuardResult:
        """L2: A→B→A→B 模式 ≥2 对（A 和 B 必须不同）。"""
        if len(self._history) < 4:
            return GuardResult()
        recent = self._history[-4:]
        if recent[0].name != recent[1].name and recent[0].name == recent[2].name and recent[1].name == recent[3].name:
            return GuardResult(
                tripped=True,
                level="L2",
                reason=f"检测到乒乓模式：{recent[0].name} ⇄ {recent[1].name}，已循环 2 轮。",
                diagnosis={"level": "L2", "tool_a": recent[0].name, "tool_b": recent[1].name, "cycles": 2},
            )
        return GuardResult()

    def _check_l3_poll_no_progress(self) -> GuardResult:
        """L3: 同一工具连续 4+ 次调用且结果高度相似。"""
        if len(self._history) < 4:
            return GuardResult()
        recent4 = self._history[-4:]
        names = [r.name for r in recent4]
        if len(set(names)) != 1:
            return GuardResult()
        if all(
            _result_similar(recent4[i].result_text, recent4[i + 1].result_text) > 0.9
            for i in range(3)
        ):
            return GuardResult(
                tripped=True,
                level="L3",
                reason=f"连续 4 次调用「{names[0]}」返回结果高度相似，模型可能卡在无进展轮询。",
                diagnosis={"level": "L3", "tool_name": names[0], "poll_count": 4},
            )
        return GuardResult()

    def _check_l4_unknown_repeat(self) -> GuardResult:
        """L4: 模型持续请求不存在的工具（按 error_code 判断，不再字符串耦合）。"""
        unknown = [r for r in self._history if r.is_error and r.error_code == UNKNOWN_TOOL_ERROR_CODE]
        if len(unknown) >= 2:
            return GuardResult(
                tripped=True,
                level="L4",
                reason=f"模型连续 {len(unknown)} 次请求不存在或不可用的工具，可能是模型幻觉。",
                diagnosis={"level": "L4", "unknown_count": len(unknown)},
            )
        return GuardResult()

    def _check_l5_global_fuse(self, max_iterations: int) -> GuardResult:
        """L5: 总迭代次数超过上限的 2 倍（硬熔断）。"""
        if len(self._history) >= max_iterations * 2:
            return GuardResult(
                tripped=True,
                level="L5",
                reason=f"回合工具调用次数已达 {len(self._history)}，超过上限 {max_iterations} 的 2 倍，全局熔断。",
                diagnosis={"level": "L5", "total_calls": len(self._history), "max_iterations": max_iterations},
            )
        return GuardResult()

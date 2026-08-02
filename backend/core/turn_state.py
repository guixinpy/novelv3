"""回合状态对象（吸收 hermes-agent TurnRetryState：一次性 guard 收敛为可命名可单测对象）。

一个回合创建一个 TurnState 实例，承载循环内所有可变状态：
- 重试/恢复相关的一次性标记
- 工具错误样本（供回合末注入诊断）
- guard 诊断（供 follow-up 注入）
- wall-clock 计时（turn 级时间上限）
- exit_detail 收集（回合结束时的结构化诊断）
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class TurnState:
    # ── 预算与计时 ──
    max_wall_clock_ms: float | None = None
    _started_at: float | None = None

    # ── 压缩 ──
    compacted: bool = False

    # ── 工具错误样本 ──
    tool_error_total: int = 0
    tool_error_samples: list[tuple[str, str]] = field(default_factory=list)

    # ── guard ──
    last_guard_diagnosis: dict | None = None

    # ── 恢复注入计数（每回合 ≤1 条）──
    recovery_injected: bool = False

    def start(self) -> None:
        self._started_at = time.monotonic()

    def elapsed_ms(self) -> float:
        if self._started_at is None:
            return 0.0
        return (time.monotonic() - self._started_at) * 1000

    def wall_clock_exhausted(self) -> bool:
        return self.max_wall_clock_ms is not None and self.elapsed_ms() >= self.max_wall_clock_ms

    def record_tool_error(self, name: str, result_text: str, max_samples: int = 3) -> None:
        self.tool_error_total += 1
        if len(self.tool_error_samples) < max_samples:
            self.tool_error_samples.append((name, result_text[:120]))

    def record_guard(self, diagnosis: dict) -> None:
        self.last_guard_diagnosis = diagnosis

    def claim_recovery(self) -> bool:
        """每回合只注入一条恢复消息（guard 或工具错误）。"""
        if self.recovery_injected:
            return False
        self.recovery_injected = True
        return True

    def exit_detail(self) -> dict:
        detail: dict = {
            "tool_errors": self.tool_error_total,
            "compacted": self.compacted,
            "elapsed_ms": round(self.elapsed_ms(), 1),
        }
        if self.tool_error_samples:
            detail["error_samples"] = [
                {"name": name, "text": text} for name, text in self.tool_error_samples
            ]
        if self.last_guard_diagnosis:
            detail["guard"] = self.last_guard_diagnosis
        return detail

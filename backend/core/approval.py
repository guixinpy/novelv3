"""审批门（arch-refactor 恢复旧 ApprovalGate，与新内核双队列融合）。

作为 BeforeToolCall 钩子接入 loop：permission=write 的工具调用被拦截，
发射 ApprovalPending 事件并等待人工 approve/reject；超时自动拒绝（fail-closed）。

会话级实例：由 API 层持有（一个会话一个 gate），与 harness 同生命周期。

线程安全（flaky 根治）：等待用 threading.Event + asyncio.to_thread——
approve/reject 可从任意线程调用（HTTP 端点跑在线程池、测试线程直调），
asyncio.Event.set 跨线程是未定义行为（实测偶发丢失唤醒导致审批永不放行）。

并发正确性（code-review 三轮 #3/#4）：_pending/_decisions 等全部受
threading.Lock 保护——approve 的 check-then-act、pending_requests 迭代、
等待协程的清理均原子；等待用 try/finally 确保取消/异常时清理（客户端断开
不再泄漏 pending/decisions 条目——此前重构删除 finally 导致永久泄漏）。
"""
from __future__ import annotations

import asyncio
import threading
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from core.events import ApprovalPending, LoopEvent
from core.tools.base import PermissionLevel, ToolContext, ToolRegistry

# 审批等待超时：10 分钟未决策自动拒绝（防 SSE 挂起）
APPROVAL_TIMEOUT_SECONDS = 600.0


class ApprovalGate:
    def __init__(self, registry: ToolRegistry, timeout_seconds: float = APPROVAL_TIMEOUT_SECONDS) -> None:
        self._registry = registry
        self._timeout = timeout_seconds
        self._emit: Callable[[LoopEvent], Awaitable[None] | None] | None = None
        self._lock = threading.Lock()
        self._pending: dict[str, threading.Event] = {}
        self._decisions: dict[str, bool] = {}
        self._reasons: dict[str, str] = {}
        self._pending_info: dict[str, dict[str, Any]] = {}

    def set_emitter(self, emit: Callable[[LoopEvent], Awaitable[None] | None] | None) -> None:
        self._emit = emit

    def pending_requests(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {"call_id": call_id, **info}
                for call_id, info in self._pending_info.items()
            ]

    async def before_tool_call(
        self, name: str, arguments: dict | None, ctx: ToolContext,
    ) -> str | None:
        """BeforeToolCall 钩子：write 工具拦截等待批准。返回 None 放行，字符串拦截。"""
        try:
            definition = self._registry.get(name)
        except KeyError:
            return None  # 未知工具由 registry 处理
        if definition.permission != PermissionLevel.WRITE:
            return None

        call_id = uuid.uuid4().hex[:12]
        event = threading.Event()
        with self._lock:
            self._pending[call_id] = event
            self._pending_info[call_id] = {"name": name, "arguments": arguments or {}, "status": "pending"}

        if self._emit is not None:
            outcome = self._emit(ApprovalPending(call_id=call_id, name=name, arguments=arguments))
            if outcome is not None:
                await outcome

        try:
            # threading.Event.wait 线程安全（approve 可从 HTTP 线程/测试线程调用）；
            # 超时返回 False（等待线程自行退出，不泄漏）
            decided = await asyncio.to_thread(event.wait, self._timeout)
        finally:
            # 清理必须无条件执行（code-review 三轮 #3：此前重构删 finally，
            # 等待被取消（SSE 断开）时 pending/decisions 永久泄漏）
            with self._lock:
                self._pending.pop(call_id, None)
                self._pending_info.pop(call_id, None)
                approved = self._decisions.pop(call_id, False)
                reason = self._reasons.pop(call_id, "")

        if not decided:
            # 超时自动拒绝（fail-closed），防 SSE 无限挂起
            approved = False
            reason = "审批等待超时（10 分钟未决策），已自动拒绝。"
        if approved:
            return None
        return f"用户拒绝了工具「{name}」的调用。{reason}请改用其他方案，或先征得用户同意再尝试。"

    def approve(self, call_id: str) -> bool:
        with self._lock:
            if call_id not in self._pending:
                return False
            self._decisions[call_id] = True
            self._pending[call_id].set()
            return True

    def reject(self, call_id: str, reason: str = "") -> bool:
        with self._lock:
            if call_id not in self._pending:
                return False
            self._decisions[call_id] = False
            self._reasons[call_id] = reason
            self._pending[call_id].set()
            return True

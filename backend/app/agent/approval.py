"""审批门：拦截 permission=write/propose 的工具调用，等待用户批准或拒绝。

作为 BeforeToolCall 接入 loop._execute_one 的工具执行前钩子。
"""
from __future__ import annotations

import asyncio
import inspect
import uuid
from collections.abc import Awaitable, Callable

from app.agent.events import ApprovalPending, LoopEvent
from app.agent.tooling import PermissionLevel, ToolContext, ToolRegistry


class ApprovalGate:
    """审批门实例。每个会话一个，由 v2_sessions API 持有。

    双状态角色：
    1. BeforeToolCall 回调 —— 在 loop._execute_one 中检查权限并拦截
    2. 外部控制接口 —— API 端点通过 approve() / reject() 解锁
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry
        self._emit: Callable[[LoopEvent], Awaitable[None] | None] | None = None
        self._pending_id: str | None = None
        self._event: asyncio.Event | None = None
        self._approved: bool | None = None
        self._reject_reason: str = ""

    def set_emitter(self, emit: Callable[[LoopEvent], Awaitable[None]]) -> None:
        """由 harness 在每次 _run_one_turn 前设置当前回合的事件发射器。"""
        self._emit = emit

    @property
    def pending_info(self) -> dict | None:
        """当前待审批项信息，供 API 查询。无待审批返回 None。"""
        if self._pending_id is None:
            return None
        return {"approval_id": self._pending_id}

    async def before_tool_call(
        self, name: str, arguments: dict | None, ctx: ToolContext,
    ) -> str | None:
        """BeforeToolCall 签名兼容的回调。返回 None 放行，返回字符串拦截。"""
        try:
            tool_def = self._registry.get(name)
        except KeyError:
            # 未知工具（模型幻觉）：拦截并给出可恢复错误，避免 KeyError 崩掉整个 SSE 请求
            return (
                f"工具 {name} 不存在。可用工具：{sorted(self._registry.names())}。"
                "请改用其中之一。"
            )
        if tool_def.permission in (PermissionLevel.READ,):
            return None  # 只读工具直接放行

        approval_id = str(uuid.uuid4())
        self._pending_id = approval_id
        self._event = asyncio.Event()
        self._approved = None
        self._reject_reason = ""

        if self._emit is not None:
            outcome = self._emit(ApprovalPending(
                approval_id=approval_id,
                tool_name=name,
                arguments=arguments,
            ))
            if inspect.isawaitable(outcome):
                await outcome

        # 等待外部信号（approve / reject）
        await self._event.wait()
        self._event = None
        self._pending_id = None

        if self._approved:
            return None  # 放行
        return self._reject_reason or "用户拒绝了此操作，请调整方案后重试。"

    def approve(self) -> bool:
        """批准当前待审批的工具调用。无待审批时返回 False。"""
        if self._event is None:
            return False
        self._approved = True
        self._event.set()
        return True

    def reject(self, reason: str = "") -> bool:
        """拒绝当前待审批的工具调用。可附理由给模型。"""
        if self._event is None:
            return False
        self._approved = False
        self._reject_reason = reason or "用户拒绝了此操作，请调整方案后重试。"
        self._event.set()
        return True

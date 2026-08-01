"""有状态外壳（openclaw harness 模式 / CADR-004）。

持有会话历史、JSONL 追加日志、steering/follow-up 队列；
把每条用户消息交给无状态的 run_turn，事件以异步迭代器形式向外流出。
"""
from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

from app.agent.budget import IterationBudget, TokenBudget
from app.agent.approval import ApprovalGate
from app.agent.compaction import (
    check_context_usage,
    compact_history,
    reset_compaction_stats,
)
from app.agent.events import (
    ApprovalPending,
    ContextWarning,
    GuardTripped,
    LoopEvent,
    ToolCallFinished,
    TurnEnded,
)
from app.agent.loop import BeforeToolCall, EventSink, StopReason, run_turn
from app.agent.providers.base import Provider
from app.agent.tooling import ToolContext, ToolRegistry

import asyncio


def _sanitize_tool_message_order(history: list[dict]) -> list[dict]:
    """删除孤立的 tool 消息（前面没有带 tool_calls 的 assistant 消息）。

    DeepSeek 要求 tool 消息必须响应某条 assistant(tool_calls)；
    压缩把中间 assistant 收进摘要后，会留下无配对的 tool 消息导致 HTTP 400。
    """
    cleaned: list[dict] = []
    for msg in history:
        if msg.get("role") == "tool":
            prev_non_tool: dict | None = None
            for m in reversed(cleaned):
                if m.get("role") != "tool":
                    prev_non_tool = m
                    break
            if (
                prev_non_tool is None
                or prev_non_tool.get("role") != "assistant"
                or "tool_calls" not in prev_non_tool
            ):
                continue
        cleaned.append(msg)
    return cleaned


@dataclass
class HarnessConfig:
    system_prompt: str
    max_iterations_per_turn: int = 30
    max_tokens_per_turn: int | None = None
    provider_kwargs: dict | None = None


class AgentHarness:
    def __init__(
        self,
        *,
        session_id: str,
        session_dir: Path,
        provider: Provider,
        registry: ToolRegistry,
        tool_context: ToolContext,
        config: HarnessConfig,
        before_tool_call: BeforeToolCall | None = None,
        approval_gate: ApprovalGate | None = None,
    ) -> None:
        self.approval_gate: ApprovalGate | None = approval_gate
        self.session_id = session_id
        self.log_path = Path(session_dir) / f"{session_id}.jsonl"
        self.provider = provider
        self.registry = registry
        self.tool_context = tool_context
        self.config = config
        self.before_tool_call = before_tool_call
        reset_compaction_stats()
        self._steering: deque[str] = deque()
        self._follow_ups: deque[str] = deque()
        self.messages: list[dict] = self._load()

    # ---- 持久化 ----

    def _load(self) -> list[dict]:
        if not self.log_path.exists():
            return []
        messages: list[dict] = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("type") == "message":
                messages.append(entry["data"])
            elif entry.get("type") == "compaction":
                # 压缩快照是此后消息状态的真相源（append-only 日志中的检查点）
                messages = list(entry["data"]["messages"][1:])
        return messages

    def _append_log(self, entry_type: str, data: dict) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"type": entry_type, "data": data}, ensure_ascii=False) + "\n")

    def _persist_new_messages(self, before_count: int, history: list[dict]) -> None:
        for message in history[before_count:]:
            self._append_log("message", message)
            self.messages.append(message)

    # ---- 队列 ----

    def queue_steering(self, text: str) -> None:
        self._steering.append(text)

    def queue_follow_up(self, text: str) -> None:
        self._follow_ups.append(text)

    def _drain_steering(self) -> list[str]:
        drained = list(self._steering)
        self._steering.clear()
        return drained

    # ---- 主入口 ----

    async def send(self, user_text: str) -> AsyncIterator[LoopEvent]:
        """处理一条用户消息（含 follow-up 链），逐事件产出。"""
        # 主队列：maxsize=1 保证 steering 注入时序
        # 审批通道：无上限，防止 ApprovalPending 被工具事件阻塞
        main_queue: asyncio.Queue[LoopEvent | None] = asyncio.Queue(maxsize=1)
        approval_queue: asyncio.Queue[LoopEvent] = asyncio.Queue()

        async def sink(event: LoopEvent) -> None:
            # ApprovalPending 走独立通道，其余走主队列
            if isinstance(event, ApprovalPending):
                await approval_queue.put(event)
            await main_queue.put(event)

        async def worker() -> None:
            try:
                pending = user_text
                while pending is not None:
                    await self._run_one_turn(pending, sink)
                    pending = self._follow_ups.popleft() if self._follow_ups else None
            finally:
                await main_queue.put(None)

        task = asyncio.create_task(worker())
        try:
            while True:
                # 优先消费审批事件（非阻塞），再等主队列
                try:
                    while True:
                        approval_event = approval_queue.get_nowait()
                        yield approval_event
                except asyncio.QueueEmpty:
                    pass

                event = await main_queue.get()
                if event is None:
                    break
                yield event

                # yield 后立即排空审批队列（可能在等待期间积累）
                try:
                    while True:
                        approval_event = approval_queue.get_nowait()
                        yield approval_event
                except asyncio.QueueEmpty:
                    pass

            await task
        finally:
            if not task.done():
                task.cancel()

    async def _run_one_turn(
        self, user_text: str, sink: EventSink,
    ) -> None:
        self._append_log("message", {"role": "user", "content": user_text})
        self.messages.append({"role": "user", "content": user_text})

        history = [{"role": "system", "content": self.config.system_prompt}, *self.messages]
        last_guard_diagnosis: dict | None = None
        tool_error_total = 0
        tool_error_samples: list[tuple[str, str]] = []

        # 上下文用量预检 + 自动压缩（M3：75% 阈值 + 头尾保护；超限时压缩中间历史）
        ctx_warning = check_context_usage(history)
        if ctx_warning is not None:
            pct, total = ctx_warning
            await sink(ContextWarning(usage_pct=round(pct, 3), total_tokens=total, max_tokens=128_000))
            compressed = compact_history(history)
            if len(compressed) < len(history):
                compressed = _sanitize_tool_message_order(compressed)
                summary = next(
                    (m.get("content", "") for m in compressed
                     if isinstance(m.get("content"), str) and m["content"].startswith("[上下文压缩]")),
                    "",
                )
                self._append_log(
                    "compaction",
                    {
                        "messages": compressed,
                        "summary": summary,
                        "before_count": len(history),
                        "after_count": len(compressed),
                        "usage_pct": round(pct, 3),
                    },
                )
                self.messages = compressed[1:]
                history = compressed

        before_count = len(history)

        async def persisting_sink(event: LoopEvent) -> None:
            nonlocal last_guard_diagnosis, tool_error_total, tool_error_samples
            if isinstance(event, TurnEnded):
                self._append_log(
                    "turn_ended",
                    {
                        "stop_reason": event.stop_reason,
                        "iterations": event.iterations,
                        "prompt_tokens": event.usage.prompt_tokens,
                        "completion_tokens": event.usage.completion_tokens,
                    },
                )
            elif isinstance(event, GuardTripped):
                last_guard_diagnosis = event.diagnosis
            elif isinstance(event, ToolCallFinished) and event.is_error:
                tool_error_total += 1
                if len(tool_error_samples) < 3:
                    tool_error_samples.append((event.name, event.result_text[:120]))
            await sink(event)

        if self.approval_gate is not None:
            self.approval_gate.set_emitter(persisting_sink)

        result = await run_turn(
            provider=self.provider,
            messages=history,
            registry=self.registry,
            tool_context=self.tool_context,
            iteration_budget=IterationBudget(self.config.max_iterations_per_turn),
            token_budget=TokenBudget(self.config.max_tokens_per_turn),
            event_sink=persisting_sink,
            before_tool_call=self.before_tool_call,
            steering_source=self._drain_steering,
            extra_provider_kwargs=self.config.provider_kwargs,
        )
        self._persist_new_messages(before_count, result.messages)

        # 风险→恢复：GuardTripped 后注入诊断+恢复建议
        if last_guard_diagnosis is not None:
            level = last_guard_diagnosis.get("level", "")
            tool_name = last_guard_diagnosis.get("tool_name", "")
            recover_advice = (
                f"【护栏触发 - {level}】检测到循环风险：工具「{tool_name}」重复调用。"
                f"请更换策略：换用不同的工具或调整参数后再试。"
            )
            self.queue_follow_up(recover_advice)
        elif tool_error_total:
            # T1 R2：回合内工具错误 → 通用「错误诊断 + 下一步建议」注入（每回合 ≤1 条）
            detail = "; ".join(f"{name}: {text[:80]}" for name, text in tool_error_samples)
            if tool_error_total > len(tool_error_samples):
                detail += f"（另有 {tool_error_total - len(tool_error_samples)} 次未列出）"
            self.queue_follow_up(
                f"【工具调用提示】本回合 {tool_error_total} 次工具调用失败（{detail}）。"
                f"建议：调整参数重试，或改用其他工具。"
            )

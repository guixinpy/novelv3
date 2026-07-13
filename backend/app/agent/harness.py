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
from app.agent.events import LoopEvent, TurnEnded
from app.agent.loop import BeforeToolCall, run_turn
from app.agent.providers.base import Provider
from app.agent.tooling import ToolContext, ToolRegistry

import asyncio


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
    ) -> None:
        self.approval_gate: ApprovalGate | None = (
            before_tool_call
            if isinstance(before_tool_call, ApprovalGate)
            else None
        )
        self.session_id = session_id
        self.log_path = Path(session_dir) / f"{session_id}.jsonl"
        self.provider = provider
        self.registry = registry
        self.tool_context = tool_context
        self.config = config
        self.before_tool_call = before_tool_call
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
        return messages

    def _append_log(self, entry_type: str, data: dict) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"type": entry_type, "data": data}, ensure_ascii=False) + "\n")

    def _persist_new_messages(self, before_count: int, history: list[dict]) -> None:
        # history = [system] + self.messages[:] + 新消息；system 不持久化
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
        # maxsize=1：消费者跟上节奏前生产者阻塞，保证 steering 注入时序可预期
        queue: asyncio.Queue[LoopEvent | None] = asyncio.Queue(maxsize=1)

        async def sink(event: LoopEvent) -> None:
            await queue.put(event)

        async def worker() -> None:
            try:
                pending = user_text
                while pending is not None:
                    await self._run_one_turn(pending, sink)
                    pending = self._follow_ups.popleft() if self._follow_ups else None
            finally:
                await queue.put(None)

        task = asyncio.create_task(worker())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
            await task
        finally:
            if not task.done():
                task.cancel()

    async def _run_one_turn(self, user_text: str, sink) -> None:
        self._append_log("message", {"role": "user", "content": user_text})
        self.messages.append({"role": "user", "content": user_text})

        history = [{"role": "system", "content": self.config.system_prompt}, *self.messages]
        before_count = len(history)

        async def persisting_sink(event: LoopEvent) -> None:
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

"""有状态外壳（迁移旧 app/agent/harness.py + 吸收改进）。

持有会话转录、steering/follow-up 双队列、CompactionState（实例级）、
幂等键、写锁；把每条用户消息交给无状态 run_turn，事件以异步迭代器向外流出。

吸收点：
- steer/followUp 双队列 + one-at-a-time（openclaw #1）：生成中改方向 / 完成后追加
- CompactionState 实例化（修旧缺陷 #1：多会话并发不污染）
- 幂等键 + 会话写锁（openclaw #5）：重复投递安全、并发写保护
- KV-cache 契约（openhuman #1）：system prompt 首轮构建字节冻结，
  动态内容（快照/注入）骑尾部 user 消息，不改 prompt 前缀
- api_content sidecar（hermes #5）：存储干净内容，发送精确字节
"""
from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path

from core.context.compaction import CompactionState, check_context_usage, compact_history
from core.events import (
    AgentEnd,
    AgentStart,
    ApprovalPending,
    Compaction,
    ContextWarning,
    GuardTripped,
    LoopEvent,
    TurnEnded,
)
from core.guards.budget import IterationBudget, TokenBudget
from core.loop import BeforeToolCall, EventSink, run_turn
from core.providers.base import Provider
from core.session.transcript import Transcript, strip_api_fields
from core.tools.base import ToolContext, ToolRegistry

# 快照提供者：由外部（API 层）注入，避免内核依赖领域模块（CADR-005）
SnapshotProvider = Callable[[], str | None]
# 状态重注入提供者：压缩后把跨压缩存活的状态（设定/大纲/人物卡）重新注入
InjectionProvider = Callable[[], str | None]

# 压缩后清理孤立 tool 消息（DeepSeek 要求 tool 消息必须响应某条 assistant(tool_calls)）
_SUMMARY_PREFIX = "[上下文压缩]"


def _sanitize_tool_message_order(history: list[dict]) -> list[dict]:
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
    max_wall_clock_ms: float | None = None
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
        snapshot_provider: SnapshotProvider | None = None,
        injection_provider: InjectionProvider | None = None,
    ) -> None:
        self.session_id = session_id
        self.provider = provider
        self.registry = registry
        self.tool_context = tool_context
        self.config = config
        self.before_tool_call = before_tool_call
        self._snapshot_provider = snapshot_provider
        self._injection_provider = injection_provider
        self.transcript = Transcript(Path(session_dir) / f"{session_id}.jsonl")
        # 实例级压缩状态（修旧版模块级全局缺陷）
        self._compaction_state = CompactionState()
        # 双注入队列（openclaw）：steering 回合内注入 / follow-up 回合后追加
        self._steering: deque[str] = deque()
        self._follow_ups: deque[str] = deque()
        # 幂等键：已处理的 user 消息（重复投递安全）
        self._processed_idempotency_keys: set[str] = set()
        # 会话写锁：同一会话并发 send 时后者等待（openclaw 写锁思想）
        self._write_lock = asyncio.Lock()
        self._turn_index = 0
        self._recovery_injected = False

    # ── 队列（openclaw steer/followUp 语义）──

    def queue_steering(self, text: str) -> None:
        """生成中注入方向：当前工具批完成后、下次 LLM 调用前生效。"""
        self._steering.append(text)

    def queue_follow_up(self, text: str) -> None:
        """完成后追加要求：agent 本要停止时注入再续跑一轮。"""
        self._follow_ups.append(text)

    def _drain_steering_one(self) -> list[str]:
        """one-at-a-time drain（openclaw QueueMode）：每条 steering 独占一次注入机会。"""
        if not self._steering:
            return []
        return [self._steering.popleft()]

    # ── 快照与状态注入 ──

    def _build_snapshot(self) -> str | None:
        if self._snapshot_provider is None:
            return None
        try:
            return self._snapshot_provider()
        except Exception:
            # 快照是只读辅助，失败静默跳过，不阻断写作
            return None

    def _build_system_and_tail(self) -> tuple[str, list[dict]]:
        """KV-cache 契约：system 首轮构建字节冻结，动态内容骑尾部 user 消息。"""
        return self.config.system_prompt, []

    # ── 主入口 ──

    async def send(
        self,
        user_text: str,
        *,
        idempotency_key: str | None = None,
    ) -> AsyncIterator[LoopEvent]:
        """处理一条用户消息（含 follow-up 链），逐事件产出。

        idempotency_key 非 None 且已处理过 → 直接结束（重复投递安全）。
        """
        if idempotency_key is not None and idempotency_key in self._processed_idempotency_keys:
            return

        async with self._write_lock:
            self._processed_idempotency_keys.add(idempotency_key) if idempotency_key else None
            async for event in self._send_locked(user_text):
                yield event

    async def _send_locked(self, user_text: str) -> AsyncIterator[LoopEvent]:
        yield AgentStart(session_id=self.session_id)

        main_queue: asyncio.Queue[LoopEvent | None] = asyncio.Queue(maxsize=1)
        approval_queue: asyncio.Queue[LoopEvent] = asyncio.Queue()

        async def sink(event: LoopEvent) -> None:
            if isinstance(event, ApprovalPending):
                await approval_queue.put(event)
            await main_queue.put(event)

        async def worker() -> None:
            try:
                pending = user_text
                while pending is not None:
                    self._turn_index += 1
                    await self._run_one_turn(pending, sink)
                    pending = self._follow_ups.popleft() if self._follow_ups else None
            finally:
                await main_queue.put(None)

        task = asyncio.create_task(worker())
        try:
            while True:
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

        yield AgentEnd(turns=self._turn_index)

    async def _run_one_turn(self, user_text: str, sink: EventSink) -> None:
        self._recovery_injected = False
        user_message = {"role": "user", "content": user_text}
        self.transcript.append_message(user_message)

        # KV-cache 契约：system 冻结，快照骑尾部 user 消息（不改 prompt 前缀）
        system_content = self.config.system_prompt
        snapshot = self._build_snapshot()
        dynamic_tail: list[dict] = []
        if snapshot:
            dynamic_tail.append({"role": "user", "content": f"[项目状态]\n{snapshot}"})
        history = [{"role": "system", "content": system_content}, *dynamic_tail, *self.transcript.messages]

        # 上下文用量预检 + 自动压缩（护栏：冷却/防抖/合理性校验由 CompactionState 承担）
        ctx_warning = check_context_usage(history)
        if ctx_warning is not None:
            pct, total = ctx_warning
            await sink(ContextWarning(usage_pct=round(pct, 3), total_tokens=total, max_tokens=128_000))
            compressed = compact_history(
                history,
                state=self._compaction_state,
                extra_context=snapshot,
                injection_provider=self._injection_provider,
            )
            if len(compressed) < len(history):
                compressed = _sanitize_tool_message_order(compressed)
                summary = next(
                    (m.get("content", "") for m in compressed
                     if isinstance(m.get("content"), str) and m["content"].startswith(_SUMMARY_PREFIX)),
                    "",
                )
                self.transcript.record_compaction(compressed, summary)
                await sink(
                    Compaction(
                        before_count=len(history),
                        after_count=len(compressed),
                        summary=summary[:300],
                    )
                )
                history = compressed
                # 压缩后：护栏新窗口从零开始（避免旧调用计入新窗口）
                self._compaction_state.mark_compacted()

        before_count = len(history)
        guard_diagnoses: list[dict] = []

        async def persisting_sink(event: LoopEvent) -> None:
            if isinstance(event, TurnEnded):
                # 回合结束元数据只写日志（事件重放用），绝不进入 messages（会被发给模型）
                self.transcript.record_event("turn_ended", event.__dict__)
            elif isinstance(event, GuardTripped):
                guard_diagnoses.append(event.diagnosis)
            await sink(event)

        result = await run_turn(
            provider=self.provider,
            messages=history,
            registry=self.registry,
            tool_context=self.tool_context,
            iteration_budget=IterationBudget(self.config.max_iterations_per_turn),
            token_budget=TokenBudget(self.config.max_tokens_per_turn),
            event_sink=persisting_sink,
            before_tool_call=self.before_tool_call,
            steering_source=self._drain_steering_one,
            extra_provider_kwargs=self.config.provider_kwargs,
            max_wall_clock_ms=self.config.max_wall_clock_ms,
        )
        # 持久化新消息（sidecar：剥离 api_content 等发送专用字段）
        self.transcript.append_messages([strip_api_fields(m) for m in result.messages[before_count:]])

        # 风险→恢复：guard 触发或工具错误 → 注入诊断+恢复建议（每回合 ≤1 条）
        exit_detail = result.exit_detail
        guard = exit_detail.get("guard")
        if guard is not None:
            level = guard.get("level", "")
            tool_name = guard.get("tool_name", "")
            recover_advice = (
                f"【护栏触发 - {level}】检测到循环风险：工具「{tool_name}」重复调用。"
                f"请更换策略：换用不同的工具或调整参数后再试。"
            )
            self.queue_follow_up(recover_advice)
        elif exit_detail.get("tool_errors") and not self._recovery_injected:
            self._recovery_injected = True
            samples = exit_detail.get("error_samples") or []
            detail = "; ".join(f"{s['name']}: {s['text'][:80]}" for s in samples)
            total = exit_detail.get("tool_errors", 0)
            if total > len(samples):
                detail += f"（另有 {total - len(samples)} 次未列出）"
            self.queue_follow_up(
                f"【工具调用提示】本回合 {total} 次工具调用失败（{detail}）。"
                f"建议：调整参数重试，或改用其他工具。"
            )

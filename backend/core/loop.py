"""无状态回合引擎（迁移旧 app/agent/loop.py + 吸收改进）。

一个回合 = 从一条用户消息开始，循环「LLM 调用 → 工具执行 → 观察回填」，
直到模型自然结束或预算耗尽。本模块不持有任何会话状态，事件经 sink 发出。

改进（对照旧版）：
- TurnState 对象化（hermes）：循环内一次性状态收敛为可单测对象
- 失败分类进事件（openhuman）：ToolFinished 携带 error_code/next_action
- wall-clock 上限（openhuman）：turn 级时间总控
- 优雅暂停（openhuman）：到迭代上限返回部分结果 + paused 状态，可 checkpoint 续写
- 压缩后循环守卫（openclaw）：压缩后窗口内死循环检测
- 错误编码为消息：provider 异常不会静默，经 provider 层 retryable 标志决策
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from core.events import (
    AssistantDelta,
    AssistantMessage,
    GuardTripped,
    ToolFinished,
    ToolStarted,
    TurnEnded,
)
from core.guards.budget import IterationBudget, TokenBudget
from core.guards.loop_guards import GuardSystem
from core.providers.base import Provider, ProviderResponse, TextDelta, ToolCall, Usage
from core.tools.base import PermissionLevel, ToolContext, ToolRegistry, ToolResult
from core.turn_state import TurnState

EventSink = Callable[[Any], "Awaitable[None] | None"]
# 返回 None 放行；返回字符串则拦截，字符串作为给模型的解释
BeforeToolCall = Callable[[str, dict | None, ToolContext], Awaitable[str | None]]
# 工具批执行后排空 steering 消息（openclaw 模式），返回要注入的 user 消息文本列表
SteeringSource = Callable[[], list[str]]


class StopReason(StrEnum):
    COMPLETED = "completed"
    ITERATION_BUDGET_EXHAUSTED = "iteration_budget_exhausted"
    TOKEN_BUDGET_EXHAUSTED = "token_budget_exhausted"
    WALL_CLOCK_EXCEEDED = "wall_clock_exceeded"
    INTERRUPTED = "interrupted"
    GUARD_TRIPPED = "guard_tripped"


# 空响应恢复（hermes #7 阶梯的最小版）：模型无输出无工具调用时注入引导重试，
# 防"写一半停"被当作正常完成静默结束。重试次数有上限（终局仍空则正常结束）。
_EMPTY_RESPONSE_NUDGE = (
    "（上一条回复为空。）请基于当前对话继续完成你的任务，不要重复已完成的步骤。"
)
_MAX_EMPTY_RESPONSE_RETRIES = 2


@dataclass
class TurnResult:
    stop_reason: StopReason
    messages: list[dict]
    iterations: int = 0
    total_usage: Usage = field(default_factory=Usage)
    exit_detail: dict = field(default_factory=dict)
    # 优雅暂停：迭代上限前最后一条 assistant 输出（可续写的部分结果）
    partial_response: str = ""


def _tool_calls_to_message(content: str, tool_calls: list[ToolCall]) -> dict:
    return {
        "role": "assistant",
        "content": content or None,
        "tool_calls": [
            {
                "id": c.id,
                "type": "function",
                "function": {"name": c.name, "arguments": c.arguments_raw},
            }
            for c in tool_calls
        ],
    }


async def run_turn(
    *,
    provider: Provider,
    messages: list[dict],
    registry: ToolRegistry,
    tool_context: ToolContext,
    iteration_budget: IterationBudget,
    token_budget: TokenBudget,
    event_sink: EventSink,
    before_tool_call: BeforeToolCall | None = None,
    steering_source: SteeringSource | None = None,
    extra_provider_kwargs: dict | None = None,
    max_wall_clock_ms: float | None = None,
    compacted: bool = False,
    guard_system: GuardSystem | None = None,
) -> TurnResult:
    history = list(messages)
    iterations = 0
    total_prompt = 0
    total_completion = 0
    stop_reason = StopReason.COMPLETED
    partial_response = ""
    state = TurnState(max_wall_clock_ms=max_wall_clock_ms)
    state.compacted = compacted  # 压缩发生在 harness 层（code-review #11：此前恒 False）
    state.start()
    # 护栏可注入（openclaw 钩子化）：默认五级护栏，外部可换实现（测试/扩展）
    guards = guard_system if guard_system is not None else GuardSystem()

    async def emit(event: Any) -> None:
        outcome = event_sink(event)
        if outcome is not None:
            await outcome

    def usage_total() -> Usage:
        return Usage(prompt_tokens=total_prompt, completion_tokens=total_completion)

    while True:
        if not iteration_budget.consume():
            stop_reason = StopReason.ITERATION_BUDGET_EXHAUSTED
            break
        iterations += 1

        if state.wall_clock_exhausted():
            stop_reason = StopReason.WALL_CLOCK_EXCEEDED
            break

        response: ProviderResponse | None = None
        streamed_text: list[str] = []
        try:
            # 发送副本剥离 ephemeral 键（code-review #12：内部标记不发给 API，
            # 未知消息字段有 400 风险；ephemeral 仅用于 harness 持久化过滤）
            send_history = [
                {k: v for k, v in m.items() if k != "ephemeral"} for m in history
            ]
            async for event in provider.stream(
                send_history, tools=registry.to_specs(), **(extra_provider_kwargs or {})
            ):
                if isinstance(event, TextDelta):
                    streamed_text.append(event.text)
                    await emit(AssistantDelta(text=event.text))
                elif isinstance(event, ProviderResponse):
                    response = event
        except Exception as exc:  # noqa: BLE001 - provider 异常编码为消息而非静默
            if streamed_text:
                # 部分流恢复（hermes）：网络中断但已有流式文本——不丢已生成内容，
                # 累积文本作为最终回复（provider 层已保证部分流不重试防重复输出）
                partial = "".join(streamed_text)
                history.append({"role": "assistant", "content": partial})
                await emit(AssistantMessage(content=partial))
                partial_response = partial
                state.partial_stream_recovered = True
                stop_reason = StopReason.COMPLETED
                break
            stop_reason = StopReason.INTERRUPTED
            error_text = f"模型调用失败：{exc}。"
            history.append({"role": "assistant", "content": error_text})
            await emit(AssistantMessage(content=error_text))
            break
        assert response is not None  # provider 合约：流尾必为 ProviderResponse

        total_prompt += response.usage.prompt_tokens
        total_completion += response.usage.completion_tokens
        token_budget.add(response.usage)

        if not response.tool_calls:
            if not response.content.strip() and state.empty_response_retries < _MAX_EMPTY_RESPONSE_RETRIES:
                # 空响应恢复（hermes）：注入引导后重试，不当作正常完成。
                # ephemeral 标记：不进 transcript（code-review #8——此前 nudge 被持久化
                # 成永久悬空指令，与"停止"类指令冲突）
                state.record_empty_response()
                history.append({"role": "user", "content": _EMPTY_RESPONSE_NUDGE, "ephemeral": True})
                continue
            history.append({"role": "assistant", "content": response.content})
            await emit(AssistantMessage(content=response.content))
            partial_response = response.content
            stop_reason = StopReason.COMPLETED
            break

        await emit(
            AssistantMessage(
                content=response.content,
                tool_call_names=[c.name for c in response.tool_calls],
            )
        )
        history.append(_tool_calls_to_message(response.content, response.tool_calls))
        if response.content:
            partial_response = response.content  # 优雅暂停时回传最后有内容的输出

        guard_tripped = False
        for tool_call in response.tool_calls:
            result = await _execute_one(
                tool_call, registry, tool_context, before_tool_call, emit,
                iteration_budget=iteration_budget, state=state,
            )
            history.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result.to_model_text(),
                }
            )
            if result.is_error:
                state.record_tool_error(tool_call.name, result.to_model_text())
            guards.record_tool_call(
                tool_call.name,
                tool_call.arguments or {},
                result.is_error,
                result.error_code,
                result.to_model_text(),
            )
            guard_result = guards.check(max_iterations=iteration_budget.max_iterations)
            if guard_result.tripped:
                await emit(
                    GuardTripped(
                        level=guard_result.level,
                        reason=guard_result.reason,
                        diagnosis=guard_result.diagnosis,
                    )
                )
                state.record_guard(guard_result.diagnosis)
                stop_reason = StopReason.GUARD_TRIPPED
                guard_tripped = True
                break
        if guard_tripped:
            # guard 触发必须结束整个回合（避免空转浪费调用）
            break

        if steering_source is not None:
            for steering_text in steering_source():
                history.append({"role": "user", "content": steering_text})

        if token_budget.exhausted:
            stop_reason = StopReason.TOKEN_BUDGET_EXHAUSTED
            break

    await emit(
        TurnEnded(
            stop_reason=stop_reason.value,
            iterations=iterations,
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            exit_detail=state.exit_detail(),
        )
    )
    return TurnResult(
        stop_reason=stop_reason,
        messages=history,
        iterations=iterations,
        total_usage=usage_total(),
        exit_detail=state.exit_detail(),
        partial_response=partial_response,
    )


async def _execute_one(
    tool_call: ToolCall,
    registry: ToolRegistry,
    ctx: ToolContext,
    before_tool_call: BeforeToolCall | None,
    emit: Callable[[Any], Awaitable[None]],
    iteration_budget: IterationBudget | None = None,
    state: TurnState | None = None,
) -> ToolResult:
    await emit(ToolStarted(call_id=tool_call.id, name=tool_call.name, arguments=tool_call.arguments))
    if before_tool_call is not None:
        if state is not None:
            state.pause()  # 钩子执行期间暂停墙钟（审批等人工交互不计入回合预算——R5）
        try:
            block_reason = await before_tool_call(tool_call.name, tool_call.arguments, ctx)
        except Exception as exc:  # noqa: BLE001 - 钩子异常不得击穿回合（fail-closed 拦截）
            result = ToolResult.fail(
                f"工具「{tool_call.name}」的前置检查异常，本次调用未执行。错误：{exc}。"
                "请重试或改用其他工具。",
                error_code="before_tool_call_error",
            )
            await emit(
                ToolFinished(
                    call_id=tool_call.id, name=tool_call.name,
                    is_error=True, result_text=result.to_model_text(),
                    error_code=result.error_code,
                )
            )
            if state is not None:
                state.resume()
            return result
        if state is not None:
            state.resume()
        if block_reason is not None:
            result = ToolResult.fail(block_reason, error_code="tool_blocked")
            await emit(
                ToolFinished(
                    call_id=tool_call.id, name=tool_call.name,
                    is_error=True, result_text=result.to_model_text(),
                    error_code=result.error_code,
                )
            )
            return result
    result = await registry.execute(tool_call.name, tool_call.arguments, ctx)
    await emit(
        ToolFinished(
            call_id=tool_call.id,
            name=tool_call.name,
            is_error=result.is_error,
            result_text=result.to_model_text(),
            error_code=result.error_code,
            next_action="retry_or_other_tool" if result.is_error else "",
        )
    )
    # 只读工具 refund：读取不消耗创作迭代额度
    if iteration_budget is not None:
        try:
            tool_def = registry.get(tool_call.name)
            if tool_def.permission == PermissionLevel.READ:
                iteration_budget.refund()
        except KeyError:
            pass
    return result

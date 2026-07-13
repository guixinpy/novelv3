"""无状态回合引擎（CADR-001 / openclaw loop 模式）。

一个回合 = 从一条用户消息开始，循环「LLM 调用 → 工具执行 → 观察回填」，
直到模型自然结束或预算耗尽。本模块不持有任何会话状态，事件经 sink 发出。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, Callable

from app.agent.budget import IterationBudget, TokenBudget
from app.agent.events import (
    AssistantDelta,
    AssistantMessage,
    GuardTripped,
    LoopEvent,
    ToolCallFinished,
    ToolCallStarted,
    TurnEnded,
)
from app.agent.guards import GuardSystem
from app.agent.providers.base import (
    Provider,
    ProviderResponse,
    TextDelta,
    ToolCall,
    Usage,
)
from app.agent.tooling import PermissionLevel, ToolContext, ToolRegistry, ToolResult

EventSink = Callable[[LoopEvent], "Awaitable[None] | None"]
# 返回 None 放行；返回字符串则拦截，字符串作为给模型的解释
BeforeToolCall = Callable[[str, dict | None, ToolContext], Awaitable[str | None]]
# 带事件发射能力的审批回调——ApprovalGate 用 emit 发 ApprovalPending 事件
BeforeToolCallWithEvent = Callable[
    [str, dict | None, ToolContext, "EventSink"], Awaitable[str | None]
]
# 工具批执行后排空 steering 消息（openclaw 模式），返回要注入的 user 消息文本列表
SteeringSource = Callable[[], list[str]]


class StopReason(str, Enum):
    COMPLETED = "completed"
    ITERATION_BUDGET_EXHAUSTED = "iteration_budget_exhausted"
    TOKEN_BUDGET_EXHAUSTED = "token_budget_exhausted"
    INTERRUPTED = "interrupted"
    GUARD_TRIPPED = "guard_tripped"


@dataclass
class TurnResult:
    stop_reason: StopReason
    messages: list[dict]
    iterations: int = 0
    total_usage: Usage = field(default_factory=Usage)


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
) -> TurnResult:
    history = list(messages)
    iterations = 0
    total_prompt = 0
    total_completion = 0
    stop_reason = StopReason.COMPLETED
    guards = GuardSystem()

    async def emit(event: LoopEvent) -> None:
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

        response: ProviderResponse | None = None
        async for event in provider.stream(
            history, tools=registry.to_specs(), **(extra_provider_kwargs or {})
        ):
            if isinstance(event, TextDelta):
                await emit(AssistantDelta(text=event.text))
            elif isinstance(event, ProviderResponse):
                response = event
        assert response is not None  # provider 合约：流尾必为 ProviderResponse

        total_prompt += response.usage.prompt_tokens
        total_completion += response.usage.completion_tokens
        token_budget.add(response.usage)

        if not response.tool_calls:
            history.append({"role": "assistant", "content": response.content})
            await emit(AssistantMessage(content=response.content))
            stop_reason = StopReason.COMPLETED
            break

        await emit(
            AssistantMessage(
                content=response.content,
                tool_call_names=[c.name for c in response.tool_calls],
            )
        )
        history.append(_tool_calls_to_message(response.content, response.tool_calls))

        for tool_call in response.tool_calls:
            result = await _execute_one(
                tool_call, registry, tool_context, before_tool_call, emit,
                iteration_budget=iteration_budget,
            )
            history.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result.to_model_text(),
                }
            )
            guards.record_tool_call(tool_call.name, tool_call.arguments or {}, result.is_error, result.to_model_text())
            guard_result = guards.check(max_iterations=iteration_budget.max_iterations)
            if guard_result.tripped:
                await emit(GuardTripped(level=guard_result.level, reason=guard_result.reason, diagnosis=guard_result.diagnosis))
                stop_reason = StopReason.GUARD_TRIPPED
                break

        if steering_source is not None:
            for steering_text in steering_source():
                history.append({"role": "user", "content": steering_text})

        if token_budget.exhausted:
            stop_reason = StopReason.TOKEN_BUDGET_EXHAUSTED
            break

    await emit(TurnEnded(stop_reason=stop_reason.value, iterations=iterations, usage=usage_total()))
    return TurnResult(
        stop_reason=stop_reason,
        messages=history,
        iterations=iterations,
        total_usage=usage_total(),
    )


async def _execute_one(
    tool_call: ToolCall,
    registry: ToolRegistry,
    ctx: ToolContext,
    before_tool_call: BeforeToolCall | None,
    emit: Callable[[LoopEvent], Awaitable[None]],
    iteration_budget: IterationBudget | None = None,
) -> ToolResult:
    await emit(ToolCallStarted(id=tool_call.id, name=tool_call.name, arguments=tool_call.arguments))
    if before_tool_call is not None:
        block_reason = await before_tool_call(tool_call.name, tool_call.arguments, ctx)
        if block_reason is not None:
            result = ToolResult.fail(block_reason)
            await emit(
                ToolCallFinished(
                    id=tool_call.id, name=tool_call.name,
                    is_error=True, result_text=result.to_model_text(),
                )
            )
            return result
    result = await registry.execute(tool_call.name, tool_call.arguments, ctx)
    await emit(
        ToolCallFinished(
            id=tool_call.id, name=tool_call.name,
            is_error=result.is_error, result_text=result.to_model_text(),
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

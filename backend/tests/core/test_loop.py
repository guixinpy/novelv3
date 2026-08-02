"""循环引擎测试：scripted mock provider 驱动，断言事件序列与停止原因。

覆盖失败路径（护栏/预算/错误/优雅暂停）+ steering 注入顺序 + 工具序列回填。
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from core.events import AssistantDelta, AssistantMessage, GuardTripped, ToolFinished, TurnEnded
from core.guards.budget import IterationBudget, TokenBudget
from core.loop import StopReason, run_turn
from core.tools.base import ToolContext, ToolRegistry, ToolResult, tool

from tests.core.conftest import ScriptedProvider


class EchoArgs(BaseModel):
    text: str = Field(..., min_length=1)


def make_registry() -> ToolRegistry:
    registry = ToolRegistry()

    @tool(registry=registry, name="echo", description="回声", args_model=EchoArgs)
    def echo(ctx: ToolContext, text: str) -> ToolResult:
        return ToolResult.ok({"echo": text})

    @tool(registry=registry, name="always_fail", description="总是失败", args_model=None)
    def always_fail(ctx: ToolContext) -> ToolResult:
        return ToolResult.fail("内部错误", error_code="boom")

    @tool(registry=registry, name="write", description="写入", args_model=None, permission="write")
    def write(ctx: ToolContext) -> ToolResult:
        return ToolResult.ok({"status": "written"})

    return registry


def collect(events) -> tuple[list, dict]:
    collected = []
    turn_ended = None
    for event in events:
        collected.append(event)
        if isinstance(event, TurnEnded):
            turn_ended = event
    return collected, turn_ended


async def run(provider: ScriptedProvider, registry: ToolRegistry, **kwargs):
    events = []
    turn_ended = None

    async def sink(event):
        nonlocal turn_ended
        events.append(event)
        if isinstance(event, TurnEnded):
            turn_ended = event

    result = await run_turn(
        provider=provider,
        messages=[{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
        registry=registry,
        tool_context=ToolContext(),
        iteration_budget=IterationBudget(kwargs.pop("max_iterations", 30)),
        token_budget=TokenBudget(kwargs.pop("max_tokens", None)),
        event_sink=sink,
        **kwargs,
    )
    return result, events, turn_ended


async def test_normal_completion(scripted_provider_factory):
    provider = scripted_provider_factory([{"content": "完成"}])
    result, events, turn_ended = await run(provider, make_registry())
    assert result.stop_reason == StopReason.COMPLETED
    assert result.iterations == 1
    assert result.partial_response == "完成"
    assert turn_ended.stop_reason == StopReason.COMPLETED.value
    # 事件流：delta 先行，message 收尾
    assert any(isinstance(e, AssistantDelta) for e in events)
    assert isinstance(events[-2], AssistantMessage)


async def test_tool_sequence_and_result_feed_back(scripted_provider_factory):
    provider = scripted_provider_factory(
        [
            {"content": "", "tool_calls": [{"name": "echo", "arguments": {"text": "hi"}}]},
            {"content": "最终回答"},
        ]
    )
    result, events, turn_ended = await run(provider, make_registry())
    assert result.stop_reason == StopReason.COMPLETED
    # 工具结果回填进 history（tool 消息在 assistant(tool_calls) 之后）
    tool_messages = [m for m in result.messages if m.get("role") == "tool"]
    assert len(tool_messages) == 1
    assert "hi" in tool_messages[0]["content"]
    # 第二次请求携带工具结果
    assert len(provider.requests) == 2
    assert provider.requests[1][-1]["role"] == "tool"
    # 事件顺序：tool_finished 出现在第一个带 tool_calls 的 assistant_message 之后
    kinds = [e.kind.value for e in events]
    first_tool_msg = next(i for i, e in enumerate(events) if isinstance(e, AssistantMessage) and e.tool_call_names)
    assert "tool_finished" in kinds[first_tool_msg:]


async def test_guard_l1_tripped_on_repeat(scripted_provider_factory):
    provider = scripted_provider_factory(
        [
            {"content": "", "tool_calls": [{"name": "echo", "arguments": {"text": "x"}}]},
            {"content": "", "tool_calls": [{"name": "echo", "arguments": {"text": "x"}}]},
            {"content": "", "tool_calls": [{"name": "echo", "arguments": {"text": "x"}}]},
        ]
    )
    result, events, turn_ended = await run(provider, make_registry())
    assert result.stop_reason == StopReason.GUARD_TRIPPED
    assert any(isinstance(e, GuardTripped) and e.level == "L1" for e in events)
    # guard 触发后不再继续调用 provider
    assert len(provider.requests) == 3


async def test_l4_unknown_tool_by_error_code(scripted_provider_factory):
    """L4 幻觉工具：按 error_code 判断（修旧版字符串耦合）。"""
    provider = scripted_provider_factory(
        [
            {"content": "", "tool_calls": [{"name": "no_such_tool", "arguments": {}}]},
            {"content": "", "tool_calls": [{"name": "no_such_tool", "arguments": {}}]},
        ]
    )
    result, events, turn_ended = await run(provider, make_registry())
    assert result.stop_reason == StopReason.GUARD_TRIPPED
    guard = next(e for e in events if isinstance(e, GuardTripped))
    assert guard.level == "L4"
    finished = [e for e in events if isinstance(e, ToolFinished) and e.is_error]
    assert finished and finished[0].error_code == "unknown_tool"


async def test_iteration_budget_graceful_pause(scripted_provider_factory):
    """优雅暂停（openhuman）：预算耗尽返回部分结果而非硬失败。

    用 write 工具（read 工具会 refund 预算，无法触发预算耗尽）。
    """
    provider = scripted_provider_factory(
        [
            {"content": "已写入", "tool_calls": [{"name": "write", "arguments": {}}]},
            {"content": "继续写入", "tool_calls": [{"name": "write", "arguments": {}}]},
        ]
    )
    result, events, turn_ended = await run(provider, make_registry(), max_iterations=2)
    assert result.stop_reason == StopReason.ITERATION_BUDGET_EXHAUSTED
    assert result.partial_response != ""  # 可续写的部分结果
    assert turn_ended.exit_detail.get("elapsed_ms") is not None


async def test_steering_injected_before_next_llm_call(scripted_provider_factory):
    """steering 在工具批完成后、下次 LLM 调用前注入（one-at-a-time）。"""
    provider = scripted_provider_factory(
        [
            {"content": "", "tool_calls": [{"name": "echo", "arguments": {"text": "a"}}]},
            {"content": "回应 steering", "tool_calls": []},
        ]
    )
    steering_calls = {"n": 0}

    def steering_source():
        steering_calls["n"] += 1
        if steering_calls["n"] == 1:
            return ["改方向"]
        return []

    result, _, _ = await run(provider, make_registry(), steering_source=steering_source)
    assert result.stop_reason == StopReason.COMPLETED
    # 第二次请求包含 steering 消息
    assert len(provider.requests) == 2
    second = provider.requests[1]
    assert any(m.get("role") == "user" and m.get("content") == "改方向" for m in second)


async def test_provider_error_becomes_message(scripted_provider_factory):
    """provider 异常编码为消息（INTERRUPTED），不静默不炸。"""
    provider = scripted_provider_factory([{"content": "", "error": "network down", "retryable": True}])
    result, events, turn_ended = await run(provider, make_registry())
    assert result.stop_reason == StopReason.INTERRUPTED
    assert turn_ended.stop_reason == StopReason.INTERRUPTED.value
    assert any(isinstance(e, AssistantMessage) and "网络" not in e.content for e in events)


async def test_tool_error_visible_to_model(scripted_provider_factory):
    """工具错误回填为 tool 消息，模型可见可调整。"""
    provider = scripted_provider_factory(
        [
            {"content": "", "tool_calls": [{"name": "always_fail", "arguments": {}}]},
            {"content": "重试方案", "tool_calls": []},
        ]
    )
    result, events, turn_ended = await run(provider, make_registry())
    assert result.stop_reason == StopReason.COMPLETED
    tool_msgs = [m for m in result.messages if m.get("role") == "tool"]
    assert len(tool_msgs) == 1
    assert "error" in tool_msgs[0]["content"]
    finished = [e for e in events if isinstance(e, ToolFinished)]
    assert finished[0].error_code == "boom"
    assert finished[0].next_action == "retry_or_other_tool"

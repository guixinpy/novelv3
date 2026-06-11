import pytest

from app.agent.budget import IterationBudget, TokenBudget
from app.agent.events import (
    AssistantDelta,
    AssistantMessage,
    ToolCallFinished,
    ToolCallStarted,
    TurnEnded,
)
from app.agent.loop import StopReason, run_turn
from app.agent.tooling import ToolContext, ToolRegistry, ToolResult, tool
from test_support.agent_fakes import FakeProvider, call, text_response, tool_response


def make_registry() -> ToolRegistry:
    registry = ToolRegistry()

    @tool(registry=registry, name="read_chapter", description="读取章节", permission="read",
          parameters={"type": "object", "properties": {"chapter_index": {"type": "integer"}},
                      "required": ["chapter_index"]})
    async def read_chapter(ctx: ToolContext, chapter_index: int) -> ToolResult:
        return ToolResult.ok({"index": chapter_index, "content": f"第{chapter_index}章正文"})

    return registry


def collect_events():
    events = []
    return events, events.append


@pytest.mark.asyncio
async def test_plain_text_turn_ends_immediately():
    provider = FakeProvider([text_response("你好|，作者")])
    events, sink = collect_events()
    result = await run_turn(
        provider=provider,
        messages=[{"role": "user", "content": "hi"}],
        registry=make_registry(),
        tool_context=ToolContext(project_id=1),
        iteration_budget=IterationBudget(10),
        token_budget=TokenBudget(None),
        event_sink=sink,
    )
    assert result.stop_reason == StopReason.COMPLETED
    assert result.messages[-1]["role"] == "assistant"
    assert result.messages[-1]["content"] == "你好，作者"

    deltas = [e.text for e in events if isinstance(e, AssistantDelta)]
    assert deltas == ["你好", "，作者"]
    assert isinstance(events[-1], TurnEnded)


@pytest.mark.asyncio
async def test_tool_call_executed_and_fed_back():
    provider = FakeProvider([
        tool_response(call("read_chapter", '{"chapter_index": 3}')),
        text_response("第3章讲了灯塔。"),
    ])
    events, sink = collect_events()
    result = await run_turn(
        provider=provider,
        messages=[{"role": "user", "content": "第三章讲了什么"}],
        registry=make_registry(),
        tool_context=ToolContext(project_id=1),
        iteration_budget=IterationBudget(10),
        token_budget=TokenBudget(None),
        event_sink=sink,
    )
    assert result.stop_reason == StopReason.COMPLETED

    # 第二次 LLM 调用收到了 assistant tool_calls 消息和 tool 结果消息
    second_call = provider.calls[1]
    assert second_call[-2]["role"] == "assistant"
    assert second_call[-2]["tool_calls"][0]["function"]["name"] == "read_chapter"
    assert second_call[-1]["role"] == "tool"
    assert second_call[-1]["tool_call_id"] == "call_1"
    assert "第3章正文" in second_call[-1]["content"]

    starts = [e for e in events if isinstance(e, ToolCallStarted)]
    finishes = [e for e in events if isinstance(e, ToolCallFinished)]
    assert len(starts) == len(finishes) == 1
    assert starts[0].name == "read_chapter"
    assert finishes[0].is_error is False


@pytest.mark.asyncio
async def test_tool_error_fed_back_to_model_not_raised():
    provider = FakeProvider([
        tool_response(call("read_chapter", '{"wrong": 1}')),
        text_response("我重新试试。"),
    ])
    events, sink = collect_events()
    result = await run_turn(
        provider=provider,
        messages=[{"role": "user", "content": "hi"}],
        registry=make_registry(),
        tool_context=ToolContext(project_id=1),
        iteration_budget=IterationBudget(10),
        token_budget=TokenBudget(None),
        event_sink=sink,
    )
    assert result.stop_reason == StopReason.COMPLETED
    tool_msg = provider.calls[1][-1]
    assert tool_msg["role"] == "tool"
    assert "chapter_index" in tool_msg["content"]
    finishes = [e for e in events if isinstance(e, ToolCallFinished)]
    assert finishes[0].is_error is True


@pytest.mark.asyncio
async def test_iteration_budget_stops_loop():
    # 模型每次都要求调用工具，预算 2 次迭代后停止
    responses = [tool_response(call("read_chapter", '{"chapter_index": 1}', id=f"c{i}"))
                 for i in range(5)]
    provider = FakeProvider(responses)
    events, sink = collect_events()
    result = await run_turn(
        provider=provider,
        messages=[{"role": "user", "content": "hi"}],
        registry=make_registry(),
        tool_context=ToolContext(project_id=1),
        iteration_budget=IterationBudget(2),
        token_budget=TokenBudget(None),
        event_sink=sink,
    )
    assert result.stop_reason == StopReason.ITERATION_BUDGET_EXHAUSTED
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_token_budget_stops_loop():
    provider = FakeProvider([
        tool_response(call("read_chapter", '{"chapter_index": 1}'), prompt=600, completion=500),
        text_response("继续"),
    ])
    events, sink = collect_events()
    result = await run_turn(
        provider=provider,
        messages=[{"role": "user", "content": "hi"}],
        registry=make_registry(),
        tool_context=ToolContext(project_id=1),
        iteration_budget=IterationBudget(10),
        token_budget=TokenBudget(max_tokens=1000),
        event_sink=sink,
    )
    assert result.stop_reason == StopReason.TOKEN_BUDGET_EXHAUSTED
    # 工具结果已回填进消息（恢复时模型能看到），但不再发起新调用
    assert result.messages[-1]["role"] == "tool"
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_before_tool_call_hook_can_block():
    provider = FakeProvider([
        tool_response(call("read_chapter", '{"chapter_index": 1}')),
        text_response("好的，不读了。"),
    ])
    events, sink = collect_events()

    async def deny_all(name: str, arguments: dict | None, ctx: ToolContext):
        return "该工具当前被审批策略禁止"

    result = await run_turn(
        provider=provider,
        messages=[{"role": "user", "content": "hi"}],
        registry=make_registry(),
        tool_context=ToolContext(project_id=1),
        iteration_budget=IterationBudget(10),
        token_budget=TokenBudget(None),
        event_sink=sink,
        before_tool_call=deny_all,
    )
    assert result.stop_reason == StopReason.COMPLETED
    tool_msg = provider.calls[1][-1]
    assert "审批策略禁止" in tool_msg["content"]
    finishes = [e for e in events if isinstance(e, ToolCallFinished)]
    assert finishes[0].is_error is True


@pytest.mark.asyncio
async def test_parallel_tool_calls_all_executed_in_order():
    provider = FakeProvider([
        tool_response(
            call("read_chapter", '{"chapter_index": 1}', id="a"),
            call("read_chapter", '{"chapter_index": 2}', id="b"),
        ),
        text_response("两章都读完了"),
    ])
    events, sink = collect_events()
    result = await run_turn(
        provider=provider,
        messages=[{"role": "user", "content": "hi"}],
        registry=make_registry(),
        tool_context=ToolContext(project_id=1),
        iteration_budget=IterationBudget(10),
        token_budget=TokenBudget(None),
        event_sink=sink,
    )
    assert result.stop_reason == StopReason.COMPLETED
    second_call = provider.calls[1]
    tool_msgs = [m for m in second_call if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == ["a", "b"]


@pytest.mark.asyncio
async def test_usage_accumulated_in_result():
    provider = FakeProvider([
        tool_response(call("read_chapter", '{"chapter_index": 1}'), prompt=10, completion=5),
        text_response("done", prompt=20, completion=8),
    ])
    events, sink = collect_events()
    result = await run_turn(
        provider=provider,
        messages=[{"role": "user", "content": "hi"}],
        registry=make_registry(),
        tool_context=ToolContext(project_id=1),
        iteration_budget=IterationBudget(10),
        token_budget=TokenBudget(None),
        event_sink=sink,
    )
    assert result.total_usage.prompt_tokens == 30
    assert result.total_usage.completion_tokens == 13


@pytest.mark.asyncio
async def test_assistant_message_event_carries_final_content():
    provider = FakeProvider([text_response("最终回答")])
    events, sink = collect_events()
    await run_turn(
        provider=provider,
        messages=[{"role": "user", "content": "hi"}],
        registry=make_registry(),
        tool_context=ToolContext(project_id=1),
        iteration_budget=IterationBudget(10),
        token_budget=TokenBudget(None),
        event_sink=sink,
    )
    finals = [e for e in events if isinstance(e, AssistantMessage)]
    assert len(finals) == 1
    assert finals[0].content == "最终回答"

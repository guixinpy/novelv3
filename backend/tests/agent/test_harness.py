import json

import pytest

from app.agent.events import AssistantMessage, TurnEnded
from app.agent.harness import AgentHarness, HarnessConfig
from app.agent.loop import StopReason
from app.agent.tooling import ToolContext, ToolRegistry, ToolResult, tool
from test_support.agent_fakes import FakeProvider, call, text_response, tool_response


def make_registry() -> ToolRegistry:
    registry = ToolRegistry()

    @tool(registry=registry, name="read_chapter", description="读取章节", permission="read",
          parameters={"type": "object", "properties": {"chapter_index": {"type": "integer"}},
                      "required": ["chapter_index"]})
    async def read_chapter(ctx: ToolContext, chapter_index: int) -> ToolResult:
        return ToolResult.ok({"index": chapter_index})

    return registry


def make_harness(tmp_path, provider, registry=None, **config_kwargs) -> AgentHarness:
    return AgentHarness(
        session_id="s1",
        session_dir=tmp_path,
        provider=provider,
        registry=registry or make_registry(),
        tool_context=ToolContext(project_id=1, session_id="s1"),
        config=HarnessConfig(system_prompt="你是写作助手。", **config_kwargs),
    )


async def drain(harness, text):
    events = []
    async for event in harness.send(text):
        events.append(event)
    return events


@pytest.mark.asyncio
async def test_send_appends_system_and_user_then_persists(tmp_path):
    provider = FakeProvider([text_response("回答")])
    harness = make_harness(tmp_path, provider)
    events = await drain(harness, "你好")

    assert isinstance(events[-1], TurnEnded)
    sent = provider.calls[0]
    assert sent[0]["role"] == "system"
    assert sent[0]["content"] == "你是写作助手。"
    assert sent[1] == {"role": "user", "content": "你好"}

    log_path = tmp_path / "s1.jsonl"
    lines = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    roles = [l["data"]["role"] for l in lines if l["type"] == "message"]
    assert roles == ["user", "assistant"]
    assert any(l["type"] == "turn_ended" for l in lines)


@pytest.mark.asyncio
async def test_multi_turn_history_accumulates(tmp_path):
    provider = FakeProvider([text_response("第一答"), text_response("第二答")])
    harness = make_harness(tmp_path, provider)
    await drain(harness, "第一问")
    await drain(harness, "第二问")

    second_call = provider.calls[1]
    contents = [(m["role"], m.get("content")) for m in second_call]
    assert contents == [
        ("system", "你是写作助手。"),
        ("user", "第一问"),
        ("assistant", "第一答"),
        ("user", "第二问"),
    ]


@pytest.mark.asyncio
async def test_resume_from_jsonl(tmp_path):
    provider = FakeProvider([text_response("第一答")])
    harness = make_harness(tmp_path, provider)
    await drain(harness, "第一问")

    # 模拟进程重启：新 harness 同一 session_id
    provider2 = FakeProvider([text_response("第二答")])
    harness2 = make_harness(tmp_path, provider2)
    await drain(harness2, "第二问")

    sent = provider2.calls[0]
    assert [m["role"] for m in sent] == ["system", "user", "assistant", "user"]
    assert sent[1]["content"] == "第一问"
    assert sent[2]["content"] == "第一答"


@pytest.mark.asyncio
async def test_tool_messages_persisted_and_resumed(tmp_path):
    provider = FakeProvider([
        tool_response(call("read_chapter", '{"chapter_index": 1}')),
        text_response("读完了"),
    ])
    harness = make_harness(tmp_path, provider)
    await drain(harness, "读第一章")

    provider2 = FakeProvider([text_response("继续")])
    harness2 = make_harness(tmp_path, provider2)
    await drain(harness2, "继续")
    roles = [m["role"] for m in provider2.calls[0]]
    assert roles == ["system", "user", "assistant", "tool", "assistant", "user"]


@pytest.mark.asyncio
async def test_follow_up_queue_runs_after_turn(tmp_path):
    provider = FakeProvider([text_response("先回答"), text_response("跟进回答")])
    harness = make_harness(tmp_path, provider)
    harness.queue_follow_up("接着写下一章")
    events = await drain(harness, "写一章")

    assert len(provider.calls) == 2
    assert provider.calls[1][-1] == {"role": "user", "content": "接着写下一章"}
    finals = [e for e in events if isinstance(e, AssistantMessage)]
    assert [f.content for f in finals] == ["先回答", "跟进回答"]


@pytest.mark.asyncio
async def test_steering_injected_mid_turn(tmp_path):
    provider = FakeProvider([
        tool_response(call("read_chapter", '{"chapter_index": 1}')),
        text_response("已按新要求处理"),
    ])
    harness = make_harness(tmp_path, provider)

    first_events = []
    async for event in harness.send("读第一章"):
        first_events.append(event)
        if len(first_events) == 1:
            harness.queue_steering("改成读第二章")

    second_call = provider.calls[1]
    steering = [m for m in second_call if m["role"] == "user" and m["content"] == "改成读第二章"]
    assert steering, f"steering message not injected: {second_call}"
    # steering 出现在 tool 结果之后
    assert second_call[-1]["content"] == "改成读第二章"


@pytest.mark.asyncio
async def test_budget_config_respected(tmp_path):
    responses = [tool_response(call("read_chapter", '{"chapter_index": 1}', id=f"c{i}"))
                 for i in range(5)]
    provider = FakeProvider(responses)
    harness = make_harness(tmp_path, provider, max_iterations_per_turn=2)
    events = await drain(harness, "hi")
    ended = [e for e in events if isinstance(e, TurnEnded)]
    assert ended[-1].stop_reason == StopReason.ITERATION_BUDGET_EXHAUSTED.value

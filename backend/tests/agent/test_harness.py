import json

import pytest

from app.agent.events import AssistantMessage, TurnEnded
from app.agent.harness import AgentHarness, HarnessConfig, _sanitize_tool_message_order
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

    @tool(registry=registry, name="write_chapter", description="写入章节", permission="write",
          parameters={"type": "object", "properties": {"content": {"type": "string"}},
                      "required": ["content"]})
    async def write_chapter(ctx: ToolContext, content: str) -> ToolResult:
        return ToolResult.ok({"written": True})

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


def test_sanitize_tool_message_order_removes_orphans():
    history = [
        {"role": "user", "content": "写吧"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "write_chapter", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "{\"ok\": true}"},
        {"role": "user", "content": "压缩摘要占位"},
        {"role": "tool", "tool_call_id": "c2", "content": "{\"ok\": true}"},  # 孤儿：前一条非 tool 是 user
        {"role": "assistant", "content": "继续", "tool_calls": [{"id": "c3", "type": "function", "function": {"name": "read_chapter", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "c3", "content": "{\"ok\": true}"},
        {"role": "tool", "tool_call_id": "c4", "content": "{\"ok\": true}"},  # 多条 tool 跟同一 assistant：保留
    ]
    cleaned = _sanitize_tool_message_order(history)
    tool_ids = [m.get("tool_call_id") for m in cleaned if m.get("role") == "tool"]
    assert tool_ids == ["c1", "c3", "c4"]


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
async def test_context_compaction_triggers_and_persists(tmp_path):
    """历史超过 75% 阈值时自动压缩，并写入可重放的日志检查点。"""
    provider = FakeProvider([text_response("回答")] * 6)
    harness = make_harness(tmp_path, provider)
    big = "x" * 60_000  # 约 30K tokens/条
    for _ in range(4):
        await drain(harness, big)

    # 第 4 次请求前历史约 120K tokens，应已触发压缩（< 未压缩的 8 条）
    assert len(provider.calls[3]) < 8

    lines = [
        json.loads(line)
        for line in (tmp_path / "s1.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    compaction_entries = [l for l in lines if l["type"] == "compaction"]
    assert len(compaction_entries) == 1
    data = compaction_entries[0]["data"]
    assert data["after_count"] < data["before_count"]

    # 重新加载后状态与压缩后一致（无旧消息重复回放，summary 在场）
    reloaded = AgentHarness(
        session_id="s1",
        session_dir=tmp_path,
        provider=FakeProvider([]),
        registry=make_registry(),
        tool_context=ToolContext(project_id=1, session_id="s1"),
        config=HarnessConfig(system_prompt="你是写作助手。"),
    )
    assert len(reloaded.messages) == data["after_count"]
    assert any(
        isinstance(m.get("content"), str) and m["content"].startswith("[上下文压缩]")
        for m in reloaded.messages
    )


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


# ── T6 R1: 回合级项目状态快照注入（不持久化） ──


@pytest.mark.asyncio
async def test_snapshot_injected_into_system_not_persisted(tmp_path, db_session):
    from domain.memory.project_snapshot import build_project_snapshot
    from app.models import ChapterContent, Project, Setup

    p = Project(name="测试", genre="悬疑")
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    db_session.add(Setup(
        project_id=p.id,
        characters=[{"name": "程砚秋"}],
        status="active",
    ))
    for i in range(1, 3):
        db_session.add(ChapterContent(
            project_id=p.id, chapter_index=i,
            title=f"第{i}章", content="正文。" * 100,
            word_count=200, status="generated",
        ))
    db_session.commit()

    provider = FakeProvider([text_response("回答")])
    harness = AgentHarness(
        session_id="s1",
        session_dir=tmp_path,
        provider=provider,
        registry=make_registry(),
        tool_context=ToolContext(project_id=p.id, session_id="s1", db=db_session),
        config=HarnessConfig(system_prompt="你是写作助手。"),
        snapshot_provider=lambda: build_project_snapshot(db_session, p.id),
    )
    await drain(harness, "你好")

    system_msg = provider.calls[0][0]
    assert system_msg["role"] == "system"
    assert "项目状态快照" in system_msg["content"]
    assert "程砚秋" in system_msg["content"]

    # 快照不持久化：jsonl 不含快照标记与角色名
    log_text = (tmp_path / "s1.jsonl").read_text(encoding="utf-8")
    assert "项目状态快照" not in log_text


@pytest.mark.asyncio
async def test_snapshot_injection_skipped_without_db(tmp_path):
    """无 db（纯内核场景）→ 快照跳过，行为不变。"""
    provider = FakeProvider([text_response("回答")])
    harness = make_harness(tmp_path, provider)
    await drain(harness, "你好")

    sent = provider.calls[0]
    assert sent[0]["content"] == "你是写作助手。"  # 无快照追加
    assert "项目状态快照" not in sent[0]["content"]


@pytest.mark.asyncio
async def test_budget_config_respected(tmp_path):
    # 写入工具消耗预算，只读工具不消耗
    responses = [
        tool_response(call("write_chapter", '{"content": "1"}', id="c0")),
        tool_response(call("write_chapter", '{"content": "2"}', id="c1")),
    ]
    provider = FakeProvider(responses)
    harness = make_harness(tmp_path, provider, max_iterations_per_turn=1)
    events = await drain(harness, "hi")
    ended = [e for e in events if isinstance(e, TurnEnded)]
    assert ended[-1].stop_reason == StopReason.ITERATION_BUDGET_EXHAUSTED.value


# ── T1 R2: 回合内工具错误 → 通用「错误诊断 + 下一步建议」注入 ──


@pytest.mark.asyncio
async def test_tool_error_injects_recovery_message(tmp_path):
    """工具错误后，同一 send 内自动注入错误诊断 + 下一步建议。"""
    provider = FakeProvider([
        tool_response(call("read_chapter", '{"missing_param": 1}')),
        text_response("我改用正确参数。"),
        text_response("修复完成"),
    ])
    harness = make_harness(tmp_path, provider)
    events = await drain(harness, "读第一章")

    # follow-up 回合（第 3 次调用）携带了注入的错误诊断 user 消息
    assert len(provider.calls) == 3
    recovery_user = provider.calls[2][-1]
    assert recovery_user["role"] == "user"
    assert "工具调用失败" in recovery_user["content"]
    assert "read_chapter" in recovery_user["content"]
    assert "建议" in recovery_user["content"]
    # 注入消息本身不再触发新的错误（回合粒度防抖）
    finals = [e for e in events if isinstance(e, AssistantMessage)]
    assert finals[-1].content == "修复完成"


@pytest.mark.asyncio
async def test_error_recovery_injected_at_most_once_per_turn(tmp_path):
    """一个回合内多次工具错误 → 只注入一条汇总消息。"""
    provider = FakeProvider([
        tool_response(call("read_chapter", '{"bad": 1}', id="a"), call("read_chapter", '{"bad": 2}', id="b")),
        text_response("两条都错了，我换工具。"),
        text_response("完成"),
    ])
    harness = make_harness(tmp_path, provider)
    await drain(harness, "hi")

    user_msgs = [
        m for call in provider.calls
        for m in call if m["role"] == "user" and "工具调用失败" in str(m.get("content", ""))
    ]
    assert len(user_msgs) == 1
    assert "2 次" in user_msgs[0]["content"]


@pytest.mark.asyncio
async def test_guard_trip_skips_generic_error_recovery(tmp_path):
    """GuardTripped 已注入恢复建议时，不再注入通用错误恢复（guard 版优先级更高）。"""
    provider = FakeProvider([
        tool_response(call("write_chapter", '{"content": "1"}', id="c0")),
        tool_response(call("write_chapter", '{"content": "1"}', id="c1")),
        tool_response(call("write_chapter", '{"content": "1"}', id="c2")),
        text_response("好的"),
    ])
    harness = make_harness(tmp_path, provider)
    await drain(harness, "hi")

    recovery_texts = [
        m.get("content", "") for call in provider.calls
        for m in call if m["role"] == "user"
    ]
    # L1 guard（连续 3 次相同调用）触发恢复建议，但不应出现通用工具错误诊断
    assert any("护栏触发" in t for t in recovery_texts)
    assert not any("工具调用失败" in t for t in recovery_texts)


# ── T1 R3: 压缩后重放一致性（sanitize 边界矩阵） ──


def test_sanitize_removes_tool_first_message():
    """tool 消息打头（前无 assistant tool_calls）→ 孤立删除。"""
    history = [
        {"role": "tool", "tool_call_id": "c0", "content": "{}"},
        {"role": "user", "content": "开始"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "read_chapter", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "{}"},
    ]
    cleaned = _sanitize_tool_message_order(history)
    tool_ids = [m.get("tool_call_id") for m in cleaned if m.get("role") == "tool"]
    assert tool_ids == ["c1"]


def test_sanitize_removes_orphan_at_end():
    """末尾孤立 tool（前一条是 assistant 但无 tool_calls）→ 删除。"""
    history = [
        {"role": "user", "content": "写吧"},
        {"role": "assistant", "content": "好的"},
        {"role": "tool", "tool_call_id": "c9", "content": "{}"},
    ]
    cleaned = _sanitize_tool_message_order(history)
    assert not any(m.get("role") == "tool" for m in cleaned)


def test_sanitize_keeps_tools_after_each_assistant_tool_call():
    """多条 assistant(tool_calls) 各自跟 tool 消息 → 全部保留。"""
    history = [
        {"role": "user", "content": "读"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "a", "type": "function", "function": {"name": "read_chapter", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "a", "content": "{}"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "b", "type": "function", "function": {"name": "read_chapter", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "b", "content": "{}"},
    ]
    cleaned = _sanitize_tool_message_order(history)
    tool_ids = [m.get("tool_call_id") for m in cleaned if m.get("role") == "tool"]
    assert tool_ids == ["a", "b"]


def test_sanitize_then_compact_then_sanitize_is_stable():
    """压缩后的历史再次 sanitize → 幂等（压缩摘要不产生新的孤立 tool 消息）。"""
    history = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "[上下文压缩] 中间消息被压缩。"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "read_chapter", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "{}"},
        {"role": "assistant", "content": "继续"},
    ]
    cleaned_once = _sanitize_tool_message_order(history)
    cleaned_twice = _sanitize_tool_message_order(cleaned_once)
    assert [m for m in cleaned_twice] == [m for m in cleaned_once]

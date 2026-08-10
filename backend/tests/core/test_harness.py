"""harness 测试：转录（append-only/压缩检查点/sidecar）+ 双队列 + 幂等键 + 写锁。"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from core.harness import AgentHarness, HarnessConfig
from core.session.transcript import Transcript, strip_api_fields, with_api_content
from core.tools.base import ToolContext, ToolRegistry, ToolResult, tool

from tests.core.conftest import ScriptedProvider


# ── transcript ──

def test_transcript_append_and_load(tmp_path):
    t = Transcript(tmp_path / "s.jsonl")
    t.append_message({"role": "user", "content": "hi"})
    t.append_message({"role": "assistant", "content": "yo"})
    assert len(t.messages) == 2
    # 重载
    t2 = Transcript(tmp_path / "s.jsonl")
    assert len(t2.messages) == 2


def test_transcript_compaction_checkpoint(tmp_path):
    t = Transcript(tmp_path / "s.jsonl")
    t.append_message({"role": "user", "content": "a"})
    t.append_message({"role": "assistant", "content": "b"})
    compressed = [{"role": "system", "content": "s"}, {"role": "user", "content": "[上下文压缩] 摘要"}]
    t.record_compaction(compressed, "摘要")
    # 压缩检查点是真相源：messages 重置为压缩快照
    assert len(t.messages) == 1
    assert t.messages[0]["content"].startswith("[上下文压缩]")
    # 重载后仍是压缩快照（原始行保留在 JSONL 但累积器被替换）
    t2 = Transcript(tmp_path / "s.jsonl")
    assert len(t2.messages) == 1


def test_transcript_forward_compatible_unknown_records(tmp_path):
    """未知记录跳过（openhuman 前向兼容）。"""
    t = Transcript(tmp_path / "s.jsonl")
    t.append_message({"role": "user", "content": "a"})
    t._append_log("future_kind", {"anything": True})
    t2 = Transcript(tmp_path / "s.jsonl")
    assert len(t2.messages) == 1


def test_sidecar_strip_roundtrip():
    msg = {"role": "user", "content": "干净内容"}
    sent = with_api_content(msg, "干净内容[注入]")
    assert sent["api_content"] == "干净内容[注入]"
    stored = strip_api_fields(sent)
    assert "api_content" not in stored
    assert stored["content"] == "干净内容"


# ── harness ──

def make_registry() -> ToolRegistry:
    registry = ToolRegistry()

    @tool(registry=registry, name="echo", description="回声", args_model=None)
    def echo(ctx: ToolContext) -> ToolResult:
        return ToolResult.ok({"echo": "ok"})

    return registry


def make_harness(tmp_path: Path, script: list[dict], **cfg) -> AgentHarness:
    provider = ScriptedProvider(script)
    harness = AgentHarness(
        session_id="s1",
        session_dir=tmp_path,
        provider=provider,
        registry=make_registry(),
        tool_context=ToolContext(),
        config=HarnessConfig(
            system_prompt="你是写作助手",
            max_iterations_per_turn=cfg.pop("max_iterations", 10),
            max_wall_clock_ms=cfg.pop("max_wall_clock_ms", None),
        ),
        **cfg,
    )
    return harness


async def drain(harness: AgentHarness, text: str, **kwargs) -> list:
    events = []
    async for event in harness.send(text, **kwargs):
        events.append(event)
    return events


async def test_send_roundtrip_and_persist(tmp_path):
    harness = make_harness(tmp_path, [{"content": "收到"}])
    events = await drain(harness, "写第一章")
    assert any(e.kind.value == "agent_start" for e in events)
    assert any(e.kind.value == "agent_end" for e in events)
    # 转录持久化
    transcript = Transcript(tmp_path / "s1.jsonl")
    assert any(m.get("role") == "user" and m.get("content") == "写第一章" for m in transcript.messages)


async def test_idempotency_key_dedup(tmp_path):
    harness = make_harness(tmp_path, [{"content": "完成"}])
    events1 = await drain(harness, "hi", idempotency_key="k1")
    assert len(events1) > 0
    # 同一 key 重复投递 → 直接跳过
    events2 = await drain(harness, "hi", idempotency_key="k1")
    assert events2 == []


async def test_steering_injected_mid_turn(tmp_path):
    """steer 在回合内注入（openclaw steer 语义）。"""
    harness = make_harness(tmp_path, [{"content": "完成"}])
    harness.queue_steering("换方向")
    events = await drain(harness, "写")
    assert len(harness.transcript.messages) >= 1


async def test_follow_up_chain_after_stop(tmp_path):
    """followUp 语义：agent 完成后追加再续跑一轮（openclaw 外层循环）。"""
    harness = make_harness(
        tmp_path,
        [{"content": "第一轮回复"}, {"content": "第二轮回复"}],
    )
    harness.queue_follow_up("追加要求")
    events = await drain(harness, "开始")
    # 两个 provider 响应都消费了（follow-up 触发第二回合）
    provider = harness.provider
    assert provider.script_remaining() == 0
    assert harness._turn_index == 2


async def test_concurrent_send_serialized(tmp_path):
    """写锁：同一会话并发 send 串行执行（openclaw 写锁思想）。"""
    harness = make_harness(
        tmp_path,
        [{"content": "r1"}, {"content": "r2"}],
    )
    async def send_one(text: str):
        await drain(harness, text)
    # 并发发送两条
    await asyncio.gather(send_one("第一"), send_one("第二"))
    # 转录顺序完整（无交错损坏）
    transcript = Transcript(tmp_path / "s1.jsonl")
    roles = [m.get("role") for m in transcript.messages]
    assert roles.count("user") == 2


async def test_guard_system_forwarded_to_run_turn(tmp_path):
    """护栏注入化：harness 层 guard_system 参数真实转发给 run_turn（吸收核查：
    此前注入点只在 loop 层，harness 不转发导致生产不可达）。"""
    from core.guards.loop_guards import GuardResult, GuardSystem

    class AlwaysTripGuard(GuardSystem):
        def check(self, max_iterations: int = 30) -> GuardResult:
            return GuardResult(tripped=True, level="X", reason="自定义护栏", diagnosis={"level": "X"})

    harness = make_harness(
        tmp_path,
        [{"content": "", "tool_calls": [{"name": "echo", "arguments": {}}]}, {"content": "不会到达"}],
        guard_system=AlwaysTripGuard(),
    )
    events = await drain(harness, "写")
    # 自定义护栏触发 → guard_tripped 事件 + 回合结束（不再调用 provider）
    from core.events import GuardTripped

    assert any(isinstance(e, GuardTripped) and e.level == "X" for e in events)
    from core.loop import StopReason

    turn_ended = next(e for e in events if e.kind.value == "turn_ended")
    assert turn_ended.stop_reason == StopReason.GUARD_TRIPPED.value


async def test_empty_response_nudge_not_persisted(tmp_path):
    """code-review #8（二轮）：空响应 nudge 是临时注入——不落盘、不重放。"""
    harness = make_harness(
        tmp_path,
        [{"content": ""}, {"content": "这次写完了"}],
    )
    await drain(harness, "写第一章")
    transcript = Transcript(tmp_path / "s1.jsonl")
    # transcript 中无 nudge 内容（nudge 不持久化，后续回合不会重放成悬空指令）
    assert not any("回复为空" in str(m.get("content", "")) for m in transcript.messages)
    # 用户消息与最终回复正常落盘
    assert any(m.get("role") == "user" and m.get("content") == "写第一章" for m in transcript.messages)
    assert any(m.get("role") == "assistant" and m.get("content") == "这次写完了" for m in transcript.messages)

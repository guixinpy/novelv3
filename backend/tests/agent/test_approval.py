"""审批门测试：ApprovalGate 的 before_tool_call、approve、reject 逻辑。"""
from __future__ import annotations

import pytest

from app.agent.approval import ApprovalGate
from app.agent.events import ApprovalPending
from app.agent.tooling import PermissionLevel, ToolContext, ToolDefinition, ToolRegistry


def _make_registry() -> ToolRegistry:
    """注册一个只读工具和一个写入工具用于测试。"""
    r = ToolRegistry()
    r.register(ToolDefinition(
        name="read_test",
        description="只读测试工具",
        parameters={"type": "object", "properties": {"x": {"type": "string"}}},
        permission=PermissionLevel.READ,
        handler=lambda ctx, x: None,
    ))
    r.register(ToolDefinition(
        name="write_test",
        description="写入测试工具",
        parameters={"type": "object", "properties": {"y": {"type": "integer"}}},
        permission=PermissionLevel.WRITE,
        handler=lambda ctx, y: None,
    ))
    return r


@pytest.fixture
def gate():
    return ApprovalGate(registry=_make_registry())


@pytest.fixture
def ctx():
    return ToolContext(project_id="p1", session_id="s1")


@pytest.mark.asyncio
async def test_read_tool_passes_through(gate: ApprovalGate, ctx: ToolContext):
    """只读工具应直接放行，不触发审批。"""
    result = await gate.before_tool_call("read_test", {"x": "hello"}, ctx)
    assert result is None  # None = 放行
    assert gate.pending_info is None  # 无待审批


@pytest.mark.asyncio
async def test_write_tool_triggers_pending(gate: ApprovalGate, ctx: ToolContext):
    """写入工具应阻塞并设置 pending 状态。"""
    pending_events = []

    async def fake_emit(event):
        pending_events.append(event)

    gate.set_emitter(fake_emit)

    # 在任务中运行 before_tool_call，它会阻塞
    async def call_gate():
        return await gate.before_tool_call("write_test", {"y": 42}, ctx)

    import asyncio
    task = asyncio.create_task(call_gate())

    # 让事件循环有机会让 before_tool_call 开始执行
    await asyncio.sleep(0)

    # 应已设置 pending 状态
    assert gate.pending_info is not None
    assert gate.pending_info["approval_id"] is not None

    # 应发出了 ApprovalPending 事件
    assert len(pending_events) == 1
    event = pending_events[0]
    assert isinstance(event, ApprovalPending)
    assert event.tool_name == "write_test"
    assert event.arguments == {"y": 42}

    # 批准
    gate.approve()
    result = await task
    assert result is None  # 放行


@pytest.mark.asyncio
async def test_reject_write_tool(gate: ApprovalGate, ctx: ToolContext):
    """拒绝写入工具应返回理由给模型。"""
    gate.set_emitter(lambda e: None)

    import asyncio
    task = asyncio.create_task(
        gate.before_tool_call("write_test", {"y": 42}, ctx)
    )
    await asyncio.sleep(0)

    gate.reject(reason="这个修改不合理，请重新考虑。")
    result = await task
    assert result is not None
    assert "不合理" in result


@pytest.mark.asyncio
async def test_approve_when_no_pending(gate: ApprovalGate):
    """没有待审批时 approve/reject 应返回 False。"""
    assert gate.approve() is False
    assert gate.reject() is False


@pytest.mark.asyncio
async def test_pending_info_cleared_after_approve(gate: ApprovalGate, ctx: ToolContext):
    """批准后 pending_info 应清空。"""
    gate.set_emitter(lambda e: None)

    import asyncio
    task = asyncio.create_task(
        gate.before_tool_call("write_test", {"y": 1}, ctx)
    )
    await asyncio.sleep(0)

    assert gate.pending_info is not None
    gate.approve()
    await task
    # 批准后 pending 状态已清除
    assert gate.pending_info is None

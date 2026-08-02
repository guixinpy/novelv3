"""v2 agent API 测试：mock provider 驱动完整会话生命周期。

会话持有 harness 实例（修复每请求重建缺陷）：steer/followup/幂等/写锁跨请求生效，
测试用 scripted provider 记录请求形状做真实断言（不再空转通过）。
"""
from __future__ import annotations

import threading
import time

import pytest

import app.api.v2.agent as agent_api
from tests.core.conftest import ScriptedProvider


@pytest.fixture
def mock_provider_factory(monkeypatch):
    """注入 scripted provider（覆盖 create_session 与懒重建两条路径）。"""

    class Handle:
        def __init__(self):
            self.provider = None

        def script(self, steps: list[dict]) -> ScriptedProvider:
            self.provider = ScriptedProvider(steps)
            monkeypatch.setattr(agent_api, "_load_provider", lambda: self.provider)
            return self.provider

    return Handle()


def _create_project(client) -> str:
    r = client.post("/api/v2/projects", json={"name": "测试项目"})
    assert r.status_code == 200
    return r.json()["id"]


def _create_session(client, project_id: str) -> str:
    r = client.post("/api/v2/agent/sessions", json={"project_id": project_id})
    assert r.status_code == 200
    return r.json()["session_id"]


def test_create_project(client):
    r = client.post("/api/v2/projects", json={"name": "新项目", "genre": "悬疑"})
    assert r.status_code == 200
    data = r.json()
    assert data["id"] and data["name"] == "新项目"


def test_create_session_rejects_missing_project(client):
    r = client.post("/api/v2/agent/sessions", json={"project_id": "nonexistent"})
    assert r.status_code == 404


def test_create_session(client, mock_provider_factory):
    mock_provider_factory.script([])
    project_id = _create_project(client)
    sid = _create_session(client, project_id)
    assert sid


def test_send_message_sse_stream(client, mock_provider_factory, tmp_path, monkeypatch):
    monkeypatch.setattr(agent_api, "_SESSIONS_DIR", tmp_path)
    mock_provider_factory.script([{"content": "你好，作者"}])
    project_id = _create_project(client)
    sid = _create_session(client, project_id)

    r2 = client.post(f"/api/v2/agent/sessions/{sid}/messages", json={"content": "写第一章"})
    assert r2.status_code == 200
    assert r2.headers["content-type"].startswith("text/event-stream")
    body = r2.text
    assert "agent_start" in body
    assert "agent_end" in body
    assert "assistant_message" in body
    assert "你好" in body
    # 事件带稳定 id（P2-8）
    assert "event_id" in body
    # 单一 agent_start（不重复）
    assert body.count("event: agent_start") == 1


def _send_with_auto_approval(client, sid: str, content: str, timeout: float = 10.0):
    """发送消息并自动批准所有 write 审批（write 工具经审批门拦截后放行）。"""
    result = {}

    def send_in_thread():
        result["resp"] = client.post(f"/api/v2/agent/sessions/{sid}/messages", json={"content": content})

    t = threading.Thread(target=send_in_thread)
    t.start()
    deadline = time.time() + timeout
    while time.time() < deadline:
        pr = client.get(f"/api/v2/agent/sessions/{sid}/pending-approvals")
        if pr.status_code == 200:
            for item in pr.json()["pending"]:
                client.post(f"/api/v2/agent/sessions/{sid}/approve", params={"call_id": item["call_id"]})
        if result.get("resp") is not None:
            break
        time.sleep(0.02)
    t.join(timeout=5)
    assert result["resp"] is not None, "send 未在超时内完成"
    return result["resp"]


def test_send_message_uses_tools_and_persists(client, mock_provider_factory, tmp_path, monkeypatch, db_session):
    monkeypatch.setattr(agent_api, "_SESSIONS_DIR", tmp_path)
    from app.models import ChapterContent

    project_id = _create_project(client)
    mock_provider_factory.script(
        [
            {"content": "我来写", "tool_calls": [{"name": "write_chapter", "arguments": {"chapter_index": 1, "content": "第一章正文内容。" * 20, "title": "开端"}}]},
            {"content": "第一章已写入", "tool_calls": []},
        ]
    )
    sid = _create_session(client, project_id)
    r2 = _send_with_auto_approval(client, sid, "写第一章")
    assert r2.status_code == 200

    chapter = db_session.query(ChapterContent).filter(ChapterContent.project_id == project_id).first()
    assert chapter is not None
    assert chapter.chapter_index == 1

    transcript_path = tmp_path / sid / f"{sid}.jsonl"
    assert transcript_path.exists()


def test_idempotency_key_dedup_across_requests(client, mock_provider_factory, tmp_path, monkeypatch):
    """幂等键跨请求生效（P0-1：会话持有 harness，不再每请求重建）。"""
    monkeypatch.setattr(agent_api, "_SESSIONS_DIR", tmp_path)
    mock_provider_factory.script([{"content": "完成"}])
    project_id = _create_project(client)
    sid = _create_session(client, project_id)

    r1 = client.post(f"/api/v2/agent/sessions/{sid}/messages", json={"content": "hi", "idempotency_key": "k1"})
    assert r1.status_code == 200
    r2 = client.post(f"/api/v2/agent/sessions/{sid}/messages", json={"content": "hi", "idempotency_key": "k1"})
    assert r2.status_code == 200
    assert "assistant_message" not in r2.text  # 幂等拦截生效


def test_steer_reaches_model(client, mock_provider_factory, tmp_path, monkeypatch):
    """steer 排入会话持有的 harness，注入真实到达模型（P0-1 真实断言）。

    旧测试因每请求重建 harness 空转通过——steer 文本从未到模型。
    """
    monkeypatch.setattr(agent_api, "_SESSIONS_DIR", tmp_path)
    mock_provider_factory.script(
        [
            # read 工具（memory_tree）不触发审批，专注验证 steer 注入
            {"content": "", "tool_calls": [{"name": "memory_tree", "arguments": {"detail_level": "overview"}}]},
            {"content": "按新方向写", "tool_calls": []},
        ]
    )
    project_id = _create_project(client)
    sid = _create_session(client, project_id)

    r = client.post(f"/api/v2/agent/sessions/{sid}/steer", json={"content": "节奏放慢"})
    assert r.status_code == 200
    r2 = client.post(f"/api/v2/agent/sessions/{sid}/messages", json={"content": "写"})
    assert r2.status_code == 200
    assert "按新方向写" in r2.text
    # 真实断言：第二次请求包含 steer 消息
    provider = mock_provider_factory.provider
    assert len(provider.requests) >= 2
    second = provider.requests[1]
    assert any(m.get("role") == "user" and m.get("content") == "节奏放慢" for m in second)


def test_write_tool_requires_approval(client, mock_provider_factory, tmp_path, monkeypatch):
    """审批门（P1-6）：write 工具被拦截，未批准不执行。"""
    monkeypatch.setattr(agent_api, "_SESSIONS_DIR", tmp_path)
    mock_provider_factory.script(
        [
            {"content": "", "tool_calls": [{"name": "write_chapter", "arguments": {"chapter_index": 1, "content": "第一章正文。" * 20}}]},
            {"content": "等待批准后继续", "tool_calls": []},
        ]
    )
    project_id = _create_project(client)
    sid = _create_session(client, project_id)

    result = {}

    def send_in_thread():
        result["resp"] = client.post(f"/api/v2/agent/sessions/{sid}/messages", json={"content": "写"})

    t = threading.Thread(target=send_in_thread)
    t.start()
    for _ in range(50):
        pr = client.get(f"/api/v2/agent/sessions/{sid}/pending-approvals")
        if pr.status_code == 200 and pr.json()["pending"]:
            break
        time.sleep(0.05)
    pr = client.get(f"/api/v2/agent/sessions/{sid}/pending-approvals")
    assert pr.status_code == 200
    pending = pr.json()["pending"]
    assert pending, "write 工具应被审批门拦截"
    call_id = pending[0]["call_id"]
    ar = client.post(f"/api/v2/agent/sessions/{sid}/approve", params={"call_id": call_id})
    assert ar.status_code == 200
    t.join(timeout=10)
    assert result["resp"].status_code == 200
    assert "等待批准后继续" in result["resp"].text


def test_events_replay(client, mock_provider_factory, tmp_path, monkeypatch):
    monkeypatch.setattr(agent_api, "_SESSIONS_DIR", tmp_path)
    mock_provider_factory.script([{"content": "完成"}])
    project_id = _create_project(client)
    sid = _create_session(client, project_id)
    client.post(f"/api/v2/agent/sessions/{sid}/messages", json={"content": "hi"})

    r2 = client.get(f"/api/v2/agent/sessions/{sid}/events")
    assert r2.status_code == 200
    events = r2.json()["events"]
    assert any(e["type"] == "message" for e in events)


def test_unknown_session_404(client):
    r = client.post("/api/v2/agent/sessions/ghost/messages", json={"content": "hi"})
    assert r.status_code == 404


def test_send_writes_chapter_then_introspects(client, mock_provider_factory, tmp_path, monkeypatch, db_session):
    """09 触发点 2（生产路径）：写完章节后自动章末自省并写入写作经验。

    自省响应是 script 的第 3 步（harness 2 步 + 自省 1 步）；幂等保证重复 send 不重复自省。
    """
    monkeypatch.setattr(agent_api, "_SESSIONS_DIR", tmp_path)
    from app.models import LongformMemory

    project_id = _create_project(client)
    mock_provider_factory.script(
        [
            {"content": "我来写", "tool_calls": [{"name": "write_chapter", "arguments": {"chapter_index": 1, "content": "第一章正文内容。" * 20, "title": "开端"}}]},
            {"content": "第一章已写入", "tool_calls": []},
            {"content": '{"experiences": [{"key": "开篇钩子", "action": "new", "text": "章末留钩子有效。"}]}'},
        ]
    )
    sid = _create_session(client, project_id)
    r2 = _send_with_auto_approval(client, sid, "写第一章")
    assert r2.status_code == 200
    # 自省已执行：writing_experience 条目存在
    exp = (
        db_session.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == "writing_experience",
        )
        .all()
    )
    assert exp, "生产路径应自动自省并写入经验"
    assert exp[0].scope_key == "开篇钩子"
    assert (exp[0].memory_metadata or {})["trust_score"] == 1


def test_send_without_chapter_skips_introspect(client, mock_provider_factory, tmp_path, monkeypatch, db_session):
    """未写新章节的回合不触发自省（无 chapter 时不调用 provider 自省）。"""
    monkeypatch.setattr(agent_api, "_SESSIONS_DIR", tmp_path)
    from app.models import LongformMemory

    project_id = _create_project(client)
    mock_provider_factory.script(
        [
            {"content": "完成了，无需写章节", "tool_calls": []},
        ]
    )
    sid = _create_session(client, project_id)
    r2 = client.post(f"/api/v2/agent/sessions/{sid}/messages", json={"content": "讨论"})
    assert r2.status_code == 200
    exp = (
        db_session.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == "writing_experience",
        )
        .all()
    )
    assert exp == []


def test_approval_pending_emitted_once(client, mock_provider_factory, tmp_path, monkeypatch):
    """R1 回归：ApprovalPending 只发一次（此前双队列双发，SSE 出现两次）。"""
    monkeypatch.setattr(agent_api, "_SESSIONS_DIR", tmp_path)
    mock_provider_factory.script(
        [
            {"content": "", "tool_calls": [{"name": "write_chapter", "arguments": {"chapter_index": 1, "content": "第一章正文。" * 20}}]},
            {"content": "继续", "tool_calls": []},
        ]
    )
    project_id = _create_project(client)
    sid = _create_session(client, project_id)

    result = {}

    def send_in_thread():
        result["resp"] = client.post(f"/api/v2/agent/sessions/{sid}/messages", json={"content": "写"})

    t = threading.Thread(target=send_in_thread)
    t.start()
    for _ in range(50):
        pr = client.get(f"/api/v2/agent/sessions/{sid}/pending-approvals")
        if pr.status_code == 200 and pr.json()["pending"]:
            break
        time.sleep(0.05)
    pr = client.get(f"/api/v2/agent/sessions/{sid}/pending-approvals")
    pending = pr.json()["pending"]
    assert pending
    client.post(f"/api/v2/agent/sessions/{sid}/approve", params={"call_id": pending[0]["call_id"]})
    t.join(timeout=10)
    body = result["resp"].text
    # SSE 流中 approval_pending 恰好一次
    assert body.count("event: approval_pending") == 1, f"approval_pending 出现 {body.count('event: approval_pending')} 次"

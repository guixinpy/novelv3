"""v2 agent API 测试：mock provider 驱动完整会话生命周期。

会话持有 harness 实例（修复每请求重建缺陷）：steer/followup/幂等/写锁跨请求生效，
测试用 scripted provider 记录请求形状做真实断言（不再空转通过）。

审批测试：send 用独立 daemon 线程（完整读 SSE body），审批直接操作内存 gate
（agent_api._sessions[sid]["gate"].approve，不经过 HTTP）——ApprovalGate 已改为
线程安全（threading.Event + asyncio.to_thread），跨线程 approve 可靠。
注意：httpx ASGITransport 不流式（等 app 完成才返回），async 流式审批不可行；
sync TestClient 流式 + HTTP 嵌套审批在 Windows 有 portal 竞态——均不可用。
daemon=True：测试失败时线程不阻塞进程退出。
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


def _send_with_auto_approval(client, sid: str, content: str, timeout: float = 15.0):
    """线程发送并自动批准所有 write 审批（直接操作线程安全的内存 gate）。"""
    result = {}

    def send_in_thread():
        result["resp"] = client.post(
            f"/api/v2/agent/sessions/{sid}/messages", json={"content": content}
        )

    t = threading.Thread(target=send_in_thread, daemon=True)
    t.start()
    deadline = time.time() + timeout
    while time.time() < deadline and result.get("resp") is None:
        session = agent_api._sessions.get(sid)
        if session is not None:
            for item in session["gate"].pending_requests():
                session["gate"].approve(item["call_id"])
        time.sleep(0.01)
    t.join(timeout=5)
    assert result.get("resp") is not None, "send 未在超时内完成"
    return result["resp"]


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
    """审批门（P1-6）：write 工具被拦截，未批准不执行（gate 内存审批，线程安全）。"""
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

    t = threading.Thread(target=send_in_thread, daemon=True)
    t.start()
    # 等待拦截真实发生（gate 出现 pending）
    deadline = time.time() + 10
    while time.time() < deadline:
        session = agent_api._sessions.get(sid)
        if session is not None and session["gate"].pending_requests():
            break
        time.sleep(0.02)
    pending = agent_api._sessions[sid]["gate"].pending_requests()
    assert pending, "write 工具应被审批门拦截"
    call_id = pending[0]["call_id"]
    assert agent_api._sessions[sid]["gate"].approve(call_id)
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

    body = _send_with_auto_approval(client, sid, "写").text
    # SSE 流中 approval_pending 恰好一次
    assert body.count("event: approval_pending") == 1, f"approval_pending 出现 {body.count('event: approval_pending')} 次"


def test_send_writes_chapter_then_introspects(client, mock_provider_factory, tmp_path, monkeypatch, db_session):
    """09 触发点 2（生产路径）：写完章节后自动章末自省并写入写作经验。

    自省响应是 script 的第 3 步（harness 2 步 + 自省 1 步）。
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


def test_introspect_after_send_out_of_order(client, mock_provider_factory, tmp_path, monkeypatch, db_session):
    """code-review 三轮 #2：乱序写章（先写 Ch3 再回写 Ch1）不自省漏检。

    差集推导：全部章号 - 已自省章号，与写入顺序无关；每批上限 3 章。
    """
    import asyncio

    monkeypatch.setattr(agent_api, "_SESSIONS_DIR", tmp_path)
    from app.models import ChapterContent, LongformMemory

    project_id = _create_project(client)
    mock_provider_factory.script(
        [
            {"content": "我来写", "tool_calls": [{"name": "write_chapter", "arguments": {"chapter_index": 3, "content": "第三章正文。" * 20}}]},
            {"content": "继续写", "tool_calls": [{"name": "write_chapter", "arguments": {"chapter_index": 1, "content": "第一章正文。" * 20}}]},
            {"content": "完成", "tool_calls": []},
            {"content": '{"experiences": []}'},
            {"content": '{"experiences": []}'},
        ]
    )
    sid = _create_session(client, project_id)
    _send_with_auto_approval(client, sid, "写第三章和第一章")
    session = agent_api._sessions[sid]

    async def run_introspect():
        await agent_api._introspect_after_send(db_session, session)

    # 直接驱动后台任务（差集逻辑单测：两次调用覆盖两章）
    asyncio.run(run_introspect())
    asyncio.run(run_introspect())
    logs = {
        r[0]
        for r in db_session.query(LongformMemory.start_chapter_index)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == "introspect_log",
        )
        .all()
    }
    # Ch1 与 Ch3 都被自省（乱序不漏检）；Ch2 不存在
    assert 1 in logs and 3 in logs


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

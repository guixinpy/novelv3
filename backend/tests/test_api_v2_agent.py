"""v2 agent API 测试：mock provider 驱动完整会话生命周期（创建→消息→SSE 事件流）。

scripted provider 注入：monkeypatch api.v2.agent._load_provider。
"""
from __future__ import annotations

import json

import pytest

import app.api.v2.agent as agent_api
from tests.core.conftest import ScriptedProvider


@pytest.fixture
def mock_provider_factory(monkeypatch):
    """注入 scripted provider，返回控制句柄。"""

    class Handle:
        def __init__(self):
            self.provider = None

        def script(self, steps: list[dict]):
            self.provider = ScriptedProvider(steps)
            monkeypatch.setattr(agent_api, "_load_provider", lambda: self.provider)
            return self.provider

    return Handle()


def test_create_session(client):
    r = client.post("/api/v2/agent/sessions", json={"project_id": "nonexistent", "system_prompt": "你好"})
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"]
    assert data["project_id"] == "nonexistent"


def test_send_message_sse_stream(client, mock_provider_factory, tmp_path, monkeypatch):
    # 会话目录指向临时目录
    monkeypatch.setattr(agent_api, "_SESSIONS_DIR", tmp_path)
    r = client.post("/api/v2/agent/sessions", json={"project_id": "p1"})
    sid = r.json()["session_id"]

    mock_provider_factory.script([{"content": "你好，作者"}])
    r2 = client.post(f"/api/v2/agent/sessions/{sid}/messages", json={"content": "写第一章"})
    assert r2.status_code == 200
    assert r2.headers["content-type"].startswith("text/event-stream")
    body = r2.text
    # SSE 事件协议：agent_start ... assistant_message ... agent_end
    assert "agent_start" in body
    assert "agent_end" in body
    assert "assistant_message" in body
    assert "你好" in body


def test_send_message_uses_tools_and_persists(client, mock_provider_factory, tmp_path, monkeypatch, db_session):
    monkeypatch.setattr(agent_api, "_SESSIONS_DIR", tmp_path)
    r = client.post("/api/v2/agent/sessions", json={"project_id": "p1"})
    sid = r.json()["session_id"]

    # 会话工具链：write_chapter 落库
    from app.models import ChapterContent, Project

    project = Project(name="测试项目")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    r = client.post("/api/v2/agent/sessions", json={"project_id": project.id})
    sid = r.json()["session_id"]

    mock_provider_factory.script(
        [
            {"content": "我来写", "tool_calls": [{"name": "write_chapter", "arguments": {"chapter_index": 1, "content": "第一章正文内容。" * 20, "title": "开端"}}]},
            {"content": "第一章已写入", "tool_calls": []},
        ]
    )
    r2 = client.post(f"/api/v2/agent/sessions/{sid}/messages", json={"content": "写第一章"})
    assert r2.status_code == 200

    # 章节落库
    chapter = db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id).first()
    assert chapter is not None
    assert chapter.chapter_index == 1
    assert chapter.status == "generated"

    # 转录持久化（agent_sessions_v2 目录）
    transcript_path = tmp_path / sid / f"{sid}.jsonl"
    assert transcript_path.exists()


def test_events_replay(client, mock_provider_factory, tmp_path, monkeypatch):
    monkeypatch.setattr(agent_api, "_SESSIONS_DIR", tmp_path)
    r = client.post("/api/v2/agent/sessions", json={"project_id": "p1"})
    sid = r.json()["session_id"]
    mock_provider_factory.script([{"content": "完成"}])
    client.post(f"/api/v2/agent/sessions/{sid}/messages", json={"content": "hi"})

    r2 = client.get(f"/api/v2/agent/sessions/{sid}/events")
    assert r2.status_code == 200
    events = r2.json()["events"]
    assert any(e["type"] == "message" for e in events)


def test_steer_and_followup_queues(client, mock_provider_factory, tmp_path, monkeypatch):
    monkeypatch.setattr(agent_api, "_SESSIONS_DIR", tmp_path)
    r = client.post("/api/v2/agent/sessions", json={"project_id": "p1"})
    sid = r.json()["session_id"]

    # steer 在回合中注入：第一次工具调用后注入方向，第二次调用前生效
    mock_provider_factory.script(
        [
            {"content": "", "tool_calls": [{"name": "write_chapter", "arguments": {"chapter_index": 1, "content": "第一章正文。" * 20}}]},
            {"content": "按新方向写", "tool_calls": []},
        ]
    )
    # 先排队 steer（回合内注入）
    client.post(f"/api/v2/agent/sessions/{sid}/steer", json={"content": "节奏放慢"})
    r2 = client.post(f"/api/v2/agent/sessions/{sid}/messages", json={"content": "写"})
    assert r2.status_code == 200
    assert "按新方向写" in r2.text


def test_unknown_session_404(client):
    r = client.post("/api/v2/agent/sessions/ghost/messages", json={"content": "hi"})
    assert r.status_code == 404

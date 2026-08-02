import json

import pytest

import app.api.v2_sessions as v2
from app.models import ChapterContent, Project
from test_support.agent_fakes import FakeProvider, call, text_response, tool_response


@pytest.fixture
def project(db_session):
    p = Project(name="灯塔旧回声")
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def session_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(v2, "SESSIONS_DIR", tmp_path)
    return tmp_path


def use_provider(monkeypatch, provider):
    monkeypatch.setattr(v2, "build_provider", lambda: provider)


def parse_sse(text: str) -> list[dict]:
    events = []
    for block in text.split("\n\n"):
        lines = [l for l in block.strip().splitlines() if l]
        if not lines:
            continue
        event_type = next((l[len("event: "):] for l in lines if l.startswith("event: ")), None)
        data_line = next((l[len("data: "):] for l in lines if l.startswith("data: ")), None)
        events.append({"event": event_type, "data": json.loads(data_line) if data_line else None})
    return events


def test_create_session(client, project, session_dir):
    resp = client.post(f"/api/v2/projects/{project.id}/sessions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"]
    assert body["project_id"] == project.id


def test_create_session_unknown_project(client, session_dir):
    resp = client.post("/api/v2/projects/nope/sessions")
    assert resp.status_code == 404


def test_send_message_streams_events(client, project, session_dir, monkeypatch):
    use_provider(monkeypatch, FakeProvider([text_response("你好|，作者")]))
    session_id = client.post(f"/api/v2/projects/{project.id}/sessions").json()["session_id"]

    with client.stream(
        "POST", f"/api/v2/sessions/{session_id}/messages", json={"content": "hi"}
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        text = "".join(resp.iter_text())

    events = parse_sse(text)
    types = [e["event"] for e in events]
    assert "assistant_delta" in types
    assert types[-1] == "turn_ended"
    deltas = [e["data"]["text"] for e in events if e["event"] == "assistant_delta"]
    assert deltas == ["你好", "，作者"]
    final = next(e for e in events if e["event"] == "assistant_message")
    assert final["data"]["content"] == "你好，作者"


def test_send_message_with_tool_call_streams_tool_events(
    client, db_session, project, session_dir, monkeypatch
):
    db_session.add(ChapterContent(project_id=project.id, chapter_index=1, title="第一章",
                                  content="海雾散去。", word_count=5, status="completed"))
    db_session.commit()
    use_provider(monkeypatch, FakeProvider([
        tool_response(call("read_chapter", '{"chapter_index": 1}')),
        text_response("第一章写了海雾。"),
    ]))
    session_id = client.post(f"/api/v2/projects/{project.id}/sessions").json()["session_id"]

    with client.stream(
        "POST", f"/api/v2/sessions/{session_id}/messages", json={"content": "看下第一章"}
    ) as resp:
        text = "".join(resp.iter_text())

    events = parse_sse(text)
    started = [e for e in events if e["event"] == "tool_call_started"]
    finished = [e for e in events if e["event"] == "tool_call_finished"]
    assert started and started[0]["data"]["name"] == "read_chapter"
    assert finished and finished[0]["data"]["is_error"] is False


def test_get_session_history(client, project, session_dir, monkeypatch):
    use_provider(monkeypatch, FakeProvider([text_response("答")]))
    session_id = client.post(f"/api/v2/projects/{project.id}/sessions").json()["session_id"]
    with client.stream(
        "POST", f"/api/v2/sessions/{session_id}/messages", json={"content": "问"}
    ) as resp:
        "".join(resp.iter_text())

    resp = client.get(f"/api/v2/sessions/{session_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["project_id"] == project.id
    roles = [m["role"] for m in body["messages"]]
    assert roles == ["user", "assistant"]


def test_send_to_unknown_session_404(client, session_dir):
    resp = client.post("/api/v2/sessions/nope/messages", json={"content": "hi"})
    assert resp.status_code == 404


def test_list_project_sessions(client, project, session_dir, monkeypatch):
    s1 = client.post(f"/api/v2/projects/{project.id}/sessions").json()["session_id"]
    s2 = client.post(f"/api/v2/projects/{project.id}/sessions").json()["session_id"]
    resp = client.get(f"/api/v2/projects/{project.id}/sessions")
    assert resp.status_code == 200
    ids = [s["session_id"] for s in resp.json()["sessions"]]
    assert set(ids) == {s1, s2}

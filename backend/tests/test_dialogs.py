import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
import pytest
from unittest.mock import AsyncMock, patch

from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session as OrmSession

from app.api import dialogs as dialogs_api
from app.core.chat_commands import (
    command_mutates_history,
    command_to_action_type,
    is_supported_chat_command,
)
from app.core.intent_router import IntentRouter
from app.models import Dialog, PendingAction
from app.schemas import ProjectDiagnosisOut

ORIGINAL_SESSION_COMMIT = OrmSession.commit


def test_state_diagnosis_empty_project(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.get(f"/api/v1/projects/{pid}/state-diagnosis")
    assert r2.status_code == 200
    data = r2.json()
    assert "setup" in data["missing_items"]
    assert data["suggested_next_step"] == "preview_setup"


def test_intent_router_confirmation():
    router = IntentRouter()
    diag = ProjectDiagnosisOut(missing_items=["setup"], completed_items=[], suggested_next_step="preview_setup")

    assert router.resolve("好的", "chatting", "act_1", diag).type == "confirm"
    assert router.resolve("算了", "chatting", "act_1", diag).type == "cancel"
    assert router.resolve("改一下主角", "chatting", "act_1", diag).type == "revise"


def test_intent_router_action_candidate():
    router = IntentRouter()
    diag = ProjectDiagnosisOut(missing_items=["setup"], completed_items=[], suggested_next_step="preview_setup")

    assert router.resolve("创建主角设定", "chatting", None, diag).type == "preview_setup"

    diag2 = ProjectDiagnosisOut(missing_items=["storyline"], completed_items=["setup"], suggested_next_step="preview_storyline")
    assert router.resolve("生成故事线", "chatting", None, diag2).type == "preview_storyline"

    diag3 = ProjectDiagnosisOut(missing_items=["outline"], completed_items=["setup", "storyline"], suggested_next_step="preview_outline")
    assert router.resolve("写第1章大纲", "chatting", None, diag3).type == "preview_outline"

    assert router.resolve("还有什么要设定的", "chatting", None, diag3).type == "query_diagnosis"


def test_intent_router_no_match():
    router = IntentRouter()
    diag = ProjectDiagnosisOut(missing_items=["setup"], completed_items=[], suggested_next_step="preview_setup")
    assert router.resolve("随便聊聊", "chatting", None, diag) is None


def test_chat_command_registry_helpers_cover_expected_commands():
    for command_name in ("clear", "compact", "setup", "storyline", "outline"):
        assert is_supported_chat_command(command_name) is True

    assert command_mutates_history("clear") is True
    assert command_mutates_history("compact") is True
    assert command_mutates_history("setup") is False
    assert command_mutates_history("storyline") is False
    assert command_mutates_history("outline") is False

    assert command_to_action_type("setup") == "preview_setup"
    assert command_to_action_type("storyline") == "preview_storyline"
    assert command_to_action_type("outline") == "preview_outline"
    assert command_to_action_type("clear") is None
    assert command_to_action_type("compact") is None


def test_chat_creates_dialog(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post("/api/v1/dialog/chat", json={"project_id": pid, "text": "你好"})
    assert r2.status_code == 200
    data = r2.json()
    assert "project_diagnosis" in data
    assert data["ui_hint"]["dialog_state"] == "CHATTING"
    assert data["ui_hint"]["active_action"]["type"] == "chat"
    assert data["ui_hint"]["active_action"]["status"] == "idle"
    assert data["ui_hint"]["active_action"]["target_panel"] is None
    assert data["refresh_targets"] == []


@patch("app.api.dialogs.load_api_key", return_value="sk-test")
@patch("app.api.dialogs.ai_service.complete", new_callable=AsyncMock)
def test_chat_uses_ai_service_for_free_text_when_model_available(mock_complete, mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test", "genre": "科幻"})
    pid = r.json()["id"]

    mock_complete.return_value.content = "你好，我可以先帮你梳理设定缺口，再决定是否生成故事线。"

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "text",
        "text": "hello",
    })

    assert r2.status_code == 200
    assert r2.json()["message"] == "你好，我可以先帮你梳理设定缺口，再决定是否生成故事线。"
    mock_complete.assert_awaited_once()
    sent_messages = mock_complete.await_args.args[0]
    assert "当前阶段：设定阶段" in sent_messages[0]["content"]
    assert "当前状态：待补全" in sent_messages[0]["content"]


@patch("app.api.dialogs.load_api_key", return_value=None)
def test_chat_reports_model_unavailable_instead_of_faking_ai_reply(mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "text",
        "text": "hello",
    })

    assert r2.status_code == 200
    assert "未配置模型 API Key" in r2.json()["message"]
    assert "建议先补全这些环节" not in r2.json()["message"]


def test_chat_button_action(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
        "params": {"project_id": pid},
    })
    assert r2.status_code == 200
    assert r2.json()["pending_action"]["type"] == "preview_setup"
    assert r2.json()["ui_hint"] == {
        "dialog_state": "PENDING_ACTION",
        "active_action": {
            "type": "preview_setup",
            "status": "pending",
            "target_panel": "setup",
            "reason": "等待用户确认",
        },
    }
    assert r2.json()["refresh_targets"] == []


def test_get_messages_includes_current_pending_action(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
        "params": {"project_id": pid},
    })
    pending = r2.json()["pending_action"]

    r3 = client.get(f"/api/v1/dialog/projects/{pid}/messages")
    assert r3.status_code == 200
    messages = r3.json()
    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["pending_action"] == pending


def test_get_messages_exposes_message_type_and_meta(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "你好"})
    assert r2.status_code == 200

    r3 = client.get(f"/api/v1/dialog/projects/{pid}/messages")
    assert r3.status_code == 200
    messages = r3.json()
    assert len(messages) >= 2

    user_message = messages[0]
    assert user_message["role"] == "user"
    assert user_message["message_type"] == "plain"
    assert "meta" in user_message
    assert user_message["meta"] is None

    assistant_message = messages[1]
    assert assistant_message["role"] == "assistant"
    assert assistant_message["message_type"] == "plain"
    assert "meta" in assistant_message
    assert assistant_message["meta"] is None


@patch("app.api.dialogs.load_api_key", return_value=None)
def test_unknown_command_input_falls_back_to_plain_chat(mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    command_payload = {
        "project_id": pid,
        "input_type": "command",
        "text": "",
        "command_name": "unknown_cmd",
        "command_args": "--scope history",
    }
    r2 = client.post("/api/v1/dialog/chat", json=command_payload)
    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"] is None
    assert body["refresh_targets"] == []
    assert body["ui_hint"]["dialog_state"] == "CHATTING"
    assert body["ui_hint"]["active_action"]["type"] == "chat"
    assert "暂不执行" not in body["message"]

    r3 = client.get(f"/api/v1/dialog/projects/{pid}/messages")
    assert r3.status_code == 200
    messages = r3.json()
    assert all("pending_action" not in m for m in messages)

    user_message = next(m for m in messages if m["role"] == "user")
    assert user_message["content"] == "/unknown_cmd --scope history"
    assert user_message["message_type"] == "plain"
    assert user_message["meta"] is None

    assistant_message = next(m for m in messages if m["role"] == "assistant")
    assert assistant_message["message_type"] == "plain"


@pytest.mark.parametrize(
    ("command_name", "expected_action_type"),
    [
        ("setup", "preview_setup"),
        ("storyline", "preview_storyline"),
        ("outline", "preview_outline"),
    ],
)
def test_command_with_args_enters_preview_pending_action_and_message(command_name, expected_action_type, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    args = "主角是植物学家"

    r2 = client.post(
        "/api/v1/dialog/chat",
        json={
            "project_id": pid,
            "input_type": "command",
            "command_name": command_name,
            "command_args": args,
        },
    )

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"]["type"] == expected_action_type
    assert body["pending_action"]["params"]["command_args"] == args
    assert f"附加要求：{args}" in body["message"]


@patch("app.api.dialogs.load_api_key", return_value=None)
@patch("app.api.dialogs.ai_service.complete", new_callable=AsyncMock)
def test_compact_replaces_previous_plain_messages_with_summary(mock_compact_complete, mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    mock_compact_complete.return_value.content = "压缩摘要：用户问候并要求继续。"

    client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "你好"})
    client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "请继续"})

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "command_name": "compact",
    })
    assert r2.status_code == 200
    assert "压缩" in r2.json()["message"]

    r3 = client.get(f"/api/v1/dialog/projects/{pid}/messages")
    assert r3.status_code == 200
    messages = r3.json()

    summary_messages = [m for m in messages if m["message_type"] == "summary"]
    assert len(summary_messages) == 1
    summary = summary_messages[0]
    assert summary["role"] == "system"
    assert summary["meta"]["command_name"] == "compact"
    assert summary["meta"]["compacted_count"] == 4
    assert summary["meta"]["summary_text"] == "压缩摘要：用户问候并要求继续。"
    assert "title" in summary["meta"]
    assert "summary_text" in summary["meta"]

    plain_messages = [m for m in messages if m["message_type"] == "plain"]
    assert plain_messages == []
    mock_compact_complete.assert_awaited_once()


def test_clear_removes_old_messages_and_pending_action(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "先聊一点"})
    client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
    })

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "command_name": "clear",
    })
    assert r2.status_code == 200
    assert "清空" in r2.json()["message"]

    r3 = client.get(f"/api/v1/dialog/projects/{pid}/messages")
    assert r3.status_code == 200
    messages = r3.json()
    assert len(messages) == 1
    assert messages[0]["role"] == "system"
    assert messages[0]["message_type"] == "command"
    assert messages[0]["meta"]["command_name"] == "clear"

    dialog = db_session.query(Dialog).filter(Dialog.project_id == pid).first()
    assert dialog is not None
    assert dialog.pending_action_id is None
    assert dialog.state == "chatting"


def test_compact_is_blocked_while_pending_action_exists(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
    })

    dialog_before = db_session.query(Dialog).filter(Dialog.project_id == pid).first()
    assert dialog_before is not None
    pending_action_id = dialog_before.pending_action_id
    assert pending_action_id is not None

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "command_name": "compact",
    })
    assert r2.status_code == 200
    assert "待处理" in r2.json()["message"]

    r3 = client.get(f"/api/v1/dialog/projects/{pid}/messages")
    assert r3.status_code == 200
    messages = r3.json()
    assert all(m["message_type"] != "summary" for m in messages)
    assert any(m["role"] == "system" and m["message_type"] == "command" for m in messages)

    dialog_after = db_session.query(Dialog).filter(Dialog.project_id == pid).first()
    assert dialog_after is not None
    assert dialog_after.pending_action_id == pending_action_id


def test_clear_invalidates_old_pending_action_and_resolve_rejects_it(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
    })
    pending_action_id = r2.json()["pending_action"]["id"]

    r3 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "command_name": "clear",
    })
    assert r3.status_code == 200

    pending = db_session.query(PendingAction).filter(PendingAction.id == pending_action_id).first()
    assert pending is not None
    assert pending.status == "cancelled"
    assert pending.resolved_at is not None

    r4 = client.post("/api/v1/dialog/resolve-action", json={
        "action_id": pending_action_id,
        "decision": "confirm",
    })
    assert r4.status_code == 409
    assert "no longer active" in r4.json()["detail"]


def test_compact_failure_does_not_drop_history(client):
    commit_counter = {"count": 0}

    def flaky_commit(session, *args, **kwargs):
        commit_counter["count"] += 1
        if commit_counter["count"] == 2:
            raise RuntimeError("forced commit failure")
        return ORIGINAL_SESSION_COMMIT(session, *args, **kwargs)

    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "A"})
    client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "B"})

    with patch("sqlalchemy.orm.session.Session.commit", autospec=True, side_effect=flaky_commit):
        r2 = client.post("/api/v1/dialog/chat", json={
            "project_id": pid,
            "input_type": "command",
            "command_name": "compact",
        })

    assert r2.status_code == 200
    assert "未变更" in r2.json()["message"]

    r3 = client.get(f"/api/v1/dialog/projects/{pid}/messages")
    assert r3.status_code == 200
    messages = r3.json()
    assert any(m["message_type"] == "plain" and m["content"] == "A" for m in messages)
    assert any(m["message_type"] == "plain" and m["content"] == "B" for m in messages)
    assert all(m["message_type"] != "summary" for m in messages)


@patch("app.api.dialogs.load_api_key", return_value=None)
@patch("app.api.dialogs.ai_service.complete", new_callable=AsyncMock)
def test_command_text_conflict_prefers_raw_text_as_single_source(mock_compact_complete, mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    mock_compact_complete.return_value.content = "冲突输入时采用 text 源。"

    client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "你好"})

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "text": "/compact from-text",
        "command_name": "clear",
        "command_args": "--from-name",
    })
    assert r2.status_code == 200
    assert "压缩" in r2.json()["message"]

    r3 = client.get(f"/api/v1/dialog/projects/{pid}/messages")
    assert r3.status_code == 200
    messages = r3.json()
    assert any(
        m["role"] == "user"
        and m["message_type"] == "command"
        and m["content"] == "/compact from-text"
        and m["meta"] == {"command_name": "compact", "command_args": "from-text"}
        for m in messages
    )
    assert mock_compact_complete.await_count == 1


@patch("app.api.dialogs.load_api_key", return_value=None)
@patch("app.api.dialogs.ai_service.complete", new_callable=AsyncMock)
def test_compact_only_compresses_messages_after_last_summary(mock_compact_complete, mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    mock_compact_complete.side_effect = [
        type("R", (), {"content": "第一段摘要"})(),
        type("R", (), {"content": "第二段摘要"})(),
    ]

    client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "第一轮1"})
    client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "第一轮2"})
    r1 = client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "command", "command_name": "compact"})
    assert r1.status_code == 200

    client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "第二轮1"})
    r2 = client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "command", "command_name": "compact"})
    assert r2.status_code == 200

    r3 = client.get(f"/api/v1/dialog/projects/{pid}/messages")
    assert r3.status_code == 200
    messages = r3.json()

    summary_messages = [m for m in messages if m["message_type"] == "summary"]
    assert len(summary_messages) == 2
    assert summary_messages[0]["meta"]["summary_text"] == "第一段摘要"
    assert summary_messages[1]["meta"]["summary_text"] == "第二段摘要"
    assert all(m["message_type"] != "plain" for m in messages)
    assert mock_compact_complete.await_count == 2

def test_resolve_action_confirm_sets_dialog_state_running(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
    })
    action_id = r2.json()["pending_action"]["id"]

    with patch("app.api.dialogs._execute_action_background") as mock_background:
        r3 = client.post("/api/v1/dialog/resolve-action", json={
            "action_id": action_id,
            "decision": "confirm",
        })
    assert r3.status_code == 200
    assert r3.json()["dialog_state"] == "RUNNING"
    assert r3.json()["action_result"]["status"] == "generating"
    assert r3.json()["ui_hint"] == {
        "dialog_state": "RUNNING",
        "active_action": {
            "type": "generate_setup",
            "status": "running",
            "target_panel": "setup",
            "reason": "用户确认执行",
        },
    }
    assert r3.json()["refresh_targets"] == []
    mock_background.assert_called_once()

    dialog = db_session.query(Dialog).filter(Dialog.project_id == pid).first()
    assert dialog is not None
    assert dialog.pending_action_id is None
    assert dialog.state == "running"


@pytest.mark.parametrize("result_payload", [
    {"status": "success"},
    {"status": "failed", "error": "boom"},
])
def test_background_completion_restores_dialog_state_to_chatting(result_payload, client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
    })
    dialog = db_session.query(Dialog).filter(Dialog.project_id == pid).first()
    assert dialog is not None
    dialog.state = "running"
    db_session.commit()
    background_session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_session.get_bind(),
    )

    with patch("app.db.SessionLocal", background_session_factory), \
            patch("app.api.dialogs._execute_action", new=AsyncMock(return_value=result_payload)), \
            patch("app.api.dialogs.asyncio.ensure_future", side_effect=lambda coro: asyncio.run(coro)):
        dialogs_api._execute_action_background("generate_setup", pid, dialog.id)

    db_session.expire_all()
    refreshed_dialog = db_session.query(Dialog).filter(Dialog.project_id == pid).first()
    assert refreshed_dialog is not None
    assert refreshed_dialog.state == "chatting"

    latest_message = (
        db_session.query(dialogs_api.DialogMessage)
        .filter(dialogs_api.DialogMessage.dialog_id == dialog.id)
        .order_by(dialogs_api.DialogMessage.created_at.desc())
        .first()
    )
    assert latest_message is not None
    assert latest_message.action_result["type"] == "generate_setup"
    assert latest_message.action_result["status"] == result_payload["status"]


@pytest.mark.parametrize("command_name", ["clear", "compact", "setup"])
def test_running_dialog_blocks_mutating_commands(command_name, client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
    })
    action_id = r2.json()["pending_action"]["id"]

    with patch("app.api.dialogs._execute_action_background"):
        r3 = client.post("/api/v1/dialog/resolve-action", json={
            "action_id": action_id,
            "decision": "confirm",
        })
    assert r3.status_code == 200

    r4 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "command_name": command_name,
    })
    assert r4.status_code == 200
    assert "正在执行" in r4.json()["message"]
    assert r4.json()["ui_hint"]["dialog_state"] == "RUNNING"

    dialog = db_session.query(Dialog).filter(Dialog.project_id == pid).first()
    assert dialog is not None
    assert dialog.state == "running"
    assert dialog.pending_action_id is None


def test_resolve_action_double_confirm_only_one_effective(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
    })
    action_id = r2.json()["pending_action"]["id"]

    barrier = threading.Barrier(2)

    class _SyncDateTime:
        @staticmethod
        def now(tz=None):
            try:
                barrier.wait(timeout=1)
            except threading.BrokenBarrierError:
                pass
            from datetime import datetime as _RealDateTime
            return _RealDateTime.now(tz)

    with patch("app.api.dialogs.datetime", _SyncDateTime), patch("app.api.dialogs._execute_action_background") as mock_background:
        def _confirm_once():
            return client.post("/api/v1/dialog/resolve-action", json={
                "action_id": action_id,
                "decision": "confirm",
            })

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = [f.result() for f in [pool.submit(_confirm_once), pool.submit(_confirm_once)]]

    statuses = sorted(resp.status_code for resp in responses)
    assert statuses == [200, 409]
    assert mock_background.call_count == 1


def test_resolve_action_confirm_passes_command_args_to_background(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "command_name": "setup",
        "command_args": "主角是植物学家",
    })
    assert r2.status_code == 200
    action_id = r2.json()["pending_action"]["id"]

    with patch("app.api.dialogs._execute_action_background") as mock_background:
        r3 = client.post("/api/v1/dialog/resolve-action", json={
            "action_id": action_id,
            "decision": "confirm",
        })

    assert r3.status_code == 200
    mock_background.assert_called_once()
    assert mock_background.call_args.args[0] == "generate_setup"
    assert mock_background.call_args.kwargs["command_args"] == "主角是植物学家"

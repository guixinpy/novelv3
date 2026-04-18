from unittest.mock import AsyncMock, patch

from app.core.intent_router import IntentRouter
from app.models import Dialog
from app.schemas import ProjectDiagnosisOut


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
    assert user_message["message_type"] == "text"
    assert "meta" in user_message
    assert user_message["meta"] is None

    assistant_message = messages[1]
    assert assistant_message["role"] == "assistant"
    assert assistant_message["message_type"] == "text"
    assert "meta" in assistant_message
    assert assistant_message["meta"] is None


def test_unknown_command_input_round_trips_as_command_message(client):
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

    r3 = client.get(f"/api/v1/dialog/projects/{pid}/messages")
    assert r3.status_code == 200
    messages = r3.json()
    assert all("pending_action" not in m for m in messages)

    user_command = next(m for m in messages if m["role"] == "user")
    assert user_command["content"] == "/unknown_cmd"
    assert user_command["message_type"] == "command"
    assert user_command["meta"] == {
        "command_name": "unknown_cmd",
        "command_args": "--scope history",
    }


def test_compact_replaces_previous_plain_messages_with_summary(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

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
    assert "title" in summary["meta"]
    assert "summary_text" in summary["meta"]

    plain_messages = [m for m in messages if m["message_type"] == "text"]
    assert plain_messages == []


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

@patch("app.api.setups.load_api_key", return_value="sk-test")
@patch("app.api.setups.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.setups.ai_service.parse_json")
def test_resolve_action_confirm(mock_parse, mock_complete, mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
    })
    action_id = r2.json()["pending_action"]["id"]

    mock_complete.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
    mock_parse.return_value = {"world_building": {}, "characters": [], "core_concept": {}}

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

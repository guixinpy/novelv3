from unittest.mock import AsyncMock, patch

from app.core.intent_router import IntentRouter
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
    assert "project_diagnosis" in r2.json()


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
        "target_panel": "setup",
        "status": "pending",
    }
    assert r2.json()["refresh_targets"] == []


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
    assert r3.json()["action_result"]["status"] == "generating"
    assert r3.json()["ui_hint"] == {
        "dialog_state": "RUNNING",
        "target_panel": "setup",
        "status": "running",
    }
    assert r3.json()["refresh_targets"] == []

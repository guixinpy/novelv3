import asyncio
import contextlib
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import event
from sqlalchemy.orm.session import Session as OrmSession

from app.api import dialogs as dialogs_api
from app.core.chat_commands import (
    command_agent_route,
    command_mutates_history,
    command_to_agent_intent_text,
    command_to_agent_tool_name,
    command_to_action_type,
    is_supported_chat_command,
    is_legacy_chat_command,
    public_chat_command_names,
)
from app.core.dialog_agent_routes import DIALOG_AGENT_ROUTE_VERSION, build_dialog_agent_route
from app.core.chat_compaction import build_compaction_summary, select_compactable_plain_messages
from app.core.intent_router import IntentRouter, parse_chapter_index
from app.models import (
    AIModelCallTrace,
    BackgroundTask,
    ChapterContent,
    Dialog,
    DialogMessage,
    Outline,
    PendingAction,
    Project,
    Setup,
    Storyline,
    WritingAgentRun,
    WritingAgentStep,
)
from app.schemas import ProjectDiagnosisOut
from app.services.actions.action_result_service import ActionResultService
from app.services.dialog.messages import DialogMessageService

ORIGINAL_SESSION_COMMIT = OrmSession.commit


def _expected_agent_route(source: str, action_type: str, agent_tool_name: str, *, command_name: str | None = None):
    route = {
        "version": DIALOG_AGENT_ROUTE_VERSION,
        "source": source,
        "action_type": action_type,
        "agent_action_type": agent_tool_name,
        "agent_tool_name": agent_tool_name,
        "requires_confirmation": True,
        "entrypoint": "dialog_pending_action",
    }
    if command_name is not None:
        route["command_name"] = command_name
    return route


def _latest_dialog_route_trace(db_session, project_id: str) -> AIModelCallTrace | None:
    return (
        db_session.query(AIModelCallTrace)
        .filter(
            AIModelCallTrace.project_id == project_id,
            AIModelCallTrace.trace_type == "dialog_route_decision",
        )
        .order_by(AIModelCallTrace.created_at.desc(), AIModelCallTrace.id.desc())
        .first()
    )


def _latest_dialog_agent_route_trace(db_session, project_id: str) -> AIModelCallTrace | None:
    return (
        db_session.query(AIModelCallTrace)
        .filter(
            AIModelCallTrace.project_id == project_id,
            AIModelCallTrace.trace_type == "dialog_agent_route",
        )
        .order_by(AIModelCallTrace.created_at.desc(), AIModelCallTrace.id.desc())
        .first()
    )


def _seed_project_ready_for_chapter_generation(db_session, project_id: str, total_chapters: int = 3) -> None:
    db_session.add(Setup(project_id=project_id, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=project_id, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=project_id,
            status="generated",
            total_chapters=total_chapters,
            chapters=[
                {"chapter_index": chapter_index, "title": f"第{chapter_index}章", "summary": "章节摘要。"}
                for chapter_index in range(1, total_chapters + 1)
            ],
        )
    )
    db_session.commit()


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

    diag4 = ProjectDiagnosisOut(missing_items=["content"], completed_items=["setup", "storyline", "outline"], suggested_next_step="preview_chapter")
    chapter_candidate = router.resolve("请开始写正文，从第1章开始生成", "chatting", None, diag4)
    assert chapter_candidate is not None
    assert chapter_candidate.type == "preview_chapter"
    assert chapter_candidate.params["chapter_index"] == 1


def test_intent_router_projection_explains_setup_route():
    router = IntentRouter()
    diag = ProjectDiagnosisOut(missing_items=["setup"], completed_items=[], suggested_next_step="preview_setup")

    projection = router.project("创建主角设定", "chatting", None, diag).to_dict()

    assert projection["status"] == "matched"
    assert projection["version"] == "phase105.intent_projection.v1"
    assert projection["input"]["normalized_text"] == "创建主角设定"
    assert len(projection["input"]["input_hash"]) == 64
    assert projection["rule_id"] == "setup_intent"
    assert projection["decision"]["rule_id"] == "setup_intent"
    assert projection["decision"]["reason_code"] == "intent_rule_matched"
    assert projection["decision"]["match_evidence"] == [{"kind": "pattern", "name": "setup_phrase"}]
    assert projection["candidate"] == {"type": "preview_setup", "params": {"project_id": ""}}
    assert projection["agent_route"] == _expected_agent_route(
        "text_intent",
        "preview_setup",
        "generate_setup",
    )
    assert projection["tool_selection"] == {
        "selected_tool": "generate_setup",
        "why_this_tool": "dialog_action_to_agent_tool.preview_setup",
        "availability_checked": False,
    }
    assert {"code": "requires_confirmation", "passed": True} in projection["preconditions"]
    assert projection["diagnosis"]["missing_items"] == ["setup"]
    assert projection["extracted_params"] == {}


def test_intent_router_projection_explains_chapter_route():
    router = IntentRouter()
    diag = ProjectDiagnosisOut(
        missing_items=[],
        completed_items=["setup", "storyline", "outline"],
        suggested_next_step="preview_chapter",
    )

    projection = router.project("请开始写正文，从第3章开始生成。", "chatting", None, diag).to_dict()

    assert projection["status"] == "matched"
    assert projection["rule_id"] == "chapter_intent"
    assert projection["decision"]["rule_id"] == "chapter_intent"
    assert projection["decision"]["match_evidence"] == [{"kind": "pattern", "name": "chapter_generation_phrase"}]
    assert projection["candidate"] == {
        "type": "preview_chapter",
        "params": {"chapter_index": 3, "chapter_index_source": "explicit_user"},
    }
    assert projection["agent_route"] == _expected_agent_route(
        "text_intent",
        "preview_chapter",
        "generate_chapter",
    )
    assert projection["extracted_params"] == {"chapter_index": 3, "chapter_index_source": "explicit_user"}
    assert {"code": "outline_completed", "passed": True} in projection["preconditions"]
    assert projection["trace"]["projection_id"].startswith("intent:")


def test_intent_router_low_detail_continue_uses_chapter_when_outline_ready():
    router = IntentRouter()
    diagnosis = ProjectDiagnosisOut(
        missing_items=["content"],
        completed_items=["setup", "storyline", "outline"],
        suggested_next_step="preview_chapter",
    )

    candidate = router.resolve("继续吧", "chatting", None, diagnosis)

    assert candidate is not None
    assert candidate.type == "preview_chapter"
    assert candidate.params["chapter_index"] == 1


def test_intent_router_next_chapter_phrase_uses_chapter_when_outline_ready():
    router = IntentRouter()
    diagnosis = ProjectDiagnosisOut(
        missing_items=["content"],
        completed_items=["setup", "storyline", "outline"],
        suggested_next_step="preview_chapter",
    )

    candidate = router.resolve("下一章", "chatting", None, diagnosis)

    assert candidate is not None
    assert candidate.type == "preview_chapter"
    assert candidate.params["chapter_index"] == 1
    assert candidate.params["chapter_index_source"] == "router_default"


def test_intent_router_review_phrase_routes_to_preview_review():
    router = IntentRouter()
    diagnosis = ProjectDiagnosisOut(
        missing_items=[],
        completed_items=["setup", "storyline", "outline", "content"],
        suggested_next_step="preview_chapter",
    )

    candidate = router.resolve("审稿第2章并给出修订计划", "chatting", None, diagnosis)

    assert candidate is not None
    assert candidate.type == "preview_review"
    assert candidate.params["chapter_index"] == 2
    assert candidate.params["chapter_index_source"] == "explicit_user"


def test_intent_router_recovery_phrase_routes_to_preview_recovery():
    router = IntentRouter()
    diagnosis = ProjectDiagnosisOut(
        missing_items=[],
        completed_items=["setup", "storyline", "outline"],
        suggested_next_step="preview_chapter",
    )

    candidate = router.resolve("恢复上一轮阻塞的写作任务", "chatting", None, diagnosis)

    assert candidate is not None
    assert candidate.type == "preview_recovery"
    assert candidate.params == {}


def test_intent_router_projection_reports_no_match():
    router = IntentRouter()
    diag = ProjectDiagnosisOut(missing_items=["setup"], completed_items=[], suggested_next_step="preview_setup")

    projection = router.project("随便聊聊", "chatting", None, diag).to_dict()

    assert projection["status"] == "no_match"
    assert projection["rule_id"] is None
    assert projection["reason"] == "no_intent_rule_matched"
    assert projection["decision"]["reason_code"] == "no_intent_rule_matched"
    assert projection["candidate"] is None
    assert projection["agent_route"] is None
    assert projection["tool_selection"] == {
        "selected_tool": None,
        "why_this_tool": None,
        "availability_checked": False,
    }
    assert {"rule_id": "setup_intent", "reason_code": "intent_pattern_not_matched"} in projection["rejected_candidates"]


def test_intent_router_no_match():
    router = IntentRouter()
    diag = ProjectDiagnosisOut(missing_items=["setup"], completed_items=[], suggested_next_step="preview_setup")
    assert router.resolve("随便聊聊", "chatting", None, diag) is None


def test_chat_command_registry_helpers_cover_expected_commands():
    assert public_chat_command_names() == ["continue", "status", "clear", "compact"]

    for command_name in ("continue", "status", "clear", "compact", "setup", "storyline", "outline", "chapter"):
        assert is_supported_chat_command(command_name) is True

    assert command_mutates_history("continue") is False
    assert command_mutates_history("status") is False
    assert command_mutates_history("clear") is True
    assert command_mutates_history("compact") is True
    assert command_mutates_history("setup") is False
    assert command_mutates_history("storyline") is False
    assert command_mutates_history("outline") is False
    assert command_mutates_history("chapter") is False

    assert command_to_agent_intent_text("continue") == "继续"
    assert command_to_agent_intent_text("status") == "接下来做什么"

    assert command_to_action_type("setup") is None
    assert command_to_action_type("storyline") is None
    assert command_to_action_type("outline") is None
    assert command_to_action_type("chapter") is None
    assert command_to_action_type("clear") is None
    assert command_to_action_type("compact") is None

    assert command_to_agent_tool_name("setup") is None
    assert command_to_agent_tool_name("storyline") is None
    assert command_to_agent_tool_name("outline") is None
    assert command_to_agent_tool_name("chapter") is None
    assert command_to_agent_tool_name("clear") is None
    assert command_to_agent_tool_name("compact") is None

    assert is_legacy_chat_command("setup") is True
    assert is_legacy_chat_command("chapter") is True
    assert is_legacy_chat_command("continue") is False
    assert command_agent_route("setup") is None
    assert command_agent_route("chapter") is None
    assert command_agent_route("clear") is None


def test_chat_command_catalog_endpoint_returns_agent_control_surface(client):
    response = client.get("/api/v1/dialog/chat-commands")

    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "phase27.agent_chat_command_catalog.v1"
    assert data["public_command_names"] == ["continue", "status", "clear", "compact"]
    assert data["legacy_alias_names"] == ["setup", "storyline", "outline", "chapter"]
    commands = {command["name"]: command for command in data["commands"]}
    assert commands["continue"]["public"] is True
    assert commands["continue"]["legacy"] is False
    assert commands["continue"]["supports_args"] is False
    assert commands["continue"]["category"] == "agent_control"
    assert commands["continue"]["capability_id"] == "agent.continue"
    assert commands["continue"]["control_projection_type"] == "continue_agent_control"
    assert commands["continue"]["required_agent_tools"] == [
        "inspect_agent_health_projection",
        "inspect_agent_command_contracts",
        "plan_recovery_tools",
        "plan_recommended_followups",
        "prepare_generate_chapter_execution",
    ]
    assert commands["continue"]["available"] is True
    assert commands["continue"]["unavailable_reasons"] == []
    assert commands["continue"]["agent_intent_text"] == "继续"
    assert commands["status"]["control_projection_type"] == "agent_health_projection"
    assert commands["status"]["required_agent_tools"] == [
        "inspect_agent_health_projection",
        "inspect_agent_command_contracts",
    ]
    assert commands["clear"]["control_projection_type"] == ""
    assert commands["setup"]["public"] is False
    assert commands["setup"]["legacy"] is True
    assert commands["setup"]["supports_args"] is True
    assert commands["setup"]["control_projection_type"] == ""
    assert "action_type" not in commands["setup"]


def test_agent_route_approval_opt_in_metadata_is_explicit():
    expected_default = _expected_agent_route(
        "slash_command",
        "preview_setup",
        "generate_setup",
        command_name="setup",
    )
    assert build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup") == expected_default
    assert command_agent_route("setup") is None

    explicit_route = build_dialog_agent_route(
        "preview_setup",
        source="slash_command",
        command_name="setup",
        use_agent_approval_chain=True,
    )

    assert explicit_route == {**expected_default, "use_agent_approval_chain": True}


def test_dialog_control_plane_agent_route_approval_opt_in_metadata_routes_prepare_tool(db_session):
    from app.services.writing_agent.dialog_control_plane import prepare_dialog_agent_run_dispatch

    project = Project(name="Agent Route Approval Opt In Metadata")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)
    route = build_dialog_agent_route(
        "preview_setup",
        source="slash_command",
        command_name="setup",
        use_agent_approval_chain=True,
    )

    dispatch = prepare_dialog_agent_run_dispatch(
        db_session,
        project_id=project.id,
        dialog_id=dialog.id,
        action_type="generate_setup",
        command_args="雾港悬疑",
        action_params={"project_id": project.id, "agent_route": route},
    )

    run_tool = dispatch.run.input["tools"][0]
    task_tool = dispatch.task.payload["tools"][0]
    assert run_tool["tool_name"] == "prepare_generate_setup_execution"
    assert task_tool["tool_name"] == "prepare_generate_setup_execution"
    assert run_tool["params"] == {}
    assert task_tool["params"] == {}


def test_dialog_control_plane_agent_route_approval_opt_in_false_cannot_bypass_setup_prepare(db_session):
    from app.services.writing_agent.dialog_control_plane import prepare_dialog_agent_run_dispatch

    project = Project(name="Agent Route Approval Opt In Override")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)
    route = build_dialog_agent_route(
        "preview_setup",
        source="slash_command",
        command_name="setup",
        use_agent_approval_chain=True,
    )

    dispatch = prepare_dialog_agent_run_dispatch(
        db_session,
        project_id=project.id,
        dialog_id=dialog.id,
        action_type="generate_setup",
        command_args="雾港悬疑",
        action_params={
            "project_id": project.id,
            "agent_route": route,
            "use_agent_approval_chain": False,
        },
    )

    run_tool = dispatch.run.input["tools"][0]
    task_tool = dispatch.task.payload["tools"][0]
    assert run_tool["tool_name"] == "prepare_generate_setup_execution"
    assert task_tool["tool_name"] == "prepare_generate_setup_execution"
    assert run_tool["params"] == {}
    assert task_tool["params"] == {}


def test_chapter_command_leading_index_wins_over_context_mentions(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    _seed_project_ready_for_chapter_generation(db_session, pid)

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "command_name": "chapter",
        "command_args": "2 第二章承接第1章的原始记忆芯片",
    })

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"]["params"]["chapter_index"] == 2
    assert body["pending_action"]["params"]["agent_route"] == _expected_agent_route(
        "text_intent",
        "preview_chapter",
        "generate_chapter",
    )
    assert "第2章正文" in body["pending_action"]["description"]


def test_chapter_command_without_index_uses_first_unwritten_outline_chapter(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(
        Outline(
            project_id=pid,
            status="generated",
            total_chapters=2,
            chapters=[
                {"chapter_index": 1, "title": "旧灯塔", "summary": "林舟开始调查。"},
                {"chapter_index": 2, "title": "雨夜证词", "summary": "林舟追查新的证词。"},
            ],
        )
    )
    db_session.add(
        ChapterContent(
            project_id=pid,
            chapter_index=1,
            title="旧灯塔",
            content="第一章正文",
            status="generated",
        )
    )
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "command_name": "chapter",
    })

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"]["params"]["chapter_index"] == 2
    assert body["pending_action"]["params"]["agent_route"] == _expected_agent_route(
        "text_intent",
        "preview_chapter",
        "generate_chapter",
    )


def test_chapter_command_explicit_reserved_target_adds_conflict_warning(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(
        Outline(
            project_id=pid,
            status="generated",
            total_chapters=2,
            chapters=[
                {"chapter_index": 1, "title": "一", "summary": "一"},
                {"chapter_index": 2, "title": "二", "summary": "二"},
            ],
        )
    )
    db_session.add(
        BackgroundTask(
            project_id=pid,
            task_type="writing_agent_run",
            status="running",
            payload={"action_type": "generate_chapter", "tools": [{"params": {"chapter_index": 2}}]},
        )
    )
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "command_name": "chapter",
        "command_args": "2",
    })

    assert r2.status_code == 200
    pending = r2.json()["pending_action"]
    assert pending["params"]["chapter_index"] == 2
    assert pending["params"]["chapter_target_conflict"] == {
        "status": "reserved",
        "chapter_index": 2,
        "reason": "pending_or_running_generation",
        "source": "single_task",
        "source_label": "单章生成任务",
    }
    assert "已有单章生成任务" in pending["description"]


def test_chapter_command_explicit_range_reserved_target_labels_conflict_source(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    _seed_project_ready_for_chapter_generation(db_session, pid)
    db_session.add(
        BackgroundTask(
            project_id=pid,
            task_type="generate_chapter_range",
            status="running",
            payload={"chapter_range": {"start": 2, "end": 3}},
        )
    )
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "command_name": "chapter",
        "command_args": "2",
    })

    assert r2.status_code == 200
    pending = r2.json()["pending_action"]
    assert pending["params"]["chapter_target_conflict"] == {
        "status": "reserved",
        "chapter_index": 2,
        "reason": "pending_or_running_generation",
        "source": "range_task",
        "source_label": "批量生成任务",
    }
    assert "已有批量生成任务" in pending["description"]


def test_resolve_chapter_conflict_confirmation_records_decision_metadata(client, db_session):
    project_id = client.post("/api/v1/projects", json={"name": "Chapter Conflict Audit"}).json()["id"]
    _seed_project_ready_for_chapter_generation(db_session, project_id)
    db_session.add(
        BackgroundTask(
            project_id=project_id,
            task_type="generate_chapter_range",
            status="running",
            payload={"chapter_range": {"start": 2, "end": 3}},
        )
    )
    db_session.commit()
    pending = client.post(
        "/api/v1/dialog/chat",
        json={
            "project_id": project_id,
            "input_type": "command",
            "command_name": "chapter",
            "command_args": "2",
        },
    ).json()["pending_action"]

    with patch("app.api.dialogs.LocalTaskRunner.start"):
        response = client.post(
            "/api/v1/dialog/resolve-action",
            json={"action_id": pending["id"], "decision": "confirm"},
        )

    assert response.status_code == 200
    decision = response.json()["action_result"]["data"]["approval_decision"]
    assert decision["chapter_target_conflict"] == {
        "status": "reserved",
        "chapter_index": 2,
        "reason": "pending_or_running_generation",
        "source": "range_task",
        "source_label": "批量生成任务",
    }
    detail_items = response.json()["action_result_view"]["detail_items"]
    assert {"label": "章节冲突", "value": "批量生成任务"} in detail_items


def test_agent_control_plane_routes_confirmed_setup_through_writing_agent_run(client, db_session, monkeypatch):
    started_task_ids: list[str] = []

    def fake_start(self, task_id, work):
        started_task_ids.append(task_id)
        return None

    monkeypatch.setattr("app.api.dialogs.LocalTaskRunner.start", fake_start)
    project_id = client.post("/api/v1/projects", json={"name": "Agent Control Plane"}).json()["id"]
    pending = client.post(
        "/api/v1/dialog/chat",
        json={
            "project_id": project_id,
            "input_type": "command",
            "command_name": "setup",
            "command_args": "雾港悬疑，主角是记忆取证师",
        },
    ).json()["pending_action"]
    assert pending["params"]["agent_route"]["agent_tool_name"] == "generate_setup"
    assert pending["params"]["agent_route"]["agent_action_type"] == "generate_setup"
    dialog = db_session.query(Dialog).filter_by(project_id=project_id, dialog_type="hermes").one()
    request_message = (
        db_session.query(DialogMessage)
        .filter(DialogMessage.dialog_id == dialog.id, DialogMessage.role == "user")
        .order_by(DialogMessage.created_at.desc(), DialogMessage.id.desc())
        .first()
    )
    response_message = (
        db_session.query(DialogMessage)
        .filter(DialogMessage.dialog_id == dialog.id, DialogMessage.role == "assistant")
        .order_by(DialogMessage.created_at.desc(), DialogMessage.id.desc())
        .first()
    )
    route_trace = _latest_dialog_agent_route_trace(db_session, project_id)
    assert route_trace is not None
    assert route_trace.status == "success"
    assert route_trace.model == "local-dialog-router"
    assert route_trace.dialog_id == dialog.id
    assert route_trace.request_message_id == request_message.id
    assert route_trace.response_message_id == response_message.id
    assert route_trace.trace_metadata["agent_route"] == pending["params"]["agent_route"]
    assert route_trace.trace_metadata["action_type"] == "preview_setup"
    assert route_trace.trace_metadata["source"] == "text_intent"
    assert route_trace.trace_metadata["command_name"] == "setup"
    assert route_trace.trace_metadata["pending_action_id"] == pending["id"]

    response = client.post(
        "/api/v1/dialog/resolve-action",
        json={"action_id": pending["id"], "decision": "confirm"},
    )

    body = response.json()
    run = db_session.query(WritingAgentRun).filter_by(project_id=project_id).one()
    task = db_session.query(BackgroundTask).filter_by(id=body["action_result"]["data"]["task_id"]).one()
    assert response.status_code == 200
    assert body["action_result"]["type"] == "generate_setup"
    assert body["action_result"]["data"]["agent_run_id"] == run.id
    assert body["action_result"]["data"]["task_id"] == task.id
    assert body["action_result"]["data"]["control_plane"]["version"] == "phase65.agent_control_plane.v1"
    assert run.entrypoint == "dialog_pending_action"
    assert run.dialog_id is not None
    assert run.background_task_id == task.id
    assert run.input["control_plane"]["version"] == "phase65.agent_control_plane.v1"
    assert run.input["control_plane"]["source"] == "dialog_pending_action"
    assert run.input["tools"][0]["tool_name"] == "prepare_generate_setup_execution"
    assert run.input["tools"][0]["command_args"] == "雾港悬疑，主角是记忆取证师"
    assert "agent_route" not in run.input["tools"][0]["params"]
    assert task.task_type == "writing_agent_run"
    assert task.payload["agent_run_id"] == run.id
    assert task.payload["action_type"] == "generate_setup"
    assert started_task_ids == [task.id]


def test_pending_action_exposes_route_opt_in_safety_view_without_contract_hash(client):
    project_id = client.post("/api/v1/projects", json={"name": "Agent Safety View"}).json()["id"]

    response = client.post(
        "/api/v1/dialog/chat",
        json={
            "project_id": project_id,
            "input_type": "command",
            "command_name": "setup",
            "command_args": "雾港悬疑",
        },
    )

    assert response.status_code == 200
    pending = response.json()["pending_action"]
    safety_view = pending["safety_view"]
    recommendation = safety_view["recommendations"][0]
    assert safety_view["kind"] == "pending_action_safety"
    assert recommendation["kind"] == "route_upgrade_preview"
    assert recommendation["title"] == "可先生成路由升级审批契约"
    assert recommendation["message"] == "这只生成审批准备信息，不会执行当前待确认操作。"
    assert recommendation["severity"] == "info"
    assert recommendation["auto_execute"] is False
    assert recommendation["guarded_apply"] is False
    assert recommendation["action"] == {
        "kind": "prepare_route_upgrade_contract",
        "label": "生成审批契约",
        "pending_action_id": pending["id"],
        "auto_execute": False,
        "guarded_apply": False,
    }
    assert "approval:" not in str(safety_view)
    assert "approval_contract" not in str(safety_view)
    assert "params_diff" not in str(safety_view)
    assert "route_before" not in str(safety_view)
    assert "route_after" not in str(safety_view)
    assert "apply_pending_action_route_approval_opt_in" not in str(safety_view)
    assert "preview_pending_action_route_approval_opt_in_apply_contract" not in str(safety_view)

    messages = client.get(f"/api/v1/dialog/projects/{project_id}/messages").json()
    assert messages[-1]["pending_action"]["safety_view"] == safety_view


@pytest.mark.parametrize(
    ("action_type", "params"),
    [
        ("preview_setup", {}),
        (
            "preview_setup",
            {
                "agent_route": {"agent_tool_name": "generate_setup"},
                "use_agent_approval_chain": False,
            },
        ),
        (
            "preview_setup",
            {"agent_route": {"agent_tool_name": "generate_setup", "use_agent_approval_chain": True}},
        ),
        ("preview_setup", {"agent_route": {"source": "slash_command"}}),
        ("", {"agent_route": {"agent_tool_name": "generate_setup"}}),
    ],
)
def test_pending_action_safety_view_omits_non_upgradeable_routes(action_type, params):
    from app.services.actions.pending_action_projection import pending_action_safety_view

    assert pending_action_safety_view(action_type, params, pending_action_id="pending-1") is None


def test_pending_action_safety_view_omits_action_without_pending_action_id():
    from app.services.actions.pending_action_projection import pending_action_safety_view

    view = pending_action_safety_view(
        "preview_setup",
        {"agent_route": {"agent_tool_name": "generate_setup"}},
        pending_action_id="",
    )

    assert view is not None
    recommendation = view["recommendations"][0]
    assert "action" not in recommendation


def test_dialog_control_plane_setup_route_defaults_to_prepare_even_without_approval_opt_in(db_session):
    from app.services.writing_agent.dialog_control_plane import prepare_dialog_agent_run_dispatch

    project = Project(name="Dialog Approval Opt In Default")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)

    dispatch = prepare_dialog_agent_run_dispatch(
        db_session,
        project_id=project.id,
        dialog_id=dialog.id,
        action_type="generate_setup",
        command_args="雾港悬疑",
        action_params={"project_id": project.id, "use_agent_approval_chain": False},
    )

    run_tool = dispatch.run.input["tools"][0]
    task_tool = dispatch.task.payload["tools"][0]
    assert run_tool["tool_name"] == "prepare_generate_setup_execution"
    assert task_tool["tool_name"] == "prepare_generate_setup_execution"
    assert "use_agent_approval_chain" not in run_tool["params"]
    assert "use_agent_approval_chain" not in task_tool["params"]


@pytest.mark.parametrize(
    ("action_type", "command_args", "expected_tool_name"),
    [
        ("generate_setup", "雾港悬疑", "prepare_generate_setup_execution"),
        ("generate_storyline", "双线叙事", "prepare_generate_storyline_execution"),
        ("generate_outline", "每章留钩子", "prepare_generate_outline_execution"),
    ],
)
def test_dialog_control_plane_approval_chain_opt_in_routes_to_prepare_tool(
    db_session,
    action_type,
    command_args,
    expected_tool_name,
):
    from app.services.writing_agent.dialog_control_plane import prepare_dialog_agent_run_dispatch

    project = Project(name=f"Dialog Approval Opt In {action_type}")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)

    dispatch = prepare_dialog_agent_run_dispatch(
        db_session,
        project_id=project.id,
        dialog_id=dialog.id,
        action_type=action_type,
        command_args=command_args,
        action_params={
            "project_id": project.id,
            "agent_route": {"source": "test"},
            "use_agent_approval_chain": True,
            "user_note": "保留给工具的普通参数",
        },
    )

    run_tool = dispatch.run.input["tools"][0]
    task_tool = dispatch.task.payload["tools"][0]
    assert run_tool["tool_name"] == expected_tool_name
    assert task_tool["tool_name"] == expected_tool_name
    assert run_tool["params"] == {"user_note": "保留给工具的普通参数"}
    assert task_tool["params"] == {"user_note": "保留给工具的普通参数"}


def test_text_intent_creates_pending_setup_action(client, db_session):
    project_id = client.post("/api/v1/projects", json={"name": "Text Intent Agent"}).json()["id"]
    text = "创建主角设定，主角是植物学家"

    response = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": project_id, "input_type": "text", "text": text},
    )

    body = response.json()
    dialog = db_session.query(Dialog).filter_by(project_id=project_id).one()
    pending = db_session.query(PendingAction).filter_by(dialog_id=dialog.id).one()
    assert response.status_code == 200
    assert body["pending_action"]["type"] == "preview_setup"
    assert body["pending_action"]["params"]["project_id"] == project_id
    assert body["pending_action"]["params"]["command_args"] == text
    assert body["pending_action"]["params"]["agent_route"] == _expected_agent_route(
        "text_intent",
        "preview_setup",
        "generate_setup",
    )
    assert pending.type == "preview_setup"
    assert pending.params["project_id"] == project_id
    assert pending.params["command_args"] == text
    assert pending.params["agent_route"] == _expected_agent_route(
        "text_intent",
        "preview_setup",
        "generate_setup",
    )
    assert dialog.state == "pending_action"


def test_text_intent_confirm_routes_to_agent_run(client, db_session, monkeypatch):
    started_task_ids: list[str] = []

    def fake_start(self, task_id, work):
        started_task_ids.append(task_id)
        return None

    monkeypatch.setattr("app.api.dialogs.LocalTaskRunner.start", fake_start)
    project_id = client.post("/api/v1/projects", json={"name": "Text Intent Confirm"}).json()["id"]
    text = "创建主角设定，主角是植物学家"
    pending = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": project_id, "input_type": "text", "text": text},
    ).json()["pending_action"]

    response = client.post(
        "/api/v1/dialog/resolve-action",
        json={"action_id": pending["id"], "decision": "confirm"},
    )

    body = response.json()
    run = db_session.query(WritingAgentRun).filter_by(project_id=project_id).one()
    assert response.status_code == 200
    assert body["action_result"]["data"]["agent_run_id"] == run.id
    assert run.entrypoint == "dialog_pending_action"
    assert run.input["tools"][0]["tool_name"] == "prepare_generate_setup_execution"
    assert run.input["tools"][0]["command_args"] == text
    assert "agent_route" not in run.input["tools"][0]["params"]
    assert started_task_ids == [body["action_result"]["data"]["task_id"]]


def test_text_intent_confirm_routes_review_to_planned_agent_run(client, db_session, monkeypatch):
    started_task_ids: list[str] = []

    def fake_start(self, task_id, work):
        started_task_ids.append(task_id)
        return None

    monkeypatch.setattr("app.api.dialogs.LocalTaskRunner.start", fake_start)
    project_id = client.post("/api/v1/projects", json={"name": "Text Intent Review"}).json()["id"]
    db_session.add(Setup(project_id=project_id, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=project_id, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=project_id,
            status="generated",
            total_chapters=2,
            chapters=[{"chapter_index": 2, "title": "雾中人", "summary": "线索指向失踪档案。"}],
        )
    )
    db_session.add(
        ChapterContent(
            project_id=project_id,
            chapter_index=2,
            title="雾中人",
            content="林深在雾里追上失踪档案的线索。",
            status="generated",
        )
    )
    db_session.commit()

    pending = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": project_id, "input_type": "text", "text": "审稿第2章并给出修订计划"},
    ).json()["pending_action"]
    response = client.post(
        "/api/v1/dialog/resolve-action",
        json={"action_id": pending["id"], "decision": "confirm"},
    )

    body = response.json()
    run = db_session.query(WritingAgentRun).filter_by(project_id=project_id).one()
    assert response.status_code == 200
    assert pending["type"] == "preview_review"
    assert pending["params"]["agent_route"]["agent_tool_name"] == "plan_writing_agent_run"
    assert body["action_result"]["type"] == "review_chapter"
    assert body["action_result"]["data"]["agent_run_id"] == run.id
    assert run.input["planner"]["intent_class"] == "review_chapter"
    assert [tool["tool_name"] for tool in run.input["tools"]] == [
        "describe_agent_tools",
        "review_chapter_quality",
        "review_chapter_continuity",
        "plan_chapter_revision",
    ]
    assert [tool["params"].get("chapter_index") for tool in run.input["tools"][1:]] == [2, 2, 2]
    assert started_task_ids == [body["action_result"]["data"]["task_id"]]


def test_text_intent_confirm_routes_recovery_to_planned_agent_run(client, db_session, monkeypatch):
    started_task_ids: list[str] = []

    def fake_start(self, task_id, work):
        started_task_ids.append(task_id)
        return None

    monkeypatch.setattr("app.api.dialogs.LocalTaskRunner.start", fake_start)
    project_id = client.post("/api/v1/projects", json={"name": "Text Intent Recovery"}).json()["id"]
    db_session.add(Setup(project_id=project_id, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=project_id, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=project_id,
            status="generated",
            total_chapters=2,
            chapters=[{"chapter_index": 2, "title": "雾中人", "summary": "线索指向失踪档案。"}],
        )
    )
    blocked_run = WritingAgentRun(
        project_id=project_id,
        goal="阻塞的直接章节执行",
        status="blocked",
        entrypoint="api",
        input={},
    )
    db_session.add(blocked_run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=blocked_run.id,
            project_id=project_id,
            step_index=1,
            tool_name="execute_generate_chapter_with_approval",
            status="blocked",
            input={"params": {"chapter_index": 2}},
            output={
                "status": "blocked",
                "agent_tool_result": {
                    "recovery": {
                        "status": "recommended",
                        "source_tool": "execute_generate_chapter_with_approval",
                        "reason_code": "resource_binding_target_mismatch",
                        "next_tool": "prepare_generate_chapter_execution",
                        "next_params": {"chapter_index": 2},
                    }
                },
            },
        )
    )
    db_session.commit()

    pending = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": project_id, "input_type": "text", "text": "恢复上一轮阻塞的写作任务"},
    ).json()["pending_action"]
    response = client.post(
        "/api/v1/dialog/resolve-action",
        json={"action_id": pending["id"], "decision": "confirm"},
    )

    body = response.json()
    run = (
        db_session.query(WritingAgentRun)
        .filter(WritingAgentRun.project_id == project_id, WritingAgentRun.entrypoint == "dialog_pending_action")
        .one()
    )
    assert response.status_code == 200
    assert pending["type"] == "preview_recovery"
    assert pending["params"]["agent_route"]["agent_tool_name"] == "plan_writing_agent_run"
    assert body["action_result"]["type"] == "recover_blocked_run"
    assert body["action_result"]["data"]["agent_run_id"] == run.id
    assert run.input["planner"]["intent_class"] == "recover_blocked_run"
    assert [tool["tool_name"] for tool in run.input["tools"]] == ["describe_agent_tools", "plan_recovery_tools"]
    assert run.input["tools"][1]["params"] == {"run_id": blocked_run.id}
    assert started_task_ids == [body["action_result"]["data"]["task_id"]]


def test_text_intent_preserves_regular_chat(client, db_session):
    project_id = client.post("/api/v1/projects", json={"name": "Text Intent Chat"}).json()["id"]

    response = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": project_id, "input_type": "text", "text": "随便聊聊"},
    )

    body = response.json()
    dialog = db_session.query(Dialog).filter_by(project_id=project_id).one()
    assert response.status_code == 200
    assert body["pending_action"] is None
    assert dialog.state != "pending_action"
    assert db_session.query(PendingAction).filter_by(dialog_id=dialog.id).count() == 0


def test_text_intent_query_diagnosis_does_not_create_pending_action(client, db_session):
    project_id = client.post("/api/v1/projects", json={"name": "Text Intent Diagnosis"}).json()["id"]

    response = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": project_id, "input_type": "text", "text": "接下来做什么"},
    )

    body = response.json()
    dialog = db_session.query(Dialog).filter_by(project_id=project_id).one()
    assert response.status_code == 200
    assert body["pending_action"] is None
    assert "目前项目还缺少" in body["message"]
    assert dialog.state != "pending_action"
    assert db_session.query(PendingAction).filter_by(dialog_id=dialog.id).count() == 0


@pytest.mark.asyncio
async def test_agent_control_plane_background_work_records_terminal_dialog_message(db_session, monkeypatch):
    project = Project(name="Agent Control Plane Work")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)

    from app.schemas.writing_agent import WritingAgentRunCreate, WritingAgentToolRequest
    from app.services.tasks.background_task_service import BackgroundTaskService
    from app.services.writing_agent.dialog_control_plane import (
        CONTROL_PLANE_VERSION,
        build_dialog_agent_run_background_work,
    )
    from app.services.writing_agent.run_service import WritingAgentRunService

    tools = [WritingAgentToolRequest(tool_name="prepare_generate_setup_execution", command_args="雾港悬疑")]
    run = WritingAgentRunService(db_session).create_run(
        project.id,
        WritingAgentRunCreate(
            goal="通过对话确认执行 generate_setup",
            entrypoint="dialog_pending_action",
            tools=tools,
            input={"control_plane": {"version": CONTROL_PLANE_VERSION}},
        ),
        effective_tools=tools,
        dialog_id=dialog.id,
    )
    task = BackgroundTaskService(db_session).create(
        project_id=project.id,
        task_type="writing_agent_run",
        payload={"agent_run_id": run.id},
    )
    run.background_task_id = task.id
    db_session.commit()

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        return {"status": "success", "trace_id": None}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)
    work = build_dialog_agent_run_background_work(
        run_id=run.id,
        tools=[tool.model_dump() for tool in tools],
        dialog_id=dialog.id,
        action_type="generate_setup",
        command_args="雾港悬疑",
        action_params={"project_id": project.id},
    )

    result = await work(db_session, task)

    terminal = db_session.query(DialogMessage).filter_by(dialog_id=dialog.id, role="assistant").one()
    saved_run = db_session.query(WritingAgentRun).filter_by(id=run.id).one()
    assert result["agent_run_id"] == run.id
    assert result["status"] == "approval_required"
    assert saved_run.status == "success"
    assert terminal.action_result["type"] == "generate_setup"
    assert terminal.action_result["status"] == "approval_required"
    assert terminal.action_result["data"]["agent_run_id"] == run.id
    assert terminal.action_result["data"]["background_task_id"] == task.id
    assert terminal.action_result["data"]["control_plane"]["version"] == CONTROL_PLANE_VERSION
    assert "steps" not in terminal.action_result["data"]


@pytest.mark.asyncio
async def test_agent_control_plane_background_work_records_blocked_dialog_message(db_session):
    project = Project(name="Agent Control Plane Blocked")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)

    from app.schemas.writing_agent import WritingAgentRunCreate, WritingAgentToolRequest
    from app.services.tasks.background_task_service import BackgroundTaskService
    from app.services.writing_agent.dialog_control_plane import (
        CONTROL_PLANE_VERSION,
        build_dialog_agent_run_background_work,
    )
    from app.services.writing_agent.run_service import WritingAgentRunService

    tools = [WritingAgentToolRequest(tool_name="preflight_writing", params={"chapter_index": 1})]
    run = WritingAgentRunService(db_session).create_run(
        project.id,
        WritingAgentRunCreate(
            goal="通过对话确认执行 generate_setup",
            entrypoint="dialog_pending_action",
            tools=tools,
            input={"control_plane": {"version": CONTROL_PLANE_VERSION}},
        ),
        effective_tools=tools,
        dialog_id=dialog.id,
    )
    task = BackgroundTaskService(db_session).create(
        project_id=project.id,
        task_type="writing_agent_run",
        payload={"agent_run_id": run.id},
    )
    run.background_task_id = task.id
    db_session.commit()
    work = build_dialog_agent_run_background_work(
        run_id=run.id,
        tools=[tool.model_dump() for tool in tools],
        dialog_id=dialog.id,
        action_type="generate_setup",
        command_args=None,
        action_params={"project_id": project.id},
    )

    result = await work(db_session, task)

    terminal = db_session.query(DialogMessage).filter_by(dialog_id=dialog.id, role="system").one()
    assert result["status"] == "blocked"
    assert terminal.action_result["status"] == "blocked"
    assert terminal.action_result["data"]["agent_run_id"] == run.id
    assert terminal.action_result["data"]["control_plane"]["version"] == CONTROL_PLANE_VERSION


def test_parse_chapter_index_uses_earliest_chapter_mention():
    assert parse_chapter_index("继续写第二章，承接第1章") == 2
    assert parse_chapter_index("写第二章承接第1章的原始记忆芯片") == 2
    assert parse_chapter_index("生成第2章，呼应第一章") == 2


@pytest.mark.asyncio
@patch("app.api.chapters.create_or_replace_chapter", new_callable=AsyncMock)
async def test_execute_chapter_action_passes_command_args_as_generation_feedback(mock_create_chapter, db_session):
    mock_create_chapter.return_value = SimpleNamespace()

    result = await dialogs_api._execute_action(
        "generate_chapter",
        "project-1",
        db_session,
        command_args="2 每章约1800-2200字，结尾有钩子",
        action_params={"chapter_index": 2},
    )

    assert result == {"status": "success", "chapter_index": 2}
    mock_create_chapter.assert_awaited_once_with(
        db_session,
        "project-1",
        2,
        extra_feedback="2 每章约1800-2200字，结尾有钩子",
    )


@pytest.mark.asyncio
@patch("app.api.chapters.create_or_replace_chapter", new_callable=AsyncMock)
async def test_execute_chapter_action_returns_athena_analysis_skip_notice(mock_create_chapter, db_session):
    mock_create_chapter.return_value = SimpleNamespace(
        athena_analysis_result={
            "status": "skipped",
            "reason": "missing_world_model_profile",
            "chapter_index": 1,
            "proposal_bundle_id": None,
            "created": {"proposal_items": 0},
            "skipped": {"duplicates": 0},
        }
    )

    result = await dialogs_api._execute_action(
        "generate_chapter",
        "project-1",
        db_session,
        action_params={"chapter_index": 1},
    )

    assert result["status"] == "success"
    assert result["athena_analysis"]["status"] == "skipped"
    assert result["athena_analysis"]["reason"] == "missing_world_model_profile"


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


@pytest.mark.asyncio
async def test_compaction_fallback_summary_keeps_goal_action_diagnosis_and_command_args():
    class BrokenAIService:
        async def complete(self, *args, **kwargs):
            raise RuntimeError("boom")

    messages = [
        SimpleNamespace(
            role="user",
            content="我想先把这个项目做成硬科幻世界观。",
            action_result=None,
            meta=None,
        ),
        SimpleNamespace(
            role="assistant",
            content="已收到你的请求。确认要执行吗？\n附加要求：主角是植物学家。",
            action_result=None,
            meta=None,
        ),
        SimpleNamespace(
            role="system",
            content="操作已确认，正在生成中...",
            action_result={"type": "generate_setup", "status": "generating"},
            meta=None,
        ),
    ]
    diagnosis = ProjectDiagnosisOut(
        missing_items=["storyline", "outline", "content"],
        completed_items=["setup"],
        suggested_next_step="preview_storyline",
    )

    summary = await build_compaction_summary(
        messages,
        ai_service=BrokenAIService(),
        model="deepseek-chat",
        project_name="测试项目",
        diagnosis=diagnosis,
    )

    assert "用户目标：" in summary.summary_text
    assert "硬科幻世界观" in summary.summary_text
    assert "最近动作：" in summary.summary_text
    assert "generate_setup" in summary.summary_text
    assert "项目诊断：" in summary.summary_text
    assert "缺失 故事线、大纲、正文" in summary.summary_text
    assert "最近补充要求：" in summary.summary_text
    assert "主角是植物学家" in summary.summary_text


@pytest.mark.asyncio
async def test_compaction_summary_uses_registry_backed_prompt(monkeypatch):
    build_calls = []

    class FakeAssembler:
        def build(self, prompt_id, variables):
            build_calls.append((prompt_id, variables))
            return SimpleNamespace(content="REGISTRY_COMPACT_PROMPT")

    class CapturingAIService:
        def __init__(self):
            self.messages = None

        async def complete(self, messages, **kwargs):
            self.messages = messages
            return SimpleNamespace(content="模型生成的压缩摘要")

    monkeypatch.setattr("app.core.chat_compaction.PromptAssembler", FakeAssembler)

    ai_service = CapturingAIService()
    messages = [
        SimpleNamespace(role="user", content="请继续生成故事线。", action_result=None, meta=None),
        SimpleNamespace(role="assistant", content="我会参考现有设定。", action_result=None, meta=None),
    ]
    diagnosis = ProjectDiagnosisOut(
        missing_items=["outline", "content"],
        completed_items=["setup", "storyline"],
        suggested_next_step="preview_outline",
    )

    summary = await build_compaction_summary(
        messages,
        ai_service=ai_service,
        model="deepseek-chat",
        project_name="潮汐门",
        diagnosis=diagnosis,
    )

    assert build_calls == [
        (
            "dialog.compact",
            {
                "project_name": "潮汐门",
                "dialog_lines": "1. [user] 请继续生成故事线。\n2. [assistant] 我会参考现有设定。",
            },
        )
    ]
    assert ai_service.messages == [
        {"role": "system", "content": "REGISTRY_COMPACT_PROMPT"}
    ]
    assert summary.summary_text == "模型生成的压缩摘要"


@pytest.mark.asyncio
async def test_compaction_summary_bounds_dialog_lines_for_long_history(monkeypatch):
    build_calls = []

    class FakeAssembler:
        def build(self, prompt_id, variables):
            build_calls.append((prompt_id, variables))
            return SimpleNamespace(content="REGISTRY_COMPACT_PROMPT")

    class CapturingAIService:
        async def complete(self, messages, **kwargs):
            return SimpleNamespace(content="长对话压缩摘要")

    monkeypatch.setattr("app.core.chat_compaction.PromptAssembler", FakeAssembler)

    messages = [
        SimpleNamespace(
            role="user" if index % 2 else "assistant",
            content=f"第{index}条 " + ("长对话内容" * 80),
            action_result=None,
            meta=None,
        )
        for index in range(1, 181)
    ]
    diagnosis = ProjectDiagnosisOut(
        missing_items=[],
        completed_items=["setup", "storyline", "outline", "content"],
        suggested_next_step="continue_writing",
    )

    summary = await build_compaction_summary(
        messages,
        ai_service=CapturingAIService(),
        model="deepseek-chat",
        project_name="百万字项目",
        diagnosis=diagnosis,
    )

    assert build_calls
    dialog_lines = build_calls[0][1]["dialog_lines"]
    assert len(dialog_lines) <= 12000
    assert "已省略" in dialog_lines
    assert "第180条" in dialog_lines
    assert "第1条" not in dialog_lines
    assert summary.compacted_count == 180
    assert summary.summary_text == "长对话压缩摘要"


@pytest.mark.asyncio
async def test_compaction_summary_returns_fallback_when_prompt_build_fails(monkeypatch):
    class BrokenAssembler:
        def build(self, prompt_id, variables):
            raise RuntimeError("template unavailable")

    class UnusedAIService:
        async def complete(self, messages, **kwargs):
            raise AssertionError("AI complete should not be called when prompt build fails")

    monkeypatch.setattr("app.core.chat_compaction.PromptAssembler", BrokenAssembler)

    messages = [
        SimpleNamespace(role="user", content="我要把项目推进到大纲阶段。", action_result=None, meta=None),
        SimpleNamespace(role="assistant", content="准备生成故事线。", action_result=None, meta=None),
    ]
    diagnosis = ProjectDiagnosisOut(
        missing_items=["outline", "content"],
        completed_items=["setup", "storyline"],
        suggested_next_step="preview_outline",
    )

    summary = await build_compaction_summary(
        messages,
        ai_service=UnusedAIService(),
        model="deepseek-chat",
        project_name="潮汐门",
        diagnosis=diagnosis,
    )

    assert "用户目标：我要把项目推进到大纲阶段。" in summary.summary_text
    assert "项目诊断：" in summary.summary_text
    assert "已完成 设定、故事线" in summary.summary_text
    assert "缺失 大纲、正文" in summary.summary_text


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


def test_chat_text_that_matches_action_intent_creates_pending_action(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test", "genre": "科幻"})
    pid = r.json()["id"]

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "text",
        "text": "创建主角设定",
    })

    assert r2.status_code == 200
    body = r2.json()
    dialog = db_session.query(Dialog).filter_by(project_id=pid).one()
    assert body["pending_action"]["type"] == "preview_setup"
    assert body["pending_action"]["params"]["project_id"] == pid
    assert body["pending_action"]["params"]["command_args"] == "创建主角设定"
    assert db_session.query(PendingAction).filter_by(dialog_id=dialog.id).count() == 1
    request_message = (
        db_session.query(DialogMessage)
        .filter(DialogMessage.dialog_id == dialog.id, DialogMessage.role == "user")
        .order_by(DialogMessage.created_at.desc(), DialogMessage.id.desc())
        .first()
    )
    response_message = (
        db_session.query(DialogMessage)
        .filter(DialogMessage.dialog_id == dialog.id, DialogMessage.role == "assistant")
        .order_by(DialogMessage.created_at.desc(), DialogMessage.id.desc())
        .first()
    )
    route_trace = _latest_dialog_agent_route_trace(db_session, pid)
    assert route_trace is not None
    assert route_trace.status == "success"
    assert route_trace.model == "local-dialog-router"
    assert route_trace.dialog_id == dialog.id
    assert route_trace.request_message_id == request_message.id
    assert route_trace.response_message_id == response_message.id
    assert route_trace.trace_metadata["agent_route"] == body["pending_action"]["params"]["agent_route"]
    assert route_trace.trace_metadata["action_type"] == "preview_setup"
    assert route_trace.trace_metadata["source"] == "text_intent"
    assert route_trace.trace_metadata["pending_action_id"] == body["pending_action"]["id"]


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
    assert r2.json()["pending_action"]["params"]["project_id"] == pid
    assert r2.json()["pending_action"]["params"]["agent_route"] == _expected_agent_route(
        "button_action",
        "preview_setup",
        "generate_setup",
    )
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


def test_chat_button_action_merges_project_id_with_extra_params(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
        "params": {"command_args": "设定保持简洁"},
    })

    assert r2.status_code == 200
    assert r2.json()["pending_action"]["params"] == {
        "project_id": pid,
        "command_args": "设定保持简洁",
        "agent_route": _expected_agent_route(
            "button_action",
            "preview_setup",
            "generate_setup",
        ),
    }


def test_chat_text_start_writing_creates_pending_chapter_action(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(Setup(project_id=pid, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=pid, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=pid,
            status="generated",
            total_chapters=20,
            chapters=[{"chapter_index": 1, "title": "旧灯塔", "summary": "林舟开始调查。"}],
        )
    )
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "text",
        "text": "请开始写正文，从第1章开始生成。",
    })

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"]["type"] == "preview_chapter"
    assert body["pending_action"]["params"]["project_id"] == pid
    assert body["pending_action"]["params"]["chapter_index"] == 1
    assert body["pending_action"]["params"]["command_args"] == "请开始写正文，从第1章开始生成。"
    assert body["pending_action"]["params"]["agent_route"] == _expected_agent_route(
        "text_intent",
        "preview_chapter",
        "generate_chapter",
    )
    assert body["ui_hint"]["dialog_state"] == "PENDING_ACTION"
    assert body["ui_hint"]["active_action"]["type"] == "preview_chapter"


def test_chat_text_low_detail_continue_creates_pending_chapter_action(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(Setup(project_id=pid, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=pid, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=pid,
            status="generated",
            total_chapters=20,
            chapters=[{"chapter_index": 1, "title": "旧灯塔", "summary": "林舟开始调查。"}],
        )
    )
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "text",
        "text": "继续吧",
    })

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"]["type"] == "preview_chapter"
    assert body["pending_action"]["params"]["project_id"] == pid
    assert body["pending_action"]["params"]["chapter_index"] == 1
    assert body["pending_action"]["params"]["command_args"] == "继续吧"
    assert body["pending_action"]["params"]["agent_route"] == _expected_agent_route(
        "text_intent",
        "preview_chapter",
        "generate_chapter",
    )
    assert body["ui_hint"]["dialog_state"] == "PENDING_ACTION"
    route_trace = _latest_dialog_route_trace(db_session, pid)
    assert route_trace is not None
    assert "control_projection_type" not in route_trace.trace_metadata


def test_continue_command_routes_through_low_detail_agent_continue(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Agent Slash Continue"})
    pid = r.json()["id"]
    db_session.add(Setup(project_id=pid, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=pid, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=pid,
            status="generated",
            total_chapters=2,
            chapters=[
                {"chapter_index": 1, "title": "旧灯塔", "summary": "林舟开始调查。"},
                {"chapter_index": 2, "title": "雾中人", "summary": "线索指向失踪档案。"},
            ],
        )
    )
    db_session.add(
        ChapterContent(project_id=pid, chapter_index=1, title="旧灯塔", content="第一章正文", status="generated")
    )
    db_session.commit()

    r2 = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": pid, "input_type": "command", "command_name": "continue"},
    )

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"]["type"] == "preview_chapter"
    assert body["pending_action"]["params"]["chapter_index"] == 2
    assert body["pending_action"]["params"]["chapter_index_source"] == "inferred_next_unwritten"
    assert body["pending_action"]["params"]["agent_route"] == _expected_agent_route(
        "text_intent",
        "preview_chapter",
        "generate_chapter",
    )
    assert body["pending_action"]["params"]["command_args"] == "继续"
    assert body["meta"]["dialog_route_decision"]["selected_route"] == "chapter_generation"
    assert body["meta"]["control_projection_type"] == "continue_agent_control"
    assert body["meta"]["agent_control"] == {
        "version": "phase32.continue_agent_control.v1",
        "command_name": "continue",
        "source": "slash_command",
        "selected_route": "chapter_generation",
        "reason_code": "no_recovery_or_followup",
        "source_run_id": None,
        "required_agent_tools": [
            "inspect_agent_health_projection",
            "inspect_agent_command_contracts",
            "plan_recovery_tools",
            "plan_recommended_followups",
            "prepare_generate_chapter_execution",
        ],
    }
    assert body["pending_action"]["params"]["agent_control"] == body["meta"]["agent_control"]
    assert body["pending_action"]["params"]["control_projection_type"] == "continue_agent_control"
    route_trace = _latest_dialog_route_trace(db_session, pid)
    assert route_trace is not None
    assert route_trace.trace_metadata["dialog_route_decision"] == body["meta"]["dialog_route_decision"]
    assert route_trace.trace_metadata["agent_control"] == body["meta"]["agent_control"]
    assert route_trace.trace_metadata["control_projection_type"] == "continue_agent_control"


def test_unavailable_agent_command_returns_feedback_without_pending_action(client, db_session, monkeypatch):
    r = client.post("/api/v1/projects", json={"name": "Unavailable Agent Command"})
    pid = r.json()["id"]
    unavailable_reason = "缺少 Agent 工具适配器：prepare_generate_chapter_execution"
    monkeypatch.setattr(
        dialogs_api,
        "build_agent_chat_command_catalog",
        lambda: {
            "version": "phase27.agent_chat_command_catalog.v1",
            "public_command_names": ["status", "clear", "compact"],
            "legacy_alias_names": ["setup", "storyline", "outline", "chapter"],
            "commands": [
                {
                    "name": "continue",
                    "label": "/continue",
                    "description": "继续",
                    "public": True,
                    "legacy": False,
                    "available": False,
                    "unavailable_reasons": [unavailable_reason],
                },
            ],
        },
    )

    response = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": pid, "input_type": "command", "command_name": "continue"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message_type"] == "command"
    assert body["pending_action"] is None
    assert "/continue 暂不可用" in body["message"]
    assert unavailable_reason in body["message"]
    assert body["meta"] == {
        "command_name": "continue",
        "command_available": False,
        "unavailable_reasons": [unavailable_reason],
    }
    assert db_session.query(PendingAction).count() == 0
    feedback = (
        db_session.query(DialogMessage)
        .join(Dialog, Dialog.id == DialogMessage.dialog_id)
        .filter(Dialog.project_id == pid, DialogMessage.message_type == "command", DialogMessage.role == "system")
        .order_by(DialogMessage.created_at.desc(), DialogMessage.id.desc())
        .first()
    )
    assert feedback is not None
    assert feedback.meta == body["meta"]


def test_status_command_routes_through_agent_health_projection(client):
    r = client.post("/api/v1/projects", json={"name": "Agent Slash Status"})
    pid = r.json()["id"]

    r2 = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": pid, "input_type": "command", "command_name": "status"},
    )

    assert r2.status_code == 200
    body = r2.json()
    assert body["message_type"] == "command"
    assert body["pending_action"] is None
    assert "Agent 状态" in body["message"]
    assert "诊断项" in body["message"]
    assert body["meta"]["command_name"] == "status"
    assert body["meta"]["control_projection_type"] == "agent_health_projection"
    health = body["meta"]["agent_health_projection"]
    assert health["version"] == "phase218.agent_health_projection.v1"
    assert health["status"] in {"ready", "degraded", "needs_attention"}
    assert isinstance(health["diagnostics"], list)
    assert body["ui_hint"]["dialog_state"] == "CHATTING"
    assert body["ui_hint"]["active_action"]["reason"] == "Agent 状态"


def test_legacy_chapter_command_routes_as_agent_intent_not_direct_slash_action(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Legacy Slash Chapter"})
    pid = r.json()["id"]
    db_session.add(Setup(project_id=pid, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=pid, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=pid,
            status="generated",
            total_chapters=2,
            chapters=[
                {"chapter_index": 1, "title": "旧灯塔", "summary": "林舟开始调查。"},
                {"chapter_index": 2, "title": "雾中人", "summary": "线索指向失踪档案。"},
            ],
        )
    )
    db_session.commit()

    r2 = client.post(
        "/api/v1/dialog/chat",
        json={
            "project_id": pid,
            "input_type": "command",
            "command_name": "chapter",
            "command_args": "2 强化悬疑",
        },
    )

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"]["type"] == "preview_chapter"
    params = body["pending_action"]["params"]
    assert params["chapter_index"] == 2
    assert params["agent_route"] == _expected_agent_route(
        "text_intent",
        "preview_chapter",
        "generate_chapter",
    )
    assert params["legacy_command"] == {
        "command_name": "chapter",
        "command_args": "2 强化悬疑",
        "migration": "agent_intent_alias",
    }
    assert params["command_args"] == "2 强化悬疑"
    assert params["agent_intent_text"] == "请生成第2章正文，强化悬疑"


def test_chat_text_low_detail_continue_prefers_recovery_preview_when_blocked_run_exists(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(Setup(project_id=pid, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=pid, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=pid,
            status="generated",
            total_chapters=20,
            chapters=[{"chapter_index": 1, "title": "旧灯塔", "summary": "林舟开始调查。"}],
        )
    )
    blocked_run = WritingAgentRun(
        project_id=pid,
        goal="阻塞的直接章节执行",
        status="blocked",
        entrypoint="api",
        input={},
    )
    db_session.add(blocked_run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=blocked_run.id,
            project_id=pid,
            step_index=1,
            tool_name="execute_generate_chapter_with_approval",
            status="blocked",
            input={"params": {"chapter_index": 1}},
            output={
                "status": "blocked",
                "agent_tool_result": {
                    "recovery": {
                        "status": "recommended",
                        "source_tool": "execute_generate_chapter_with_approval",
                        "reason_code": "resource_binding_target_mismatch",
                        "next_tool": "prepare_generate_chapter_execution",
                        "next_params": {"chapter_index": 1},
                    }
                },
            },
        )
    )
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "text",
        "text": "继续吧",
    })

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"] is None
    dialog = db_session.query(Dialog).filter_by(project_id=pid, dialog_type="hermes").one()
    assert db_session.query(PendingAction).filter_by(dialog_id=dialog.id).count() == 0

    recovery_run = (
        db_session.query(WritingAgentRun)
        .filter(WritingAgentRun.project_id == pid, WritingAgentRun.entrypoint == "dialog_auto_plan")
        .one()
    )
    assert recovery_run.status == "success"
    assert recovery_run.input["planner"]["intent_class"] == "recover_blocked_run"
    assert [tool["tool_name"] for tool in recovery_run.input["tools"]] == [
        "describe_agent_tools",
        "plan_recovery_tools",
    ]
    assert body["meta"]["agent_run_id"] == recovery_run.id
    assert body["meta"]["source_run_id"] == blocked_run.id
    assert body["meta"]["agent_action_type"] == "plan_recovery_tools"
    route_decision = body["meta"]["dialog_route_decision"]
    assert route_decision["selected_route"] == "recover_blocked_run"
    assert route_decision["reason_code"] == "recoverable_run_found"
    assert route_decision["source_run_id"] == blocked_run.id

    assistant_message = (
        db_session.query(DialogMessage)
        .filter(DialogMessage.dialog_id == dialog.id, DialogMessage.role == "assistant")
        .order_by(DialogMessage.created_at.desc(), DialogMessage.id.desc())
        .first()
    )
    assert assistant_message.content == "上一轮 Agent 运行存在可恢复阻塞，我已先规划恢复工具链。"
    assert assistant_message.action_result["type"] == "plan_recovery_tools"
    assert assistant_message.action_result["status"] == "success"
    assert assistant_message.action_result["data"]["agent_run_id"] == recovery_run.id
    assert assistant_message.action_result["data"]["source_run_id"] == blocked_run.id
    assert assistant_message.action_result["data"]["route_decision"] == route_decision
    assert assistant_message.meta == body["meta"]
    request_message = (
        db_session.query(DialogMessage)
        .filter(DialogMessage.dialog_id == dialog.id, DialogMessage.role == "user")
        .order_by(DialogMessage.created_at.desc(), DialogMessage.id.desc())
        .first()
    )
    route_trace = _latest_dialog_route_trace(db_session, pid)
    assert route_trace is not None
    assert route_trace.status == "success"
    assert route_trace.model == "local-dialog-router"
    assert route_trace.dialog_id == dialog.id
    assert route_trace.request_message_id == request_message.id
    assert route_trace.response_message_id == assistant_message.id
    assert route_trace.trace_metadata["dialog_route_decision"] == route_decision
    assert route_trace.trace_metadata["agent_run_id"] == recovery_run.id
    assert route_trace.trace_metadata["source_run_id"] == blocked_run.id


def test_chat_text_low_detail_continue_previews_latest_recommended_followups(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(Setup(project_id=pid, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=pid, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=pid,
            status="generated",
            total_chapters=20,
            chapters=[{"chapter_index": 1, "title": "旧灯塔", "summary": "林舟开始调查。"}],
        )
    )
    source_run = WritingAgentRun(
        project_id=pid,
        goal="生成第1章",
        status="success",
        entrypoint="api",
        input={},
    )
    db_session.add(source_run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=source_run.id,
            project_id=pid,
            step_index=1,
            tool_name="generate_chapter",
            status="success",
            chapter_index=1,
            input={"params": {"chapter_index": 1}},
            output={
                "status": "success",
                "chapter_index": 1,
                "agent_tool_result": {
                    "recommendations": {
                        "canonical_followups": ["review_chapter_quality", "review_chapter_continuity"],
                    }
                },
            },
        )
    )
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "text",
        "text": "继续吧",
    })

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"] is None
    dialog = db_session.query(Dialog).filter_by(project_id=pid, dialog_type="hermes").one()
    assert db_session.query(PendingAction).filter_by(dialog_id=dialog.id).count() == 0

    followup_run = (
        db_session.query(WritingAgentRun)
        .filter(WritingAgentRun.project_id == pid, WritingAgentRun.entrypoint == "dialog_auto_plan")
        .one()
    )
    assert followup_run.status == "success"
    assert followup_run.input["planner"]["source_run_id"] == source_run.id
    assert [tool["tool_name"] for tool in followup_run.input["tools"]] == ["plan_recommended_followups"]
    assert body["meta"]["agent_run_id"] == followup_run.id
    assert body["meta"]["source_run_id"] == source_run.id
    assert body["meta"]["agent_action_type"] == "plan_recommended_followups"
    route_decision = body["meta"]["dialog_route_decision"]
    assert route_decision["selected_route"] == "recommended_followups"
    assert route_decision["reason_code"] == "recommended_followups_found"
    assert route_decision["source_run_id"] == source_run.id

    assistant_message = (
        db_session.query(DialogMessage)
        .filter(DialogMessage.dialog_id == dialog.id, DialogMessage.role == "assistant")
        .order_by(DialogMessage.created_at.desc(), DialogMessage.id.desc())
        .first()
    )
    assert assistant_message.content == "上一轮 Agent 运行给出了推荐后继，我已先规划后继工具链。"
    assert assistant_message.action_result["type"] == "plan_recommended_followups"
    assert assistant_message.action_result["status"] == "success"
    assert assistant_message.action_result["data"]["agent_run_id"] == followup_run.id
    assert assistant_message.action_result["data"]["source_run_id"] == source_run.id
    assert assistant_message.action_result["data"]["recommended_followups"]["status"] == "recommended"
    assert [tool["tool_name"] for tool in assistant_message.action_result["data"]["tools"]] == [
        "review_chapter_quality",
        "review_chapter_continuity",
    ]
    assert assistant_message.action_result["data"]["route_decision"] == route_decision
    assert assistant_message.meta == body["meta"]
    request_message = (
        db_session.query(DialogMessage)
        .filter(DialogMessage.dialog_id == dialog.id, DialogMessage.role == "user")
        .order_by(DialogMessage.created_at.desc(), DialogMessage.id.desc())
        .first()
    )
    route_trace = _latest_dialog_route_trace(db_session, pid)
    assert route_trace is not None
    assert route_trace.status == "success"
    assert route_trace.model == "local-dialog-router"
    assert route_trace.dialog_id == dialog.id
    assert route_trace.request_message_id == request_message.id
    assert route_trace.response_message_id == assistant_message.id
    assert route_trace.trace_metadata["dialog_route_decision"] == route_decision
    assert route_trace.trace_metadata["agent_run_id"] == followup_run.id
    assert route_trace.trace_metadata["source_run_id"] == source_run.id


def test_chat_text_low_detail_continue_uses_first_unwritten_outline_chapter(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(Setup(project_id=pid, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=pid, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=pid,
            status="generated",
            total_chapters=3,
            chapters=[
                {"chapter_index": 1, "title": "旧灯塔", "summary": "林舟开始调查。"},
                {"chapter_index": 2, "title": "雨夜证词", "summary": "林舟追查新的证词。"},
                {"chapter_index": 3, "title": "回声", "summary": "林舟发现回声。"},
            ],
        )
    )
    db_session.add(
        ChapterContent(
            project_id=pid,
            chapter_index=1,
            title="旧灯塔",
            content="第一章正文",
            status="generated",
        )
    )
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "text",
        "text": "继续吧",
    })

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"]["type"] == "preview_chapter"
    assert body["pending_action"]["params"]["project_id"] == pid
    assert body["pending_action"]["params"]["chapter_index"] == 2
    assert body["pending_action"]["params"]["command_args"] == "继续吧"
    route_decision = body["meta"]["dialog_route_decision"]
    assert route_decision["selected_route"] == "chapter_generation"
    assert route_decision["reason_code"] == "no_recovery_or_followup"
    assert body["pending_action"]["params"]["dialog_route_decision"] == route_decision

    dialog = db_session.query(Dialog).filter_by(project_id=pid, dialog_type="hermes").one()
    assistant_message = (
        db_session.query(DialogMessage)
        .filter(DialogMessage.dialog_id == dialog.id, DialogMessage.role == "assistant")
        .order_by(DialogMessage.created_at.desc(), DialogMessage.id.desc())
        .first()
    )
    assert assistant_message.meta["dialog_route_decision"] == route_decision
    request_message = (
        db_session.query(DialogMessage)
        .filter(DialogMessage.dialog_id == dialog.id, DialogMessage.role == "user")
        .order_by(DialogMessage.created_at.desc(), DialogMessage.id.desc())
        .first()
    )
    route_trace = _latest_dialog_route_trace(db_session, pid)
    assert route_trace is not None
    assert route_trace.status == "success"
    assert route_trace.model == "local-dialog-router"
    assert route_trace.dialog_id == dialog.id
    assert route_trace.request_message_id == request_message.id
    assert route_trace.response_message_id == assistant_message.id
    assert route_trace.trace_metadata["dialog_route_decision"] == route_decision
    assert route_trace.trace_metadata["action_type"] == "preview_chapter"


def test_chat_text_next_chapter_uses_inferred_chapter_source(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(Setup(project_id=pid, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=pid, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=pid,
            status="generated",
            total_chapters=2,
            chapters=[
                {"chapter_index": 1, "title": "旧灯塔", "summary": "林舟开始调查。"},
                {"chapter_index": 2, "title": "雨夜证词", "summary": "林舟追查新的证词。"},
            ],
        )
    )
    db_session.add(
        ChapterContent(
            project_id=pid,
            chapter_index=1,
            title="旧灯塔",
            content="第一章正文",
            status="generated",
        )
    )
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "text",
        "text": "下一章",
    })

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"]["type"] == "preview_chapter"
    assert body["pending_action"]["params"]["chapter_index"] == 2
    assert body["pending_action"]["params"]["chapter_index_source"] == "inferred_next_unwritten"


def test_chat_text_continue_skips_reserved_pending_chapter(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(Setup(project_id=pid, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=pid, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=pid,
            status="generated",
            total_chapters=3,
            chapters=[
                {"chapter_index": 1, "title": "一", "summary": "一"},
                {"chapter_index": 2, "title": "二", "summary": "二"},
                {"chapter_index": 3, "title": "三", "summary": "三"},
            ],
        )
    )
    db_session.add(ChapterContent(project_id=pid, chapter_index=1, title="一", content="第一章正文", status="generated"))
    other_dialog = Dialog(project_id=pid, dialog_type="athena", state="pending_action")
    db_session.add(other_dialog)
    db_session.flush()
    db_session.add(
        PendingAction(
            dialog_id=other_dialog.id,
            type="preview_chapter",
            params={"project_id": pid, "chapter_index": 2},
            status="pending",
        )
    )
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "继续吧"})

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"]["type"] == "preview_chapter"
    assert body["pending_action"]["params"]["chapter_index"] == 3


def test_chat_text_continue_skips_active_chapter_task(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(Setup(project_id=pid, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=pid, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=pid,
            status="generated",
            total_chapters=3,
            chapters=[
                {"chapter_index": 1, "title": "一", "summary": "一"},
                {"chapter_index": 2, "title": "二", "summary": "二"},
                {"chapter_index": 3, "title": "三", "summary": "三"},
            ],
        )
    )
    db_session.add(ChapterContent(project_id=pid, chapter_index=1, title="一", content="第一章正文", status="generated"))
    db_session.add(
        BackgroundTask(
            project_id=pid,
            task_type="writing_agent_run",
            status="running",
            payload={"action_type": "generate_chapter", "tools": [{"params": {"chapter_index": 2}}]},
        )
    )
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "继续吧"})

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"]["type"] == "preview_chapter"
    assert body["pending_action"]["params"]["chapter_index"] == 3


def test_chat_text_continue_skips_active_chapter_range_task(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    db_session.add(Setup(project_id=pid, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=pid, status="generated", plotlines=[], foreshadowing=[]))
    db_session.add(
        Outline(
            project_id=pid,
            status="generated",
            total_chapters=4,
            chapters=[
                {"chapter_index": 1, "title": "一", "summary": "一"},
                {"chapter_index": 2, "title": "二", "summary": "二"},
                {"chapter_index": 3, "title": "三", "summary": "三"},
                {"chapter_index": 4, "title": "四", "summary": "四"},
            ],
        )
    )
    db_session.add(ChapterContent(project_id=pid, chapter_index=1, title="一", content="第一章正文", status="generated"))
    db_session.add(
        BackgroundTask(
            project_id=pid,
            task_type="generate_chapter_range",
            status="running",
            payload={"chapter_range": {"start": 2, "end": 3}},
        )
    )
    db_session.commit()

    r2 = client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "继续吧"})

    assert r2.status_code == 200
    body = r2.json()
    assert body["pending_action"]["type"] == "preview_chapter"
    assert body["pending_action"]["params"]["chapter_index"] == 4


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


def test_get_messages_defaults_to_bounded_content_preview(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Long Message Preview"})
    pid = r.json()["id"]
    long_content = "长消息正文" * 2000
    hermes_dialog = Dialog(project_id=pid, dialog_type="hermes", state="chatting")
    athena_dialog = Dialog(project_id=pid, dialog_type="athena", state="chatting")
    db_session.add_all([hermes_dialog, athena_dialog])
    db_session.flush()
    db_session.add_all(
        [
            DialogMessage(dialog_id=hermes_dialog.id, role="assistant", message_type="plain", content=long_content),
            DialogMessage(dialog_id=athena_dialog.id, role="assistant", message_type="plain", content=long_content),
        ]
    )
    db_session.commit()

    hermes_response = client.get(f"/api/v1/dialog/projects/{pid}/messages")
    athena_response = client.get(f"/api/v1/projects/{pid}/athena/dialog/messages")

    assert hermes_response.status_code == 200
    assert athena_response.status_code == 200
    for message in [hermes_response.json()[0], athena_response.json()[0]]:
        assert message["content_truncated"] is True
        assert message["original_content_length"] == len(long_content)
        assert len(message["content"]) < len(long_content)


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
    expected_intent_text = command_to_agent_intent_text(command_name, args)

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
    assert body["pending_action"]["params"]["agent_intent_text"] == expected_intent_text
    assert body["pending_action"]["params"]["legacy_command"] == {
        "command_name": command_name,
        "command_args": args,
        "migration": "agent_intent_alias",
    }
    expected_tool_name = {
        "preview_setup": "generate_setup",
        "preview_storyline": "generate_storyline",
        "preview_outline": "generate_outline",
    }[expected_action_type]
    assert body["pending_action"]["params"]["agent_route"] == _expected_agent_route(
        "text_intent",
        expected_action_type,
        expected_tool_name,
    )


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


def test_select_compactable_plain_messages_filters_after_last_summary_without_full_history_scan(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Compact Scale"})
    pid = r.json()["id"]
    dialog = Dialog(project_id=pid, dialog_type="hermes", state="chatting")
    db_session.add(dialog)
    db_session.commit()

    base_time = datetime(2026, 1, 1, tzinfo=UTC)
    old_messages = [
        DialogMessage(
            dialog_id=dialog.id,
            role="user",
            message_type="plain",
            content=f"old-{index}",
            created_at=base_time + timedelta(seconds=index),
        )
        for index in range(200)
    ]
    summary = DialogMessage(
        dialog_id=dialog.id,
        role="system",
        message_type="summary",
        content="历史摘要",
        created_at=base_time + timedelta(seconds=300),
    )
    recent_messages = [
        DialogMessage(
            dialog_id=dialog.id,
            role="user",
            message_type="plain",
            content="new-1",
            created_at=base_time + timedelta(seconds=301),
        ),
        DialogMessage(
            dialog_id=dialog.id,
            role="assistant",
            message_type="plain",
            content="new-2",
            created_at=base_time + timedelta(seconds=302),
        ),
    ]
    db_session.add_all([*old_messages, summary, *recent_messages])
    db_session.commit()

    statements: list[str] = []

    def capture_statement(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        statements.append(" ".join(statement.lower().split()))

    bind = db_session.get_bind()
    event.listen(bind, "before_cursor_execute", capture_statement)
    try:
        compactable = select_compactable_plain_messages(db_session, dialog.id)
    finally:
        event.remove(bind, "before_cursor_execute", capture_statement)

    assert [message.content for message in compactable] == ["new-1", "new-2"]
    full_history_selects = [
        statement
        for statement in statements
        if "from dialog_messages" in statement
        and "where dialog_messages.dialog_id" in statement
        and "message_type =" not in statement
    ]
    assert full_history_selects == []


def test_select_compactable_plain_messages_projects_bounded_content_preview(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Compact Preview"})
    pid = r.json()["id"]
    dialog = Dialog(project_id=pid, dialog_type="hermes", state="chatting")
    db_session.add(dialog)
    db_session.commit()
    full_content = "很长的对话内容" * 1000
    db_session.add(
        DialogMessage(
            dialog_id=dialog.id,
            role="user",
            message_type="plain",
            content=full_content,
            action_result={"type": "chat", "status": "done"},
        )
    )
    db_session.commit()
    statements: list[str] = []

    def capture_statement(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        statements.append(" ".join(statement.lower().split()))

    bind = db_session.get_bind()
    event.listen(bind, "before_cursor_execute", capture_statement)
    try:
        compactable = select_compactable_plain_messages(db_session, dialog.id)
    finally:
        event.remove(bind, "before_cursor_execute", capture_statement)

    assert len(compactable) == 1
    assert compactable[0].id
    assert compactable[0].role == "user"
    assert compactable[0].action_result == {"type": "chat", "status": "done"}
    assert 0 < len(compactable[0].content) <= 2000
    assert compactable[0].content != full_content
    plain_message_selects = [
        statement.split(" from dialog_messages", 1)[0]
        for statement in statements
        if " from dialog_messages" in statement
        and "dialog_messages.message_type" in statement
        and "content" in statement.split(" from dialog_messages", 1)[0]
    ]
    assert plain_message_selects
    assert all("dialog_messages.content as" not in select_clause for select_clause in plain_message_selects)


def test_latest_unfinished_action_type_scans_only_action_result_messages(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Running Guard Scale"})
    pid = r.json()["id"]
    dialog = Dialog(project_id=pid, dialog_type="hermes", state="running")
    db_session.add(dialog)
    db_session.commit()

    base_time = datetime(2026, 1, 2, tzinfo=UTC)
    plain_messages = [
        DialogMessage(
            dialog_id=dialog.id,
            role="user",
            message_type="plain",
            content=f"plain-{index}",
            created_at=base_time + timedelta(seconds=index),
        )
        for index in range(300)
    ]
    running_message = DialogMessage(
        dialog_id=dialog.id,
        role="system",
        message_type="command",
        content="正在生成中",
        action_result={"type": "generate_chapter", "status": "running"},
        created_at=base_time + timedelta(seconds=400),
    )
    db_session.add_all([*plain_messages, running_message])
    db_session.commit()

    statements: list[str] = []

    def capture_statement(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        statements.append(" ".join(statement.lower().split()))

    bind = db_session.get_bind()
    event.listen(bind, "before_cursor_execute", capture_statement)
    try:
        running_action_type = dialogs_api._latest_unfinished_action_type(db_session, dialog.id)
    finally:
        event.remove(bind, "before_cursor_execute", capture_statement)

    assert running_action_type == "generate_chapter"
    full_message_selects = [
        statement
        for statement in statements
        if "from dialog_messages" in statement
        and "where dialog_messages.dialog_id" in statement
        and "action_result is not null" not in statement
    ]
    assert full_message_selects == []


def test_resolve_action_confirm_sets_dialog_state_running(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
    })
    action_id = r2.json()["pending_action"]["id"]

    with patch("app.api.dialogs.LocalTaskRunner.start") as mock_start:
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
    mock_start.assert_called_once()
    assert r3.json()["action_result"]["data"]["agent_run_id"]

    dialog = db_session.query(Dialog).filter(Dialog.project_id == pid).first()
    assert dialog is not None
    assert dialog.pending_action_id is None
    assert dialog.state == "running"


def test_resolve_action_confirm_creates_background_task(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    r2 = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
    })
    action_id = r2.json()["pending_action"]["id"]

    with patch("app.api.dialogs.LocalTaskRunner.start") as start:
        r3 = client.post("/api/v1/dialog/resolve-action", json={
            "action_id": action_id,
            "decision": "confirm",
        })

    assert r3.status_code == 200
    task_id = r3.json()["action_result"]["data"]["task_id"]
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == task_id).one()
    run = db_session.query(WritingAgentRun).filter(WritingAgentRun.id == r3.json()["action_result"]["data"]["agent_run_id"]).one()
    assert task.project_id == pid
    assert task.task_type == "writing_agent_run"
    assert task.payload["agent_run_id"] == run.id
    assert task.payload["action_type"] == "generate_setup"
    assert task.payload["tools"][0]["tool_name"] == "prepare_generate_setup_execution"
    assert task.payload["dialog_id"]
    assert task.status == "pending"
    assert run.background_task_id == task.id
    assert run.entrypoint == "dialog_pending_action"
    start.assert_called_once()


def test_resolve_chapter_action_confirm_dispatches_prepare_tool(client, db_session):
    project_id = client.post("/api/v1/projects", json={"name": "Chapter Prepare Dispatch"}).json()["id"]
    _seed_project_ready_for_chapter_generation(db_session, project_id)
    response = client.post(
        "/api/v1/dialog/chat",
        json={
            "project_id": project_id,
            "input_type": "command",
            "command_name": "chapter",
            "command_args": "2 承接上一章记忆线索",
        },
    )
    action_id = response.json()["pending_action"]["id"]

    with patch("app.api.dialogs.LocalTaskRunner.start") as start:
        confirmed = client.post(
            "/api/v1/dialog/resolve-action",
            json={"action_id": action_id, "decision": "confirm"},
        )

    assert confirmed.status_code == 200
    start.assert_called_once()
    result_view = confirmed.json()["action_result_view"]
    assert result_view["type"] == "generate_chapter"
    assert result_view["status"] == "generating"
    assert result_view["label"] == "正文生成中..."
    assert result_view["variant"] == "neutral"
    assert result_view["detail_items"] == [
        {"label": "用户决策", "value": "已确认"},
        {"label": "审批模式", "value": "单次确认"},
        {"label": "目标章节", "value": "第2章"},
        {"label": "章节来源", "value": "用户指定"},
    ]
    payload = confirmed.json()["action_result"]["data"]
    decision = payload["approval_decision"]
    assert decision["chapter_index"] == 2
    assert decision["chapter_index_source"] == "explicit_user"
    task = db_session.query(BackgroundTask).filter(BackgroundTask.id == payload["task_id"]).one()
    run = db_session.query(WritingAgentRun).filter(WritingAgentRun.id == payload["agent_run_id"]).one()
    decision_message = (
        db_session.query(DialogMessage)
        .filter(DialogMessage.dialog_id == run.dialog_id, DialogMessage.role == "system")
        .order_by(DialogMessage.created_at.desc(), DialogMessage.id.desc())
        .first()
    )
    assert task.payload["action_type"] == "generate_chapter"
    assert task.payload["tools"][0]["tool_name"] == "prepare_generate_chapter_execution"
    assert task.payload["tools"][0]["params"]["chapter_index"] == 2
    assert run.request_message_id == decision_message.id
    assert decision_message.action_result["data"]["agent_run_id"] == run.id
    assert run.input["tools"][0]["tool_name"] == "prepare_generate_chapter_execution"
    assert run.input["tools"][0]["command_args"] == "2 承接上一章记忆线索"
    assert run.input["tools"][0]["params"]["chapter_index"] == 2


@pytest.mark.asyncio
async def test_chapter_prepare_background_work_records_approval_required_without_generating(db_session):
    project = Project(name="Chapter Prepare Work")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)

    from app.services.writing_agent.dialog_control_plane import prepare_dialog_agent_run_dispatch

    dispatch = prepare_dialog_agent_run_dispatch(
        db_session,
        project_id=project.id,
        dialog_id=dialog.id,
        action_type="generate_chapter",
        command_args="2 承接上一章记忆线索",
        action_params={"project_id": project.id, "chapter_index": 2},
    )

    result = await dispatch.work(db_session, dispatch.task)

    terminal = db_session.query(DialogMessage).filter_by(dialog_id=dialog.id, role="assistant").one()
    pending = db_session.query(PendingAction).filter_by(dialog_id=dialog.id, status="pending").one()
    refreshed_dialog = db_session.query(Dialog).filter(Dialog.id == dialog.id).one()
    assert result["status"] == "approval_required"
    assert result["agent_run_id"] == dispatch.run.id
    assert terminal.action_result["type"] == "generate_chapter"
    assert terminal.action_result["status"] == "approval_required"
    assert "等待确认" in terminal.content
    assert terminal.action_result["data"]["chapter_index"] == 2
    assert terminal.action_result["data"]["agent_plan_approval_contract_hash"].startswith("approval:")
    assert pending.type == "generate_chapter"
    assert pending.params["chapter_index"] == 2
    assert pending.params["confirm_execute"] is True
    assert pending.params["approval_contract_hash"] == terminal.action_result["data"]["agent_plan_approval_contract_hash"]
    assert pending.params["approval_contract"] == terminal.action_result["data"]["agent_plan_approval_contract"]
    assert refreshed_dialog.pending_action_id == pending.id
    assert refreshed_dialog.state == "pending_action"
    assert db_session.query(ChapterContent).filter_by(project_id=project.id, chapter_index=2).count() == 0


@pytest.mark.asyncio
async def test_chapter_approval_pending_message_uses_specific_description(db_session):
    project = Project(name="Chapter Approval Pending Description")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)

    from app.services.writing_agent.dialog_control_plane import prepare_dialog_agent_run_dispatch

    dispatch = prepare_dialog_agent_run_dispatch(
        db_session,
        project_id=project.id,
        dialog_id=dialog.id,
        action_type="generate_chapter",
        command_args="2 承接上一章记忆线索",
        action_params={"project_id": project.id, "chapter_index": 2},
    )
    await dispatch.work(db_session, dispatch.task)

    messages = DialogMessageService(db_session).list_messages(project.id)
    pending_action = messages[-1]["pending_action"]
    assert pending_action["type"] == "generate_chapter"
    assert "第2章正文" in pending_action["description"]
    assert "确认后" in pending_action["description"]
    assert pending_action["description"] != "已准备好执行操作。"
    preview = pending_action["execution_preview"]
    assert preview["title"] == "待执行：生成正文"
    assert preview["write_step_count"] == 1
    assert preview["approval_contract_hash"].startswith("approval:")
    assert preview["steps"][0]["tool_name"] == "generate_chapter"
    assert preview["steps"][0]["label"] == "生成正文"
    assert preview["steps"][0]["params"]["chapter_index"] == 2
    assert preview["audit"] == {
        "kind": "approval_contract",
        "approval_contract_hash": preview["approval_contract_hash"],
        "approval_contract_version": "phase108.agent_plan_approval_contract.v1",
        "plan_id": f"direct-generate:{project.id}:chapter:2",
        "source_projection_id": None,
        "planner_version": "phase114.generate_chapter_execution_prepare.v1",
        "intent_class": "direct_generate_chapter",
    }


@pytest.mark.asyncio
async def test_get_messages_includes_action_result_view_for_approval_required(db_session):
    project = Project(name="Chapter Approval Result View")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)

    from app.services.writing_agent.dialog_control_plane import prepare_dialog_agent_run_dispatch

    dispatch = prepare_dialog_agent_run_dispatch(
        db_session,
        project_id=project.id,
        dialog_id=dialog.id,
        action_type="generate_chapter",
        command_args="2 承接上一章记忆线索",
        action_params={"project_id": project.id, "chapter_index": 2},
    )
    await dispatch.work(db_session, dispatch.task)

    messages = DialogMessageService(db_session).list_messages(project.id)
    result_view = messages[-1]["action_result_view"]
    assert result_view == {
        "type": "generate_chapter",
        "status": "approval_required",
        "label": "生成正文等待确认",
        "variant": "neutral",
    }


def test_get_messages_includes_action_result_view_for_recovery_preview(db_session):
    project = Project(name="Recovery Preview Result View")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)
    dialogs_api._save_message(
        db_session,
        dialog.id,
        "assistant",
        "上一轮 Agent 运行存在可恢复阻塞，我已先规划恢复工具链。",
        action_result={
            "type": "plan_recovery_tools",
            "status": "success",
            "data": {
                "agent_run_id": "recovery-run-123456",
                "source_run_id": "blocked-run-abcdef",
                "recovery": {"status": "recommended"},
                "tools": [{"tool_name": "prepare_generate_chapter_execution"}],
                "execution_policy": {"status": "ready"},
                "route_decision": {
                    "selected_route": "recover_blocked_run",
                    "reason_code": "recoverable_run_found",
                },
            },
        },
    )

    messages = DialogMessageService(db_session).list_messages(project.id)

    assert messages[-1]["action_result_view"] == {
        "type": "plan_recovery_tools",
        "status": "success",
        "label": "恢复预览已生成",
        "variant": "success",
        "detail_items": [
            {"label": "来源运行", "value": "blocked-"},
            {"label": "继续路由", "value": "恢复阻塞运行"},
            {"label": "路由原因", "value": "发现可恢复运行"},
            {"label": "恢复状态", "value": "建议恢复"},
            {"label": "执行策略", "value": "可执行"},
            {"label": "恢复工具", "value": "1 个"},
        ],
    }


def test_get_messages_includes_action_result_view_for_recommended_followup_result_view(db_session):
    project = Project(name="Recommended Followup Result View")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)
    dialogs_api._save_message(
        db_session,
        dialog.id,
        "assistant",
        "我已预览上一轮推荐的后继工具链。",
        action_result={
            "type": "plan_recommended_followups",
            "status": "success",
            "data": {
                "agent_run_id": "followup-run-123456",
                "source_run_id": "source-run-abcdef",
                "recommended_followups": {
                    "status": "recommended",
                    "provenance_write_tools": [{"tool_name": "prepare_repair_longform_maintenance", "params": {}}],
                },
                "tools": [{"tool_name": "inspect_agent_memory_route"}],
                "route_decision": {
                    "selected_route": "recommended_followups",
                    "reason_code": "recommended_followups_found",
                },
            },
        },
    )

    messages = DialogMessageService(db_session).list_messages(project.id)

    assert messages[-1]["action_result_view"] == {
        "type": "plan_recommended_followups",
        "status": "success",
        "label": "推荐后继预览已生成",
        "variant": "success",
        "detail_items": [
            {"label": "来源运行", "value": "source-r"},
            {"label": "继续路由", "value": "推荐后继"},
            {"label": "路由原因", "value": "发现上一轮推荐后继"},
            {"label": "推荐状态", "value": "已推荐"},
            {"label": "自动后继", "value": "1 个"},
            {"label": "需确认修复", "value": "1 个"},
        ],
    }


def test_get_messages_includes_agent_discovery_view_detail_items(db_session):
    project = Project(name="Agent Discovery Result View")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)
    dialogs_api._save_message(
        db_session,
        dialog.id,
        "assistant",
        "Agent 已按创作执行者身份规划工具面。",
        action_result={
            "type": "plan_recovery_tools",
            "status": "success",
            "data": {
                "agent_profile": "drafting_worker",
                "agent_profile_definition": {
                    "version": "phase212.agent_profile_definition.v1",
                    "status": "known",
                    "profile": "drafting_worker",
                    "display_name": "创作执行者",
                    "role": "worker",
                    "tier": "worker",
                    "delegation_allowed": False,
                    "delegate_to_profiles": [],
                    "source": "planner_trace",
                },
                "agent_tool_discovery": {
                    "version": "phase210.agent_tool_discovery_projection.v1",
                    "status": "applied",
                    "scope_applied": True,
                    "scope_source": "agent_profile",
                    "requested_profile": "drafting_worker",
                    "effective_profile": "drafting_worker",
                    "visible_tool_count": 12,
                    "filtered_by_profile_count": 7,
                    "filter_stages": ["profile"],
                },
            },
        },
    )

    messages = DialogMessageService(db_session).list_messages(project.id)
    detail_items = messages[-1]["action_result_view"]["detail_items"]

    assert {"label": "Agent 身份", "value": "创作执行者"} in detail_items
    assert {"label": "Agent 角色", "value": "worker"} in detail_items
    assert {"label": "编排层级", "value": "worker"} in detail_items
    assert {"label": "委派", "value": "不可委派"} in detail_items
    assert {"label": "工具面", "value": "已按身份收窄"} in detail_items
    assert {"label": "可见工具", "value": "12 个"} in detail_items
    assert {"label": "已过滤", "value": "7 个"} in detail_items


def test_get_messages_includes_delegate_profile_targets_detail_item(db_session):
    project = Project(name="Delegate Profile Targets Result View")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)
    dialogs_api._save_message(
        db_session,
        dialog.id,
        "assistant",
        "Agent 已按编排主控身份规划工具面。",
        action_result={
            "type": "plan_recovery_tools",
            "status": "success",
            "data": {
                "agent_profile": "orchestrator",
                "agent_profile_definition": {
                    "version": "phase212.agent_profile_definition.v1",
                    "status": "known",
                    "profile": "orchestrator",
                    "display_name": "编排主控",
                    "role": "orchestrator",
                    "tier": "reasoning",
                    "delegation_allowed": True,
                    "delegate_to_profiles": [
                        "drafting_worker",
                        "reviewer_worker",
                        "world_model_worker",
                        "recovery_worker",
                    ],
                    "source": "planner_trace",
                },
            },
        },
    )

    messages = DialogMessageService(db_session).list_messages(project.id)
    detail_items = messages[-1]["action_result_view"]["detail_items"]

    assert {"label": "Agent 身份", "value": "编排主控"} in detail_items
    assert {"label": "委派", "value": "可委派"} in detail_items
    assert {"label": "可委派目标", "value": "4 个声明"} in detail_items


def test_get_messages_includes_agent_profile_policy_audit_detail_item(db_session):
    project = Project(name="Profile Policy Audit Result View")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)
    dialogs_api._save_message(
        db_session,
        dialog.id,
        "assistant",
        "Agent 已检查 profile 策略审计。",
        action_result={
            "type": "plan_recovery_tools",
            "status": "success",
            "data": {
                "agent_profile": "orchestrator",
                "agent_profile_policy_audit": {
                    "version": "phase215.agent_profile_policy_audit.v1",
                    "status": "needs_attention",
                    "summary": {"issues": 2, "delegate_edges": 4},
                    "issues": [
                        {
                            "code": "delegate_target_missing_definition",
                            "profile": "orchestrator",
                            "target": "ghost_worker",
                        }
                    ],
                },
            },
        },
    )

    messages = DialogMessageService(db_session).list_messages(project.id)
    detail_items = messages[-1]["action_result_view"]["detail_items"]

    assert {"label": "Agent 身份", "value": "编排主控"} in detail_items
    assert {"label": "策略审计", "value": "需关注：2 个问题"} in detail_items
    assert "delegate_target_missing_definition" not in str(detail_items)
    assert "ghost_worker" not in str(detail_items)


def test_get_messages_includes_agent_command_contract_detail_items(db_session):
    project = Project(name="Agent Command Contract Result View")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)
    dialogs_api._save_message(
        db_session,
        dialog.id,
        "assistant",
        "Agent 已检查命令契约。",
        action_result={
            "type": "plan_recovery_tools",
            "status": "success",
            "data": {
                "agent_profile": "orchestrator",
                "agent_command_contracts": {
                    "source": "planner_trace.agent_health_projection.command_contracts",
                    "summary": {
                        "agent_control_commands": 2,
                        "gap_count": 0,
                    },
                    "commands": [{"name": "continue"}],
                },
            },
        },
    )

    messages = DialogMessageService(db_session).list_messages(project.id)
    detail_items = messages[-1]["action_result_view"]["detail_items"]

    assert {"label": "Agent 身份", "value": "编排主控"} in detail_items
    assert {"label": "命令契约", "value": "已投影"} in detail_items
    assert {"label": "控制命令", "value": "2 个"} in detail_items
    assert {"label": "契约缺口", "value": "0 个"} in detail_items
    assert "planner_trace.agent_health_projection.command_contracts" not in str(detail_items)
    assert "continue" not in str(detail_items)


def test_get_messages_includes_agent_control_plane_readiness_detail_items(db_session):
    project = Project(name="Agent Control Plane Result View")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)
    dialogs_api._save_message(
        db_session,
        dialog.id,
        "assistant",
        "Agent 已检查控制平面。",
        action_result={
            "type": "plan_recovery_tools",
            "status": "success",
            "data": {
                "agent_profile": "orchestrator",
                "agent_control_plane_readiness": {
                    "source": "planner_trace.agent_health_projection.control_plane_readiness",
                    "status": "ready",
                    "version": "phase46.agent_control_plane_readiness.v1",
                    "summary": {
                        "tool_gap_count": 0,
                        "command_gap_count": 0,
                        "total_gap_count": 0,
                    },
                    "recommended_next_tools": ["inspect_agent_health_projection"],
                },
            },
        },
    )

    messages = DialogMessageService(db_session).list_messages(project.id)
    detail_items = messages[-1]["action_result_view"]["detail_items"]

    assert {"label": "Agent 身份", "value": "编排主控"} in detail_items
    assert {"label": "控制平面", "value": "可继续编排"} in detail_items
    assert {"label": "控制面缺口", "value": "0 个"} in detail_items
    assert {"label": "工具缺口", "value": "0 个"} in detail_items
    assert {"label": "命令缺口", "value": "0 个"} in detail_items
    assert {"label": "建议检查", "value": "1 项"} in detail_items
    assert "planner_trace.agent_health_projection.control_plane_readiness" not in str(detail_items)
    assert "inspect_agent_health_projection" not in str(detail_items)


@pytest.mark.asyncio
async def test_chapter_approval_followup_dispatches_execute_tool(db_session):
    project = Project(name="Chapter Approval Execute Dispatch")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)

    from app.services.writing_agent.dialog_control_plane import prepare_dialog_agent_run_dispatch

    prepare_dispatch = prepare_dialog_agent_run_dispatch(
        db_session,
        project_id=project.id,
        dialog_id=dialog.id,
        action_type="generate_chapter",
        command_args="2 承接上一章记忆线索",
        action_params={"project_id": project.id, "chapter_index": 2},
    )
    await prepare_dispatch.work(db_session, prepare_dispatch.task)

    pending = db_session.query(PendingAction).filter_by(dialog_id=dialog.id, status="pending").one()
    execute_dispatch = prepare_dialog_agent_run_dispatch(
        db_session,
        project_id=project.id,
        dialog_id=dialog.id,
        action_type=pending.type,
        command_args=pending.params.get("command_args"),
        action_params=pending.params,
    )

    tool = execute_dispatch.run.input["tools"][0]
    assert execute_dispatch.task.payload["action_type"] == "generate_chapter"
    assert tool["tool_name"] == "execute_generate_chapter_with_approval"
    assert tool["params"]["chapter_index"] == 2
    assert tool["params"]["confirm_execute"] is True
    assert tool["params"]["approval_contract_hash"] == pending.params["approval_contract_hash"]
    assert tool["params"]["approval_contract"] == pending.params["approval_contract"]


@pytest.mark.asyncio
async def test_chapter_approval_followup_resolve_action_records_decision_metadata(client, db_session):
    project = Project(name="Chapter Approval Decision Metadata")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)

    from app.services.writing_agent.dialog_control_plane import prepare_dialog_agent_run_dispatch

    prepare_dispatch = prepare_dialog_agent_run_dispatch(
        db_session,
        project_id=project.id,
        dialog_id=dialog.id,
        action_type="generate_chapter",
        command_args="2 承接上一章记忆线索",
        action_params={"project_id": project.id, "chapter_index": 2},
    )
    await prepare_dispatch.work(db_session, prepare_dispatch.task)

    pending = db_session.query(PendingAction).filter_by(dialog_id=dialog.id, status="pending").one()

    with patch("app.api.dialogs.LocalTaskRunner.start"):
        response = client.post(
            "/api/v1/dialog/resolve-action",
            json={"action_id": pending.id, "decision": "confirm"},
        )

    assert response.status_code == 200
    action_result = response.json()["action_result"]
    decision = action_result["data"]["approval_decision"]
    assert decision["kind"] == "pending_action_decision"
    assert decision["pending_action_id"] == pending.id
    assert decision["pending_action_type"] == "generate_chapter"
    assert decision["action_type"] == "generate_chapter"
    assert decision["decision"] == "confirm"
    assert decision["decision_comment"] == ""
    assert decision["approval_mode"] == "single"
    assert decision["approval_contract_hash"] == pending.params["approval_contract_hash"]
    assert decision["approval_contract_version"] == "phase108.agent_plan_approval_contract.v1"
    assert decision["chapter_index"] == 2
    assert decision["resolved_at"]
    view = response.json()["action_result_view"]
    assert view["detail_items"] == [
        {"label": "用户决策", "value": "已确认"},
        {"label": "审批模式", "value": "单次确认"},
        {"label": "目标章节", "value": "第2章"},
        {"label": "审批契约", "value": "已绑定"},
    ]
    assert pending.params["approval_contract_hash"] not in str(view)

    terminal = (
        db_session.query(DialogMessage)
        .filter(DialogMessage.dialog_id == dialog.id, DialogMessage.role == "system")
        .order_by(DialogMessage.created_at.desc())
        .first()
    )
    assert terminal.action_result["data"]["approval_decision"] == decision


@pytest.mark.asyncio
async def test_background_action_work_records_failure_message_on_exception(client, db_session, monkeypatch):
    r = client.post("/api/v1/projects", json={"name": "Background Failure Message"})
    pid = r.json()["id"]
    dialog = Dialog(project_id=pid, dialog_type="hermes", state="running")
    db_session.add(dialog)
    db_session.flush()
    task = BackgroundTask(project_id=pid, task_type="generate_setup", status="running")
    db_session.add(task)
    db_session.commit()

    async def fail_action(*_args, **_kwargs):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(dialogs_api, "_execute_action", fail_action)
    work = dialogs_api.build_action_background_work("generate_setup", pid, dialog.id)

    with pytest.raises(RuntimeError, match="model unavailable"):
        await work(db_session, task)

    db_session.expire_all()
    refreshed_dialog = db_session.query(Dialog).filter(Dialog.id == dialog.id).one()
    latest_message = (
        db_session.query(DialogMessage)
        .filter(DialogMessage.dialog_id == dialog.id)
        .order_by(DialogMessage.created_at.desc(), DialogMessage.id.desc())
        .first()
    )
    assert refreshed_dialog.state == "chatting"
    assert latest_message is not None
    assert "model unavailable" in latest_message.content
    assert latest_message.action_result == {"type": "generate_setup", "status": "failed"}


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
    ActionResultService(db_session).record_completion(
        action_type="generate_setup",
        project_id=pid,
        dialog_id=dialog.id,
        result=result_payload,
    )

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


def test_background_completion_attaches_generation_trace_to_system_message(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
    })
    dialog = db_session.query(Dialog).filter(Dialog.project_id == pid).first()
    trace = AIModelCallTrace(
        project_id=pid,
        trace_type="setup_generation",
        status="success",
        messages=[{"role": "user", "content": "生成设定"}],
        context_blocks=[],
    )
    db_session.add(trace)
    db_session.commit()
    ActionResultService(db_session).record_completion(
        action_type="generate_setup",
        project_id=pid,
        dialog_id=dialog.id,
        result={"status": "success", "trace_id": trace.id},
    )

    db_session.expire_all()
    latest_message = (
        db_session.query(dialogs_api.DialogMessage)
        .filter(dialogs_api.DialogMessage.dialog_id == dialog.id)
        .order_by(dialogs_api.DialogMessage.created_at.desc())
        .first()
    )
    db_session.refresh(trace)
    assert latest_message is not None
    assert trace.dialog_id == dialog.id
    assert trace.response_message_id == latest_message.id


def test_chapter_completion_mentions_skipped_athena_analysis(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    dialog = Dialog(project_id=pid, dialog_type="hermes", state="running")
    db_session.add(dialog)
    db_session.commit()

    message = ActionResultService(db_session).record_completion(
        action_type="generate_chapter",
        project_id=pid,
        dialog_id=dialog.id,
        result={
            "status": "success",
            "chapter_index": 1,
            "athena_analysis": {
                "status": "skipped",
                "reason": "missing_world_model_profile",
                "chapter_index": 1,
                "proposal_bundle_id": None,
                "created": {"proposal_items": 0},
                "skipped": {"duplicates": 0},
            },
        },
    )

    assert message is not None
    assert "第1章正文生成完成" in message.content
    assert "Athena 世界模型尚未导入" in message.content
    assert message.action_result["data"]["athena_analysis"]["reason"] == "missing_world_model_profile"


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

    with patch("app.api.dialogs.LocalTaskRunner.start"):
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
            with contextlib.suppress(threading.BrokenBarrierError):
                barrier.wait(timeout=1)
            from datetime import datetime as _RealDateTime
            return _RealDateTime.now(tz)

    with patch("app.api.dialogs.datetime", _SyncDateTime), patch("app.api.dialogs.LocalTaskRunner.start") as mock_start:
        def _confirm_once():
            return client.post("/api/v1/dialog/resolve-action", json={
                "action_id": action_id,
                "decision": "confirm",
            })

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = [f.result() for f in [pool.submit(_confirm_once), pool.submit(_confirm_once)]]

    statuses = sorted(resp.status_code for resp in responses)
    assert statuses == [200, 409]
    assert mock_start.call_count == 1


def test_resolve_action_confirm_passes_command_args_to_background(client, db_session):
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

    with patch("app.api.dialogs.LocalTaskRunner.start") as mock_start:
        r3 = client.post("/api/v1/dialog/resolve-action", json={
            "action_id": action_id,
            "decision": "confirm",
        })

    assert r3.status_code == 200
    mock_start.assert_called_once()
    run = db_session.query(WritingAgentRun).filter_by(project_id=pid).one()
    assert run.input["tools"][0]["tool_name"] == "prepare_generate_setup_execution"
    assert run.input["tools"][0]["command_args"] == "主角是植物学家"

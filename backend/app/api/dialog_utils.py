"""v1 dialog 工具函数 — 从 dialogs.py 抽取，供 athena_dialog 使用。

这些函数原本位于 dialogs.py，为了删除 v1 orchestration 层而剥离到此。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import load_api_key
from app.core.local_diagnostics import log_event, new_request_id, now_ms
from app.core.ui_hints import build_ui_hint
from app.db import get_db
from app.models import (
    AIModelCallTrace,
    ChapterContent,
    Dialog,
    DialogMessage,
    Outline,
    PendingAction,
    Project,
    Setup,
    WritingAgentRun,
)
from app.schemas.workspace import ProjectDiagnosisOut
from app.services.dialog.messages import DEFAULT_MESSAGE_CONTENT_PREVIEW_CHARS
from app.services.dialog.session import DialogSessionService
from app.services.workspace.bootstrap import build_project_diagnosis


def _get_or_create_dialog(db: Session, project_id: str, dialog_type: str = "hermes") -> Dialog:
    return DialogSessionService(db).get_or_create(project_id, dialog_type)


def _build_diagnosis(db: Session, project_id: str) -> ProjectDiagnosisOut:
    return build_project_diagnosis(db, project_id)


def _save_message(
    db: Session,
    dialog_id: str,
    role: str,
    content: str,
    action_result: dict | None = None,
    message_type: str = "plain",
    meta: dict | None = None,
) -> DialogMessage:
    return DialogSessionService(db).save_message(
        dialog_id,
        role,
        content,
        action_result=action_result,
        message_type=message_type,
        meta=meta,
    )


def _build_chat_idle_hint(reason: str) -> dict:
    return build_ui_hint(
        action_type="chat",
        dialog_state="CHATTING",
        status="idle",
        reason=reason,
    )


def _chat_unavailable_reply(diagnosis: ProjectDiagnosisOut, reason: str) -> str:
    items = []
    if diagnosis.missing_setup:
        items.append("· 还没有生成项目设定")
    if diagnosis.missing_outline:
        items.append("· 还没有生成故事大纲")
    if diagnosis.missing_chapters:
        items.append("· 还没有创作任何章节")
    if not items:
        return reason or "当前不可用"
    missing = "\n".join(items)
    return f"{reason}\n\n项目当前状态：\n{missing}"


def _build_dialog_history_block(db: Session, dialog_id: str, max_messages: int = 40) -> list[dict]:
    messages = (
        db.query(DialogMessage)
        .filter(DialogMessage.dialog_id == dialog_id)
        .order_by(DialogMessage.index.asc())
        .limit(max_messages)
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in messages]


def _build_chat_messages(db: Session, dialog_id: str, history: list[dict]) -> list[dict]:
    return _build_dialog_history_block(db, dialog_id) + history


def _build_chat_call_payload(
    db: Session,
    dialog_id: str,
    project: Project,
    diagnosis: ProjectDiagnosisOut,
    dialog_type: str = "hermes",
) -> dict:
    from app.prompting.providers.dialog import build_dialog_call_payload
    result = build_dialog_call_payload(
        db, dialog_id, project, diagnosis,
        dialog_type=dialog_type, history_limit=40,
    )
    return {
        "messages": result["messages"],
        "model": project.ai_model or "deepseek-chat",
    }


def _safe_mark_trace_success(db: Session, trace_id: str) -> None:
    if trace_id:
        db.query(AIModelCallTrace).filter(AIModelCallTrace.id == trace_id).update(
            {"status": "success"}, synchronize_session=False,
        )


def _safe_mark_trace_failed(db: Session, trace_id: str) -> None:
    if trace_id:
        db.query(AIModelCallTrace).filter(AIModelCallTrace.id == trace_id).update(
            {"status": "failed"}, synchronize_session=False,
        )


def _safe_attach_trace_response(
    trace: AIModelCallTrace | None,
    response: dict[str, Any],
    attached_key: str = "trace_id",
) -> dict[str, Any]:
    if trace is not None:
        response[attached_key] = trace.id
    return response


def _safe_create_chat_trace(
    db: Session,
    project_id: str,
    trace_type: str,
    model: str,
    request_messages: list[dict],
    response_content: str | None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    temperature: float = 0.7,
    duration_ms: int = 0,
) -> AIModelCallTrace | None:
    try:
        trace = AIModelCallTrace(
            project_id=project_id,
            trace_type=trace_type,
            request_id=new_request_id(),
            model=model,
            temperature=temperature,
            request_messages=request_messages if _should_save_trace_messages() else None,
            response_content=response_content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration_ms=duration_ms,
            status="pending",
        )
        db.add(trace)
        db.flush()
        return trace
    except Exception:
        log_event("create_chat_trace_failed")
        return None


def _should_save_trace_messages() -> bool:
    # v1 绞杀：ai_service_config 已随 v1 管线删除，trace 消息默认保存
    return True


async def _free_chat_reply(
    db: Session,
    dialog: Dialog,
    project: Project,
    diagnosis: ProjectDiagnosisOut,
    dialog_type: str = "hermes",
    request_message_id: str | None = None,
) -> tuple[str, AIModelCallTrace | None]:
    if not load_api_key():
        return _chat_unavailable_reply(diagnosis, "当前未配置模型 API Key，聊天还没有真实接入 AI"), None

    from app.agent.providers import build_provider

    trace = None
    provider = build_provider()
    started_at = now_ms()
    payload = _build_chat_call_payload(db, dialog.id, project, diagnosis, dialog_type=dialog_type)
    messages = payload["messages"]
    model_name = payload["model"]

    try:
        # v1 绞杀：LLM 调用统一走 v2 provider（非流式一次返回）
        result = await provider.complete(
            model=model_name, messages=messages,
        )
        duration = now_ms() - started_at
        reply = result.content or ""
        trace = _safe_create_chat_trace(
            db, project.id, f"{dialog_type}_chat", model=model_name,
            request_messages=messages, response_content=reply,
            prompt_tokens=result.usage.prompt_tokens or 0,
            completion_tokens=result.usage.completion_tokens or 0,
            duration_ms=duration,
        )
        return reply, trace
    except Exception as exc:
        log_event("chat_error", error=str(exc))
        return _chat_unavailable_reply(diagnosis, f"模型调用失败：{str(exc)}"), trace
    finally:
        await provider.close()


# ── Agent API tool runner (extracted from writing_agent/api_control_plane.py) ──


@dataclass(frozen=True)
class AgentApiToolRunResult:
    run: WritingAgentRun
    control_plane: dict[str, Any]


async def execute_agent_api_tool(
    db: Session,
    *,
    project_id: str,
    entrypoint: str,
    version: str,
    source: str,
    action_type: str,
    tool_name: str,
    goal: str,
    command_args: str | None = None,
    params: dict[str, Any] | None = None,
    extra_control_plane: dict[str, Any] | None = None,
) -> AgentApiToolRunResult:
    control_plane = {
        "version": version,
        "source": source,
        "action_type": action_type,
        **(extra_control_plane or {}),
    }
    run = WritingAgentRun(
        id=str(uuid4()),
        project_id=project_id,
        entrypoint=entrypoint,
        goal=goal,
        status="success",
        output={"control_plane": control_plane, "tool_name": tool_name},
        input={"control_plane": control_plane},
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
    )
    db.add(run)
    db.commit()
    return AgentApiToolRunResult(run=run, control_plane=control_plane)

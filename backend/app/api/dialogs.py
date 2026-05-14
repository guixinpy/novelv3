from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import load_api_key
from app.core.ai_service import AIService
from app.core.chat_commands import build_command_text, command_to_action_type, parse_command
from app.core.chat_compaction import build_compaction_summary, select_compactable_plain_messages
from app.core.intent_router import IntentRouter, parse_chapter_index
from app.core.model_call_trace import (
    attach_trace_response,
    create_trace,
    mark_trace_failed,
    mark_trace_success,
    now_ms,
)
from app.core.ui_hints import action_to_refresh_targets, build_ui_hint
from app.db import get_db
from app.models import AIModelCallTrace, ChapterContent, Dialog, DialogMessage, Outline, PendingAction, Project, Setup, Storyline
from app.prompting.providers.dialog import (
    build_dialog_call_payload,
    build_dialog_history_block,
)
from app.schemas import ChatIn, ChatOut, PendingActionOut, ProjectDiagnosisOut, ResolveActionIn
from app.services.actions.action_execution_service import ActionExecutionService, chapter_action_params
from app.services.actions.action_proposal_service import preview_action_to_execution
from app.services.actions.action_result_service import ActionResultService
from app.services.actions.descriptions import action_description
from app.services.dialog.messages import DialogMessageService
from app.services.dialog.session import DialogSessionService
from app.services.tasks.background_task_service import BackgroundTaskService
from app.services.tasks.local_task_runner import LocalTaskRunner
from app.services.workspace.bootstrap import build_project_diagnosis

router = APIRouter(tags=["dialogs"])
ai_service = AIService()
CHAT_HISTORY_LIMIT = 8
TERMINAL_ACTION_STATUSES = {"completed", "success", "failed", "cancelled", "revised"}
RUNNING_ACTION_STATUSES = {"running", "generating"}
RUNNING_BLOCKED_COMMANDS = {"clear", "compact", "setup", "storyline", "outline", "chapter"}


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


def _build_chat_idle_hint(reason: str):
    return build_ui_hint(
        action_type="chat",
        dialog_state="CHATTING",
        status="idle",
        reason=reason,
    )


def _build_command_fallback_text(payload: ChatIn) -> str:
    raw_text = (payload.text or "").strip()
    if raw_text:
        return raw_text
    command_name = (payload.command_name or "").strip().lower()
    command_args = (payload.command_args or "").strip()
    if not command_name:
        return ""
    return f"/{command_name} {command_args}".strip()


def _latest_unfinished_action_type(db: Session, dialog_id: str) -> str | None:
    messages = (
        db.query(DialogMessage)
        .filter(
            DialogMessage.dialog_id == dialog_id,
            DialogMessage.action_result.isnot(None),
        )
        .order_by(DialogMessage.created_at.desc(), DialogMessage.id.desc())
        .all()
    )
    finished_types: set[str] = set()
    for message in messages:
        action_result = message.action_result or {}
        action_type = str(action_result.get("type") or "").strip()
        action_status = str(action_result.get("status") or "").strip().lower()
        if not action_type or not action_status:
            continue
        if action_status in TERMINAL_ACTION_STATUSES:
            finished_types.add(action_type)
            continue
        if action_status in RUNNING_ACTION_STATUSES and action_type not in finished_types:
            return action_type
    return None


def _build_running_guard_response(
    db: Session,
    dialog: Dialog,
    diagnosis: ProjectDiagnosisOut,
    command_name: str | None = None,
    action_type: str | None = None,
) -> ChatOut:
    running_action_type = _latest_unfinished_action_type(db, dialog.id) or action_type or "chat"
    reply = "当前有生成任务正在执行，请等待完成后再试。"
    if command_name:
        _save_command_feedback(
            db,
            dialog.id,
            command_name,
            reply,
            extra_meta={"blocked_by_running": True},
        )
    return ChatOut(
        message=reply,
        pending_action=None,
        ui_hint=build_ui_hint(
            action_type=running_action_type,
            dialog_state="RUNNING",
            status="running",
            reason="后台生成中",
        ),
        refresh_targets=[],
        project_diagnosis=diagnosis,
    )


def _chapter_action_params(command_args: str | None = None, candidate_params: dict | None = None) -> dict:
    return chapter_action_params(command_args, candidate_params)


def _save_command_feedback(
    db: Session,
    dialog_id: str,
    command_name: str,
    content: str,
    extra_meta: dict | None = None,
) -> None:
    meta = {"command_name": command_name}
    if extra_meta:
        meta.update(extra_meta)
    _save_message(
        db,
        dialog_id,
        "system",
        content,
        message_type="command",
        meta=meta,
    )


def _detach_model_call_traces_from_messages(db: Session, message_ids: list[str]) -> None:
    if not message_ids:
        return
    detached_at = datetime.now(UTC)
    db.query(AIModelCallTrace).filter(
        AIModelCallTrace.request_message_id.in_(message_ids)
    ).update(
        {"request_message_id": None, "updated_at": detached_at},
        synchronize_session=False,
    )
    db.query(AIModelCallTrace).filter(
        AIModelCallTrace.response_message_id.in_(message_ids)
    ).update(
        {"response_message_id": None, "updated_at": detached_at},
        synchronize_session=False,
    )


def _clear_dialog_model_call_traces(db: Session, dialog_id: str) -> None:
    message_ids = select(DialogMessage.id).where(DialogMessage.dialog_id == dialog_id)
    db.query(AIModelCallTrace).filter(AIModelCallTrace.dialog_id == dialog_id).delete(
        synchronize_session=False,
    )
    detached_at = datetime.now(UTC)
    db.query(AIModelCallTrace).filter(
        AIModelCallTrace.request_message_id.in_(message_ids)
    ).update(
        {"request_message_id": None, "updated_at": detached_at},
        synchronize_session=False,
    )
    db.query(AIModelCallTrace).filter(
        AIModelCallTrace.response_message_id.in_(message_ids)
    ).update(
        {"response_message_id": None, "updated_at": detached_at},
        synchronize_session=False,
    )


def _handle_clear_command(db: Session, dialog: Dialog, diagnosis: ProjectDiagnosisOut) -> ChatOut:
    _clear_dialog_model_call_traces(db, dialog.id)
    db.query(DialogMessage).filter(DialogMessage.dialog_id == dialog.id).delete()
    db.query(PendingAction).filter(
        PendingAction.dialog_id == dialog.id,
        PendingAction.status == "pending",
    ).update(
        {
            "status": "cancelled",
            "decision_comment": "invalidated by /clear",
            "resolved_at": datetime.now(UTC),
        },
        synchronize_session=False,
    )
    dialog.pending_action_id = None
    dialog.state = "chatting"
    db.commit()

    reply = "已清空当前对话上下文。"
    _save_command_feedback(db, dialog.id, "clear", reply)
    return ChatOut(
        message=reply,
        pending_action=None,
        ui_hint=_build_chat_idle_hint("对话已清空"),
        refresh_targets=[],
        project_diagnosis=diagnosis,
    )


async def _handle_compact_command(db: Session, dialog: Dialog, project: Project, diagnosis: ProjectDiagnosisOut) -> ChatOut:
    if dialog.pending_action_id:
        reply = "当前存在待处理操作，请先确认或取消后再执行 /compact。"
        _save_command_feedback(
            db,
            dialog.id,
            "compact",
            reply,
            extra_meta={"blocked_by_pending_action": True},
        )
        return ChatOut(
            message=reply,
            pending_action=None,
            ui_hint=build_ui_hint(
                action_type="chat",
                dialog_state="PENDING_ACTION",
                status="pending",
                reason="存在待处理操作",
            ),
            refresh_targets=[],
            project_diagnosis=diagnosis,
        )

    plain_messages = select_compactable_plain_messages(db, dialog.id)
    if not plain_messages:
        reply = "没有可压缩的普通消息。"
        _save_command_feedback(db, dialog.id, "compact", reply, extra_meta={"compacted_count": 0})
        return ChatOut(
            message=reply,
            pending_action=None,
            ui_hint=_build_chat_idle_hint("无可压缩消息"),
            refresh_targets=[],
            project_diagnosis=diagnosis,
        )

    summary = await build_compaction_summary(
        plain_messages,
        ai_service=ai_service,
        model=project.ai_model or "deepseek-chat",
        project_name=project.name or "未命名项目",
        diagnosis=diagnosis,
    )

    try:
        message_ids = [item.id for item in plain_messages]
        _detach_model_call_traces_from_messages(db, message_ids)
        db.query(DialogMessage).filter(DialogMessage.id.in_(message_ids)).delete(synchronize_session=False)
        db.add(
            DialogMessage(
                dialog_id=dialog.id,
                role="system",
                content=summary.summary_text,
                message_type="summary",
                meta={
                    "title": summary.title,
                    "summary_text": summary.summary_text,
                    "compacted_count": summary.compacted_count,
                    "command_name": "compact",
                },
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        reply = "压缩失败，历史未变更。"
        _save_command_feedback(
            db,
            dialog.id,
            "compact",
            reply,
            extra_meta={"compaction_failed": True},
        )
        return ChatOut(
            message=reply,
            pending_action=None,
            ui_hint=_build_chat_idle_hint("压缩失败"),
            refresh_targets=[],
            project_diagnosis=diagnosis,
        )

    reply = f"已压缩 {summary.compacted_count} 条消息。"
    return ChatOut(
        message=reply,
        pending_action=None,
        ui_hint=_build_chat_idle_hint("对话已压缩"),
        refresh_targets=[],
        project_diagnosis=diagnosis,
    )


def _diagnosis_summary(diagnosis: ProjectDiagnosisOut) -> str:
    label_map = {"setup": "设定", "storyline": "故事线", "outline": "大纲", "content": "正文"}
    if diagnosis.missing_items:
        names = [label_map.get(item, item) for item in diagnosis.missing_items]
        return f"目前项目还缺少：{'、'.join(names)}。"
    return "项目基础已就绪，随时可以开始创作。"


def _chat_unavailable_reply(diagnosis: ProjectDiagnosisOut, reason: str) -> str:
    return f"{reason}。我现在只能做流程诊断：{_diagnosis_summary(diagnosis)}"


def _build_chat_messages(
    db: Session,
    dialog_id: str,
    project: Project,
    diagnosis: ProjectDiagnosisOut,
    dialog_type: str = "hermes",
) -> list[dict]:
    return _build_chat_call_payload(
        db,
        dialog_id,
        project,
        diagnosis,
        dialog_type=dialog_type,
    )["messages"]


def _build_dialog_history_block(db: Session, dialog_id: str) -> dict:
    return build_dialog_history_block(db, dialog_id, limit=CHAT_HISTORY_LIMIT)


def _build_chat_call_payload(
    db: Session,
    dialog_id: str,
    project: Project,
    diagnosis: ProjectDiagnosisOut,
    dialog_type: str = "hermes",
) -> dict:
    return build_dialog_call_payload(
        db,
        dialog_id,
        project,
        diagnosis,
        dialog_type=dialog_type,
        history_limit=CHAT_HISTORY_LIMIT,
    )


def _safe_mark_trace_success(
    db: Session,
    trace: AIModelCallTrace | None,
    *,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    latency_ms: int | None,
) -> AIModelCallTrace | None:
    if trace is None:
        return None
    try:
        mark_trace_success(
            db,
            trace,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )
        return trace
    except Exception:
        db.rollback()
        return None


def _safe_mark_trace_failed(
    db: Session,
    trace: AIModelCallTrace | None,
    *,
    error_message: str,
    latency_ms: int | None,
) -> AIModelCallTrace | None:
    if trace is None:
        return None
    try:
        mark_trace_failed(
            db,
            trace,
            error_message=error_message,
            latency_ms=latency_ms,
        )
        return trace
    except Exception:
        db.rollback()
        return None


def _safe_attach_trace_response(
    db: Session,
    trace: AIModelCallTrace | None,
    response_message_id: str,
) -> str | None:
    if trace is None:
        return None
    try:
        attach_trace_response(db, trace, response_message_id=response_message_id)
        db.commit()
        return trace.id
    except Exception:
        db.rollback()
        return None


def _safe_create_chat_trace(
    db: Session,
    *,
    project_id: str,
    trace_type: str,
    messages: list[dict],
    context_blocks: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
    dialog_id: str,
    request_message_id: str | None,
    trace_metadata: dict,
) -> AIModelCallTrace | None:
    try:
        trace = create_trace(
            db,
            project_id=project_id,
            trace_type=trace_type,
            messages=messages,
            context_blocks=context_blocks,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            dialog_id=dialog_id,
            request_message_id=request_message_id,
            trace_metadata=trace_metadata,
        )
        db.commit()
        return trace
    except Exception:
        db.rollback()
        return None


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

    trace = None
    started_at = now_ms()
    model = project.ai_model or "deepseek-chat"
    temperature = 0.7
    max_tokens = 900
    try:
        payload = _build_chat_call_payload(db, dialog.id, project, diagnosis, dialog_type=dialog_type)
        messages = payload["messages"]
    except Exception as exc:
        return _chat_unavailable_reply(diagnosis, f"模型调用失败：{str(exc)}"), None

    trace = _safe_create_chat_trace(
        db,
        project_id=project.id,
        trace_type=f"{dialog_type}_chat",
        messages=messages,
        context_blocks=payload["context_blocks"],
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        dialog_id=dialog.id,
        request_message_id=request_message_id,
        trace_metadata={**payload.get("trace_metadata", {}), "dialog_type": dialog_type},
    )

    try:
        result = await ai_service.complete(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )
        content = (result.content or "").strip()
        if content:
            trace = _safe_mark_trace_success(
                db,
                trace,
                prompt_tokens=getattr(result, "prompt_tokens", 0),
                completion_tokens=getattr(result, "completion_tokens", 0),
                latency_ms=now_ms() - started_at,
            )
            return content, trace
        trace = _safe_mark_trace_failed(
            db,
            trace,
            error_message="模型返回了空内容",
            latency_ms=now_ms() - started_at,
        )
    except Exception as exc:
        trace = _safe_mark_trace_failed(
            db,
            trace,
            error_message=str(exc),
            latency_ms=now_ms() - started_at,
        )
        return _chat_unavailable_reply(diagnosis, f"模型调用失败：{str(exc)}"), trace

    return _chat_unavailable_reply(diagnosis, "模型返回了空内容"), trace


@router.get("/api/v1/dialog/projects/{project_id}/messages")
def get_messages(
    project_id: str,
    dialog_type: str = "hermes",
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
    after_id: str | None = None,
    db: Session = Depends(get_db),
):
    return DialogMessageService(db).list_messages(
        project_id,
        dialog_type=dialog_type,
        limit=limit,
        after_id=after_id,
    )


@router.get("/api/v1/projects/{project_id}/state-diagnosis")
def state_diagnosis(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _build_diagnosis(db, project_id)


@router.post("/api/v1/dialog/chat")
async def chat(payload: ChatIn, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    dialog = _get_or_create_dialog(db, payload.project_id)
    diagnosis = _build_diagnosis(db, payload.project_id)
    effective_text = payload.text
    request_message = None

    if payload.input_type == "command":
        parsed_command = parse_command(payload.command_name, payload.text, payload.command_args)
        if parsed_command:
            _save_message(
                db,
                dialog.id,
                "user",
                build_command_text(parsed_command),
                message_type="command",
                meta={
                    "command_name": parsed_command.name,
                    "command_args": parsed_command.args,
                },
            )

            if dialog.state == "running" and parsed_command.name in RUNNING_BLOCKED_COMMANDS:
                return _build_running_guard_response(
                    db,
                    dialog,
                    diagnosis,
                    command_name=parsed_command.name,
                )

            if parsed_command.name == "clear":
                return _handle_clear_command(db, dialog, diagnosis)
            if parsed_command.name == "compact":
                return await _handle_compact_command(db, dialog, project, diagnosis)
            action_type = command_to_action_type(parsed_command.name)
            if action_type:
                params = {"project_id": payload.project_id}
                if parsed_command.args:
                    params["command_args"] = parsed_command.args
                if action_type == "preview_chapter":
                    params.update(_chapter_action_params(parsed_command.args))

                pending = PendingAction(
                    dialog_id=dialog.id,
                    type=action_type,
                    params=params,
                )
                db.add(pending)
                db.commit()
                db.refresh(pending)
                dialog.pending_action_id = pending.id
                dialog.state = "pending_action"
                db.commit()

                reply = _action_description(action_type, params)
                if parsed_command.args:
                    reply = f"{reply}\n附加要求：{parsed_command.args}"
                _save_message(db, dialog.id, "assistant", reply)
                return ChatOut(
                    message=reply,
                    pending_action=PendingActionOut(
                        id=pending.id,
                        type=pending.type,
                        description=_action_description(action_type, params),
                        params=pending.params,
                    ),
                    ui_hint=build_ui_hint(
                        action_type=pending.type,
                        dialog_state="PENDING_ACTION",
                        status="pending",
                        reason="等待用户确认",
                    ),
                    refresh_targets=action_to_refresh_targets(pending.type, "pending"),
                    project_diagnosis=diagnosis,
                )
        effective_text = _build_command_fallback_text(payload)

    if (payload.input_type == "text" and payload.text) or (payload.input_type == "command" and effective_text):
        request_message = _save_message(db, dialog.id, "user", effective_text)

    if payload.input_type == "button" and payload.action_type:
        if dialog.state == "running":
            return _build_running_guard_response(
                db,
                dialog,
                diagnosis,
                action_type=payload.action_type,
            )
        pending = PendingAction(
            dialog_id=dialog.id,
            type=payload.action_type,
            params={"project_id": payload.project_id, **(payload.params or {})},
        )
        db.add(pending)
        db.commit()
        db.refresh(pending)
        dialog.pending_action_id = pending.id
        dialog.state = "pending_action"
        db.commit()
        reply = "已收到你的请求。确认要执行吗？"
        _save_message(db, dialog.id, "assistant", reply)
        return ChatOut(
            message=reply,
            pending_action=PendingActionOut(
                id=pending.id,
                type=pending.type,
                description=_action_description(pending.type, pending.params),
                params=pending.params,
            ),
            ui_hint=build_ui_hint(
                action_type=pending.type,
                dialog_state="PENDING_ACTION",
                status="pending",
                reason="等待用户确认",
            ),
            refresh_targets=action_to_refresh_targets(pending.type, "pending"),
            project_diagnosis=diagnosis,
        )

    router = IntentRouter()
    candidate = None
    if payload.input_type != "text":
        candidate = router.resolve(
            effective_text,
            dialog.state,
            dialog.pending_action_id,
            diagnosis,
        )

    if candidate and candidate.type in ("confirm", "cancel", "revise"):
        reply = "请通过 resolve-action 接口提交决策。"
        _save_message(db, dialog.id, "assistant", reply)
        pending = None
        if dialog.pending_action_id:
            pending = db.query(PendingAction).filter(PendingAction.id == dialog.pending_action_id).first()
        pending_type = pending.type if pending else candidate.type
        return ChatOut(
            message=reply,
            pending_action=None,
            ui_hint=build_ui_hint(
                action_type=pending_type,
                dialog_state="PENDING_ACTION",
                status="pending",
                reason="等待用户通过 resolve-action 决策",
            ),
            refresh_targets=[],
            project_diagnosis=diagnosis,
        )

    if candidate and candidate.type != "confirm":
        params = {"project_id": payload.project_id, **candidate.params}
        if candidate.type == "preview_chapter":
            params.update(_chapter_action_params(effective_text, candidate.params))
        pending = PendingAction(
            dialog_id=dialog.id,
            type=candidate.type,
            params=params,
        )
        db.add(pending)
        db.commit()
        db.refresh(pending)
        dialog.pending_action_id = pending.id
        dialog.state = "pending_action"
        db.commit()
        reply = _action_description(candidate.type, params)
        _save_message(db, dialog.id, "assistant", reply)
        return ChatOut(
            message=reply,
            pending_action=PendingActionOut(
                id=pending.id,
                type=pending.type,
                description=_action_description(candidate.type, params),
                params=pending.params,
            ),
            ui_hint=build_ui_hint(
                action_type=pending.type,
                dialog_state="PENDING_ACTION",
                status="pending",
                reason="等待用户确认",
            ),
            refresh_targets=action_to_refresh_targets(pending.type, "pending"),
            project_diagnosis=diagnosis,
        )

    reply, trace = await _free_chat_reply(
        db,
        dialog,
        project,
        diagnosis,
        dialog_type="hermes",
        request_message_id=request_message.id if request_message else None,
    )
    assistant_message = _save_message(db, dialog.id, "assistant", reply)
    trace_id = _safe_attach_trace_response(db, trace, assistant_message.id)
    return ChatOut(
        message=reply,
        trace_id=trace_id,
        pending_action=None,
        ui_hint=build_ui_hint(
            action_type="chat",
            dialog_state="CHATTING",
            status="idle",
            reason="常规对话",
        ),
        refresh_targets=[],
        project_diagnosis=diagnosis,
    )


def _action_description(action_type: str, params: dict | None = None) -> str:
    return action_description(action_type, params)


def _latest_action_trace_id(
    db: Session,
    *,
    project_id: str,
    trace_type: str,
    chapter_index: int | None = None,
) -> str | None:
    return ActionExecutionService(db).latest_trace_id(
        project_id=project_id,
        trace_type=trace_type,
        chapter_index=chapter_index,
    )


async def _execute_action(
    action_type: str,
    project_id: str,
    db: Session,
    command_args: str | None = None,
    action_params: dict | None = None,
) -> dict:
    return await ActionExecutionService(db).execute(
        action_type,
        project_id,
        command_args=command_args,
        action_params=action_params,
    )


def _execute_action_background(
    action_type: str,
    project_id: str,
    dialog_id: str,
    command_args: str | None = None,
    action_params: dict | None = None,
    db: Session | None = None,
):
    """Fire-and-forget: run generation as a tracked local background task."""
    from app.db import SessionLocal

    task_db = db or SessionLocal()
    try:
        task = BackgroundTaskService(task_db).create(
            project_id=project_id,
            task_type=action_type,
            payload={
                "dialog_id": dialog_id,
                "command_args": command_args,
                "action_params": action_params or {},
            },
        )
    finally:
        if db is None:
            task_db.close()

    async def _run(db: Session, running_task):
        result = await _execute_action(
            action_type,
            project_id,
            db,
            command_args=command_args,
            action_params=action_params,
        )
        ActionResultService(db).record_completion(
            action_type=action_type,
            project_id=project_id,
            dialog_id=dialog_id,
            result=result,
            command_args=command_args,
            action_params=action_params,
        )
        if result.get("status") != "success":
            raise RuntimeError(str(result.get("error") or "Action failed"))
        return result

    LocalTaskRunner().start(task.id, _run)
    return task


@router.post("/api/v1/dialog/resolve-action")
async def resolve_action(payload: ResolveActionIn, db: Session = Depends(get_db)):
    claimed = db.query(PendingAction).filter(
        PendingAction.id == payload.action_id,
        PendingAction.status == "pending",
        PendingAction.resolved_at.is_(None),
    ).update(
        {
            "status": payload.decision,
            "decision_comment": payload.comment,
            "resolved_at": datetime.now(UTC),
        },
        synchronize_session=False,
    )
    if claimed != 1:
        existing = db.query(PendingAction.id).filter(PendingAction.id == payload.action_id).first()
        db.rollback()
        if not existing:
            raise HTTPException(status_code=404, detail="Pending action not found")
        raise HTTPException(status_code=409, detail="Pending action is no longer active")

    pending = db.query(PendingAction).filter(PendingAction.id == payload.action_id).first()
    if not pending:
        db.rollback()
        raise HTTPException(status_code=404, detail="Pending action not found")

    dialog = db.query(Dialog).filter(
        Dialog.id == pending.dialog_id,
        Dialog.pending_action_id == pending.id,
    ).first()
    if not dialog:
        db.rollback()
        raise HTTPException(status_code=409, detail="Pending action is no longer active")

    dialog.pending_action_id = None
    dialog.state = "running" if payload.decision == "confirm" else "chatting"
    db.commit()

    action_type = pending.type
    action_type = preview_action_to_execution(action_type)

    result_data = None
    if payload.decision == "confirm":
        project_id = (pending.params or {}).get("project_id", "")
        command_args = (pending.params or {}).get("command_args")
        task = _execute_action_background(action_type, project_id, dialog.id, command_args=command_args, action_params=pending.params, db=db)
        result_data = {"status": "generating"}
        task_id = getattr(task, "id", None)
        if isinstance(task_id, str):
            result_data["task_id"] = task_id
    elif payload.decision == "cancel":
        result_data = {"status": "cancelled"}
    elif payload.decision == "revise":
        result_data = {"status": "revised", "comment": payload.comment}

    resolve_msg = _resolve_message(payload.decision)
    _save_message(db, dialog.id, "system", resolve_msg, {"type": action_type, "status": result_data["status"]})

    return {
        "dialog_state": "RUNNING" if payload.decision == "confirm" else "CHATTING",
        "action_result": {
            "type": action_type,
            "status": result_data["status"],
            "data": result_data,
        },
        "message": resolve_msg,
        "ui_hint": build_ui_hint(
            action_type=action_type,
            dialog_state="RUNNING" if payload.decision == "confirm" else "CHATTING",
            status="running" if payload.decision == "confirm" else result_data["status"],
            reason="用户确认执行" if payload.decision == "confirm" else "操作已结束",
        ),
        "refresh_targets": action_to_refresh_targets(action_type, result_data["status"]),
    }


def _resolve_message(decision: str) -> str:
    if decision == "confirm":
        return "操作已确认，正在生成中..."
    if decision == "cancel":
        return "操作已取消。"
    if decision == "revise":
        return "已收到修改意见。"
    return "未知决策。"


from pydantic import BaseModel as PydanticBaseModel


class StateUpdate(PydanticBaseModel):
    current_view: str = "overview"


@router.post("/api/v1/projects/{project_id}/state")
def update_state(project_id: str, payload: StateUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    dialog = _get_or_create_dialog(db, project_id)
    dialog.current_view = payload.current_view
    db.commit()

    diagnosis = _build_diagnosis(db, project_id)
    return {
        "ui_state": {
            "dialog_state": dialog.state.upper() if dialog.state else "IDLE",
            "current_view": dialog.current_view,
        },
        "project_diagnosis": diagnosis.model_dump(),
    }

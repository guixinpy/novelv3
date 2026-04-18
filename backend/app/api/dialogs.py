import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Project, Setup, Storyline, Outline, ChapterContent, Dialog, DialogMessage, PendingAction
from app.schemas import ChatOut, ChatIn, ResolveActionIn, ProjectDiagnosisOut, PendingActionOut, ChatMessageOut
from app.core.ai_service import AIService
from app.core.chat_commands import build_command_text, parse_command
from app.core.chat_compaction import build_compaction_summary, select_compactable_plain_messages
from app.core.prompt_manager import PromptManager
from app.config import load_api_key
from datetime import datetime, timezone
from app.core.intent_router import IntentRouter
from app.core.ui_hints import build_ui_hint, action_to_refresh_targets

router = APIRouter(tags=["dialogs"])
ai_service = AIService()
CHAT_HISTORY_LIMIT = 8
PHASE_LABELS = {
    "setup": "设定阶段",
    "storyline": "故事线阶段",
    "outline": "大纲阶段",
    "content": "正文阶段",
}
STATUS_LABELS = {
    "draft": "待补全",
    "writing": "正文写作中",
    "outline_generated": "大纲已生成",
    "storyline_generated": "故事线已生成",
    "setup_approved": "设定已确认",
}


def _get_or_create_dialog(db: Session, project_id: str) -> Dialog:
    dialog = db.query(Dialog).filter(Dialog.project_id == project_id).first()
    if not dialog:
        dialog = Dialog(project_id=project_id)
        db.add(dialog)
        db.commit()
        db.refresh(dialog)
    return dialog


def _build_diagnosis(db: Session, project_id: str) -> ProjectDiagnosisOut:
    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    storyline = db.query(Storyline).filter(Storyline.project_id == project_id).first()
    outline = db.query(Outline).filter(Outline.project_id == project_id).first()
    chapters = db.query(ChapterContent).filter(ChapterContent.project_id == project_id).count()

    completed = []
    missing = []
    next_step = None

    if setup and setup.status == "generated":
        completed.append("setup")
    else:
        missing.append("setup")
        next_step = "preview_setup"

    if storyline and storyline.status == "generated":
        completed.append("storyline")
    else:
        missing.append("storyline")
        if not next_step:
            next_step = "preview_storyline"

    if outline and outline.status == "generated":
        completed.append("outline")
    else:
        missing.append("outline")
        if not next_step:
            next_step = "preview_outline"

    if chapters > 0:
        completed.append("content")
    else:
        missing.append("content")
        if not next_step:
            next_step = "preview_outline"

    return ProjectDiagnosisOut(
        missing_items=missing,
        completed_items=completed,
        suggested_next_step=next_step,
    )


def _save_message(
    db: Session,
    dialog_id: str,
    role: str,
    content: str,
    action_result: dict | None = None,
    message_type: str = "text",
    meta: dict | None = None,
):
    msg = DialogMessage(
        dialog_id=dialog_id,
        role=role,
        content=content,
        action_result=action_result,
        message_type=message_type,
        meta=meta,
    )
    db.add(msg)
    db.commit()


def _build_chat_idle_hint(reason: str):
    return build_ui_hint(
        action_type="chat",
        dialog_state="CHATTING",
        status="idle",
        reason=reason,
    )


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


def _handle_clear_command(db: Session, dialog: Dialog, diagnosis: ProjectDiagnosisOut) -> ChatOut:
    db.query(DialogMessage).filter(DialogMessage.dialog_id == dialog.id).delete()
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
    )

    message_ids = [item.id for item in plain_messages]
    db.query(DialogMessage).filter(DialogMessage.id.in_(message_ids)).delete(synchronize_session=False)
    db.commit()

    _save_message(
        db,
        dialog.id,
        "system",
        summary.summary_text,
        message_type="summary",
        meta={
            "title": summary.title,
            "summary_text": summary.summary_text,
            "compacted_count": summary.compacted_count,
            "command_name": "compact",
        },
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


def _phase_label(phase: str | None) -> str:
    return PHASE_LABELS.get(phase or "", phase or "未开始")


def _status_label(status: str | None) -> str:
    return STATUS_LABELS.get(status or "", status or "待补全")


def _build_chat_messages(db: Session, dialog_id: str, project: Project, diagnosis: ProjectDiagnosisOut) -> list[dict]:
    pm = PromptManager()
    history = db.query(DialogMessage) \
        .filter(DialogMessage.dialog_id == dialog_id) \
        .order_by(DialogMessage.created_at.desc()) \
        .limit(CHAT_HISTORY_LIMIT) \
        .all()

    history.reverse()
    system_prompt = pm.load(
        "chat_project_assistant",
        {
            "project_name": project.name or "未命名项目",
            "project_genre": project.genre or "未分类题材",
            "project_description": project.description or "暂无项目描述",
            "project_phase": _phase_label(project.current_phase),
            "project_status": _status_label(project.status),
            "current_words": str(project.current_word_count or 0),
            "target_words": str(project.target_word_count or 0),
            "completed_items": "、".join(diagnosis.completed_items) if diagnosis.completed_items else "无",
            "missing_items": "、".join(diagnosis.missing_items) if diagnosis.missing_items else "无",
            "suggested_next_step": diagnosis.suggested_next_step or "无",
        },
    )
    messages = [{"role": "system", "content": system_prompt}]

    for item in history:
        if item.role in ("user", "assistant"):
            messages.append({"role": item.role, "content": item.content})
        elif item.role == "system":
            messages.append({"role": "assistant", "content": f"[系统消息] {item.content}"})

    return messages


async def _free_chat_reply(db: Session, dialog: Dialog, project: Project, diagnosis: ProjectDiagnosisOut) -> str:
    if not load_api_key():
        return _chat_unavailable_reply(diagnosis, "当前未配置模型 API Key，聊天还没有真实接入 AI")

    try:
        messages = _build_chat_messages(db, dialog.id, project, diagnosis)
        result = await ai_service.complete(
            messages,
            temperature=0.7,
            max_tokens=900,
            model=project.ai_model or "deepseek-chat",
        )
        content = (result.content or "").strip()
        if content:
            return content
    except Exception as exc:
        return _chat_unavailable_reply(diagnosis, f"模型调用失败：{str(exc)}")

    return _chat_unavailable_reply(diagnosis, "模型返回了空内容")


@router.get("/api/v1/dialog/projects/{project_id}/messages")
def get_messages(project_id: str, db: Session = Depends(get_db)):
    dialog = db.query(Dialog).filter(Dialog.project_id == project_id).first()
    if not dialog:
        return []
    msgs = db.query(DialogMessage).filter(DialogMessage.dialog_id == dialog.id).order_by(DialogMessage.created_at).all()
    pending_action = None
    if dialog.pending_action_id:
        pending = db.query(PendingAction).filter(PendingAction.id == dialog.pending_action_id).first()
        if pending:
            pending_action = PendingActionOut(
                id=pending.id,
                type=pending.type,
                description=_action_description(pending.type),
                params=pending.params,
            ).model_dump()

    last_assistant_message_id = None
    if pending_action:
        for message in reversed(msgs):
            if message.role == "assistant":
                last_assistant_message_id = message.id
                break

    payload = []
    for message in msgs:
        item = {
            "role": message.role,
            "message_type": message.message_type,
            "content": message.content,
            "meta": message.meta,
            "action_result": message.action_result,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        }
        if pending_action and message.id == last_assistant_message_id:
            item["pending_action"] = pending_action
        payload.append(item)
    return payload


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

    if payload.input_type == "command":
        parsed_command = parse_command(payload.command_name, payload.text, payload.command_args)
        if parsed_command:
            _save_message(
                db,
                dialog.id,
                "user",
                build_command_text(parsed_command, payload.text),
                message_type="command",
                meta={
                    "command_name": parsed_command.name,
                    "command_args": parsed_command.args,
                },
            )

            if parsed_command.name == "clear":
                return _handle_clear_command(db, dialog, diagnosis)
            if parsed_command.name == "compact":
                return await _handle_compact_command(db, dialog, project, diagnosis)

        command_content = payload.text or (f"/{payload.command_name}" if payload.command_name else "")
        if command_content:
            _save_message(
                db,
                dialog.id,
                "user",
                command_content,
                message_type="command",
                meta={
                    "command_name": payload.command_name,
                    "command_args": payload.command_args,
                },
            )
        return ChatOut(
            message="已记录命令输入，当前版本暂不执行该命令。",
            pending_action=None,
            ui_hint=_build_chat_idle_hint("命令输入仅持久化，不进入动作流"),
            refresh_targets=[],
            project_diagnosis=diagnosis,
        )

    if payload.input_type == "text" and payload.text:
        _save_message(db, dialog.id, "user", payload.text)

    if payload.input_type == "button" and payload.action_type:
        pending = PendingAction(
            dialog_id=dialog.id,
            type=payload.action_type,
            params=payload.params or {"project_id": payload.project_id},
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
                description=_action_description(pending.type),
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
    candidate = router.resolve(
        payload.text,
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
        pending = PendingAction(
            dialog_id=dialog.id,
            type=candidate.type,
            params={"project_id": payload.project_id},
        )
        db.add(pending)
        db.commit()
        db.refresh(pending)
        dialog.pending_action_id = pending.id
        dialog.state = "pending_action"
        db.commit()
        reply = _action_description(candidate.type)
        _save_message(db, dialog.id, "assistant", reply)
        return ChatOut(
            message=reply,
            pending_action=PendingActionOut(
                id=pending.id,
                type=pending.type,
                description=_action_description(candidate.type),
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

    reply = await _free_chat_reply(db, dialog, project, diagnosis)
    _save_message(db, dialog.id, "assistant", reply)
    return ChatOut(
        message=reply,
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


def _action_description(action_type: str) -> str:
    mapping = {
        "preview_setup": "我建议先为项目生成设定，这样后续创作更有基础。",
        "preview_storyline": "基于已有设定，我可以生成故事线。",
        "preview_outline": "故事线已就绪，接下来可以生成完整大纲。",
        "query_diagnosis": "让我看看项目当前状态...",
    }
    return mapping.get(action_type, "已准备好执行操作。")


import asyncio

async def _execute_action(action_type: str, project_id: str, db: Session) -> dict:
    if not project_id:
        return {"status": "failed", "error": "缺少项目 ID"}
    try:
        if action_type == "generate_setup":
            from app.api.setups import generate_setup
            await generate_setup(project_id, db)
            return {"status": "success"}
        elif action_type == "generate_storyline":
            from app.api.storylines import generate_storyline
            await generate_storyline(project_id, db)
            return {"status": "success"}
        elif action_type == "generate_outline":
            from app.api.outlines import generate_outline
            await generate_outline(project_id, db)
            return {"status": "success"}
        else:
            return {"status": "success"}
    except HTTPException as e:
        return {"status": "failed", "error": e.detail}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def _execute_action_background(action_type: str, project_id: str, dialog_id: str):
    """Fire-and-forget: run generation in background, update dialog message when done."""
    from app.db import SessionLocal

    async def _run():
        db = SessionLocal()
        try:
            result = await _execute_action(action_type, project_id, db)
            label_map = {"generate_setup": "设定", "generate_storyline": "故事线", "generate_outline": "大纲"}
            label = label_map.get(action_type, action_type)
            if result["status"] == "success":
                _save_message(db, dialog_id, "system", f"{label}生成完成。", {"type": action_type, "status": "success"})
            else:
                _save_message(db, dialog_id, "system", f"{label}生成失败：{result.get('error', '未知错误')}", {"type": action_type, "status": "failed"})
        finally:
            db.close()

    asyncio.ensure_future(_run())


@router.post("/api/v1/dialog/resolve-action")
async def resolve_action(payload: ResolveActionIn, db: Session = Depends(get_db)):
    pending = db.query(PendingAction).filter(PendingAction.id == payload.action_id).first()
    if not pending:
        raise HTTPException(status_code=404, detail="Pending action not found")

    pending.status = payload.decision
    pending.decision_comment = payload.comment
    pending.resolved_at = datetime.now(timezone.utc)
    db.commit()

    dialog = db.query(Dialog).filter(Dialog.id == pending.dialog_id).first()
    if dialog:
        dialog.pending_action_id = None
        dialog.state = "chatting"
        db.commit()

    action_type = pending.type
    if action_type.startswith("preview_"):
        action_type = action_type.replace("preview_", "generate_")

    result_data = None
    if payload.decision == "confirm":
        project_id = (pending.params or {}).get("project_id", "")
        if dialog:
            _execute_action_background(action_type, project_id, dialog.id)
        result_data = {"status": "generating"}
    elif payload.decision == "cancel":
        result_data = {"status": "cancelled"}
    elif payload.decision == "revise":
        result_data = {"status": "revised", "comment": payload.comment}

    resolve_msg = _resolve_message(payload.decision)
    if dialog:
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

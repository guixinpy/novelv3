from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.athena_shared import (
    create_dialog_world_update_proposal,
    get_current_profile,
    looks_like_world_update_request,
    require_project,
)
from app.db import get_db
from app.schemas import ChatIn, ChatOut, ResolveActionIn
from app.services.dialog.messages import DialogMessageService

router = APIRouter()


@router.get("/dialog/messages")
def get_athena_messages(
    project_id: str,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
    after_id: str | None = None,
    db: Session = Depends(get_db),
):
    return DialogMessageService(db).list_messages(
        project_id,
        dialog_type="athena",
        limit=limit,
        after_id=after_id,
    )


@router.post("/dialog/chat")
async def athena_chat(project_id: str, payload: ChatIn, db: Session = Depends(get_db)):
    from app.api.dialogs import (
        _build_chat_idle_hint,
        _build_diagnosis,
        _free_chat_reply,
        _get_or_create_dialog,
        _safe_attach_trace_response,
        _save_message,
    )
    project = require_project(db, project_id)
    payload.project_id = project_id
    dialog = _get_or_create_dialog(db, project_id, dialog_type="athena")
    diagnosis = _build_diagnosis(db, project_id)

    user_text = (payload.text or "").strip()
    if payload.input_type == "text" and not user_text:
        raise HTTPException(status_code=422, detail="Athena chat text cannot be empty")

    request_message = None
    if user_text:
        request_message = _save_message(db, dialog.id, "user", user_text)

    if user_text and looks_like_world_update_request(user_text):
        profile = get_current_profile(db, project_id)
        if profile is None:
            reply = (
                "我不能把这次内容标记为世界模型更新：当前项目还没有建立正式 world-model profile。"
                "请先在 Athena 建立或导入世界档案；在此之前，我只能把 setup 草稿作为参考，不能声称已经写入真相层。"
            )
            _save_message(db, dialog.id, "assistant", reply)
            return ChatOut(
                message=reply,
                pending_action=None,
                ui_hint=_build_chat_idle_hint("Athena 对话"),
                refresh_targets=[],
                project_diagnosis=diagnosis,
            )

        bundle, item = create_dialog_world_update_proposal(
            db=db,
            project_id=project_id,
            profile=profile,
            dialog_id=dialog.id,
            text=user_text,
        )
        reply = (
            "我已把这次世界模型修改记录为待审提案，而不是直接写入真相层。"
            f"请到 Athena > 提案 审阅：{bundle.title}（1 项，条目 {item.id}）。"
        )
        _save_message(db, dialog.id, "assistant", reply)
        return ChatOut(
            message=reply,
            pending_action=None,
            ui_hint=_build_chat_idle_hint("Athena 对话"),
            refresh_targets=["proposals"],
            project_diagnosis=diagnosis,
        )

    reply, trace = await _free_chat_reply(
        db,
        dialog,
        project,
        diagnosis,
        dialog_type="athena",
        request_message_id=request_message.id if request_message else None,
    )
    assistant_message = _save_message(db, dialog.id, "assistant", reply)
    trace_id = _safe_attach_trace_response(db, trace, assistant_message.id)
    return ChatOut(
        message=reply,
        trace_id=trace_id,
        pending_action=None,
        ui_hint=_build_chat_idle_hint("Athena 对话"),
        refresh_targets=[],
        project_diagnosis=diagnosis,
    )


@router.post("/dialog/resolve-action")
async def athena_resolve_action(project_id: str, payload: ResolveActionIn, db: Session = Depends(get_db)):
    from app.api.dialogs import resolve_action
    return await resolve_action(payload, db)

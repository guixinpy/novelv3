import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Project, Setup, Storyline, Outline, ChapterContent, Dialog, DialogMessage, PendingAction
from app.schemas import ChatOut, ChatIn, ResolveActionIn, ProjectDiagnosisOut, PendingActionOut, ChatMessageOut
from app.core.ai_service import AIService
from app.core.prompt_manager import PromptManager
from app.config import load_api_key
from datetime import datetime, timezone
from app.core.intent_router import IntentRouter

router = APIRouter(tags=["dialogs"])
ai_service = AIService()


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


def _save_message(db: Session, dialog_id: str, role: str, content: str, action_result: dict | None = None):
    msg = DialogMessage(dialog_id=dialog_id, role=role, content=content, action_result=action_result)
    db.add(msg)
    db.commit()


@router.get("/api/v1/dialog/projects/{project_id}/messages")
def get_messages(project_id: str, db: Session = Depends(get_db)):
    dialog = db.query(Dialog).filter(Dialog.project_id == project_id).first()
    if not dialog:
        return []
    msgs = db.query(DialogMessage).filter(DialogMessage.dialog_id == dialog.id).order_by(DialogMessage.created_at).all()
    return [{"role": m.role, "content": m.content, "action_result": m.action_result, "created_at": m.created_at.isoformat() if m.created_at else None} for m in msgs]


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
        return ChatOut(
            message=reply,
            pending_action=None,
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
            project_diagnosis=diagnosis,
        )

    reply = _free_reply(payload.text, diagnosis)
    _save_message(db, dialog.id, "assistant", reply)
    return ChatOut(
        message=reply,
        pending_action=None,
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


def _free_reply(text: str, diagnosis: ProjectDiagnosisOut) -> str:
    if diagnosis.missing_items:
        return f"目前项目还缺少：{', '.join(diagnosis.missing_items)}。建议先补全这些环节。"
    return "项目基础已就绪，随时可以开始创作。"


@router.post("/api/v1/dialog/resolve-action")
def resolve_action(payload: ResolveActionIn, db: Session = Depends(get_db)):
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
        result_data = {"status": "success"}
    elif payload.decision == "cancel":
        result_data = {"status": "cancelled"}
    elif payload.decision == "revise":
        result_data = {"status": "revised", "comment": payload.comment}

    resolve_msg = _resolve_message(payload.decision)
    if dialog:
        _save_message(db, dialog.id, "system", resolve_msg, {"type": action_type, "status": result_data["status"]})

    return {
        "action_result": {
            "type": action_type,
            "status": result_data["status"],
            "data": result_data,
        },
        "dialog_state": dialog.state if dialog else "chatting",
        "message": resolve_msg,
    }


def _resolve_message(decision: str) -> str:
    if decision == "confirm":
        return "操作已确认。"
    if decision == "cancel":
        return "操作已取消。"
    if decision == "revise":
        return "已收到修改意见。"
    return "未知决策。"

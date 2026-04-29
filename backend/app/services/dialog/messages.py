from sqlalchemy.orm import Session

from app.models import AIModelCallTrace, Dialog, DialogMessage, PendingAction
from app.schemas import PendingActionOut


def _action_description(action_type: str, params: dict | None = None) -> str:
    if action_type == "preview_chapter":
        chapter_index = (params or {}).get("chapter_index")
        if chapter_index:
            return f"我可以生成第{chapter_index}章正文，完成后会进入 Calliope 和正文进度。"
        return "我可以生成下一章正文，完成后会进入 Calliope 和正文进度。"
    mapping = {
        "preview_setup": "我建议先为项目生成设定，这样后续创作更有基础。",
        "preview_storyline": "基于已有设定，我可以生成故事线。",
        "preview_outline": "故事线已就绪，接下来可以生成完整大纲。",
        "query_diagnosis": "让我看看项目当前状态...",
    }
    return mapping.get(action_type, "已准备好执行操作。")


class DialogMessageService:
    def __init__(self, db: Session):
        self.db = db

    def list_messages(
        self,
        project_id: str,
        *,
        dialog_type: str = "hermes",
        limit: int | None = None,
        after_id: str | None = None,
    ) -> list[dict]:
        dialog = self.db.query(Dialog).filter(
            Dialog.project_id == project_id,
            Dialog.dialog_type == dialog_type,
        ).first()
        if not dialog:
            return []

        query = self.db.query(DialogMessage).filter(DialogMessage.dialog_id == dialog.id)
        if after_id:
            cursor = self.db.query(DialogMessage).filter(
                DialogMessage.dialog_id == dialog.id,
                DialogMessage.id == after_id,
            ).first()
            if not cursor:
                return []
            query = query.filter(DialogMessage.created_at > cursor.created_at)

        if limit:
            messages = list(reversed(query.order_by(DialogMessage.created_at.desc()).limit(limit).all()))
        else:
            messages = query.order_by(DialogMessage.created_at).all()

        pending_action = self._pending_action_payload(dialog)
        last_assistant_message_id = self._last_assistant_message_id(messages) if pending_action else None
        trace_by_response_id = self._trace_by_response_id(dialog, messages)

        payload = []
        for message in messages:
            item = {
                "id": message.id,
                "role": message.role,
                "message_type": message.message_type,
                "content": message.content,
                "meta": message.meta,
                "action_result": message.action_result,
                "trace_id": trace_by_response_id.get(message.id),
                "created_at": message.created_at.isoformat() if message.created_at else None,
            }
            if pending_action and message.id == last_assistant_message_id:
                item["pending_action"] = pending_action
            payload.append(item)
        return payload

    def _pending_action_payload(self, dialog: Dialog) -> dict | None:
        if not dialog.pending_action_id:
            return None
        pending = self.db.query(PendingAction).filter(PendingAction.id == dialog.pending_action_id).first()
        if not pending:
            return None
        return PendingActionOut(
            id=pending.id,
            type=pending.type,
            description=_action_description(pending.type),
            params=pending.params,
        ).model_dump()

    @staticmethod
    def _last_assistant_message_id(messages: list[DialogMessage]) -> str | None:
        for message in reversed(messages):
            if message.role == "assistant":
                return message.id
        return None

    def _trace_by_response_id(self, dialog: Dialog, messages: list[DialogMessage]) -> dict[str, str]:
        message_ids = [message.id for message in messages]
        if not message_ids:
            return {}
        traces = (
            self.db.query(AIModelCallTrace)
            .filter(
                AIModelCallTrace.dialog_id == dialog.id,
                AIModelCallTrace.response_message_id.in_(message_ids),
            )
            .all()
        )
        return {
            trace.response_message_id: trace.id
            for trace in traces
            if trace.response_message_id
        }


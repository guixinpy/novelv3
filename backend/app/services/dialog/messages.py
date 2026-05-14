from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import AIModelCallTrace, Dialog, DialogMessage, PendingAction
from app.core.model_call_trace import truncate_text
from app.schemas import PendingActionOut
from app.services.actions.descriptions import action_description


DEFAULT_DIALOG_MESSAGE_LIMIT = 80
DEFAULT_MESSAGE_CONTENT_PREVIEW_CHARS = 6000


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
        max_content_chars: int | None = None,
    ) -> list[dict]:
        dialog = self.db.query(Dialog).filter(
            Dialog.project_id == project_id,
            Dialog.dialog_type == dialog_type,
        ).first()
        if not dialog:
            return []

        query = self.db.query(DialogMessage).filter(DialogMessage.dialog_id == dialog.id)
        effective_limit = limit if limit is not None else DEFAULT_DIALOG_MESSAGE_LIMIT
        if after_id:
            cursor = self.db.query(DialogMessage).filter(
                DialogMessage.dialog_id == dialog.id,
                DialogMessage.id == after_id,
            ).first()
            if not cursor:
                return []
            query = query.filter(
                or_(
                    DialogMessage.created_at > cursor.created_at,
                    and_(
                        DialogMessage.created_at == cursor.created_at,
                        DialogMessage.id > cursor.id,
                    ),
                )
            )
            messages = query.order_by(DialogMessage.created_at.asc(), DialogMessage.id.asc()).limit(effective_limit).all()
        else:
            messages = list(
                reversed(
                    query.order_by(DialogMessage.created_at.desc(), DialogMessage.id.desc())
                    .limit(effective_limit)
                    .all()
                )
            )

        pending_action = self._pending_action_payload(dialog)
        last_assistant_message_id = self._last_assistant_message_id(messages) if pending_action else None
        trace_by_response_id = self._trace_by_response_id(dialog, messages)

        payload = []
        for message in messages:
            content_payload = self._content_payload(message.content, max_content_chars=max_content_chars)
            item = {
                "id": message.id,
                "role": message.role,
                "message_type": message.message_type,
                "content": content_payload["content"],
                "meta": message.meta,
                "action_result": message.action_result,
                "trace_id": trace_by_response_id.get(message.id),
                "created_at": message.created_at.isoformat() if message.created_at else None,
            }
            if content_payload["content_truncated"]:
                item["content_truncated"] = True
                item["original_content_length"] = content_payload["original_content_length"]
            if pending_action and message.id == last_assistant_message_id:
                item["pending_action"] = pending_action
            payload.append(item)
        return payload

    @staticmethod
    def _content_payload(content: str, *, max_content_chars: int | None) -> dict:
        if max_content_chars is None:
            return {
                "content": content,
                "content_truncated": False,
                "original_content_length": len(content or ""),
            }
        truncated = truncate_text(content, max_chars=max_content_chars)
        return {
            "content": truncated["content"],
            "content_truncated": truncated["truncated"],
            "original_content_length": truncated["original_char_count"],
        }

    def _pending_action_payload(self, dialog: Dialog) -> dict | None:
        if not dialog.pending_action_id:
            return None
        pending = self.db.query(PendingAction).filter(PendingAction.id == dialog.pending_action_id).first()
        if not pending:
            return None
        return PendingActionOut(
            id=pending.id,
            type=pending.type,
            description=action_description(pending.type),
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
            self.db.query(AIModelCallTrace.response_message_id, AIModelCallTrace.id)
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

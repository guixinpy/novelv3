from sqlalchemy.orm import Session

from app.models import Dialog, DialogMessage


class DialogSessionService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, project_id: str, dialog_type: str = "hermes") -> Dialog:
        dialog = self.db.query(Dialog).filter(
            Dialog.project_id == project_id,
            Dialog.dialog_type == dialog_type,
        ).first()
        if not dialog:
            dialog = Dialog(project_id=project_id, dialog_type=dialog_type)
            self.db.add(dialog)
            self.db.commit()
            self.db.refresh(dialog)
        return dialog

    def save_message(
        self,
        dialog_id: str,
        role: str,
        content: str,
        action_result: dict | None = None,
        message_type: str = "plain",
        meta: dict | None = None,
    ) -> DialogMessage:
        message = DialogMessage(
            dialog_id=dialog_id,
            role=role,
            content=content,
            action_result=action_result,
            message_type=message_type,
            meta=meta,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

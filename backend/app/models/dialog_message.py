import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String, Text, text

from app.db import Base


class DialogMessage(Base):
    __tablename__ = "dialog_messages"
    __table_args__ = (
        Index("ix_dialog_messages_dialog_type_created", "dialog_id", "message_type", "created_at", "id"),
        Index(
            "ix_dialog_messages_dialog_action_created",
            "dialog_id",
            "created_at",
            "id",
            sqlite_where=text("action_result IS NOT NULL"),
        ),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dialog_id = Column(String, ForeignKey("dialogs.id"), nullable=False)
    role = Column(String, nullable=False)
    message_type = Column(String, nullable=False, default="plain")
    content = Column(Text, default="")
    meta = Column(JSON, nullable=True)
    action_result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

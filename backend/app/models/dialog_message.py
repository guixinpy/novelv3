import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey
from app.db import Base


class DialogMessage(Base):
    __tablename__ = "dialog_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dialog_id = Column(String, ForeignKey("dialogs.id"), nullable=False)
    role = Column(String, nullable=False)
    message_type = Column(String, nullable=False, default="plain")
    content = Column(Text, default="")
    meta = Column(JSON, nullable=True)
    action_result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

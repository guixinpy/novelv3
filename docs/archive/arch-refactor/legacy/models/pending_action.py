import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text

from app.db import Base


class PendingAction(Base):
    __tablename__ = "pending_actions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dialog_id = Column(String, ForeignKey("dialogs.id"), nullable=False)
    type = Column(String, nullable=False)
    params = Column(JSON, default=dict)
    status = Column(String, default="pending")
    decision_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    resolved_at = Column(DateTime, nullable=True)

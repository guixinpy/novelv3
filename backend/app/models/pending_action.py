import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, JSON, Text, DateTime, ForeignKey
from app.db import Base


class PendingAction(Base):
    __tablename__ = "pending_actions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dialog_id = Column(String, ForeignKey("dialogs.id"), nullable=False)
    type = Column(String, nullable=False)
    params = Column(JSON, default=dict)
    status = Column(String, default="pending")
    decision_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)

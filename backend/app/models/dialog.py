import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String

from app.db import Base


class Dialog(Base):
    __tablename__ = "dialogs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    dialog_type = Column(String, default="hermes", nullable=False, server_default="hermes")
    state = Column(String, default="idle")
    pending_action_id = Column(String, nullable=True)
    current_view = Column(String, default="setup")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

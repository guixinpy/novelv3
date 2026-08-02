import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class AIModelCallTrace(Base):
    __tablename__ = "ai_model_call_traces"
    __table_args__ = (
        Index("ix_ai_model_call_traces_project_type_created", "project_id", "trace_type", "created_at"),
        Index("ix_ai_model_call_traces_dialog_response", "dialog_id", "response_message_id"),
        Index("ix_ai_model_call_traces_project_chapter", "project_id", "chapter_index"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    trace_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="running")
    model = Column(String, nullable=True)
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    dialog_id = Column(String, ForeignKey("dialogs.id"), nullable=True)
    request_message_id = Column(String, ForeignKey("dialog_messages.id"), nullable=True)
    response_message_id = Column(String, ForeignKey("dialog_messages.id"), nullable=True)
    chapter_id = Column(String, ForeignKey("chapter_contents.id"), nullable=True)
    chapter_index = Column(Integer, nullable=True)
    messages = Column(JSON, default=list)
    context_blocks = Column(JSON, default=list)
    trace_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

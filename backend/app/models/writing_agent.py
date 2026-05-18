import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class WritingAgentRun(Base):
    __tablename__ = "writing_agent_runs"
    __table_args__ = (
        Index("ix_writing_agent_runs_project_created", "project_id", "created_at", "id"),
        Index("ix_writing_agent_runs_project_status_created", "project_id", "status", "created_at", "id"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    goal = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="pending")
    entrypoint = Column(String, nullable=False, default="api")
    input = Column(JSON, default=dict)
    output = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    background_task_id = Column(String, ForeignKey("background_tasks.id"), nullable=True)
    dialog_id = Column(String, ForeignKey("dialogs.id"), nullable=True)
    request_message_id = Column(String, ForeignKey("dialog_messages.id"), nullable=True)
    response_message_id = Column(String, ForeignKey("dialog_messages.id"), nullable=True)
    created_at = Column(DateTime, default=_now)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class WritingAgentStep(Base):
    __tablename__ = "writing_agent_steps"
    __table_args__ = (
        Index("ix_writing_agent_steps_run_order", "run_id", "step_index", "id"),
        Index("ix_writing_agent_steps_project_tool_created", "project_id", "tool_name", "created_at", "id"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    run_id = Column(String, ForeignKey("writing_agent_runs.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    step_index = Column(Integer, nullable=False)
    tool_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    input = Column(JSON, default=dict)
    output = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    trace_id = Column(String, ForeignKey("ai_model_call_traces.id"), nullable=True)
    background_task_id = Column(String, ForeignKey("background_tasks.id"), nullable=True)
    target_type = Column(String, nullable=True)
    target_id = Column(String, nullable=True)
    chapter_index = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=_now)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

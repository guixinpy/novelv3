from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WritingAgentToolRequest(BaseModel):
    tool_name: str
    command_args: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class WritingAgentRunCreate(BaseModel):
    goal: str
    entrypoint: str = "api"
    tools: list[WritingAgentToolRequest] = Field(default_factory=list)
    input: dict[str, Any] = Field(default_factory=dict)


class WritingAgentStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    project_id: str
    step_index: int
    tool_name: str
    status: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] | None = None
    error: str | None = None
    trace_id: str | None = None
    background_task_id: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    chapter_index: int | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class WritingAgentRunListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    goal: str
    status: str
    entrypoint: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] | None = None
    error: str | None = None
    background_task_id: str | None = None
    dialog_id: str | None = None
    request_message_id: str | None = None
    response_message_id: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime | None = None


class WritingAgentRunDetail(WritingAgentRunListItem):
    steps: list[WritingAgentStepOut] = Field(default_factory=list)


class PaginatedWritingAgentRuns(BaseModel):
    total: int
    items: list[WritingAgentRunListItem]
    offset: int = 0
    limit: int = 20
    has_more: bool = False

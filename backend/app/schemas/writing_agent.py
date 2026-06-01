from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WritingAgentToolRequest(BaseModel):
    tool_name: str
    command_args: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    planner: dict[str, Any] = Field(default_factory=dict)


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
    tool_call_id: str | None = None
    resource_binding: dict[str, Any] | None = None
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
    agent_profile: str | None = None
    agent_profile_scope: dict[str, Any] | None = None
    agent_tool_discovery: dict[str, Any] | None = None
    agent_profile_definition: dict[str, Any] | None = None
    agent_profile_policy_audit: dict[str, Any] | None = None
    agent_command_contracts: dict[str, Any] | None = None
    agent_control_plane_readiness: dict[str, Any] | None = None
    agent_worker_route_registry: dict[str, Any] | None = None
    agent_dogfood_evidence: dict[str, Any] | None = None
    steps: list[WritingAgentStepOut] = Field(default_factory=list)


class PaginatedWritingAgentRuns(BaseModel):
    total: int
    items: list[WritingAgentRunListItem]
    offset: int = 0
    limit: int = 20
    has_more: bool = False

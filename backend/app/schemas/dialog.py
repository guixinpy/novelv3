from datetime import datetime
from pydantic import BaseModel, Field


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    action_result: dict | None = None
    created_at: datetime


class ChatIn(BaseModel):
    project_id: str
    input_type: str = "text"
    text: str = ""
    action_type: str | None = None
    params: dict = Field(default_factory=dict)


class ResolveActionIn(BaseModel):
    action_id: str
    decision: str
    comment: str = ""


class PendingActionOut(BaseModel):
    id: str
    type: str
    description: str
    params: dict
    requires_confirmation: bool = True


class ActiveActionOut(BaseModel):
    type: str
    status: str
    target_panel: str
    reason: str = ""


class ProjectDiagnosisOut(BaseModel):
    missing_items: list[str] = Field(default_factory=list)
    completed_items: list[str] = Field(default_factory=list)
    suggested_next_step: str | None = None


class UiHintOut(BaseModel):
    dialog_state: str
    active_action: ActiveActionOut


class ChatOut(BaseModel):
    message: str
    pending_action: PendingActionOut | None = None
    ui_hint: UiHintOut | None = None
    refresh_targets: list[str] = Field(default_factory=list)
    project_diagnosis: ProjectDiagnosisOut

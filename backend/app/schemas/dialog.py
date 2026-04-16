from datetime import datetime
from pydantic import BaseModel


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
    params: dict = {}


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


class ProjectDiagnosisOut(BaseModel):
    missing_items: list[str] = []
    completed_items: list[str] = []
    suggested_next_step: str | None = None


class ChatOut(BaseModel):
    message: str
    pending_action: PendingActionOut | None = None
    project_diagnosis: ProjectDiagnosisOut

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConsistencyIssueOut(BaseModel):
    id: str
    project_id: str
    chapter_index: int
    checker_name: str
    severity: str
    subject: str
    description: str
    evidence: str
    suggested_fix: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

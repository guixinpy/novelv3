from datetime import datetime
from pydantic import BaseModel, ConfigDict


class Milestone(BaseModel):
    chapter_index: int
    event: str


class Plotline(BaseModel):
    name: str
    type: str = "main"
    milestones: list[Milestone] = []


class Foreshadowing(BaseModel):
    hint: str
    planted_chapter: int
    resolved_chapter: int | None = None
    status: str = "planted"


class StorylineOut(BaseModel):
    id: str
    project_id: str
    plotlines: list[Plotline] = []
    foreshadowing: list[Foreshadowing] = []
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

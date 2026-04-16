from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    genre: str = ""
    target_word_count: int = 0
    style: str = ""
    complexity: int = 3


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    genre: str | None = None
    target_word_count: int | None = None
    style: str | None = None
    complexity: int | None = None
    status: str | None = None
    current_phase: str | None = None
    current_word_count: int | None = None


class ProjectOut(ProjectCreate):
    id: str
    status: str
    current_phase: str
    current_word_count: int
    ai_model: str
    language: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

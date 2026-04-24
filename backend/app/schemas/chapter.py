from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChapterOut(BaseModel):
    id: str
    project_id: str
    chapter_index: int
    title: str
    content: str
    word_count: int
    status: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    generation_time: int
    temperature: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

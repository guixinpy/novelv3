from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChapterOutline(BaseModel):
    chapter_index: int
    title: str
    summary: str
    scenes: list[str] = []
    characters: list[str] = []
    purpose: str = ""


class OutlineOut(BaseModel):
    id: str
    project_id: str
    total_chapters: int
    chapters: list[ChapterOutline] = []
    plotlines: list[dict] = []
    foreshadowing: list[dict] = []
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

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
    chapters_total: int | None = None
    chapters_offset: int | None = None
    chapters_limit: int | None = None
    chapters_has_more: bool | None = None
    plotlines_total: int | None = None
    plotlines_offset: int | None = None
    plotlines_limit: int | None = None
    plotlines_has_more: bool | None = None
    foreshadowing_total: int | None = None
    foreshadowing_offset: int | None = None
    foreshadowing_limit: int | None = None
    foreshadowing_has_more: bool | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

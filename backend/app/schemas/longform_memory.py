from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LongformMemoryRebuildResult(BaseModel):
    status: str
    project_id: str
    counts_by_type: dict[str, int]
    total_memories: int
    current_word_count: int


class LongformMemoryDiagnostics(BaseModel):
    project_id: str
    chapter_count: int
    current_word_count: int
    counts_by_type: dict[str, int]
    total_memories: int
    latest_updated_at: datetime | None = None


class LongformContextSection(BaseModel):
    key: str
    title: str
    items: list[dict[str, Any]] = Field(default_factory=list)


class LongformContextPackage(BaseModel):
    project_id: str
    chapter_index: int
    sections: list[LongformContextSection]
    prompt_context: str

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


class LongformMaintenanceDiagnostics(BaseModel):
    project_id: str
    status: str
    chapter_count: int
    stale_memory_count: int
    missing_memory_count: int
    stale_retrieval_count: int
    missing_retrieval_count: int
    stale_chapter_indexes: list[int] = Field(default_factory=list)
    missing_memory_chapter_indexes: list[int] = Field(default_factory=list)
    stale_retrieval_chapter_indexes: list[int] = Field(default_factory=list)
    missing_retrieval_chapter_indexes: list[int] = Field(default_factory=list)
    latest_chapter_updated_at: datetime | None = None
    latest_memory_updated_at: datetime | None = None
    latest_retrieval_updated_at: datetime | None = None
    latest_synced_chapter_index: int | None = None


class LongformMaintenanceRepairResult(BaseModel):
    project_id: str
    status: str
    repaired_memory_count: int
    repaired_retrieval_count: int
    refreshed_chapter_indexes: list[int] = Field(default_factory=list)
    synced_scope_keys: list[str] = Field(default_factory=list)
    has_more: bool
    remaining_issue_count: int
    remaining: LongformMaintenanceDiagnostics


class LongformContextSection(BaseModel):
    key: str
    title: str
    items: list[dict[str, Any]] = Field(default_factory=list)


class LongformContextPackage(BaseModel):
    project_id: str
    chapter_index: int
    sections: list[LongformContextSection]
    prompt_context: str

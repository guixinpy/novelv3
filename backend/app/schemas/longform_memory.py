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


class LongformWordTargetDiagnostics(BaseModel):
    status: str = "untracked"
    target_average_word_count: int | None = None
    target_min_word_count: int | None = None
    target_max_word_count: int | None = None
    under_target_count: int = 0
    within_target_count: int = 0
    over_target_count: int = 0
    under_target_chapter_indexes: list[int] = Field(default_factory=list)
    over_target_chapter_indexes: list[int] = Field(default_factory=list)


class LongformMaintenanceRecommendation(BaseModel):
    kind: str
    severity: str
    title: str
    message: str
    chapter_indexes: list[int] = Field(default_factory=list)


class LongformMaintenanceDiagnostics(BaseModel):
    project_id: str
    status: str
    ready_for_writing: bool = True
    issue_count: int = 0
    recommendations: list[LongformMaintenanceRecommendation] = Field(default_factory=list)
    chapter_count: int
    word_target: LongformWordTargetDiagnostics = Field(default_factory=LongformWordTargetDiagnostics)
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

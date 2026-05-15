from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StorylineOut(BaseModel):
    id: str
    project_id: str
    plotlines: list[dict] = []
    foreshadowing: list[dict] = []
    plotlines_count: int | None = None
    foreshadowing_count: int | None = None
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

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StorylineOut(BaseModel):
    id: str
    project_id: str
    plotlines: list[dict] = []
    foreshadowing: list[dict] = []
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

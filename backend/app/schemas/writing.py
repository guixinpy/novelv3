from pydantic import BaseModel


class WritingStateOut(BaseModel):
    project_id: str
    current_chapter: int
    status: str
    last_error: str | None = None

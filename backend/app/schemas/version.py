from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VersionCreate(BaseModel):
    node_type: str
    node_id: str
    content: str
    description: str = ""
    author: str = "user"


class VersionOut(BaseModel):
    id: str
    project_id: str
    node_type: str
    node_id: str
    version_number: int
    content: str
    description: str
    author: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VersionSummary(BaseModel):
    id: str
    version_number: int
    node_type: str
    node_id: str
    description: str
    author: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TopologyNode(BaseModel):
    id: str
    type: str
    label: str
    meta: dict = {}


class TopologyEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    meta: dict = {}


class TopologyOut(BaseModel):
    id: str
    project_id: str
    version: int
    nodes: list[TopologyNode] = []
    edges: list[TopologyEdge] = []
    indexes: dict = {}
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

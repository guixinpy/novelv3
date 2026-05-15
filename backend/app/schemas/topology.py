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
    nodes_total: int | None = None
    nodes_offset: int | None = None
    nodes_limit: int | None = None
    nodes_has_more: bool | None = None
    edges_total: int | None = None
    edges_offset: int | None = None
    edges_limit: int | None = None
    edges_has_more: bool | None = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

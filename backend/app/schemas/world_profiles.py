from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GenreProfileCreate(BaseModel):
    canonical_id: str
    display_name: str
    contract_version: str
    primary_alias: str = ""
    field_authority: dict[str, Any] = Field(default_factory=dict)
    schema_payload: dict[str, Any] = Field(default_factory=dict)
    module_payload: dict[str, Any] = Field(default_factory=dict)
    event_types: list[str] = Field(default_factory=list)
    checker_config: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class GenreProfileOut(GenreProfileCreate):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectProfileVersionAppend(BaseModel):
    genre_profile_id: str
    version: int = Field(ge=1)
    contract_version: str
    profile_payload: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", frozen=True)


class ProjectProfileVersionOut(ProjectProfileVersionAppend):
    id: str
    project_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorldProjectionOut(BaseModel):
    view_type: str
    entities: dict[str, dict[str, Any]] = Field(default_factory=dict)
    entities_total: int | None = None
    entities_offset: int | None = None
    entities_limit: int | None = None
    entities_has_more: bool | None = None
    relations: dict[str, Any] = Field(default_factory=dict)
    relations_total: int | None = None
    relations_offset: int | None = None
    relations_limit: int | None = None
    relations_has_more: bool | None = None
    presence: dict[str, Any] = Field(default_factory=dict)
    presence_total: int | None = None
    presence_offset: int | None = None
    presence_limit: int | None = None
    presence_has_more: bool | None = None
    occurred_events: dict[str, Any] = Field(default_factory=dict)
    occurred_events_total: int | None = None
    occurred_events_offset: int | None = None
    occurred_events_limit: int | None = None
    occurred_events_has_more: bool | None = None
    event_links: dict[str, Any] = Field(default_factory=dict)
    event_links_total: int | None = None
    event_links_offset: int | None = None
    event_links_limit: int | None = None
    event_links_has_more: bool | None = None
    facts: dict[str, dict[str, Any]] = Field(default_factory=dict)
    facts_total: int | None = None
    facts_offset: int | None = None
    facts_limit: int | None = None
    facts_has_more: bool | None = None

    model_config = ConfigDict(extra="forbid")


class ProjectWorldOverviewOut(BaseModel):
    project_profile: ProjectProfileVersionOut | None
    projection: WorldProjectionOut | None

    model_config = ConfigDict(extra="forbid")


class WorldModelDashboardMetricsOut(BaseModel):
    entity_count: int = 0
    fact_count: int = 0
    presence_count: int = 0
    event_count: int = 0
    pending_bundle_count: int = 0
    pending_item_count: int = 0

    model_config = ConfigDict(extra="forbid")


class WorldModelNextActionOut(BaseModel):
    action: str
    label: str

    model_config = ConfigDict(extra="forbid")


class WorldModelDashboardOut(BaseModel):
    project_profile: ProjectProfileVersionOut | None
    metrics: WorldModelDashboardMetricsOut
    next_action: WorldModelNextActionOut

    model_config = ConfigDict(extra="forbid")

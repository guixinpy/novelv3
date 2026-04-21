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
    relations: dict[str, Any] = Field(default_factory=dict)
    presence: dict[str, Any] = Field(default_factory=dict)
    occurred_events: dict[str, Any] = Field(default_factory=dict)
    event_links: dict[str, Any] = Field(default_factory=dict)
    facts: dict[str, dict[str, Any]] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class ProjectWorldOverviewOut(BaseModel):
    project_profile: ProjectProfileVersionOut | None
    projection: WorldProjectionOut | None

    model_config = ConfigDict(extra="forbid")

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CharacterProfile(BaseModel):
    name: str
    age: int | None = None
    gender: str | None = None
    personality: str | None = None
    background: str | None = None
    goals: str | None = None
    character_status: str = "alive"


class WorldBuilding(BaseModel):
    background: str = ""
    geography: str = ""
    society: str = ""
    rules: str = ""
    atmosphere: str = ""


class CoreConcept(BaseModel):
    theme: str = ""
    premise: str = ""
    hook: str = ""
    unique_selling_point: str = ""


class SetupOut(BaseModel):
    id: str
    project_id: str
    world_building: WorldBuilding = WorldBuilding()
    characters: list[CharacterProfile] = []
    core_concept: CoreConcept = CoreConcept()
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

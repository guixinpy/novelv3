from fastapi import APIRouter
from pydantic import BaseModel
from app.config import load_api_key, save_api_key

router = APIRouter(prefix="/api/v1/config", tags=["config"])


class ConfigOut(BaseModel):
    has_api_key: bool


class ConfigIn(BaseModel):
    api_key: str


@router.get("", response_model=ConfigOut)
def get_config():
    return {"has_api_key": bool(load_api_key())}


@router.put("")
def update_config(payload: ConfigIn):
    save_api_key(payload.api_key)
    return {"has_api_key": True}

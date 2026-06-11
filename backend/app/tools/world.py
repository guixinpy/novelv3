"""世界观查询工具（M1：按名称/别名查实体；提案类工具在 M2 加入）。"""
from __future__ import annotations

from sqlalchemy import func

from app.agent.tooling import ToolContext, ToolResult, tool
from app.models import ProjectProfileVersion, WorldCharacter, WorldFaction, WorldLocation
from app.tools.registry import registry


def _current_profile_version(ctx: ToolContext) -> int | None:
    row = (
        ctx.db.query(ProjectProfileVersion.version)
        .filter(ProjectProfileVersion.project_id == ctx.project_id)
        .order_by(ProjectProfileVersion.version.desc())
        .first()
    )
    return row[0] if row else None


def _character_card(c: WorldCharacter) -> dict:
    return {
        "canonical_id": c.canonical_id,
        "name": c.name,
        "aliases": c.aliases or [],
        "role_type": c.role_type,
        "identity_anchor": c.identity_anchor,
        "core_traits": c.core_traits or [],
        "core_drives": c.core_drives or [],
        "public_persona": c.public_persona,
    }


def _named_card(entity) -> dict:
    return {
        "canonical_id": entity.canonical_id,
        "name": entity.name,
        "aliases": getattr(entity, "aliases", None) or [],
    }


def _matches(query: str, name: str, aliases: list | None) -> bool:
    q = query.strip().lower()
    if q in (name or "").lower():
        return True
    return any(q in str(alias).lower() for alias in (aliases or []))


@tool(
    registry=registry,
    name="query_world",
    description=(
        "按名称或别名查询世界观实体（人物/地点/势力），返回当前生效设定版本下的实体卡片。"
        "写作或检查一致性前，先用本工具确认人物设定。空 query 返回全部实体概览。"
    ),
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "实体名称或别名（支持部分匹配）；留空列出全部"},
            "limit": {"type": "integer", "description": "每类实体最多返回数量，默认 10"},
        },
    },
)
async def query_world(ctx: ToolContext, query: str = "", limit: int = 10) -> ToolResult:
    version = _current_profile_version(ctx)
    if version is None:
        return ToolResult.ok(
            {
                "profile_version": None,
                "characters": [],
                "locations": [],
                "factions": [],
                "note": "项目尚未初始化世界观设定版本。",
            }
        )

    def fetch(model):
        return (
            ctx.db.query(model)
            .filter(model.project_id == ctx.project_id, model.profile_version == version)
            .order_by(func.lower(model.name).asc())
            .all()
        )

    characters = [c for c in fetch(WorldCharacter) if not query or _matches(query, c.name, c.aliases)]
    locations = [l for l in fetch(WorldLocation) if not query or _matches(query, l.name, getattr(l, "aliases", None))]
    factions = [f for f in fetch(WorldFaction) if not query or _matches(query, f.name, getattr(f, "aliases", None))]

    return ToolResult.ok(
        {
            "profile_version": version,
            "characters": [_character_card(c) for c in characters[:limit]],
            "locations": [_named_card(l) for l in locations[:limit]],
            "factions": [_named_card(f) for f in factions[:limit]],
        }
    )

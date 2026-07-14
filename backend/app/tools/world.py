"""世界观查询与提案工具。"""
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


@tool(
    registry=registry,
    name="propose_world_change",
    description=(
        "提出世界观变更提案：修改/新增人物、地点、势力等实体的属性。"
        "提案会进入审批流程，批准后模型会继续执行变更操作。"
        "格式为实体类型+实体引用+变更字段。"
    ),
    permission="write",
    parameters={
        "type": "object",
        "properties": {
            "entity_type": {
                "type": "string",
                "description": "实体类型: character / location / faction",
                "enum": ["character", "location", "faction"],
            },
            "entity_name": {"type": "string", "description": "目标实体的名称"},
            "changes": {
                "type": "object",
                "description": "要变更的字段及其新值, 例如 {\"core_traits\": [\"勇敢\", \"机智\"]}",
            },
            "rationale": {"type": "string", "description": "变更理由"},
        },
        "required": ["entity_type", "entity_name", "changes"],
    },
)
async def propose_world_change(ctx: ToolContext, entity_type: str, entity_name: str, changes: dict, rationale: str = "") -> ToolResult:
    return ToolResult.ok({
        "proposed": {
            "entity_type": entity_type,
            "entity_name": entity_name,
            "changes": changes,
            "rationale": rationale,
        },
        "message": f"收到{entity_type}「{entity_name}」的变更提案，请用户审批。审批通过后再用 update_setup 工具应用变更。",
    })


# ── P2: On-Demand Entity Co-occurrence (openhuman pattern) ──


@tool(
    registry=registry,
    name="derive_entity_relations",
    description=(
        "按需推导实体之间的关系（不依赖预建图数据库）。"
        "从 LongformMemory 和章节内容中检测哪些人物/地点在相同上下文中共同出现。"
        "用于一致性检查：如果两个角色声称在不同地点但曾同章出现，可能存在矛盾。"
    ),
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "entity_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "要检查的实体名称列表（不超过 10 个）",
            },
            "min_co_occurrence": {
                "type": "integer",
                "description": "最少共现次数阈值（默认 1）",
                "default": 1,
            },
        },
        "required": ["entity_names"],
    },
)
async def derive_entity_relations(
    ctx: ToolContext,
    entity_names: list[str],
    min_co_occurrence: int = 1,
) -> ToolResult:
    if len(entity_names) > 10:
        return ToolResult.fail("实体名称列表不超过 10 个。")
    if len(entity_names) < 2:
        return ToolResult.ok({"pairs": [], "hint": "至少需要 2 个实体才能推导关系。"})

    from app.models import ChapterContent, LongformMemory

    # Collect contexts where entities appear
    entity_contexts: dict[str, set] = {name: set() for name in entity_names}

    # 1. Check LongformMemory (plotlines, arc_summaries, entity_states)
    memories = (
        ctx.db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == ctx.project_id,
            LongformMemory.memory_type.in_(["plotline", "entity_state", "arc_summary", "story_arc"]),
        )
        .all()
    )
    for m in memories:
        text = f"{m.title} {m.summary} {m.scope_key}"
        for name in entity_names:
            if name in text:
                entity_contexts[name].add(f"memory:{m.id[:8]}:{m.title[:30]}")

    # 2. Check chapter titles
    chapters = (
        ctx.db.query(ChapterContent)
        .filter(ChapterContent.project_id == ctx.project_id)
        .all()
    )
    for ch in chapters:
        text = f"{ch.title or ''} {ch.content or ''}"
        for name in entity_names:
            if name in text:
                entity_contexts[name].add(f"chapter:{ch.chapter_index}")

    # 3. Compute co-occurrence pairs
    pairs = []
    names = sorted(entity_names)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            shared = entity_contexts[a] & entity_contexts[b]
            if len(shared) >= min_co_occurrence:
                # Determine relationship type
                rel_type = "weak"
                if len(shared) >= 3:
                    rel_type = "strong"
                elif len(shared) >= 2:
                    rel_type = "moderate"

                pairs.append({
                    "entity_a": a,
                    "entity_b": b,
                    "co_occurrence_count": len(shared),
                    "relationship": rel_type,
                    "shared_contexts": sorted(shared)[:5],
                })

    # Find isolated entities
    isolated = []
    for name in entity_names:
        if not entity_contexts[name]:
            isolated.append({"entity": name, "status": "no_references_found"})
        elif len(entity_contexts[name]) <= 1:
            isolated.append({"entity": name, "status": "minimal_references", "contexts": list(entity_contexts[name])})

    return ToolResult.ok({
        "pairs": pairs,
        "total_pairs": len(pairs),
        "isolated_entities": isolated,
        "hint": (
            "共现关系从记忆和章节中按需推导（不依赖预建图数据库）。"
            f"共发现 {len(pairs)} 对关系，{len(isolated)} 个实体缺少足够上下文。"
        ) if pairs or isolated else "未发现实体间的共现关系。可能原因：实体名拼写不一致，或尚未在记忆/章节中充分出现。",
    })

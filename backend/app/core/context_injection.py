"""Build world model context summaries for dialog system prompts."""

from sqlalchemy.orm import Session

from app.models import (
    ProjectProfileVersion,
    Setup,
    WorldCharacter,
    WorldEvent,
    WorldFactClaim,
    WorldFaction,
    WorldLocation,
    WorldRelation,
    WorldRule,
)


def _get_current_profile(db: Session, project_id: str) -> ProjectProfileVersion | None:
    return (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc())
        .first()
    )


def build_athena_world_context(db: Session, project_id: str) -> str:
    """Full world knowledge for Athena dialog — entities, relations, rules, facts, timeline."""
    profile = _get_current_profile(db, project_id)
    if profile is None:
        setup = db.query(Setup).filter(Setup.project_id == project_id).first()
        if setup is None:
            return "当前项目尚未建立正式 world-model profile，也没有可参考的 Setup 草稿。"

        lines = [
            "当前项目尚未建立正式 world-model profile；以下内容来自 Setup 草稿，尚未导入 canonical world-model。",
        ]
        if setup.characters:
            names = [
                item.get("name")
                for item in setup.characters
                if isinstance(item, dict) and item.get("name")
            ]
            if names:
                lines.append("Setup 草稿角色：" + "、".join(names[:20]))
        if isinstance(setup.world_building, dict) and setup.world_building:
            lines.append(f"Setup 草稿世界设定：{setup.world_building}")
        if isinstance(setup.core_concept, dict) and setup.core_concept:
            lines.append(f"Setup 草稿核心概念：{setup.core_concept}")
        return "\n".join(lines)

    sections = []

    characters = db.query(WorldCharacter).filter(WorldCharacter.project_id == project_id).all()
    locations = db.query(WorldLocation).filter(WorldLocation.project_id == project_id).all()
    factions = db.query(WorldFaction).filter(WorldFaction.project_id == project_id).all()
    if characters or locations or factions:
        lines = ["## 世界实体"]
        for c in characters[:20]:
            lines.append(f"- 角色：{c.name}（{getattr(c, 'role', '未知')}）")
        for loc in locations[:10]:
            lines.append(f"- 地点：{loc.name}")
        for f in factions[:10]:
            lines.append(f"- 阵营：{f.name}")
        sections.append("\n".join(lines))

    relations = db.query(WorldRelation).filter(WorldRelation.project_id == project_id).limit(30).all()
    if relations:
        lines = ["## 关系网络"]
        for r in relations:
            lines.append(f"- {r.source_ref} → {r.relation_type} → {r.target_ref}")
        sections.append("\n".join(lines))

    rules = db.query(WorldRule).filter(WorldRule.project_id == project_id).limit(20).all()
    if rules:
        lines = ["## 世界规则"]
        for r in rules:
            lines.append(f"- {r.description}")
        sections.append("\n".join(lines))

    facts = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.claim_status == "confirmed",
            WorldFactClaim.claim_layer == "truth",
        )
        .limit(50)
        .all()
    )
    if facts:
        lines = ["## 当前确认事实"]
        for f in facts:
            lines.append(f"- {f.subject_ref}.{f.predicate} = {f.object_ref_or_value}")
        sections.append("\n".join(lines))

    events = (
        db.query(WorldEvent)
        .filter(
            WorldEvent.project_id == project_id,
            WorldEvent.project_profile_version_id == profile.id,
        )
        .order_by(WorldEvent.chapter_index.asc())
        .limit(30)
        .all()
    )
    if events:
        lines = ["## 时间线事件"]
        for e in events:
            lines.append(f"- 第{e.chapter_index}章：{e.description}")
        sections.append("\n".join(lines))

    if not sections:
        return "世界档案已建立（v{}），但尚无结构化数据。".format(profile.version)

    return "\n\n".join(sections)


def build_hermes_world_context(db: Session, project_id: str, chapter_index: int | None = None) -> str:
    """Compact world summary for Hermes dialog — focused on current chapter context."""
    profile = _get_current_profile(db, project_id)
    if profile is None:
        return ""

    sections = []

    characters = db.query(WorldCharacter).filter(WorldCharacter.project_id == project_id).limit(10).all()
    if characters:
        names = ", ".join(c.name for c in characters)
        sections.append(f"主要角色：{names}")

    fact_query = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.claim_status == "confirmed",
            WorldFactClaim.claim_layer == "truth",
        )
    )
    if chapter_index is not None:
        fact_query = fact_query.filter(WorldFactClaim.chapter_index <= chapter_index)
    facts = fact_query.limit(20).all()
    if facts:
        lines = ["关键事实："]
        for f in facts:
            lines.append(f"  {f.subject_ref}.{f.predicate} = {f.object_ref_or_value}")
        sections.append("\n".join(lines))

    relations = db.query(WorldRelation).filter(WorldRelation.project_id == project_id).limit(15).all()
    if relations:
        lines = ["角色关系："]
        for r in relations:
            lines.append(f"  {r.source_ref} → {r.relation_type} → {r.target_ref}")
        sections.append("\n".join(lines))

    if not sections:
        return ""

    return "\n".join(sections)

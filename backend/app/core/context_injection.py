"""Build world model context summaries for dialog system prompts."""

import json

from sqlalchemy.orm import Session

from app.core.model_call_trace import build_context_block
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


def _source_for_record(record, *, label: str | None = None, chapter_index: int | None = None) -> dict:
    source = {
        "source_type": record.__class__.__name__,
        "source_id": record.id,
    }
    if label:
        source["label"] = label
    if chapter_index is not None:
        source["chapter_index"] = chapter_index
    return source


def _format_value(value) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _get_current_profile(db: Session, project_id: str) -> ProjectProfileVersion | None:
    return (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc())
        .first()
    )


def _build_setup_fallback_block(db: Session, project_id: str, *, key_prefix: str) -> dict:
    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    if setup is None:
        return build_context_block(
            key=f"{key_prefix}.setup_fallback",
            kind="setup_fallback",
            title="Setup 草稿兜底",
            content="当前项目尚未建立正式 world-model profile，也没有可参考的 Setup 草稿。",
        )

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

    return build_context_block(
        key=f"{key_prefix}.setup_fallback",
        kind="setup_fallback",
        title="Setup 草稿兜底",
        content="\n".join(lines),
        sources=[_source_for_record(setup, label="Setup 草稿")],
    )


def build_athena_world_context_blocks(db: Session, project_id: str) -> list[dict]:
    """Structured world knowledge blocks for Athena model-call tracing."""
    profile = _get_current_profile(db, project_id)
    if profile is None:
        return [_build_setup_fallback_block(db, project_id, key_prefix="athena")]

    blocks = []

    characters = (
        db.query(WorldCharacter)
        .filter(
            WorldCharacter.project_id == project_id,
            WorldCharacter.profile_version == profile.version,
        )
        .order_by(WorldCharacter.name.asc(), WorldCharacter.canonical_id.asc(), WorldCharacter.id.asc())
        .limit(20)
        .all()
    )
    locations = (
        db.query(WorldLocation)
        .filter(
            WorldLocation.project_id == project_id,
            WorldLocation.profile_version == profile.version,
        )
        .order_by(WorldLocation.name.asc(), WorldLocation.canonical_id.asc(), WorldLocation.id.asc())
        .limit(10)
        .all()
    )
    factions = (
        db.query(WorldFaction)
        .filter(
            WorldFaction.project_id == project_id,
            WorldFaction.profile_version == profile.version,
        )
        .order_by(WorldFaction.name.asc(), WorldFaction.canonical_id.asc(), WorldFaction.id.asc())
        .limit(10)
        .all()
    )
    entity_lines = []
    entity_sources = []
    for character in characters:
        entity_lines.append(f"- 角色：{character.name}（{character.role_type}）")
        entity_sources.append(_source_for_record(character, label=character.name))
    for location in locations:
        entity_lines.append(f"- 地点：{location.name}")
        entity_sources.append(_source_for_record(location, label=location.name))
    for faction in factions:
        entity_lines.append(f"- 阵营：{faction.name}")
        entity_sources.append(_source_for_record(faction, label=faction.name))
    if entity_lines:
        blocks.append(
            build_context_block(
                key="athena.world_entities",
                kind="world_entity",
                title="世界实体",
                content="\n".join(entity_lines),
                sources=entity_sources,
            )
        )

    relations = (
        db.query(WorldRelation)
        .filter(
            WorldRelation.project_id == project_id,
            WorldRelation.profile_version == profile.version,
        )
        .order_by(
            WorldRelation.source_entity_ref.asc(),
            WorldRelation.relation_type.asc(),
            WorldRelation.target_entity_ref.asc(),
            WorldRelation.id.asc(),
        )
        .limit(30)
        .all()
    )
    if relations:
        blocks.append(
            build_context_block(
                key="athena.world_relations",
                kind="world_relation",
                title="关系网络",
                content="\n".join(
                    f"- {item.source_entity_ref} → {item.relation_type} → {item.target_entity_ref}"
                    for item in relations
                ),
                sources=[_source_for_record(item, label=item.relation_id) for item in relations],
            )
        )

    rules = (
        db.query(WorldRule)
        .filter(
            WorldRule.project_id == project_id,
            WorldRule.profile_version == profile.version,
        )
        .order_by(WorldRule.primary_alias.asc(), WorldRule.canonical_id.asc(), WorldRule.id.asc())
        .limit(20)
        .all()
    )
    if rules:
        blocks.append(
            build_context_block(
                key="athena.world_rules",
                kind="world_rule",
                title="世界规则",
                content="\n".join(f"- {item.name}：{item.statement}" for item in rules),
                sources=[_source_for_record(item, label=item.name) for item in rules],
            )
        )

    facts = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.project_profile_version_id == profile.id,
            WorldFactClaim.profile_version == profile.version,
            WorldFactClaim.claim_status == "confirmed",
            WorldFactClaim.claim_layer == "truth",
        )
        .order_by(
            WorldFactClaim.chapter_index.asc(),
            WorldFactClaim.intra_chapter_seq.asc(),
            WorldFactClaim.claim_id.asc(),
            WorldFactClaim.id.asc(),
        )
        .limit(50)
        .all()
    )
    if facts:
        blocks.append(
            build_context_block(
                key="athena.world_facts",
                kind="world_fact",
                title="当前确认事实",
                content="\n".join(
                    f"- {item.subject_ref}.{item.predicate} = {_format_value(item.object_ref_or_value)}"
                    for item in facts
                ),
                sources=[
                    _source_for_record(
                        item,
                        label=item.claim_id,
                        chapter_index=item.chapter_index,
                    )
                    for item in facts
                ],
            )
        )

    events = (
        db.query(WorldEvent)
        .filter(
            WorldEvent.project_id == project_id,
            WorldEvent.project_profile_version_id == profile.id,
            WorldEvent.profile_version == profile.version,
        )
        .order_by(
            WorldEvent.chapter_index.asc(),
            WorldEvent.intra_chapter_seq.asc(),
            WorldEvent.event_id.asc(),
            WorldEvent.id.asc(),
        )
        .limit(30)
        .all()
    )
    if events:
        blocks.append(
            build_context_block(
                key="athena.world_timeline",
                kind="world_timeline",
                title="时间线事件",
                content="\n".join(
                    f"- 第{item.chapter_index}章：{item.event_type} {_format_value(item.primitive_payload)}"
                    for item in events
                ),
                sources=[
                    _source_for_record(
                        item,
                        label=item.event_id,
                        chapter_index=item.chapter_index,
                    )
                    for item in events
                ],
            )
        )

    if not blocks:
        blocks.append(
            build_context_block(
                key="athena.world_profile",
                kind="world_profile",
                title="世界档案",
                content="世界档案已建立（v{}），但尚无结构化数据。".format(profile.version),
                sources=[_source_for_record(profile, label=f"profile v{profile.version}")],
            )
        )

    return blocks


def build_hermes_world_context_blocks(
    db: Session,
    project_id: str,
    chapter_index: int | None = None,
) -> list[dict]:
    """Structured compact world context blocks for Hermes model-call tracing."""
    profile = _get_current_profile(db, project_id)
    if profile is None:
        return []

    blocks = []

    characters = (
        db.query(WorldCharacter)
        .filter(
            WorldCharacter.project_id == project_id,
            WorldCharacter.profile_version == profile.version,
        )
        .order_by(WorldCharacter.name.asc(), WorldCharacter.canonical_id.asc(), WorldCharacter.id.asc())
        .limit(10)
        .all()
    )
    if characters:
        blocks.append(
            build_context_block(
                key="hermes.world_entities",
                kind="world_entity",
                title="主要角色",
                content="主要角色：" + "、".join(item.name for item in characters),
                sources=[_source_for_record(item, label=item.name) for item in characters],
            )
        )

    fact_query = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.project_profile_version_id == profile.id,
            WorldFactClaim.profile_version == profile.version,
            WorldFactClaim.claim_status == "confirmed",
            WorldFactClaim.claim_layer == "truth",
        )
    )
    if chapter_index is not None:
        fact_query = fact_query.filter(WorldFactClaim.chapter_index <= chapter_index)
    facts = (
        fact_query
        .order_by(
            WorldFactClaim.chapter_index.asc(),
            WorldFactClaim.intra_chapter_seq.asc(),
            WorldFactClaim.claim_id.asc(),
            WorldFactClaim.id.asc(),
        )
        .limit(20)
        .all()
    )
    if facts:
        blocks.append(
            build_context_block(
                key="hermes.world_facts",
                kind="world_fact",
                title="关键事实",
                content="\n".join(
                    f"- {item.subject_ref}.{item.predicate} = {_format_value(item.object_ref_or_value)}"
                    for item in facts
                ),
                sources=[
                    _source_for_record(
                        item,
                        label=item.claim_id,
                        chapter_index=item.chapter_index,
                    )
                    for item in facts
                ],
            )
        )

    relations = (
        db.query(WorldRelation)
        .filter(
            WorldRelation.project_id == project_id,
            WorldRelation.profile_version == profile.version,
        )
        .order_by(
            WorldRelation.source_entity_ref.asc(),
            WorldRelation.relation_type.asc(),
            WorldRelation.target_entity_ref.asc(),
            WorldRelation.id.asc(),
        )
        .limit(15)
        .all()
    )
    if relations:
        blocks.append(
            build_context_block(
                key="hermes.world_relations",
                kind="world_relation",
                title="角色关系",
                content="\n".join(
                    f"- {item.source_entity_ref} → {item.relation_type} → {item.target_entity_ref}"
                    for item in relations
                ),
                sources=[_source_for_record(item, label=item.relation_id) for item in relations],
            )
        )

    return blocks


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

    characters = (
        db.query(WorldCharacter)
        .filter(
            WorldCharacter.project_id == project_id,
            WorldCharacter.profile_version == profile.version,
        )
        .order_by(WorldCharacter.name.asc(), WorldCharacter.canonical_id.asc(), WorldCharacter.id.asc())
        .all()
    )
    locations = (
        db.query(WorldLocation)
        .filter(
            WorldLocation.project_id == project_id,
            WorldLocation.profile_version == profile.version,
        )
        .order_by(WorldLocation.name.asc(), WorldLocation.canonical_id.asc(), WorldLocation.id.asc())
        .all()
    )
    factions = (
        db.query(WorldFaction)
        .filter(
            WorldFaction.project_id == project_id,
            WorldFaction.profile_version == profile.version,
        )
        .order_by(WorldFaction.name.asc(), WorldFaction.canonical_id.asc(), WorldFaction.id.asc())
        .all()
    )
    if characters or locations or factions:
        lines = ["## 世界实体"]
        for c in characters[:20]:
            lines.append(f"- 角色：{c.name}（{c.role_type}）")
        for loc in locations[:10]:
            lines.append(f"- 地点：{loc.name}")
        for f in factions[:10]:
            lines.append(f"- 阵营：{f.name}")
        sections.append("\n".join(lines))

    relations = (
        db.query(WorldRelation)
        .filter(
            WorldRelation.project_id == project_id,
            WorldRelation.profile_version == profile.version,
        )
        .order_by(
            WorldRelation.source_entity_ref.asc(),
            WorldRelation.relation_type.asc(),
            WorldRelation.target_entity_ref.asc(),
            WorldRelation.id.asc(),
        )
        .limit(30)
        .all()
    )
    if relations:
        lines = ["## 关系网络"]
        for r in relations:
            lines.append(f"- {r.source_entity_ref} → {r.relation_type} → {r.target_entity_ref}")
        sections.append("\n".join(lines))

    rules = (
        db.query(WorldRule)
        .filter(
            WorldRule.project_id == project_id,
            WorldRule.profile_version == profile.version,
        )
        .order_by(WorldRule.primary_alias.asc(), WorldRule.canonical_id.asc(), WorldRule.id.asc())
        .limit(20)
        .all()
    )
    if rules:
        lines = ["## 世界规则"]
        for r in rules:
            lines.append(f"- {r.name}：{r.statement}")
        sections.append("\n".join(lines))

    facts = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.project_profile_version_id == profile.id,
            WorldFactClaim.profile_version == profile.version,
            WorldFactClaim.claim_status == "confirmed",
            WorldFactClaim.claim_layer == "truth",
        )
        .order_by(
            WorldFactClaim.chapter_index.asc(),
            WorldFactClaim.intra_chapter_seq.asc(),
            WorldFactClaim.claim_id.asc(),
            WorldFactClaim.id.asc(),
        )
        .limit(50)
        .all()
    )
    if facts:
        lines = ["## 当前确认事实"]
        for f in facts:
            lines.append(f"- {f.subject_ref}.{f.predicate} = {_format_value(f.object_ref_or_value)}")
        sections.append("\n".join(lines))

    events = (
        db.query(WorldEvent)
        .filter(
            WorldEvent.project_id == project_id,
            WorldEvent.project_profile_version_id == profile.id,
            WorldEvent.profile_version == profile.version,
        )
        .order_by(
            WorldEvent.chapter_index.asc(),
            WorldEvent.intra_chapter_seq.asc(),
            WorldEvent.event_id.asc(),
            WorldEvent.id.asc(),
        )
        .limit(30)
        .all()
    )
    if events:
        lines = ["## 时间线事件"]
        for e in events:
            lines.append(f"- 第{e.chapter_index}章：{e.event_type} {_format_value(e.primitive_payload)}")
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

    characters = (
        db.query(WorldCharacter)
        .filter(
            WorldCharacter.project_id == project_id,
            WorldCharacter.profile_version == profile.version,
        )
        .order_by(WorldCharacter.name.asc(), WorldCharacter.canonical_id.asc(), WorldCharacter.id.asc())
        .limit(10)
        .all()
    )
    if characters:
        names = ", ".join(c.name for c in characters)
        sections.append(f"主要角色：{names}")

    fact_query = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.project_profile_version_id == profile.id,
            WorldFactClaim.profile_version == profile.version,
            WorldFactClaim.claim_status == "confirmed",
            WorldFactClaim.claim_layer == "truth",
        )
    )
    if chapter_index is not None:
        fact_query = fact_query.filter(WorldFactClaim.chapter_index <= chapter_index)
    facts = (
        fact_query
        .order_by(
            WorldFactClaim.chapter_index.asc(),
            WorldFactClaim.intra_chapter_seq.asc(),
            WorldFactClaim.claim_id.asc(),
            WorldFactClaim.id.asc(),
        )
        .limit(20)
        .all()
    )
    if facts:
        lines = ["关键事实："]
        for f in facts:
            lines.append(f"  {f.subject_ref}.{f.predicate} = {_format_value(f.object_ref_or_value)}")
        sections.append("\n".join(lines))

    relations = (
        db.query(WorldRelation)
        .filter(
            WorldRelation.project_id == project_id,
            WorldRelation.profile_version == profile.version,
        )
        .order_by(
            WorldRelation.source_entity_ref.asc(),
            WorldRelation.relation_type.asc(),
            WorldRelation.target_entity_ref.asc(),
            WorldRelation.id.asc(),
        )
        .limit(15)
        .all()
    )
    if relations:
        lines = ["角色关系："]
        for r in relations:
            lines.append(f"  {r.source_entity_ref} → {r.relation_type} → {r.target_entity_ref}")
        sections.append("\n".join(lines))

    if not sections:
        return ""

    return "\n".join(sections)

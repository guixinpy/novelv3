"""Long-form world-model services for Athena."""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.l1_extractor import L1RuleExtractor
from app.core.world_contracts import DERIVED
from app.core.world_proposal_service import calculate_bundle_impact_scope, create_bundle, write_candidate_fact
from app.models import (
    ChapterContent,
    ConsistencyCheck,
    GenreProfile,
    Outline,
    Project,
    ProjectProfileVersion,
    Setup,
    WorldArtifact,
    WorldCharacter,
    WorldFaction,
    WorldFactClaim,
    WorldLocation,
    WorldProposalItem,
    WorldRule,
)
from app.schemas.world_proposals import ProposalCandidateFactCreate


SETUP_IMPORT_PROFILE_PREFIX = "project-setup-import"
ATHENA_ANALYZER = "athena.chapter_analyzer"


def get_current_profile(db: Session, project_id: str) -> ProjectProfileVersion | None:
    return (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc())
        .first()
    )


def import_setup_to_world_model(db: Session, project_id: str) -> dict[str, Any]:
    project = _require_project(db, project_id)
    setup = _require_setup(db, project_id)
    profile = get_current_profile(db, project_id)
    created_profile = False
    if profile is None:
        profile = _create_setup_profile(db, project=project, setup=setup)
        created_profile = True

    created = {
        "profile": 1 if created_profile else 0,
        "characters": 0,
        "locations": 0,
        "factions": 0,
        "artifacts": 0,
        "rules": 0,
    }
    for index, raw_character in enumerate(setup.characters or [], start=1):
        if not isinstance(raw_character, dict):
            continue
        name = str(raw_character.get("name") or "").strip()
        if not name:
            continue
        canonical_id = _entity_ref("char", name)
        existing = (
            db.query(WorldCharacter)
            .filter(
                WorldCharacter.project_id == project_id,
                WorldCharacter.profile_version == profile.version,
                WorldCharacter.canonical_id == canonical_id,
            )
            .first()
        )
        if existing:
            continue
        db.add(
            WorldCharacter(
                project_id=project_id,
                profile_version=profile.version,
                character_id=f"setup-character-{index}",
                canonical_id=canonical_id,
                primary_alias=name,
                name=name,
                aliases=[],
                role_type="character",
                identity_anchor=name,
                origin_background=str(raw_character.get("background") or ""),
                core_traits=[raw_character.get("personality")] if raw_character.get("personality") else [],
                core_drives=[raw_character.get("goals")] if raw_character.get("goals") else [],
                core_fears=[],
                taboos_or_bottom_lines=[],
                base_capabilities=[],
                capability_ceiling_or_constraints=[],
                default_affiliations=[],
                public_persona=str(raw_character.get("personality") or ""),
                hidden_truths=[],
                notes=f"Setup import; status={raw_character.get('character_status', 'alive')}",
                contract_version=profile.contract_version,
            )
        )
        created["characters"] += 1

    imported_terms = _extract_setup_world_terms(setup)
    for index, term in enumerate(imported_terms["locations"], start=1):
        if _create_setup_location(db, project_id=project_id, profile=profile, name=term["name"], notes=term["notes"], index=index):
            created["locations"] += 1
    for index, term in enumerate(imported_terms["factions"], start=1):
        if _create_setup_faction(db, project_id=project_id, profile=profile, name=term["name"], notes=term["notes"], index=index):
            created["factions"] += 1
    for index, term in enumerate(imported_terms["artifacts"], start=1):
        if _create_setup_artifact(db, project_id=project_id, profile=profile, name=term["name"], notes=term["notes"], index=index):
            created["artifacts"] += 1

    rules_text = ""
    if isinstance(setup.world_building, dict):
        rules_text = str(setup.world_building.get("rules") or "").strip()
    if rules_text:
        canonical_id = "rule.setup.world-rules"
        existing_rule = (
            db.query(WorldRule)
            .filter(
                WorldRule.project_id == project_id,
                WorldRule.profile_version == profile.version,
                WorldRule.canonical_id == canonical_id,
            )
            .first()
        )
        if not existing_rule:
            db.add(
                WorldRule(
                    project_id=project_id,
                    profile_version=profile.version,
                    rule_id=canonical_id,
                    canonical_id=canonical_id,
                    primary_alias="Setup 世界规则",
                    name="Setup 世界规则",
                    rule_type="setup_constraint",
                    scope="world",
                    statement=rules_text,
                    preconditions=[],
                    effects=[],
                    constraints=[rules_text],
                    exceptions=[],
                    violation_cost="需要人工修订或建立例外提案",
                    enforcement_agent="athena",
                    repair_or_override_path="通过 Athena 提案审批变更世界规则",
                    notes="Imported from Setup.world_building.rules",
                    contract_version=profile.contract_version,
                )
            )
            created["rules"] += 1

    db.commit()
    return {
        "status": "completed",
        "profile_version": profile.version,
        "project_profile_version_id": profile.id,
        "created": created,
    }


def analyze_chapter_to_world_proposals(db: Session, project_id: str, chapter_index: int) -> dict[str, Any]:
    _require_project(db, project_id)
    profile = get_current_profile(db, project_id)
    if profile is None:
        return {
            "status": "skipped",
            "reason": "missing_world_model_profile",
            "chapter_index": chapter_index,
            "task_id": None,
            "proposal_bundle_id": None,
            "created": {"proposal_items": 0},
            "skipped": {"duplicates": 0},
        }
    chapter = _require_chapter(db, project_id, chapter_index)
    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    characters = setup.characters if setup and setup.characters else _characters_from_world_model(db, project_id, profile.version)
    facts = L1RuleExtractor().extract(chapter, characters)
    candidates = [
        _candidate_from_l1_fact(project_id=project_id, profile=profile, chapter=chapter, fact=fact)
        for fact in facts
        if fact.get("type") == "character_presence"
    ]
    candidates.extend(
        _extract_non_character_entity_mentions(
            db=db,
            project_id=project_id,
            profile=profile,
            chapter=chapter,
        )
    )

    duplicate_count = 0
    new_candidates = []
    for candidate in candidates:
        if _claim_or_candidate_exists(db, project_id=project_id, claim_id=candidate.claim_id):
            duplicate_count += 1
            continue
        new_candidates.append(candidate)

    bundle_id = None
    if new_candidates:
        bundle = create_bundle(
            db=db,
            project_id=project_id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            created_by=ATHENA_ANALYZER,
            title=f"第{chapter_index}章世界事实候选",
            summary=f"从《{chapter.title}》自动抽取 {len(new_candidates)} 条低风险世界事实候选。",
        )
        bundle_id = bundle.id
        for candidate in new_candidates:
            write_candidate_fact(
                db=db,
                bundle_id=bundle.id,
                created_by=ATHENA_ANALYZER,
                candidate=candidate,
            )
        calculate_bundle_impact_scope(db=db, bundle_id=bundle.id)
    db.commit()

    return {
        "status": "completed",
        "reason": None,
        "chapter_index": chapter_index,
        "task_id": None,
        "proposal_bundle_id": bundle_id,
        "created": {"proposal_items": len(new_candidates)},
        "skipped": {"duplicates": duplicate_count},
    }


def build_chapter_context_package(db: Session, project_id: str, chapter_index: int) -> dict[str, Any]:
    _require_project(db, project_id)
    profile = get_current_profile(db, project_id)
    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    outline = db.query(Outline).filter(Outline.project_id == project_id).first()

    sections: list[dict[str, Any]] = []
    lines: list[str] = [f"【目标章节】第{chapter_index}章"]

    if profile is None:
        if setup:
            lines.append("【世界模型】尚未导入正式 world-model，以下仅为 Setup 草稿。")
            _append_setup_context(lines, setup)
            _append_retrieval_context(db=db, project_id=project_id, chapter_index=chapter_index, lines=lines, sections=sections)
        return {
            "chapter_index": chapter_index,
            "profile_version": None,
            "project_profile_version_id": None,
            "sections": sections,
            "prompt_context": "\n".join(lines),
        }

    lines.append(f"【世界模型】Profile v{profile.version}")
    if outline and outline.chapters:
        for chapter_outline in outline.chapters:
            if isinstance(chapter_outline, dict) and chapter_outline.get("chapter_index") == chapter_index:
                summary = f"{chapter_outline.get('title', '')}：{chapter_outline.get('summary', '')}".strip("：")
                lines.append(f"【本章大纲】{summary}")
                sections.append({"key": "outline", "title": "本章大纲", "items": [chapter_outline]})
                break

    _append_retrieval_context(db=db, project_id=project_id, chapter_index=chapter_index, lines=lines, sections=sections)

    characters = (
        db.query(WorldCharacter)
        .filter(WorldCharacter.project_id == project_id, WorldCharacter.profile_version == profile.version)
        .order_by(WorldCharacter.name.asc())
        .limit(30)
        .all()
    )
    if characters:
        items = [
            {
                "ref": character.canonical_id,
                "name": character.name,
                "role_type": character.role_type,
                "notes": character.notes,
            }
            for character in characters
        ]
        sections.append({"key": "characters", "title": "相关角色", "items": items})
        lines.append("【相关角色】" + "、".join(f"{item['name']}({item['ref']})" for item in items[:12]))

    locations = (
        db.query(WorldLocation)
        .filter(WorldLocation.project_id == project_id, WorldLocation.profile_version == profile.version)
        .order_by(WorldLocation.name.asc())
        .limit(20)
        .all()
    )
    if locations:
        items = [
            {
                "ref": location.canonical_id,
                "name": location.name,
                "location_type": location.location_type,
                "notes": location.notes,
            }
            for location in locations
        ]
        sections.append({"key": "locations", "title": "关键地点", "items": items})
        lines.append("【关键地点】" + "、".join(f"{item['name']}({item['ref']})" for item in items[:12]))

    factions = (
        db.query(WorldFaction)
        .filter(WorldFaction.project_id == project_id, WorldFaction.profile_version == profile.version)
        .order_by(WorldFaction.name.asc())
        .limit(20)
        .all()
    )
    if factions:
        items = [
            {
                "ref": faction.canonical_id,
                "name": faction.name,
                "faction_type": faction.faction_type,
                "notes": faction.notes,
            }
            for faction in factions
        ]
        sections.append({"key": "factions", "title": "关键势力", "items": items})
        lines.append("【关键势力】" + "、".join(f"{item['name']}({item['ref']})" for item in items[:12]))

    artifacts = (
        db.query(WorldArtifact)
        .filter(WorldArtifact.project_id == project_id, WorldArtifact.profile_version == profile.version)
        .order_by(WorldArtifact.name.asc())
        .limit(20)
        .all()
    )
    if artifacts:
        items = [
            {
                "ref": artifact.canonical_id,
                "name": artifact.name,
                "artifact_type": artifact.artifact_type,
                "notes": artifact.notes,
            }
            for artifact in artifacts
        ]
        sections.append({"key": "artifacts", "title": "关键物件", "items": items})
        lines.append("【关键物件】" + "、".join(f"{item['name']}({item['ref']})" for item in items[:12]))

    rules = (
        db.query(WorldRule)
        .filter(WorldRule.project_id == project_id, WorldRule.profile_version == profile.version)
        .order_by(WorldRule.name.asc())
        .limit(12)
        .all()
    )
    if rules:
        items = [
            {
                "ref": rule.canonical_id,
                "name": rule.name,
                "rule_type": rule.rule_type,
                "statement": rule.statement,
            }
            for rule in rules
        ]
        sections.append({"key": "rules", "title": "世界规则", "items": items})
        lines.append("【世界规则】")
        for rule in items[:8]:
            statement = str(rule["statement"]).replace("\n", " ")[:300]
            lines.append(f"- {rule['name']}({rule['ref']}): {statement}")

    facts = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.profile_version == profile.version,
            WorldFactClaim.claim_status == "confirmed",
            WorldFactClaim.claim_layer == "truth",
        )
        .filter((WorldFactClaim.chapter_index.is_(None)) | (WorldFactClaim.chapter_index <= chapter_index))
        .order_by(WorldFactClaim.chapter_index.desc(), WorldFactClaim.intra_chapter_seq.desc(), WorldFactClaim.claim_id.asc())
        .limit(40)
        .all()
    )
    if facts:
        items = [
            {
                "claim_id": fact.claim_id,
                "subject_ref": fact.subject_ref,
                "predicate": fact.predicate,
                "value": fact.object_ref_or_value,
                "chapter_index": fact.chapter_index,
            }
            for fact in facts
        ]
        sections.append({"key": "facts", "title": "已确认事实", "items": items})
        lines.append("【已确认事实】")
        for fact in items[:20]:
            lines.append(f"- {fact['subject_ref']}.{fact['predicate']} = {_json_value(fact['value'])}")

    issues = (
        db.query(ConsistencyCheck)
        .filter(
            ConsistencyCheck.project_id == project_id,
            ConsistencyCheck.status == "pending",
            ConsistencyCheck.severity.in_(["fatal", "warn"]),
        )
        .order_by(ConsistencyCheck.chapter_index.desc())
        .limit(20)
        .all()
    )
    if issues:
        items = [
            {
                "chapter_index": issue.chapter_index,
                "severity": issue.severity,
                "checker_name": issue.checker_name,
                "description": issue.description,
                "suggested_fix": issue.suggested_fix,
            }
            for issue in issues
        ]
        sections.append({"key": "open_issues", "title": "未解决一致性问题", "items": items})
        lines.append("【未解决一致性问题】")
        for issue in items[:8]:
            lines.append(f"- {issue['severity']} 第{issue['chapter_index']}章 {issue['description']}")

    return {
        "chapter_index": chapter_index,
        "profile_version": profile.version,
        "project_profile_version_id": profile.id,
        "sections": sections,
        "prompt_context": "\n".join(lines),
    }


def _create_setup_profile(db: Session, *, project: Project, setup: Setup) -> ProjectProfileVersion:
    canonical_id = f"{SETUP_IMPORT_PROFILE_PREFIX}.{project.id}"
    genre_profile = db.query(GenreProfile).filter(GenreProfile.canonical_id == canonical_id).first()
    if genre_profile is None:
        genre_profile = GenreProfile(
            canonical_id=canonical_id,
            primary_alias=project.genre or "setup",
            display_name=f"{project.name} Setup 导入档案",
            contract_version="world.contract.v1",
            field_authority={},
            schema_payload={},
            module_payload={"source": "setup_import"},
            event_types=[],
            checker_config={
                "pack_version": "world.contract.v1",
                "layers": {
                    "L0 Schema Gate": ["schema_gate"],
                    "L1 Event Ledger Gate": ["event_ledger_gate"],
                    "L2 Deterministic Replay": ["deterministic_replay"],
                    "L3 Cross-Entity Rules": ["entity_uniqueness"],
                    "L4 Profile Rules": ["profile_event_type_guard"],
                },
            },
        )
        db.add(genre_profile)
        db.flush()
    next_version = (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project.id)
        .count()
        + 1
    )
    profile = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=next_version,
        contract_version=genre_profile.contract_version,
        profile_payload={
            "source": "setup_import",
            "setup_id": setup.id,
            "world_building": setup.world_building or {},
            "core_concept": setup.core_concept or {},
        },
    )
    db.add(profile)
    db.flush()
    return profile


def _candidate_from_l1_fact(
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
    fact: dict[str, Any],
) -> ProposalCandidateFactCreate:
    name = str(fact.get("subject") or "").strip()
    subject_ref = _entity_ref("char", name)
    claim_id = f"claim.chapter.{chapter.chapter_index}.{_slug(subject_ref)}.presence_count"
    return ProposalCandidateFactCreate(
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        contract_version=profile.contract_version,
        claim_id=claim_id,
        chapter_index=chapter.chapter_index,
        intra_chapter_seq=0,
        subject_ref=subject_ref,
        predicate="presence_count",
        object_ref_or_value={
            "count": int(fact.get("new_value") or 1),
            "chapter_index": chapter.chapter_index,
            "source": "l1_rule",
        },
        claim_layer="truth",
        evidence_refs=[f"chapter:{chapter.chapter_index}"],
        authority_type=DERIVED,
        confidence=float(fact.get("confidence") or 0.85),
        notes=f"自动抽取：{name} 在第{chapter.chapter_index}章出现 {fact.get('new_value', 1)} 次。",
    )


def _extract_non_character_entity_mentions(
    *,
    db: Session,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
) -> list[ProposalCandidateFactCreate]:
    text = chapter.content or ""
    candidates: list[ProposalCandidateFactCreate] = []
    for entity in _non_character_entities_from_world_model(db, project_id, profile.version):
        mention_count = _count_entity_mentions(text=text, names=entity["names"])
        if mention_count <= 0:
            continue
        candidates.append(
            _candidate_from_entity_mention(
                project_id=project_id,
                profile=profile,
                chapter=chapter,
                entity_ref=entity["ref"],
                entity_name=entity["name"],
                entity_type=entity["entity_type"],
                mention_count=mention_count,
            )
        )
    return candidates


def _candidate_from_entity_mention(
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
    entity_ref: str,
    entity_name: str,
    entity_type: str,
    mention_count: int,
) -> ProposalCandidateFactCreate:
    claim_id = f"claim.chapter.{chapter.chapter_index}.{_slug(entity_ref)}.mentioned_in_chapter"
    return ProposalCandidateFactCreate(
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        contract_version=profile.contract_version,
        claim_id=claim_id,
        chapter_index=chapter.chapter_index,
        intra_chapter_seq=0,
        subject_ref=entity_ref,
        predicate="mentioned_in_chapter",
        object_ref_or_value={
            "chapter_index": chapter.chapter_index,
            "entity_name": entity_name,
            "entity_type": entity_type,
            "mention_count": mention_count,
            "source": "deterministic_mention",
        },
        claim_layer="truth",
        evidence_refs=[f"chapter:{chapter.chapter_index}"],
        authority_type=DERIVED,
        confidence=0.75,
        notes=f"自动抽取：{entity_name} 在第{chapter.chapter_index}章被提及 {mention_count} 次。",
    )


def _characters_from_world_model(db: Session, project_id: str, profile_version: int) -> list[dict[str, Any]]:
    characters = (
        db.query(WorldCharacter)
        .filter(WorldCharacter.project_id == project_id, WorldCharacter.profile_version == profile_version)
        .all()
    )
    return [{"name": character.name, "character_status": "alive"} for character in characters]


def _non_character_entities_from_world_model(db: Session, project_id: str, profile_version: int) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    locations = (
        db.query(WorldLocation)
        .filter(WorldLocation.project_id == project_id, WorldLocation.profile_version == profile_version)
        .order_by(WorldLocation.name.asc(), WorldLocation.canonical_id.asc())
        .all()
    )
    for location in locations:
        entities.append(_entity_mention_descriptor(location, "location"))

    factions = (
        db.query(WorldFaction)
        .filter(WorldFaction.project_id == project_id, WorldFaction.profile_version == profile_version)
        .order_by(WorldFaction.name.asc(), WorldFaction.canonical_id.asc())
        .all()
    )
    for faction in factions:
        entities.append(_entity_mention_descriptor(faction, "faction"))

    artifacts = (
        db.query(WorldArtifact)
        .filter(WorldArtifact.project_id == project_id, WorldArtifact.profile_version == profile_version)
        .order_by(WorldArtifact.name.asc(), WorldArtifact.canonical_id.asc())
        .all()
    )
    for artifact in artifacts:
        entities.append(_entity_mention_descriptor(artifact, "artifact"))
    return entities


def _entity_mention_descriptor(entity: Any, entity_type: str) -> dict[str, Any]:
    names = _entity_mention_names(entity)
    return {
        "ref": entity.canonical_id,
        "name": entity.name,
        "entity_type": entity_type,
        "names": names,
    }


def _entity_mention_names(entity: Any) -> list[str]:
    raw_names = [entity.name, entity.primary_alias, *(entity.aliases or [])]
    names: list[str] = []
    seen: set[str] = set()
    for raw_name in raw_names:
        name = str(raw_name or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def _count_entity_mentions(*, text: str, names: list[str]) -> int:
    return sum(text.count(name) for name in names if name)


def _extract_setup_world_terms(setup: Setup) -> dict[str, list[dict[str, str]]]:
    buckets: dict[str, list[dict[str, str]]] = {"locations": [], "factions": [], "artifacts": []}
    seen: dict[str, set[str]] = {key: set() for key in buckets}
    world_building = setup.world_building if isinstance(setup.world_building, dict) else {}
    core_concept = setup.core_concept if isinstance(setup.core_concept, dict) else {}
    sources = [
        ("background", str(world_building.get("background") or "")),
        ("geography", str(world_building.get("geography") or "")),
        ("society", str(world_building.get("society") or "")),
        ("rules", str(world_building.get("rules") or "")),
        ("atmosphere", str(world_building.get("atmosphere") or "")),
        ("premise", str(core_concept.get("premise") or "")),
        ("hook", str(core_concept.get("hook") or "")),
        ("unique_selling_point", str(core_concept.get("unique_selling_point") or "")),
    ]
    for source_name, text in sources:
        for term, context in _quoted_terms_with_context(text):
            bucket = _classify_setup_term(term, context, source_name)
            if not bucket or term in seen[bucket]:
                continue
            seen[bucket].add(term)
            buckets[bucket].append(
                {
                    "name": term,
                    "notes": f"来源：Setup 世界设定（{source_name}）。相关片段：{context[:220]}",
                }
            )
    return buckets


def _quoted_terms_with_context(text: str) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    for match in re.finditer(r"[‘'“\"]([^’'”\"]{2,30})[’'”\"]", text or ""):
        term = match.group(1).strip()
        if not term:
            continue
        start = max(0, match.start() - 45)
        end = min(len(text), match.end() + 45)
        results.append((term, text[start:end].strip()))
    return results


def _classify_setup_term(term: str, context: str, source_name: str) -> str | None:
    location_hints = ("站", "基地", "空间", "稳定区", "区域", "海域", "室", "维度", "城市", "城", "港", "岛", "塔", "星球")
    faction_hints = ("局", "阵线", "政府", "军方", "组织", "联盟", "公司", "学院", "教会", "计划")
    artifact_hints = ("门", "装置", "锚点", "档案", "系统", "协议", "钥", "密钥", "芯片")
    if any(hint in term for hint in location_hints):
        return "locations"
    if any(hint in term for hint in faction_hints):
        return "factions"
    if source_name == "society" and term.endswith("者"):
        return "factions"
    if any(hint in term for hint in artifact_hints) or "AI" in context or "人工智能" in context:
        return "artifacts"
    return None


def _create_setup_location(
    db: Session,
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    name: str,
    notes: str,
    index: int,
) -> bool:
    canonical_id = _entity_ref("loc", name)
    existing = (
        db.query(WorldLocation)
        .filter(
            WorldLocation.project_id == project_id,
            WorldLocation.profile_version == profile.version,
            WorldLocation.canonical_id == canonical_id,
        )
        .first()
    )
    if existing:
        return False
    db.add(
        WorldLocation(
            project_id=project_id,
            profile_version=profile.version,
            location_id=f"setup-location-{index}",
            canonical_id=canonical_id,
            primary_alias=name,
            name=name,
            aliases=[],
            location_type="setup_location",
            spatial_scope="Imported from Setup world building",
            access_constraints=[],
            functional_tags=[],
            hazards=[],
            resource_tags=[],
            surveillance_or_visibility_level="unknown",
            notes=notes,
            contract_version=profile.contract_version,
        )
    )
    return True


def _create_setup_faction(
    db: Session,
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    name: str,
    notes: str,
    index: int,
) -> bool:
    canonical_id = _entity_ref("faction", name)
    existing = (
        db.query(WorldFaction)
        .filter(
            WorldFaction.project_id == project_id,
            WorldFaction.profile_version == profile.version,
            WorldFaction.canonical_id == canonical_id,
        )
        .first()
    )
    if existing:
        return False
    db.add(
        WorldFaction(
            project_id=project_id,
            profile_version=profile.version,
            faction_id=f"setup-faction-{index}",
            canonical_id=canonical_id,
            primary_alias=name,
            name=name,
            aliases=[],
            faction_type="setup_group",
            mission_or_doctrine="Imported from Setup world building",
            structure_model="unknown",
            authority_rules=[],
            membership_rules=[],
            taboos=[],
            resource_domains=[],
            territorial_scope="",
            public_image="",
            hidden_agenda="",
            notes=notes,
            contract_version=profile.contract_version,
        )
    )
    return True


def _create_setup_artifact(
    db: Session,
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    name: str,
    notes: str,
    index: int,
) -> bool:
    canonical_id = _entity_ref("artifact", name)
    existing = (
        db.query(WorldArtifact)
        .filter(
            WorldArtifact.project_id == project_id,
            WorldArtifact.profile_version == profile.version,
            WorldArtifact.canonical_id == canonical_id,
        )
        .first()
    )
    if existing:
        return False
    db.add(
        WorldArtifact(
            project_id=project_id,
            profile_version=profile.version,
            artifact_id=f"setup-artifact-{index}",
            canonical_id=canonical_id,
            primary_alias=name,
            name=name,
            aliases=[],
            artifact_type="setup_artifact",
            origin="Imported from Setup world building",
            function_summary=notes,
            activation_conditions=[],
            usage_constraints=[],
            risk_or_side_effects=[],
            identity_or_auth_requirements=[],
            uniqueness="unknown",
            traceability="setup_import",
            notes=notes,
            contract_version=profile.contract_version,
        )
    )
    return True


def _claim_or_candidate_exists(db: Session, *, project_id: str, claim_id: str) -> bool:
    truth_exists = (
        db.query(WorldFactClaim)
        .filter(WorldFactClaim.project_id == project_id, WorldFactClaim.claim_id == claim_id)
        .first()
        is not None
    )
    if truth_exists:
        return True
    return (
        db.query(WorldProposalItem)
        .filter(WorldProposalItem.project_id == project_id, WorldProposalItem.claim_id == claim_id)
        .first()
        is not None
    )


def _append_setup_context(lines: list[str], setup: Setup) -> None:
    if setup.world_building:
        lines.append(f"【Setup 世界观】{_json_value(setup.world_building)[:800]}")
    if setup.characters:
        names = [str(item.get("name")) for item in setup.characters if isinstance(item, dict) and item.get("name")]
        if names:
            lines.append("【Setup 角色】" + "、".join(names[:20]))
    if setup.core_concept:
        lines.append(f"【Setup 核心概念】{_json_value(setup.core_concept)[:500]}")


def _append_retrieval_context(
    *,
    db: Session,
    project_id: str,
    chapter_index: int,
    lines: list[str],
    sections: list[dict[str, Any]],
) -> None:
    try:
        from app.core.athena_retrieval import build_chapter_retrieval_context

        retrieval_context = build_chapter_retrieval_context(db=db, project_id=project_id, chapter_index=chapter_index)
    except Exception:
        return
    if not retrieval_context:
        return
    sections.append(retrieval_context["section"])
    lines.extend(retrieval_context["prompt_lines"])


def _require_project(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _require_setup(db: Session, project_id: str) -> Setup:
    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    if setup is None:
        raise HTTPException(status_code=400, detail="Setup not generated yet")
    return setup


def _require_chapter(db: Session, project_id: str, chapter_index: int) -> ChapterContent:
    chapter = (
        db.query(ChapterContent)
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.chapter_index == chapter_index,
        )
        .first()
    )
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


def _entity_ref(prefix: str, name: str) -> str:
    return f"{prefix}.{name.strip()}"


def _slug(value: str) -> str:
    return re.sub(r"\s+", "_", value.strip())


def _json_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)

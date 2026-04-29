"""Long-form world-model services for Athena."""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.l1_extractor import L1RuleExtractor
from app.core.world_contracts import DERIVED
from app.core.world_context_assembler import build_chapter_world_context_package
from app.core.world_projection_service import invalidate_world_projection_cache
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
    invalidate_world_projection_cache(project_id=project_id)
    return {
        "status": "completed",
        "profile_version": profile.version,
        "project_profile_version_id": profile.id,
        "created": created,
    }


def preview_setup_import_to_world_model(db: Session, project_id: str) -> dict[str, Any]:
    _require_project(db, project_id)
    setup = _require_setup(db, project_id)
    profile = get_current_profile(db, project_id)
    profile_version = profile.version if profile else None
    imported_terms = _extract_setup_world_terms(setup)

    candidates = {
        "characters": _preview_setup_characters(setup, profile=profile, db=db, project_id=project_id),
        "locations": _preview_setup_terms(
            db=db,
            project_id=project_id,
            profile=profile,
            prefix="loc",
            terms=imported_terms["locations"],
            source="setup.world_building",
            model=WorldLocation,
        ),
        "factions": _preview_setup_terms(
            db=db,
            project_id=project_id,
            profile=profile,
            prefix="faction",
            terms=imported_terms["factions"],
            source="setup.world_building",
            model=WorldFaction,
        ),
        "artifacts": _preview_setup_terms(
            db=db,
            project_id=project_id,
            profile=profile,
            prefix="artifact",
            terms=imported_terms["artifacts"],
            source="setup.world_building",
            model=WorldArtifact,
        ),
        "rules": _preview_setup_rules(db=db, project_id=project_id, profile=profile, setup=setup),
    }
    return {
        "status": "preview",
        "project_profile_exists": profile is not None,
        "profile_version": profile_version,
        "would_create": {
            "profile": 0 if profile else 1,
            **{key: len(value) for key, value in candidates.items()},
        },
        "candidates": candidates,
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
    world_model_characters = _characters_from_world_model(db, project_id, profile.version)
    characters = world_model_characters or (setup.characters if setup and setup.characters else [])
    facts = L1RuleExtractor().extract(chapter, characters)
    candidates = [
        _candidate_from_l1_fact(project_id=project_id, profile=profile, chapter=chapter, fact=fact)
        for fact in facts
        if fact.get("type") == "character_presence"
    ]
    event_candidate = _extract_chapter_event_candidate(project_id=project_id, profile=profile, chapter=chapter)
    if event_candidate:
        candidates.append(event_candidate)
    candidates.extend(
        _extract_non_character_entity_mentions(
            db=db,
            project_id=project_id,
            profile=profile,
            chapter=chapter,
        )
    )
    candidates.extend(
        _extract_character_location_candidates(
            db=db,
            project_id=project_id,
            profile=profile,
            chapter=chapter,
            characters=characters,
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
        try:
            bundle = create_bundle(
                db=db,
                project_id=project_id,
                project_profile_version_id=profile.id,
                profile_version=profile.version,
                created_by=ATHENA_ANALYZER,
                title=f"第{chapter_index}章世界事实候选",
                summary=f"从《{chapter.title}》自动抽取 {len(new_candidates)} 条低风险世界事实候选。",
                commit=False,
            )
            bundle_id = bundle.id
            for candidate in new_candidates:
                write_candidate_fact(
                    db=db,
                    bundle_id=bundle.id,
                    created_by=ATHENA_ANALYZER,
                    candidate=candidate,
                    commit=False,
                )
            calculate_bundle_impact_scope(db=db, bundle_id=bundle.id, commit=False)
            db.commit()
        except Exception:
            db.rollback()
            raise
    invalidate_world_projection_cache(project_id=project_id)

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
    return build_chapter_world_context_package(db, project_id, chapter_index)


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


def _preview_setup_characters(
    setup: Setup,
    *,
    profile: ProjectProfileVersion | None,
    db: Session,
    project_id: str,
) -> list[dict[str, Any]]:
    candidates = []
    for raw_character in setup.characters or []:
        if not isinstance(raw_character, dict):
            continue
        name = str(raw_character.get("name") or "").strip()
        if not name:
            continue
        canonical_id = _entity_ref("char", name)
        if _setup_entity_exists(db, model=WorldCharacter, project_id=project_id, profile=profile, canonical_id=canonical_id):
            continue
        candidates.append(
            {
                "name": name,
                "canonical_id": canonical_id,
                "source": "setup.characters",
                "description": str(raw_character.get("background") or raw_character.get("personality") or ""),
            }
        )
    return candidates


def _preview_setup_terms(
    *,
    db: Session,
    project_id: str,
    profile: ProjectProfileVersion | None,
    prefix: str,
    terms: list[dict[str, str]],
    source: str,
    model,
) -> list[dict[str, Any]]:
    candidates = []
    for term in terms:
        name = str(term.get("name") or "").strip()
        if not name:
            continue
        canonical_id = _entity_ref(prefix, name)
        if _setup_entity_exists(db, model=model, project_id=project_id, profile=profile, canonical_id=canonical_id):
            continue
        candidates.append(
            {
                "name": name,
                "canonical_id": canonical_id,
                "source": source,
                "description": str(term.get("notes") or ""),
            }
        )
    return candidates


def _preview_setup_rules(
    *,
    db: Session,
    project_id: str,
    profile: ProjectProfileVersion | None,
    setup: Setup,
) -> list[dict[str, Any]]:
    rules_text = ""
    if isinstance(setup.world_building, dict):
        rules_text = str(setup.world_building.get("rules") or "").strip()
    if not rules_text:
        return []
    canonical_id = "rule.setup.world-rules"
    if _setup_entity_exists(db, model=WorldRule, project_id=project_id, profile=profile, canonical_id=canonical_id):
        return []
    return [
        {
            "name": "Setup 世界规则",
            "canonical_id": canonical_id,
            "source": "setup.world_building.rules",
            "description": rules_text,
        }
    ]


def _setup_entity_exists(
    db: Session,
    *,
    model,
    project_id: str,
    profile: ProjectProfileVersion | None,
    canonical_id: str,
) -> bool:
    if profile is None:
        return False
    return (
        db.query(model)
        .filter(
            model.project_id == project_id,
            model.profile_version == profile.version,
            model.canonical_id == canonical_id,
        )
        .first()
        is not None
    )


def _candidate_from_l1_fact(
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
    fact: dict[str, Any],
) -> ProposalCandidateFactCreate:
    name = str(fact.get("subject") or "").strip()
    subject_ref = str(fact.get("subject_ref") or "").strip() or _entity_ref("char", name)
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
            "matched_names": fact.get("matched_names") or [name],
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


def _extract_chapter_event_candidate(
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
) -> ProposalCandidateFactCreate | None:
    summary = _chapter_event_summary(chapter)
    if not summary:
        return None
    return ProposalCandidateFactCreate(
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        contract_version=profile.contract_version,
        claim_id=f"claim.chapter.{chapter.chapter_index}.event.summary",
        chapter_index=chapter.chapter_index,
        intra_chapter_seq=0,
        subject_ref=f"chapter.{chapter.chapter_index}",
        predicate="event_summary",
        object_ref_or_value={
            "chapter_index": chapter.chapter_index,
            "title": chapter.title or f"第{chapter.chapter_index}章",
            "summary": summary,
            "source": "deterministic_chapter_summary",
        },
        claim_layer="truth",
        evidence_refs=[f"chapter:{chapter.chapter_index}"],
        authority_type=DERIVED,
        confidence=0.7,
        notes=f"自动抽取：第{chapter.chapter_index}章事件摘要，需人工确认。",
    )


def _extract_character_location_candidates(
    *,
    db: Session,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
    characters: list[dict[str, Any]],
) -> list[ProposalCandidateFactCreate]:
    text = chapter.content or ""
    if not text:
        return []
    character_descriptors = _character_descriptors(characters)
    location_descriptors = _location_descriptors_from_world_model(db, project_id, profile.version)
    candidates: list[ProposalCandidateFactCreate] = []
    seen: set[tuple[str, str]] = set()
    for sentence in _chapter_sentences(text):
        for character in character_descriptors:
            if _count_entity_mentions(text=sentence, names=character["names"]) <= 0:
                continue
            for location in location_descriptors:
                if _count_entity_mentions(text=sentence, names=location["names"]) <= 0:
                    continue
                key = (character["ref"], location["ref"])
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    _candidate_from_character_location(
                        project_id=project_id,
                        profile=profile,
                        chapter=chapter,
                        character_ref=character["ref"],
                        character_name=character["name"],
                        location_ref=location["ref"],
                        location_name=location["name"],
                        evidence=sentence,
                    )
                )
                if len(candidates) >= 12:
                    return candidates
    return candidates


def _candidate_from_character_location(
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
    character_ref: str,
    character_name: str,
    location_ref: str,
    location_name: str,
    evidence: str,
) -> ProposalCandidateFactCreate:
    claim_id = f"claim.chapter.{chapter.chapter_index}.{_slug(character_ref)}.{_slug(location_ref)}.present_at_location"
    return ProposalCandidateFactCreate(
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        contract_version=profile.contract_version,
        claim_id=claim_id,
        chapter_index=chapter.chapter_index,
        intra_chapter_seq=0,
        subject_ref=character_ref,
        predicate="present_at_location",
        object_ref_or_value={
            "chapter_index": chapter.chapter_index,
            "character_name": character_name,
            "location_ref": location_ref,
            "location_name": location_name,
            "evidence": evidence[:180],
            "source": "deterministic_cooccurrence",
        },
        claim_layer="truth",
        evidence_refs=[f"chapter:{chapter.chapter_index}"],
        authority_type=DERIVED,
        confidence=0.78,
        notes=f"自动抽取：{character_name} 与 {location_name} 在同一句场景中共现。",
    )


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
    return [
        {
            "ref": character.canonical_id,
            "name": character.name,
            "aliases": character.aliases or [],
            "character_status": "alive",
        }
        for character in characters
    ]


def _character_descriptors(characters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    descriptors = []
    seen_refs: set[str] = set()
    for raw_character in characters:
        if not isinstance(raw_character, dict):
            continue
        name = str(raw_character.get("name") or "").strip()
        if not name:
            continue
        ref = str(raw_character.get("ref") or "").strip() or _entity_ref("char", name)
        if ref in seen_refs:
            continue
        seen_refs.add(ref)
        aliases = raw_character.get("aliases") if isinstance(raw_character.get("aliases"), list) else []
        names = _unique_non_empty([name, *aliases])
        descriptors.append({"ref": ref, "name": name, "names": names})
    return descriptors


def _location_descriptors_from_world_model(db: Session, project_id: str, profile_version: int) -> list[dict[str, Any]]:
    locations = (
        db.query(WorldLocation)
        .filter(WorldLocation.project_id == project_id, WorldLocation.profile_version == profile_version)
        .order_by(WorldLocation.name.asc(), WorldLocation.canonical_id.asc())
        .all()
    )
    return [_entity_mention_descriptor(location, "location") for location in locations]


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
    return _unique_non_empty(raw_names)


def _unique_non_empty(raw_names: list[Any]) -> list[str]:
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


def _chapter_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"[。！？!?；;\n]+", text or "") if sentence.strip()]


def _chapter_event_summary(chapter: ChapterContent) -> str:
    sentences = _chapter_sentences(chapter.content or "")
    if not sentences:
        return ""
    return "。".join(sentences[:2])[:220]


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
            if not bucket:
                continue
            _append_setup_term(buckets=buckets, seen=seen, bucket=bucket, term=term, context=context, source_name=source_name)
        for term, context in _unquoted_terms_with_context(text):
            bucket = _classify_setup_term(term, context, source_name)
            if not bucket:
                continue
            _append_setup_term(buckets=buckets, seen=seen, bucket=bucket, term=term, context=context, source_name=source_name)
    return buckets


def _append_setup_term(
    *,
    buckets: dict[str, list[dict[str, str]]],
    seen: dict[str, set[str]],
    bucket: str,
    term: str,
    context: str,
    source_name: str,
) -> None:
    if term in seen[bucket] or any(term != existing and term in existing for existing in seen[bucket]):
        return
    shorter_existing = [existing for existing in seen[bucket] if existing != term and existing in term]
    if shorter_existing:
        seen[bucket].difference_update(shorter_existing)
        buckets[bucket] = [item for item in buckets[bucket] if item["name"] not in shorter_existing]
    seen[bucket].add(term)
    buckets[bucket].append(
        {
            "name": term,
            "notes": f"来源：Setup 世界设定（{source_name}）。相关片段：{context[:220]}",
        }
    )


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


def _unquoted_terms_with_context(text: str) -> list[tuple[str, str]]:
    normalized = (text or "").strip()
    if not normalized:
        return []
    suffixes = (
        "稳定区",
        "守夜人联盟",
        "联盟",
        "学院",
        "教会",
        "公司",
        "政府",
        "军方",
        "阵线",
        "基地",
        "空间",
        "区域",
        "海域",
        "城市",
        "星球",
        "钥匙",
        "密钥",
        "装置",
        "系统",
        "协议",
        "档案",
        "计划",
        "城",
        "港",
        "岛",
        "塔",
        "局",
        "门",
    )
    results: list[tuple[str, str]] = []
    seen: set[str] = set()
    segments = re.split(
        r"[，。；、\s]+|旁|里|内|外|中|由|被|与|和|及|到|从|在|负责|控制|存放|开启|隐瞒|看守|矗立|封锁|必须|保持",
        normalized,
    )
    for segment in segments:
        segment = segment.strip()
        if len(segment) < 2:
            continue
        for suffix in suffixes:
            for match in re.finditer(rf"[\u4e00-\u9fffA-Za-z0-9]{{1,18}}{re.escape(suffix)}", segment):
                term = _clean_unquoted_setup_term(match.group(0))
                if not term or term in seen:
                    continue
                seen.add(term)
                start = max(0, normalized.find(segment) - 35)
                end = min(len(normalized), normalized.find(segment) + len(segment) + 35)
                results.append((term, normalized[start:end].strip()))
    return _prefer_longer_setup_terms(results)


def _prefer_longer_setup_terms(results: list[tuple[str, str]]) -> list[tuple[str, str]]:
    preferred: list[tuple[str, str]] = []
    for term, context in sorted(results, key=lambda item: (-len(item[0]), item[0])):
        if any(term != kept_term and term in kept_term for kept_term, _ in preferred):
            continue
        preferred.append((term, context))
    return preferred


def _clean_unquoted_setup_term(term: str) -> str:
    cleaned = re.sub(
        r"^(?:(故事|世界|这个|一种|一个|负责|控制|存放|开启|隐瞒|巡查|矗立|封锁|必须|保持|真实用途))+",
        "",
        term.strip(),
    )
    for delimiter in ("发生在", "位于", "藏有", "藏在", "存放", "控制", "负责", "看守", "矗立", "开启"):
        if delimiter in cleaned:
            cleaned = cleaned.split(delimiter)[-1].strip()
    if len(cleaned) < 2 or len(cleaned) > 12:
        return ""
    return cleaned


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

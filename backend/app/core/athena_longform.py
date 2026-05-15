"""Long-form world-model services for Athena."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.athena_chapter_candidates import (
    candidate_from_l1_fact as _candidate_from_l1_fact,
    extract_chapter_event_candidate as _extract_chapter_event_candidate,
    extract_character_location_candidates as _extract_character_location_candidates,
    extract_non_character_entity_mentions as _extract_non_character_entity_mentions,
)
from app.core.athena_entity_resolver import (
    characters_from_world_model as _characters_from_world_model,
    entity_ref as _entity_ref,
)
from app.core.athena_setup_terms import extract_setup_world_terms as _extract_setup_world_terms
from app.core.l1_extractor import L1RuleExtractor
from app.core.world_context_assembler import build_chapter_world_context_package
from app.core.world_projection_service import invalidate_world_projection_cache
from app.core.world_proposal_state import ACTIONABLE_REVIEW_ITEM_STATUSES
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
from app.models.genre_profile import CORE_WORLD_EVENT_TYPES


SETUP_IMPORT_PROFILE_PREFIX = "project-setup-import"
ATHENA_ANALYZER = "athena.chapter_analyzer"
ATHENA_CANDIDATE_REFRESH_FIELDS = (
    "chapter_index",
    "intra_chapter_seq",
    "subject_ref",
    "predicate",
    "object_ref_or_value",
    "claim_layer",
    "perspective_ref",
    "disclosed_to_refs",
    "valid_from_anchor_id",
    "valid_to_anchor_id",
    "source_event_ref",
    "evidence_refs",
    "authority_type",
    "confidence",
    "notes",
    "contract_version",
)


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
            "updated": {"proposal_items": 0},
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
    updated_count = 0
    updated_bundle_ids: set[str] = set()
    new_candidates = []
    for candidate in candidates:
        if _truth_claim_exists(db, project_id=project_id, claim_id=candidate.claim_id):
            duplicate_count += 1
            continue
        existing_candidate = _find_existing_candidate(
            db,
            project_id=project_id,
            profile=profile,
            claim_id=candidate.claim_id,
        )
        if existing_candidate is not None:
            duplicate_count += 1
            if _refresh_existing_athena_candidate(existing_candidate, candidate):
                updated_count += 1
                updated_bundle_ids.add(existing_candidate.bundle_id)
            continue
        new_candidates.append(candidate)

    bundle_id = None
    if new_candidates or updated_bundle_ids:
        try:
            if new_candidates:
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
                updated_bundle_ids.add(bundle.id)
            for impacted_bundle_id in sorted(updated_bundle_ids):
                calculate_bundle_impact_scope(db=db, bundle_id=impacted_bundle_id, commit=False)
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
        "updated": {"proposal_items": updated_count},
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
            event_types=list(CORE_WORLD_EVENT_TYPES),
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


def _truth_claim_exists(db: Session, *, project_id: str, claim_id: str) -> bool:
    return (
        db.query(WorldFactClaim)
        .filter(WorldFactClaim.project_id == project_id, WorldFactClaim.claim_id == claim_id)
        .first()
        is not None
    )


def _find_existing_candidate(
    db: Session,
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    claim_id: str,
) -> WorldProposalItem | None:
    return (
        db.query(WorldProposalItem)
        .filter(
            WorldProposalItem.project_id == project_id,
            WorldProposalItem.project_profile_version_id == profile.id,
            WorldProposalItem.profile_version == profile.version,
            WorldProposalItem.claim_id == claim_id,
        )
        .order_by(WorldProposalItem.updated_at.desc(), WorldProposalItem.created_at.desc())
        .first()
    )


def _refresh_existing_athena_candidate(item: WorldProposalItem, candidate: Any) -> bool:
    if item.created_by != ATHENA_ANALYZER or item.item_status not in ACTIONABLE_REVIEW_ITEM_STATUSES:
        return False
    changed = False
    for field in ATHENA_CANDIDATE_REFRESH_FIELDS:
        next_value = getattr(candidate, field)
        if getattr(item, field) != next_value:
            setattr(item, field, next_value)
            changed = True
    if changed:
        item.item_status = "needs_edit"
    return changed


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

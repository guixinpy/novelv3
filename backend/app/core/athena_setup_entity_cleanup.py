"""Cleanup helpers for phrase-like Athena Setup world entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.athena_setup_terms import clean_unquoted_setup_term, extract_setup_world_terms
from app.core.world_projection_service import invalidate_world_projection_cache
from app.models import (
    Setup,
    WorldEvent,
    WorldFactClaim,
    WorldFaction,
    WorldLocation,
    WorldProposalImpactScopeSnapshot,
    WorldProposalItem,
    WorldRelation,
)


@dataclass(frozen=True)
class EntityRename:
    entity_type: str
    profile_version: int
    old_ref: str
    old_name: str
    new_ref: str
    new_name: str
    action: str


def cleanup_phrase_like_setup_entities(db: Session, project_id: str, *, apply: bool = False) -> dict[str, Any]:
    setup_terms = _project_setup_terms(db=db, project_id=project_id)
    renames: list[EntityRename] = []

    renames.extend(_cleanup_entities(db, project_id, WorldLocation, "location", setup_terms["locations"], apply=apply))
    renames.extend(_cleanup_entities(db, project_id, WorldFaction, "faction", setup_terms["factions"], apply=apply))
    ref_rewrites = _rewrite_world_refs(db, project_id, {rename.old_ref: rename.new_ref for rename in renames}, apply=apply)

    if apply and renames:
        db.flush()
        invalidate_world_projection_cache(project_id=project_id)

    return {
        "project_id": project_id,
        "apply": apply,
        "renames": [rename.__dict__ for rename in renames],
        "ref_rewrites": ref_rewrites,
    }


def _project_setup_terms(db: Session, project_id: str) -> dict[str, set[str]]:
    setup = (
        db.query(Setup)
        .filter(Setup.project_id == project_id)
        .order_by(Setup.updated_at.desc(), Setup.created_at.desc())
        .first()
    )
    if not setup:
        return {"locations": set(), "factions": set()}
    extracted = extract_setup_world_terms(setup)
    return {
        "locations": {term["name"] for term in extracted.get("locations", [])},
        "factions": {term["name"] for term in extracted.get("factions", [])},
    }


def _cleanup_entities(
    db: Session,
    project_id: str,
    model: type[WorldLocation] | type[WorldFaction],
    entity_type: str,
    setup_names: set[str],
    *,
    apply: bool,
) -> list[EntityRename]:
    renames: list[EntityRename] = []
    entities = (
        db.query(model)
        .filter(model.project_id == project_id)
        .order_by(model.profile_version.asc(), model.created_at.asc())
        .all()
    )
    targets = {(entity.profile_version, entity.canonical_id): entity for entity in entities}
    for entity in entities:
        new_name = _normalized_entity_name(entity.name, entity_type=entity_type, setup_names=setup_names)
        if not new_name or new_name == entity.name:
            continue
        old_ref = entity.canonical_id
        old_name = entity.name
        new_ref = f"{'loc' if entity_type == 'location' else 'faction'}.{new_name}"
        target = targets.get((entity.profile_version, new_ref))
        if target and target.id != entity.id:
            if apply:
                _merge_entity(target, entity)
                db.delete(entity)
            action = "merge"
        else:
            if apply:
                _rename_entity(entity, new_ref, new_name)
            targets[(entity.profile_version, new_ref)] = entity
            action = "rename"
        renames.append(
            EntityRename(
                entity_type=entity_type,
                profile_version=entity.profile_version,
                old_ref=old_ref,
                old_name=old_name,
                new_ref=new_ref,
                new_name=new_name,
                action=action,
            )
        )
    return renames


def _normalized_entity_name(name: str, *, entity_type: str, setup_names: set[str]) -> str | None:
    if entity_type == "location":
        return _normalized_location_name(name, setup_names)
    return _normalized_faction_name(name, setup_names)


def _normalized_location_name(name: str, setup_names: set[str]) -> str | None:
    if "分为" in name:
        left = clean_unquoted_setup_term(name.split("分为", 1)[0])
        if left:
            return left
    city_name = next((candidate for candidate in setup_names if candidate.endswith("城")), None)
    if name in {"沿海城市", "沿海城"} and city_name:
        return city_name
    if "北端半岛" in name:
        return "北端半岛"
    if "渔港" in name:
        return "渔港"
    if "灯塔" in name and name != "灯塔区":
        return "灯塔"
    cleaned = clean_unquoted_setup_term(name)
    return cleaned if cleaned and cleaned != name else None


def _normalized_faction_name(name: str, setup_names: set[str]) -> str | None:
    for setup_name in sorted(setup_names, key=len, reverse=True):
        if setup_name in name:
            return setup_name
    cleaned = clean_unquoted_setup_term(name)
    return cleaned if cleaned and cleaned != name else None


def _merge_entity(target: WorldLocation | WorldFaction, source: WorldLocation | WorldFaction) -> None:
    target.aliases = _merged_aliases(target.aliases, source.aliases, source.name, source.canonical_id)
    if source.notes and source.notes not in (target.notes or ""):
        target.notes = "\n".join(part for part in [target.notes, source.notes] if part)


def _rename_entity(entity: WorldLocation | WorldFaction, new_ref: str, new_name: str) -> None:
    entity.aliases = _merged_aliases(entity.aliases, [], entity.name, entity.canonical_id)
    entity.canonical_id = new_ref
    if isinstance(entity, WorldLocation):
        entity.location_id = new_ref
    else:
        entity.faction_id = new_ref
    entity.primary_alias = new_name
    entity.name = new_name


def _merged_aliases(current: Any, extra: Any, *names: str) -> list[str]:
    merged: list[str] = []
    for value in [*(current if isinstance(current, list) else []), *(extra if isinstance(extra, list) else []), *names]:
        if isinstance(value, str) and value and value not in merged:
            merged.append(value)
    return merged


def _rewrite_world_refs(db: Session, project_id: str, ref_map: dict[str, str], *, apply: bool) -> int:
    if not ref_map:
        return 0
    rewrites = 0
    for claim in db.query(WorldFactClaim).filter(WorldFactClaim.project_id == project_id).all():
        rewrites += _rewrite_string_attr(claim, "subject_ref", ref_map, apply=apply)
        rewrites += _rewrite_json_attr(claim, "object_ref_or_value", ref_map, apply=apply)
        rewrites += _rewrite_json_attr(claim, "disclosed_to_refs", ref_map, apply=apply)
    for item in db.query(WorldProposalItem).filter(WorldProposalItem.project_id == project_id).all():
        rewrites += _rewrite_string_attr(item, "subject_ref", ref_map, apply=apply)
        rewrites += _rewrite_json_attr(item, "object_ref_or_value", ref_map, apply=apply)
        rewrites += _rewrite_json_attr(item, "disclosed_to_refs", ref_map, apply=apply)
    for snapshot in db.query(WorldProposalImpactScopeSnapshot).filter(WorldProposalImpactScopeSnapshot.project_id == project_id).all():
        rewrites += _rewrite_json_attr(snapshot, "affected_subject_refs", ref_map, apply=apply)
        rewrites += _rewrite_json_attr(snapshot, "summary", ref_map, apply=apply)
    for event in db.query(WorldEvent).filter(WorldEvent.project_id == project_id).all():
        rewrites += _rewrite_json_attr(event, "participant_refs", ref_map, apply=apply)
        rewrites += _rewrite_json_attr(event, "location_refs", ref_map, apply=apply)
        rewrites += _rewrite_json_attr(event, "primitive_payload", ref_map, apply=apply)
        rewrites += _rewrite_json_attr(event, "state_diffs", ref_map, apply=apply)
    for relation in db.query(WorldRelation).filter(WorldRelation.project_id == project_id).all():
        rewrites += _rewrite_string_attr(relation, "source_entity_ref", ref_map, apply=apply)
        rewrites += _rewrite_string_attr(relation, "target_entity_ref", ref_map, apply=apply)
    return rewrites


def _rewrite_string_attr(row: Any, attr: str, ref_map: dict[str, str], *, apply: bool) -> int:
    current = getattr(row, attr)
    replacement = ref_map.get(current)
    if not replacement:
        return 0
    if apply:
        setattr(row, attr, replacement)
    return 1


def _rewrite_json_attr(row: Any, attr: str, ref_map: dict[str, str], *, apply: bool) -> int:
    current = getattr(row, attr)
    updated = _replace_json_refs(current, ref_map)
    if updated == current:
        return 0
    if apply:
        setattr(row, attr, updated)
    return 1


def _replace_json_refs(value: Any, ref_map: dict[str, str]) -> Any:
    if isinstance(value, str):
        return ref_map.get(value, value)
    if isinstance(value, list):
        return [_replace_json_refs(item, ref_map) for item in value]
    if isinstance(value, dict):
        return {key: _replace_json_refs(item, ref_map) for key, item in value.items()}
    return value

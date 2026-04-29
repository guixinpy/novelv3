"""Entity lookup helpers shared by Athena world-model analyzers."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.models import WorldArtifact, WorldCharacter, WorldFaction, WorldLocation


def entity_ref(prefix: str, name: str) -> str:
    return f"{prefix}.{name.strip()}"


def slug(value: str) -> str:
    return re.sub(r"\s+", "_", value.strip())


def characters_from_world_model(db: Session, project_id: str, profile_version: int) -> list[dict[str, Any]]:
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


def character_descriptors(characters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    descriptors = []
    seen_refs: set[str] = set()
    for raw_character in characters:
        if not isinstance(raw_character, dict):
            continue
        name = str(raw_character.get("name") or "").strip()
        if not name:
            continue
        ref = str(raw_character.get("ref") or "").strip() or entity_ref("char", name)
        if ref in seen_refs:
            continue
        seen_refs.add(ref)
        aliases = raw_character.get("aliases") if isinstance(raw_character.get("aliases"), list) else []
        names = unique_non_empty([name, *aliases])
        descriptors.append({"ref": ref, "name": name, "names": names})
    return descriptors


def location_descriptors_from_world_model(db: Session, project_id: str, profile_version: int) -> list[dict[str, Any]]:
    locations = (
        db.query(WorldLocation)
        .filter(WorldLocation.project_id == project_id, WorldLocation.profile_version == profile_version)
        .order_by(WorldLocation.name.asc(), WorldLocation.canonical_id.asc())
        .all()
    )
    return [entity_mention_descriptor(location, "location") for location in locations]


def non_character_entities_from_world_model(db: Session, project_id: str, profile_version: int) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    locations = (
        db.query(WorldLocation)
        .filter(WorldLocation.project_id == project_id, WorldLocation.profile_version == profile_version)
        .order_by(WorldLocation.name.asc(), WorldLocation.canonical_id.asc())
        .all()
    )
    for location in locations:
        entities.append(entity_mention_descriptor(location, "location"))

    factions = (
        db.query(WorldFaction)
        .filter(WorldFaction.project_id == project_id, WorldFaction.profile_version == profile_version)
        .order_by(WorldFaction.name.asc(), WorldFaction.canonical_id.asc())
        .all()
    )
    for faction in factions:
        entities.append(entity_mention_descriptor(faction, "faction"))

    artifacts = (
        db.query(WorldArtifact)
        .filter(WorldArtifact.project_id == project_id, WorldArtifact.profile_version == profile_version)
        .order_by(WorldArtifact.name.asc(), WorldArtifact.canonical_id.asc())
        .all()
    )
    for artifact in artifacts:
        entities.append(entity_mention_descriptor(artifact, "artifact"))
    return entities


def entity_mention_descriptor(entity: Any, entity_type: str) -> dict[str, Any]:
    return {
        "ref": entity.canonical_id,
        "name": entity.name,
        "entity_type": entity_type,
        "names": entity_mention_names(entity),
    }


def entity_mention_names(entity: Any) -> list[str]:
    raw_names = [entity.name, entity.primary_alias, *(entity.aliases or [])]
    return unique_non_empty(raw_names)


def unique_non_empty(raw_names: list[Any]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for raw_name in raw_names:
        name = str(raw_name or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def count_entity_mentions(*, text: str, names: list[str]) -> int:
    return sum(text.count(name) for name in names if name)


def chapter_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"[。！？!?；;\n]+", text or "") if sentence.strip()]

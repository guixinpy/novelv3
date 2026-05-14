from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.athena_shared import get_current_profile, require_project, world_entity_description, world_entity_type
from app.core.athena_longform import import_setup_to_world_model, preview_setup_import_to_world_model
from app.db import get_db
from app.models import (
    Setup,
    WorldArtifact,
    WorldCharacter,
    WorldFaction,
    WorldLocation,
    WorldRelation,
    WorldResource,
    WorldRule,
)

router = APIRouter()
DEFAULT_ONTOLOGY_ENTITY_LIMIT = 500
DEFAULT_ONTOLOGY_RELATION_LIMIT = 1000
DEFAULT_ONTOLOGY_RULE_LIMIT = 500


@router.get("/ontology")
def get_ontology(
    project_id: str,
    db: Session = Depends(get_db),
    entity_offset: int = Query(0, ge=0),
    entity_limit: int = Query(DEFAULT_ONTOLOGY_ENTITY_LIMIT, ge=1, le=1000),
    relation_offset: int = Query(0, ge=0),
    relation_limit: int = Query(DEFAULT_ONTOLOGY_RELATION_LIMIT, ge=1, le=2000),
    rule_offset: int = Query(0, ge=0),
    rule_limit: int = Query(DEFAULT_ONTOLOGY_RULE_LIMIT, ge=1, le=1000),
):
    require_project(db, project_id)
    profile = get_current_profile(db, project_id)
    setup = db.query(Setup).filter(Setup.project_id == project_id).first()

    entities = {}
    pagination = {
        "entities": {},
        "relations": _page_meta(0, relation_offset, relation_limit),
        "rules": _page_meta(0, rule_offset, rule_limit),
    }
    if profile:
        for model, key in [
            (WorldCharacter, "characters"),
            (WorldLocation, "locations"),
            (WorldFaction, "factions"),
            (WorldArtifact, "artifacts"),
            (WorldResource, "resources"),
        ]:
            filters = [
                model.project_id == project_id,
                model.profile_version == profile.version,
            ]
            query = db.query(model).filter(*filters)
            total = db.query(func.count(model.id)).filter(*filters).scalar() or 0
            items = (
                query.order_by(model.canonical_id.asc(), model.id.asc())
                .offset(entity_offset)
                .limit(entity_limit)
                .all()
            )
            pagination["entities"][key] = _page_meta(total, entity_offset, entity_limit)
            entities[key] = [
                {
                    "id": item.id,
                    "canonical_id": item.canonical_id,
                    "name": getattr(item, "name", getattr(item, "entity_ref", item.id)),
                    "primary_alias": getattr(item, "primary_alias", ""),
                    "aliases": getattr(item, "aliases", []),
                    "type": world_entity_type(item, key),
                    "description": world_entity_description(item),
                }
                for item in items
            ]

    if not any(entities.get(k) for k in entities) and setup and setup.characters:
        entities["characters"] = [
            {"id": f"setup-char-{i}", "name": c.get("name", f"角色{i+1}")}
            for i, c in enumerate(setup.characters)
            if isinstance(c, dict)
        ]

    relations = []
    if profile:
        rel_filters = [
            WorldRelation.project_id == project_id,
            WorldRelation.profile_version == profile.version,
        ]
        rel_query = db.query(WorldRelation).filter(*rel_filters)
        rel_total = db.query(func.count(WorldRelation.id)).filter(*rel_filters).scalar() or 0
        rels = (
            rel_query.order_by(WorldRelation.relation_id.asc(), WorldRelation.id.asc())
            .offset(relation_offset)
            .limit(relation_limit)
            .all()
        )
        pagination["relations"] = _page_meta(rel_total, relation_offset, relation_limit)
        relations = [
            {
                "id": r.id,
                "source_ref": r.source_entity_ref,
                "target_ref": r.target_entity_ref,
                "relation_type": r.relation_type,
            }
            for r in rels
        ]

    rules = []
    if profile:
        rule_filters = [
            WorldRule.project_id == project_id,
            WorldRule.profile_version == profile.version,
        ]
        rule_query = db.query(WorldRule).filter(*rule_filters)
        rule_total = db.query(func.count(WorldRule.id)).filter(*rule_filters).scalar() or 0
        rule_rows = (
            rule_query.order_by(WorldRule.rule_id.asc(), WorldRule.id.asc())
            .offset(rule_offset)
            .limit(rule_limit)
            .all()
        )
        pagination["rules"] = _page_meta(rule_total, rule_offset, rule_limit)
        rules = [{"id": r.id, "rule_id": r.rule_id, "description": r.statement} for r in rule_rows]

    world_rules_from_setup = []
    if not rules and setup and setup.world_building:
        wb = setup.world_building
        if isinstance(wb, dict) and wb.get("rules"):
            world_rules_from_setup = [{"id": "setup-rule-0", "rule_id": "setup-rules", "description": wb["rules"]}]

    return {
        "entities": entities,
        "relations": relations,
        "rules": rules or world_rules_from_setup,
        "setup_summary": {
            "characters": setup.characters if setup else None,
            "world_building": setup.world_building if setup else None,
            "core_concept": setup.core_concept if setup else None,
        } if setup else None,
        "profile_version": profile.version if profile else None,
        "pagination": pagination,
    }


def _page_meta(total: int, offset: int, limit: int) -> dict:
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + limit < total,
    }


@router.get("/ontology/entities")
def get_ontology_entities(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    profile = get_current_profile(db, project_id)
    if profile is None:
        return {}
    result = {}
    for model, key in [
        (WorldCharacter, "characters"),
        (WorldLocation, "locations"),
        (WorldFaction, "factions"),
        (WorldArtifact, "artifacts"),
        (WorldResource, "resources"),
    ]:
        items = (
            db.query(model)
            .filter(
                model.project_id == project_id,
                model.profile_version == profile.version,
            )
            .all()
        )
        result[key] = [
            {
                "id": item.id,
                "canonical_id": item.canonical_id,
                "name": getattr(item, "name", getattr(item, "entity_ref", item.id)),
                "primary_alias": getattr(item, "primary_alias", ""),
                "aliases": getattr(item, "aliases", []),
                "type": world_entity_type(item, key),
                "description": world_entity_description(item),
            }
            for item in items
        ]
    return result


@router.get("/ontology/relations")
def get_ontology_relations(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    from app.api.topologies import get_topology
    return get_topology(project_id, db)


@router.get("/ontology/rules")
def get_ontology_rules(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    profile = get_current_profile(db, project_id)
    if profile is None:
        return []
    rules = (
        db.query(WorldRule)
        .filter(
            WorldRule.project_id == project_id,
            WorldRule.profile_version == profile.version,
        )
        .all()
    )
    return [{"id": r.id, "rule_id": r.rule_id, "description": r.statement, "scope": r.scope} for r in rules]


@router.post("/ontology/generate")
async def generate_ontology(project_id: str, db: Session = Depends(get_db)):
    from app.api.setups import generate_setup
    return await generate_setup(project_id, db)


@router.post("/ontology/import-setup")
def import_ontology_setup(project_id: str, db: Session = Depends(get_db)):
    return import_setup_to_world_model(db=db, project_id=project_id)


@router.get("/ontology/import-setup/preview")
def preview_ontology_setup_import(project_id: str, db: Session = Depends(get_db)):
    return preview_setup_import_to_world_model(db=db, project_id=project_id)


@router.get("/ontology/setup")
def get_ontology_setup(project_id: str, db: Session = Depends(get_db)):
    from app.api.setups import get_setup
    return get_setup(project_id, db)


@router.get("/ontology/character-graph")
def get_ontology_character_graph(project_id: str, db: Session = Depends(get_db)):
    from app.api.topologies import character_graph
    return character_graph(project_id, db)


@router.get("/ontology/topology-timeline")
def get_ontology_topology_timeline(project_id: str, db: Session = Depends(get_db)):
    from app.api.topologies import timeline
    return timeline(project_id, db)

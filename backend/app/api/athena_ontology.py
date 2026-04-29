from fastapi import APIRouter, Depends
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


@router.get("/ontology")
def get_ontology(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    profile = get_current_profile(db, project_id)
    setup = db.query(Setup).filter(Setup.project_id == project_id).first()

    entities = {}
    if profile:
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
            entities[key] = [
                {
                    "id": item.id,
                    "name": getattr(item, "name", getattr(item, "entity_ref", item.id)),
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
        rels = (
            db.query(WorldRelation)
            .filter(
                WorldRelation.project_id == project_id,
                WorldRelation.profile_version == profile.version,
            )
            .all()
        )
        relations = [
            {"id": r.id, "source_ref": r.source_ref, "target_ref": r.target_ref, "relation_type": r.relation_type}
            for r in rels
        ]

    rules = []
    if profile:
        rule_rows = (
            db.query(WorldRule)
            .filter(
                WorldRule.project_id == project_id,
                WorldRule.profile_version == profile.version,
            )
            .all()
        )
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
                "name": getattr(item, "name", getattr(item, "entity_ref", item.id)),
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

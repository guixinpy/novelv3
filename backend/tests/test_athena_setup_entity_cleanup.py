from app.core.athena_setup_entity_cleanup import cleanup_phrase_like_setup_entities
from app.core.world_contracts import AUTHORITATIVE_STRUCTURED
from app.models import (
    GenreProfile,
    Project,
    ProjectProfileVersion,
    Setup,
    WorldEvent,
    WorldFactClaim,
    WorldFaction,
    WorldLocation,
    WorldRelation,
)


def test_cleanup_phrase_like_setup_entities_renames_merges_and_rewrites_refs(db_session):
    project = Project(name="Athena Cleanup")
    genre_profile = GenreProfile(
        canonical_id="cleanup-profile",
        display_name="清理测试",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()
    profile = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    setup = Setup(
        project_id=project.id,
        world_building={
            "background": "故事发生在沿海城市‘澜城’，其灯塔区近期发生集体失忆事件。",
            "society": "政府设立记忆管理局。",
        },
        core_concept={},
        status="completed",
    )
    db_session.add_all([profile, setup])
    db_session.commit()
    db_session.add_all(
        [
            WorldLocation(
                project_id=project.id,
                profile_version=profile.version,
                location_id="loc.灯塔",
                canonical_id="loc.灯塔",
                primary_alias="灯塔",
                name="灯塔",
                aliases=[],
                location_type="landmark",
                contract_version=profile.contract_version,
            ),
            WorldLocation(
                project_id=project.id,
                profile_version=profile.version,
                location_id="loc.一座灯塔",
                canonical_id="loc.一座灯塔",
                primary_alias="一座灯塔",
                name="一座灯塔",
                aliases=[],
                location_type="landmark",
                contract_version=profile.contract_version,
            ),
            WorldLocation(
                project_id=project.id,
                profile_version=profile.version,
                location_id="loc.沿海城市",
                canonical_id="loc.沿海城市",
                primary_alias="沿海城市",
                name="沿海城市",
                aliases=[],
                location_type="city",
                contract_version=profile.contract_version,
            ),
            WorldFaction(
                project_id=project.id,
                profile_version=profile.version,
                faction_id="faction.政府设立记忆管理局",
                canonical_id="faction.政府设立记忆管理局",
                primary_alias="政府设立记忆管理局",
                name="政府设立记忆管理局",
                aliases=[],
                faction_type="agency",
                contract_version=profile.contract_version,
            ),
            WorldFactClaim(
                project_id=project.id,
                project_profile_version_id=profile.id,
                profile_version=profile.version,
                claim_id="claim-1",
                subject_ref="loc.一座灯塔",
                predicate="located_in",
                object_ref_or_value={"place": "loc.沿海城市"},
                claim_layer="truth",
                claim_status="confirmed",
                authority_type=AUTHORITATIVE_STRUCTURED,
                confidence=1.0,
                contract_version=profile.contract_version,
            ),
            WorldEvent(
                project_id=project.id,
                project_profile_version_id=profile.id,
                profile_version=profile.version,
                event_id="event-1",
                timeline_anchor_id="chapter:1",
                chapter_index=1,
                intra_chapter_seq=1,
                event_type="presence_shifted",
                participant_refs=[],
                location_refs=["loc.一座灯塔"],
                primitive_payload={"entity_ref": "faction.政府设立记忆管理局"},
                state_diffs=[],
                truth_layer="truth",
                disclosure_layer="reader",
                contract_version=profile.contract_version,
            ),
            WorldRelation(
                project_id=project.id,
                profile_version=profile.version,
                relation_id="relation-1",
                source_entity_ref="faction.政府设立记忆管理局",
                target_entity_ref="loc.一座灯塔",
                relation_type="guards",
                directionality="directed",
                status="active",
                visibility_layer="public",
                contract_version=profile.contract_version,
            ),
        ]
    )
    db_session.commit()

    dry_run = cleanup_phrase_like_setup_entities(db_session, project.id, apply=False)
    assert len(dry_run["renames"]) == 3

    result = cleanup_phrase_like_setup_entities(db_session, project.id, apply=True)
    db_session.commit()

    assert {item["new_ref"] for item in result["renames"]} == {"loc.灯塔", "loc.澜城", "faction.记忆管理局"}
    locations = {row.canonical_id: row for row in db_session.query(WorldLocation).filter_by(project_id=project.id)}
    factions = {row.canonical_id: row for row in db_session.query(WorldFaction).filter_by(project_id=project.id)}
    assert set(locations) == {"loc.灯塔", "loc.澜城"}
    assert "一座灯塔" in locations["loc.灯塔"].aliases
    assert set(factions) == {"faction.记忆管理局"}

    claim = db_session.query(WorldFactClaim).filter_by(project_id=project.id).one()
    assert claim.subject_ref == "loc.灯塔"
    assert claim.object_ref_or_value == {"place": "loc.澜城"}
    event = db_session.query(WorldEvent).filter_by(project_id=project.id).one()
    assert event.location_refs == ["loc.灯塔"]
    assert event.primitive_payload == {"entity_ref": "faction.记忆管理局"}
    relation = db_session.query(WorldRelation).filter_by(project_id=project.id).one()
    assert relation.source_entity_ref == "faction.记忆管理局"
    assert relation.target_entity_ref == "loc.灯塔"

import sqlite3
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError, IntegrityError, StatementError

from app.core.world_contracts import (
    ANNOTATION,
    AUTHORITATIVE_STRUCTURED,
    DERIVED,
    EXPLANATION_CONTRACT_VERSION_FIELD,
    OPAQUE_BLOB,
    PROFILE_VERSION_FIELD,
    PROJECT_PROFILE_VERSION_REF_FIELD,
)
from app.models import (
    GenreProfile,
    Project,
    ProjectProfileVersion,
    WorldArtifact,
    WorldCharacter,
    WorldEvent,
    WorldEvidence,
    WorldFactClaim,
    WorldFaction,
    WorldLocation,
    WorldRelation,
    WorldResource,
    WorldRule,
    WorldTimelineAnchor,
)
from app.schemas.world_events import WorldFactClaimCreate
from app.schemas.world_profiles import ProjectProfileVersionAppend


def test_genre_profile_model_can_be_created(db_session):
    profile = GenreProfile(
        canonical_id="generic",
        display_name="通用",
        contract_version="world.contract.v1",
        field_authority={"entities": AUTHORITATIVE_STRUCTURED},
        schema_payload={"required_entities": ["character"]},
    )

    db_session.add(profile)
    db_session.commit()

    saved = db_session.query(GenreProfile).filter(GenreProfile.canonical_id == "generic").one()
    assert saved.display_name == "通用"
    assert saved.field_authority["entities"] == AUTHORITATIVE_STRUCTURED


def test_core_world_entities_use_structured_minimum_fields(db_session):
    project = Project(name="Structured Entities")
    genre_profile = GenreProfile(
        canonical_id="generic-structured-entities",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    profile_version = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add(profile_version)
    db_session.commit()

    character = WorldCharacter(
        project_id=project.id,
        profile_version=1,
        character_id="char.hero",
        canonical_id="char.hero",
        primary_alias="阿临",
        name="林昼",
        aliases=["阿临"],
        role_type="protagonist",
        identity_anchor="orphan-mechanic",
        origin_background="下层轨道城长大",
        core_traits=["冷静", "偏执"],
        core_drives=["活下去", "找真相"],
        core_fears=["失控"],
        taboos_or_bottom_lines=["不出卖同伴"],
        base_capabilities=["机械维修"],
        capability_ceiling_or_constraints=["不能直接驾驶军舰"],
        default_affiliations=["faction.scrapyard"],
        public_persona="沉默修理工",
        hidden_truths=["见过事故真相"],
        notes="角色锚点",
        contract_version="world.contract.v1",
    )
    location = WorldLocation(
        project_id=project.id,
        profile_version=1,
        location_id="loc.dock-7",
        canonical_id="loc.dock-7",
        primary_alias="七号码头",
        name="七号码头",
        aliases=["旧港"],
        location_type="dock",
        parent_location_id=None,
        spatial_scope="轨道城外环",
        access_constraints=["夜间封锁"],
        functional_tags=["走私", "维修"],
        hazards=["高压蒸汽"],
        resource_tags=["燃料", "零件"],
        surveillance_or_visibility_level="high",
        notes="关键场景",
        contract_version="world.contract.v1",
    )
    faction = WorldFaction(
        project_id=project.id,
        profile_version=1,
        faction_id="faction.scrapyard",
        canonical_id="faction.scrapyard",
        primary_alias="废料帮",
        name="废料帮",
        aliases=["码头会"],
        faction_type="guild",
        mission_or_doctrine="先活下来",
        structure_model="cell",
        authority_rules=["老成员投票"],
        membership_rules=["缴纳保护费"],
        taboos=["背叛同伴"],
        resource_domains=["码头回收"],
        territorial_scope="第七码头",
        public_image="杂牌帮派",
        hidden_agenda="控制黑市燃料",
        notes="地方势力",
        contract_version="world.contract.v1",
    )
    artifact = WorldArtifact(
        project_id=project.id,
        profile_version=1,
        artifact_id="artifact.black-box",
        canonical_id="artifact.black-box",
        primary_alias="黑匣",
        name="黑匣子",
        aliases=["事故盒"],
        artifact_type="data_device",
        origin="失事舰船",
        function_summary="记录航行数据",
        activation_conditions=["接入专用终端"],
        usage_constraints=["一次性读取"],
        risk_or_side_effects=["触发追踪"],
        identity_or_auth_requirements=["舰队权限"],
        uniqueness="unique",
        traceability="serial-bound",
        notes="关键证物",
        contract_version="world.contract.v1",
    )
    rule = WorldRule(
        project_id=project.id,
        profile_version=1,
        rule_id="rule.airlock",
        canonical_id="rule.airlock",
        primary_alias="气闸规程",
        name="气闸规程",
        rule_type="safety",
        scope="dock",
        statement="进入气闸前必须双重校验",
        preconditions=["进入高压舱段"],
        effects=["开启检查流程"],
        constraints=["无授权禁止手动跳过"],
        exceptions=["舰长紧急令"],
        violation_cost="可能减压致死",
        enforcement_agent="dock.control",
        repair_or_override_path="控制室双人解锁",
        notes="硬规则",
        contract_version="world.contract.v1",
    )
    resource = WorldResource(
        project_id=project.id,
        profile_version=1,
        resource_id="resource.fuel-cell",
        canonical_id="resource.fuel-cell",
        primary_alias="燃料芯",
        name="燃料芯",
        resource_type="energy",
        unit_or_scale="cell",
        holder_type="faction",
        acquisition_paths=["黑市采购"],
        consumption_paths=["飞船启动"],
        scarcity_level="high",
        renewal_model="limited_supply",
        transferability="controlled",
        visibility="restricted",
        critical_threshold_effect="低于3枚时飞船停摆",
        notes="核心资源",
        contract_version="world.contract.v1",
    )

    db_session.add_all([character, location, faction, artifact, rule, resource])
    db_session.commit()

    saved_character = db_session.query(WorldCharacter).filter_by(canonical_id="char.hero").one()
    saved_location = db_session.query(WorldLocation).filter_by(canonical_id="loc.dock-7").one()
    saved_faction = db_session.query(WorldFaction).filter_by(canonical_id="faction.scrapyard").one()
    saved_artifact = db_session.query(WorldArtifact).filter_by(canonical_id="artifact.black-box").one()
    saved_rule = db_session.query(WorldRule).filter_by(canonical_id="rule.airlock").one()
    saved_resource = db_session.query(WorldResource).filter_by(canonical_id="resource.fuel-cell").one()

    assert saved_character.core_drives == ["活下去", "找真相"]
    assert saved_character.character_id == "char.hero"
    assert saved_location.functional_tags == ["走私", "维修"]
    assert saved_location.location_id == "loc.dock-7"
    assert saved_faction.hidden_agenda == "控制黑市燃料"
    assert saved_faction.faction_id == "faction.scrapyard"
    assert saved_artifact.identity_or_auth_requirements == ["舰队权限"]
    assert saved_artifact.artifact_id == "artifact.black-box"
    assert saved_rule.enforcement_agent == "dock.control"
    assert saved_rule.rule_id == "rule.airlock"
    assert saved_resource.critical_threshold_effect == "低于3枚时飞船停摆"
    assert saved_resource.resource_id == "resource.fuel-cell"


def test_world_relation_and_timeline_anchor_use_structured_fields(db_session):
    project = Project(name="Structured Graph")
    genre_profile = GenreProfile(
        canonical_id="generic-structured-graph",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    profile_version = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add(profile_version)
    db_session.commit()

    relation = WorldRelation(
        project_id=project.id,
        profile_version=1,
        relation_id="relation.hero-member-of-scrapyard",
        source_entity_ref="char.hero",
        target_entity_ref="faction.scrapyard",
        relation_type="member_of",
        directionality="directed",
        status="active",
        visibility_layer="public",
        strength_or_weight="high",
        start_anchor_id="anchor.ch1.s1",
        end_anchor_id=None,
        evidence_refs=["evidence.oath"],
        notes="加入帮派",
        contract_version="world.contract.v1",
    )
    anchor = WorldTimelineAnchor(
        project_id=project.id,
        profile_version=1,
        anchor_id="anchor.ch1.s1",
        chapter_index=1,
        intra_chapter_seq=1,
        world_time_label="第一章开场",
        normalized_tick_or_range="0001.0001",
        precision="scene",
        relative_to_anchor_ref=None,
        ordering_key="0001-0001",
        notes="故事起点",
        contract_version="world.contract.v1",
    )

    db_session.add_all([relation, anchor])
    db_session.commit()

    saved_relation = db_session.query(WorldRelation).filter_by(relation_id="relation.hero-member-of-scrapyard").one()
    saved_anchor = db_session.query(WorldTimelineAnchor).filter_by(anchor_id="anchor.ch1.s1").one()

    assert saved_relation.source_entity_ref == "char.hero"
    assert saved_relation.evidence_refs == ["evidence.oath"]
    assert saved_anchor.intra_chapter_seq == 1
    assert saved_anchor.normalized_tick_or_range == "0001.0001"


def test_sqlite_foreign_keys_are_enabled(db_session):
    pragma_value = db_session.execute(text("PRAGMA foreign_keys")).scalar_one()
    assert pragma_value == 1


def test_project_profile_version_is_append_only(db_session):
    project = Project(name="Append Only")
    genre_profile = GenreProfile(
        canonical_id="sci-fi",
        display_name="科幻",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    version_one = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={"era": "pre-warp"},
    )
    version_two = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=2,
        contract_version="world.contract.v1",
        profile_payload={"era": "warp"},
    )
    db_session.add_all([version_one, version_two])
    db_session.commit()

    saved_versions = (
        db_session.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project.id)
        .order_by(ProjectProfileVersion.version.asc())
        .all()
    )
    assert [item.version for item in saved_versions] == [1, 2]

    version_one.profile_payload = {"era": "retcon"}
    with pytest.raises(ValueError, match="append-only"):
        db_session.commit()
    db_session.rollback()


def test_project_profile_version_insert_rejects_contract_version_mismatch_with_genre_profile(db_session):
    project = Project(name="Contract Locked On Insert")
    genre_profile = GenreProfile(
        canonical_id="generic-contract-locked",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    version = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v2",
        profile_payload={"tone": "bad"},
    )
    db_session.add(version)

    with pytest.raises(ValueError, match="genre_profile.contract_version"):
        db_session.commit()
    db_session.rollback()

    assert db_session.query(ProjectProfileVersion).count() == 0


def test_project_profile_version_rejects_raw_sql_insert_contract_version_mismatch_at_db_level(db_session):
    project = Project(name="SQL Insert Contract Locked")
    genre_profile = GenreProfile(
        canonical_id="generic-insert-db-trigger",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    with pytest.raises(DatabaseError, match="contract_version"):
        db_session.execute(
            text(
                "INSERT INTO project_profile_versions "
                "(id, project_id, genre_profile_id, version, contract_version, profile_payload, created_at) "
                "VALUES (:id, :project_id, :genre_profile_id, :version, :contract_version, :profile_payload, CURRENT_TIMESTAMP)"
            ),
            {
                "id": "ppv-sql-bad-contract",
                "project_id": project.id,
                "genre_profile_id": genre_profile.id,
                "version": 1,
                "contract_version": "world.contract.v2",
                "profile_payload": "{}",
            },
        )
        db_session.commit()
    db_session.rollback()

    assert db_session.query(ProjectProfileVersion).count() == 0


def test_project_profile_version_rejects_raw_sql_update_at_db_level(db_session):
    project = Project(name="DB Protected")
    genre_profile = GenreProfile(
        canonical_id="generic-db-trigger",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    version = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={"tone": "strict"},
    )
    db_session.add(version)
    db_session.commit()

    with pytest.raises(DatabaseError, match="append-only"):
        db_session.execute(
            text(
                "UPDATE project_profile_versions "
                "SET contract_version = :next_version "
                "WHERE id = :version_id"
            ),
            {"next_version": "world.contract.v2", "version_id": version.id},
        )
        db_session.commit()
    db_session.rollback()

    saved = db_session.query(ProjectProfileVersion).filter_by(id=version.id).one()
    assert saved.contract_version == "world.contract.v1"


def test_project_profile_version_rejects_delete_via_orm(db_session):
    project = Project(name="ORM Delete Protected")
    genre_profile = GenreProfile(
        canonical_id="generic-delete-orm",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    version = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add(version)
    db_session.commit()

    db_session.delete(version)
    with pytest.raises(ValueError, match="append-only"):
        db_session.commit()
    db_session.rollback()


def test_project_profile_version_rejects_raw_sql_delete_at_db_level(db_session):
    project = Project(name="SQL Delete Protected")
    genre_profile = GenreProfile(
        canonical_id="generic-delete-sql",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    version = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add(version)
    db_session.commit()

    with pytest.raises(DatabaseError, match="append-only"):
        db_session.execute(
            text("DELETE FROM project_profile_versions WHERE id = :version_id"),
            {"version_id": version.id},
        )
        db_session.commit()
    db_session.rollback()

    saved = db_session.query(ProjectProfileVersion).filter_by(id=version.id).one()
    assert saved.id == version.id


def test_core_entities_reject_nonexistent_profile_version(db_session):
    project = Project(name="Missing Snapshot")
    db_session.add(project)
    db_session.commit()

    character = WorldCharacter(
        project_id=project.id,
        profile_version=99,
        character_id="char.missing",
        canonical_id="char.missing",
        name="失配角色",
        role_type="supporting",
        identity_anchor="nobody",
        contract_version="world.contract.v1",
    )
    db_session.add(character)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


@pytest.mark.parametrize("invalid_version", [0, -1])
def test_project_profile_version_rejects_nonpositive_version(db_session, invalid_version):
    project = Project(name=f"Invalid Version {invalid_version}")
    genre_profile = GenreProfile(
        canonical_id=f"generic-invalid-version-{invalid_version}",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    version = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=invalid_version,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add(version)

    with pytest.raises((IntegrityError, StatementError)):
        db_session.commit()
    db_session.rollback()


def test_core_entities_reject_nonpositive_profile_version_binding(db_session):
    project = Project(name="Zero Bound Entity")
    db_session.add(project)
    db_session.commit()

    character = WorldCharacter(
        project_id=project.id,
        profile_version=0,
        character_id="char.zero",
        canonical_id="char.zero",
        name="零号角色",
        role_type="supporting",
        identity_anchor="nobody",
        contract_version="world.contract.v1",
    )
    db_session.add(character)

    with pytest.raises((IntegrityError, StatementError)):
        db_session.commit()
    db_session.rollback()


def test_project_profile_version_schema_is_append_semantic():
    payload = ProjectProfileVersionAppend(
        genre_profile_id="genre-1",
        version=3,
        contract_version="world.contract.v1",
        profile_payload={"tone": "grim"},
    )

    assert payload.version == 3
    assert payload.profile_payload["tone"] == "grim"


def test_same_project_cannot_repeat_profile_version(db_session):
    project = Project(name="Duplicate Version")
    genre_profile = GenreProfile(
        canonical_id="mystery",
        display_name="悬疑",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    first = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={"tone": "cold"},
    )
    duplicate = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={"tone": "warmer"},
    )
    db_session.add_all([first, duplicate])

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_world_event_fact_claim_and_evidence_use_structured_fields(db_session):
    project = Project(name="Version Binding")
    genre_profile = GenreProfile(
        canonical_id="generic",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    profile_version = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=4,
        contract_version="world.contract.v1",
        profile_payload={"stakes": "high"},
    )
    db_session.add(profile_version)
    db_session.commit()

    world_event = WorldEvent(
        project_id=project.id,
        profile_version=4,
        project_profile_version_id=profile_version.id,
        event_id="event.crash",
        idempotency_key="event-crash-idem",
        chapter_index=12,
        intra_chapter_seq=3,
        event_type="event_occurred",
        timeline_anchor_id="anchor.ch12.s3",
        participant_refs=["char.hero", "artifact.black-box"],
        location_refs=["loc.dock-7"],
        precondition_event_refs=["event.departure"],
        caused_event_refs=["event.lockdown"],
        primitive_payload={"event_ref": "incident.crash", "location_ref": "loc.dock-7"},
        state_diffs=[{"field": "status", "before": "stable", "after": "destroyed"}],
        truth_layer="canonical_truth",
        disclosure_layer="reader_visible",
        evidence_refs=["evidence.black-box"],
        contract_version_refs=["world.contract.v1"],
        notes="飞船坠毁",
        contract_version="world.contract.v1",
    )
    fact_claim = WorldFactClaim(
        project_id=project.id,
        profile_version=4,
        project_profile_version_id=profile_version.id,
        claim_id="claim.ship-destroyed",
        chapter_index=12,
        intra_chapter_seq=3,
        subject_ref="artifact.black-box",
        predicate="status",
        object_ref_or_value="destroyed",
        claim_layer="truth",
        claim_status="confirmed",
        valid_from_anchor_id="anchor.ch12.s3",
        valid_to_anchor_id=None,
        source_event_ref="event.crash",
        evidence_refs=["evidence.black-box"],
        authority_type=AUTHORITATIVE_STRUCTURED,
        confidence=1.0,
        notes="残骸确认",
        contract_version="world.contract.v1",
    )
    evidence = WorldEvidence(
        project_id=project.id,
        profile_version=4,
        project_profile_version_id=profile_version.id,
        evidence_id="evidence.black-box",
        evidence_type="device_log",
        source_scope="chapter",
        content_excerpt_or_summary="黑匣子记录到爆炸前失压",
        holder_ref="char.hero",
        authenticity_status="verified",
        reliability_level="high",
        disclosure_layer="reader_visible",
        related_claim_refs=["claim.ship-destroyed"],
        related_event_refs=["event.crash"],
        timeline_anchor_id="anchor.ch12.s3",
        notes="直接证据",
        contract_version="world.contract.v1",
    )
    db_session.add_all([world_event, fact_claim, evidence])
    db_session.commit()

    saved_event = db_session.query(WorldEvent).filter(WorldEvent.id == world_event.id).one()
    saved_claim = db_session.query(WorldFactClaim).filter(WorldFactClaim.id == fact_claim.id).one()
    saved_evidence = db_session.query(WorldEvidence).filter(WorldEvidence.id == evidence.id).one()
    assert saved_event.profile_version == 4
    assert saved_event.project_profile_version_id == profile_version.id
    assert saved_event.participant_refs == ["char.hero", "artifact.black-box"]
    assert saved_event.contract_version_refs == ["world.contract.v1"]
    assert saved_claim.profile_version == 4
    assert saved_claim.project_profile_version_id == profile_version.id
    assert saved_claim.subject_ref == "artifact.black-box"
    assert saved_claim.authority_type == AUTHORITATIVE_STRUCTURED
    assert saved_evidence.evidence_type == "device_log"
    assert saved_evidence.related_event_refs == ["event.crash"]


def test_world_records_reject_cross_project_profile_version_binding(db_session):
    project_a = Project(name="Project A")
    project_b = Project(name="Project B")
    genre_profile = GenreProfile(
        canonical_id="generic-cross-project",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project_a, project_b, genre_profile])
    db_session.commit()

    version_a = ProjectProfileVersion(
        project_id=project_a.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    version_b = ProjectProfileVersion(
        project_id=project_b.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add_all([version_a, version_b])
    db_session.commit()

    event = WorldEvent(
        project_id=project_b.id,
        profile_version=1,
        project_profile_version_id=version_a.id,
        event_id="event.cross-project",
        idempotency_key="cross-project-idem",
        timeline_anchor_id="anchor.b.1",
        chapter_index=1,
        intra_chapter_seq=1,
        event_type="event_occurred",
        primitive_payload={"event_ref": "incident.cross-project"},
        truth_layer="canonical_truth",
        disclosure_layer="reader_visible",
        contract_version_refs=["world.contract.v1"],
        contract_version="world.contract.v1",
    )
    db_session.add(event)

    with pytest.raises((IntegrityError, ValueError, StatementError)):
        db_session.commit()
    db_session.rollback()


def test_world_records_reject_dangling_project_profile_version_id(db_session):
    project = Project(name="Dangling FK")
    db_session.add(project)
    db_session.commit()

    evidence = WorldEvidence(
        project_id=project.id,
        profile_version=None,
        project_profile_version_id="missing-ppv",
        evidence_id="evidence.dangling",
        evidence_type="witness_note",
        source_scope="chapter",
        disclosure_layer="reader_visible",
        contract_version="world.contract.v1",
    )
    db_session.add(evidence)

    with pytest.raises((IntegrityError, ValueError, StatementError)):
        db_session.commit()
    db_session.rollback()


def test_world_records_reject_mismatched_profile_version_reference(db_session):
    project = Project(name="Mismatched Version")
    genre_profile = GenreProfile(
        canonical_id="generic-mismatch",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    version_one = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    version_two = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=2,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add_all([version_one, version_two])
    db_session.commit()

    claim = WorldFactClaim(
        project_id=project.id,
        profile_version=1,
        project_profile_version_id=version_two.id,
        claim_id="claim.mismatch",
        subject_ref="char.hero",
        predicate="status",
        object_ref_or_value="alive",
        claim_layer="truth",
        claim_status="confirmed",
        authority_type=AUTHORITATIVE_STRUCTURED,
        confidence=0.8,
        contract_version="world.contract.v1",
    )
    db_session.add(claim)

    with pytest.raises((IntegrityError, ValueError, StatementError)):
        db_session.commit()
    db_session.rollback()


def test_world_fact_claim_rejects_invalid_authority_and_confidence(db_session):
    project = Project(name="Invalid Authority")
    genre_profile = GenreProfile(
        canonical_id="generic-invalid-authority",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    version = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add(version)
    db_session.commit()

    invalid_claim = WorldFactClaim(
        project_id=project.id,
        profile_version=1,
        project_profile_version_id=version.id,
        claim_id="claim.invalid-authority",
        subject_ref="char.hero",
        predicate="status",
        object_ref_or_value="alive",
        claim_layer="truth",
        claim_status="confirmed",
        authority_type="freeform_truthiness",
        confidence=1.2,
        contract_version="world.contract.v1",
    )
    db_session.add(invalid_claim)

    with pytest.raises((IntegrityError, ValueError, StatementError)):
        db_session.commit()
    db_session.rollback()


def test_world_fact_claim_rejects_null_confidence(db_session):
    project = Project(name="Null Confidence")
    genre_profile = GenreProfile(
        canonical_id="generic-null-confidence",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    version = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add(version)
    db_session.commit()

    claim = WorldFactClaim(
        project_id=project.id,
        profile_version=1,
        project_profile_version_id=version.id,
        claim_id="claim.null-confidence",
        subject_ref="char.hero",
        predicate="status",
        object_ref_or_value="alive",
        claim_layer="truth",
        claim_status="confirmed",
        authority_type=AUTHORITATIVE_STRUCTURED,
        confidence=None,
        contract_version="world.contract.v1",
    )
    db_session.add(claim)

    with pytest.raises((IntegrityError, StatementError)):
        db_session.commit()
    db_session.rollback()


def test_world_fact_claim_schema_rejects_invalid_authority_and_confidence():
    with pytest.raises(ValueError):
        WorldFactClaimCreate(
            project_id="project-1",
            profile_version=1,
            claim_id="claim.schema-invalid",
            subject_ref="char.hero",
            predicate="status",
            object_ref_or_value="alive",
            claim_layer="truth",
            claim_status="confirmed",
            authority_type="not_allowed",
            confidence=2.0,
            contract_version="world.contract.v1",
        )


def test_migration_upgrade_enforces_trigger_and_foreign_keys(tmp_path):
    backend_dir = Path(__file__).resolve().parents[1]
    db_path = tmp_path / "migration-check.db"
    ini_path = tmp_path / "alembic.ini"
    base_ini = (backend_dir / "alembic.ini").read_text()
    ini_path.write_text(
        base_ini.replace(
            "sqlalchemy.url = sqlite:///../data/mozhou.db",
            f"sqlalchemy.url = sqlite:///{db_path}",
        )
    )

    result = subprocess.run(
        [str(backend_dir / ".venv/bin/alembic"), "-c", str(ini_path), "upgrade", "head"],
        cwd=backend_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys=ON")

        trigger = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='trigger' "
            "AND name='trg_project_profile_versions_append_only'"
        ).fetchone()
        assert trigger is not None
        assert "append-only" in trigger[0]

        contract_insert_trigger = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='trigger' "
            "AND name='trg_project_profile_versions_contract_version_insert'"
        ).fetchone()
        assert contract_insert_trigger is not None
        assert "contract_version" in contract_insert_trigger[0]

        conn.execute(
            "INSERT INTO projects (id, name, description, genre, target_word_count, current_word_count, "
            "status, current_phase, ai_model, language, style, complexity, style_config, created_at, updated_at) "
            "VALUES (?, ?, '', '', 0, 0, 'draft', 'setup', 'deepseek-chat', 'zh-CN', '', 3, '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            ("project-1", "Project 1"),
        )
        conn.execute(
            "INSERT INTO genre_profiles (id, canonical_id, primary_alias, display_name, contract_version, field_authority, "
            "schema_payload, module_payload, event_types, checker_config, created_at, updated_at) "
            "VALUES (?, ?, '', ?, ?, '{}', '{}', '{}', '[]', '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            ("genre-1", "generic-migration", "通用", "world.contract.v1"),
        )
        conn.execute(
            "INSERT INTO project_profile_versions (id, project_id, genre_profile_id, version, contract_version, profile_payload, created_at) "
            "VALUES (?, ?, ?, ?, ?, '{}', CURRENT_TIMESTAMP)",
            ("ppv-1", "project-1", "genre-1", 1, "world.contract.v1"),
        )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO project_profile_versions (id, project_id, genre_profile_id, version, contract_version, profile_payload, created_at) "
                "VALUES (?, ?, ?, ?, ?, '{}', CURRENT_TIMESTAMP)",
                ("ppv-bad-contract", "project-1", "genre-1", 99, "world.contract.v2"),
            )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE project_profile_versions SET contract_version = ? WHERE id = ?",
                ("world.contract.v2", "ppv-1"),
            )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "DELETE FROM project_profile_versions WHERE id = ?",
                ("ppv-1",),
            )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO world_characters (id, project_id, profile_version, character_id, canonical_id, primary_alias, name, aliases, "
                "role_type, identity_anchor, origin_background, core_traits, core_drives, core_fears, taboos_or_bottom_lines, "
                "base_capabilities, capability_ceiling_or_constraints, default_affiliations, public_persona, hidden_truths, notes, contract_version, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, '', ?, '[]', ?, ?, '', '[]', '[]', '[]', '[]', '[]', '[]', '[]', '', '[]', '', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                ("char-1", "project-1", 99, "char-1", "char-1", "Ghost", "supporting", "nobody", "world.contract.v1"),
            )

        conn.execute(
            "INSERT INTO project_profile_versions (id, project_id, genre_profile_id, version, contract_version, profile_payload, created_at) "
            "VALUES (?, ?, ?, ?, ?, '{}', CURRENT_TIMESTAMP)",
            ("ppv-2", "project-1", "genre-1", 2, "world.contract.v1"),
        )

        conn.execute(
            "INSERT INTO world_proposal_bundles (id, project_id, project_profile_version_id, profile_version, parent_bundle_id, "
            "bundle_status, title, summary, created_by, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, NULL, ?, ?, '', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            ("bundle-1", "project-1", "ppv-1", 1, "pending", "bundle", "writer.alpha"),
        )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO world_proposal_items (id, project_id, project_profile_version_id, profile_version, bundle_id, parent_item_id, "
                "item_status, claim_id, chapter_index, intra_chapter_seq, subject_ref, predicate, object_ref_or_value, claim_layer, "
                "valid_from_anchor_id, valid_to_anchor_id, source_event_ref, evidence_refs, authority_type, confidence, notes, "
                "contract_version, created_by, approved_claim_id, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, NULL, ?, ?, NULL, ?, ?, ?, ?, ?, NULL, NULL, NULL, '[]', ?, ?, '', ?, ?, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (
                    "proposal-item-mismatch",
                    "project-1",
                    "ppv-2",
                    2,
                    "bundle-1",
                    "pending",
                    "claim.proposal.mismatch",
                    0,
                    "char.hero",
                    "rank",
                    '"captain"',
                    "truth",
                    "authoritative_structured",
                    0.95,
                    "world.contract.v1",
                    "writer.alpha",
                ),
            )

        trigger_names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' "
                "AND name IN ("
                "'trg_world_events_profile_binding_insert', "
                "'trg_world_fact_claims_profile_binding_insert', "
                "'trg_world_evidence_profile_binding_insert'"
                ")"
            ).fetchall()
        }
        assert trigger_names == {
            "trg_world_events_profile_binding_insert",
            "trg_world_fact_claims_profile_binding_insert",
            "trg_world_evidence_profile_binding_insert",
        }

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO world_events (id, project_id, project_profile_version_id, profile_version, event_id, idempotency_key, timeline_anchor_id, "
                "chapter_index, intra_chapter_seq, event_type, participant_refs, location_refs, precondition_event_refs, caused_event_refs, "
                "primitive_payload, state_diffs, truth_layer, disclosure_layer, evidence_refs, contract_version_refs, supersedes_event_ref, notes, contract_version, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', '[]', '[]', '[]', '{}', '[]', ?, ?, '[]', '[]', NULL, '', ?, CURRENT_TIMESTAMP)",
                (
                    "event-1",
                    "project-1",
                    "ppv-2",
                    1,
                    "event.mismatch",
                    "idem-mismatch",
                    "anchor-1",
                    1,
                    1,
                    "event_occurred",
                    "canonical_truth",
                    "reader_visible",
                    "world.contract.v1",
                ),
            )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO world_fact_claims (id, project_id, project_profile_version_id, profile_version, claim_id, chapter_index, "
                "intra_chapter_seq, subject_ref, predicate, object_ref_or_value, claim_layer, claim_status, valid_from_anchor_id, valid_to_anchor_id, "
                "source_event_ref, evidence_refs, authority_type, confidence, notes, contract_version, created_at) "
                "VALUES (?, ?, ?, ?, ?, NULL, 0, ?, ?, ?, ?, ?, NULL, NULL, NULL, '[]', ?, ?, '', ?, CURRENT_TIMESTAMP)",
                (
                    "claim-1",
                    "project-1",
                    "ppv-2",
                    1,
                    "claim.mismatch",
                    "char.hero",
                    "status",
                    "\"alive\"",
                    "truth",
                    "confirmed",
                    AUTHORITATIVE_STRUCTURED,
                    0.9,
                    "world.contract.v1",
                ),
            )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO world_evidence (id, project_id, project_profile_version_id, profile_version, evidence_id, chapter_index, "
                "intra_chapter_seq, evidence_type, source_scope, content_excerpt_or_summary, holder_ref, authenticity_status, "
                "reliability_level, disclosure_layer, related_claim_refs, related_event_refs, timeline_anchor_id, notes, contract_version, created_at) "
                "VALUES (?, ?, ?, ?, ?, NULL, 0, ?, ?, '', '', '', '', ?, '[]', '[]', NULL, '', ?, CURRENT_TIMESTAMP)",
                (
                    "evidence-1",
                    "project-1",
                    "ppv-2",
                    1,
                    "evidence.mismatch",
                    "witness_note",
                    "chapter",
                    "reader_visible",
                    "world.contract.v1",
                ),
            )

        conn.execute(
            "INSERT INTO world_events (id, project_id, project_profile_version_id, profile_version, event_id, idempotency_key, timeline_anchor_id, "
            "chapter_index, intra_chapter_seq, event_type, participant_refs, location_refs, precondition_event_refs, caused_event_refs, "
            "primitive_payload, state_diffs, truth_layer, disclosure_layer, evidence_refs, contract_version_refs, supersedes_event_ref, notes, contract_version, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', '[]', '[]', '[]', '{}', '[]', ?, ?, '[]', '[]', NULL, '', ?, CURRENT_TIMESTAMP)",
            (
                "event-2",
                "project-1",
                "ppv-2",
                2,
                "event.idempotent.one",
                "idem-duplicate",
                "anchor-2",
                2,
                1,
                "event_occurred",
                "canonical_truth",
                "reader_visible",
                "world.contract.v1",
            ),
        )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO world_events (id, project_id, project_profile_version_id, profile_version, event_id, idempotency_key, timeline_anchor_id, "
                "chapter_index, intra_chapter_seq, event_type, participant_refs, location_refs, precondition_event_refs, caused_event_refs, "
                "primitive_payload, state_diffs, truth_layer, disclosure_layer, evidence_refs, contract_version_refs, supersedes_event_ref, notes, contract_version, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', '[]', '[]', '[]', '{}', '[]', ?, ?, '[]', '[]', NULL, '', ?, CURRENT_TIMESTAMP)",
                (
                    "event-3",
                    "project-1",
                    "ppv-2",
                    2,
                    "event.idempotent.two",
                    "idem-duplicate",
                    "anchor-3",
                    2,
                    2,
                    "event_occurred",
                    "canonical_truth",
                    "reader_visible",
                    "world.contract.v1",
                ),
            )
    finally:
        conn.close()


def test_world_contracts_expose_authority_types():
    assert AUTHORITATIVE_STRUCTURED == "authoritative_structured"
    assert DERIVED == "derived"
    assert ANNOTATION == "annotation"
    assert OPAQUE_BLOB == "opaque_blob"


def test_world_contracts_expose_version_field_names():
    assert EXPLANATION_CONTRACT_VERSION_FIELD == "contract_version"
    assert PROFILE_VERSION_FIELD == "profile_version"
    assert PROJECT_PROFILE_VERSION_REF_FIELD == "project_profile_version_id"

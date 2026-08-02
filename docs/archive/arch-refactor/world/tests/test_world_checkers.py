import pytest

from app.core.world_replay import LedgerEvent
from app.models import GenreProfile, Project, ProjectProfileVersion


def _communication_event() -> LedgerEvent:
    return LedgerEvent(
        event_id="evt.signal.send",
        event_type="communication_sent",
        chapter_index=12,
        intra_chapter_seq=3,
        payload={
            "sender_ref": "ship.daedalus",
            "receiver_ref": "base.luna",
            "distance_au": 9.0,
            "channel_speed_au_per_hour": 2.0,
            "declared_delay_hours": 1.0,
        },
        idempotency_key="idem.signal.send",
    )


def test_official_profiles_can_be_loaded(db_session):
    from app.core.world_checker_registry import load_official_genre_profiles

    loaded = load_official_genre_profiles(db_session)

    assert [profile.canonical_id for profile in loaded] == ["generic", "sci_fi", "mystery"]

    generic = loaded[0]
    sci_fi = loaded[1]
    mystery = loaded[2]

    assert generic.display_name == "通用"
    assert "entity_introduced" in generic.event_types
    assert generic.schema_payload["field_groups"][0]["group_id"] == "core_entities"

    assert sci_fi.display_name == "科幻"
    assert "communication_sent" in sci_fi.event_types
    assert "communication_delay" in sci_fi.checker_config["layers"]["L4 Profile Rules"]

    assert mystery.display_name == "悬疑"
    assert "evidence_discovered" in mystery.event_types
    assert "evidence_chain_closure" in mystery.checker_config["layers"]["L4 Profile Rules"]


def test_checker_registry_runs_layers_in_order():
    from app.core.world_checker_registry import LAYER_ORDER, WorldCheckerRegistry, get_official_genre_profile

    result = WorldCheckerRegistry().run(
        profile=get_official_genre_profile("generic"),
        events=[
            LedgerEvent(
                event_id="evt.hero.introduced",
                event_type="entity_introduced",
                chapter_index=1,
                intra_chapter_seq=1,
                payload={
                    "entity_ref": "char.hero",
                    "entity_type": "character",
                    "attributes": {"name": "林昼"},
                },
                idempotency_key="idem.hero.introduced",
            )
        ],
    )

    assert result.layer_trace == list(LAYER_ORDER)
    assert result.issues == []


def test_same_input_triggers_different_checkers_under_different_profiles():
    from app.core.world_checker_registry import WorldCheckerRegistry, get_official_genre_profile

    registry = WorldCheckerRegistry()
    generic_result = registry.run(
        profile=get_official_genre_profile("generic"),
        events=[_communication_event()],
    )
    sci_fi_result = registry.run(
        profile=get_official_genre_profile("sci_fi"),
        events=[_communication_event()],
    )

    assert any(issue.code == "unsupported_event_type" for issue in generic_result.issues)
    assert all(issue.code != "communication_delay" for issue in generic_result.issues)
    assert any(issue.code == "communication_delay" for issue in sci_fi_result.issues)
    assert all(issue.code != "unsupported_event_type" for issue in sci_fi_result.issues)


def test_generic_checker_entity_uniqueness_rule_is_triggered():
    from app.core.world_checker_registry import WorldCheckerRegistry, get_official_genre_profile

    result = WorldCheckerRegistry().run(
        profile=get_official_genre_profile("generic"),
        events=[
            LedgerEvent(
                event_id="evt.hero.introduced.1",
                event_type="entity_introduced",
                chapter_index=1,
                intra_chapter_seq=1,
                payload={
                    "entity_ref": "char.hero",
                    "entity_type": "character",
                    "attributes": {"name": "林昼"},
                },
                idempotency_key="idem.hero.introduced.1",
            ),
            LedgerEvent(
                event_id="evt.hero.introduced.2",
                event_type="entity_introduced",
                chapter_index=1,
                intra_chapter_seq=2,
                payload={
                    "entity_ref": "char.hero",
                    "entity_type": "character",
                    "attributes": {"name": "林昼"},
                },
                idempotency_key="idem.hero.introduced.2",
            ),
        ],
    )

    assert any(issue.code == "entity_uniqueness" for issue in result.issues)


def test_mystery_checker_evidence_chain_rule_is_triggered():
    from app.core.world_checker_registry import WorldCheckerRegistry, get_official_genre_profile

    result = WorldCheckerRegistry().run(
        profile=get_official_genre_profile("mystery"),
        evidence=[
            {
                "evidence_id": "evidence.glove",
                "evidence_type": "physical",
                "source_scope": "scene",
                "authenticity_status": "verified",
                "reliability_level": "high",
                "holder_ref": "",
                "related_claim_refs": [],
                "related_event_refs": [],
                "disclosure_layer": "investigator_only",
            }
        ],
    )

    assert any(issue.code == "evidence_chain_closure" for issue in result.issues)


def test_project_profile_service_entry_selects_checker_pack(db_session):
    from app.core.world_checker_registry import load_official_genre_profiles, run_checks_for_project_profile

    project = Project(name="Checker Pack Service")
    db_session.add(project)
    db_session.commit()

    profiles = {profile.canonical_id: profile for profile in load_official_genre_profiles(db_session)}
    project_profile = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=profiles["sci_fi"].id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={"subgenre": "hard_sf"},
    )
    db_session.add(project_profile)
    db_session.commit()

    result = run_checks_for_project_profile(
        db=db_session,
        project_profile_version_id=project_profile.id,
        events=[_communication_event()],
    )

    assert result.profile.canonical_id == "sci_fi"
    assert any(issue.code == "communication_delay" for issue in result.issues)


@pytest.mark.parametrize(
    ("resolver_name", "resolver", "kwargs", "expected_error"),
    [
        (
            "get_checker_pack_for_project_profile",
            "get_checker_pack_for_project_profile",
            {"project_profile_version_id": "ppv.missing.by-id"},
            "project profile version ppv.missing.by-id does not exist",
        ),
        (
            "get_checker_pack_for_project_profile",
            "get_checker_pack_for_project_profile",
            {"project_id": "project.missing", "profile_version": 404},
            "project profile version does not exist for project_id=project.missing, profile_version=404",
        ),
        (
            "run_checks_for_project_profile",
            "run_checks_for_project_profile",
            {"project_profile_version_id": "ppv.missing.run"},
            "project profile version ppv.missing.run does not exist",
        ),
        (
            "run_checks_for_project_profile",
            "run_checks_for_project_profile",
            {"project_id": "project.missing.run", "profile_version": 405},
            "project profile version does not exist for project_id=project.missing.run, profile_version=405",
        ),
    ],
)
def test_project_profile_service_entry_rejects_missing_profile_lookup_as_business_error(
    db_session,
    resolver_name,
    resolver,
    kwargs,
    expected_error,
):
    from app.core import world_checker_registry as checker_registry

    entry = getattr(checker_registry, resolver)

    with pytest.raises(ValueError, match=expected_error):
        entry(db=db_session, **kwargs)


def test_project_profile_checker_pack_rejects_contract_drift(db_session):
    from app.core.world_checker_registry import (
        get_checker_pack_for_project_profile,
        load_official_genre_profiles,
        run_checks_for_project_profile,
    )

    project = Project(name="Checker Pack Drift")
    db_session.add(project)
    db_session.commit()

    profiles = {profile.canonical_id: profile for profile in load_official_genre_profiles(db_session)}
    drifted_project_profile = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=profiles["sci_fi"].id,
        version=1,
        contract_version="world.contract.v0",
        profile_payload={"subgenre": "hard_sf"},
    )
    db_session.add(drifted_project_profile)

    with pytest.raises(ValueError, match="genre_profile.contract_version"):
        db_session.commit()
    db_session.rollback()

    valid_project_profile = ProjectProfileVersion(
        id="ppv-drifted",
        project_id=project.id,
        genre_profile_id=profiles["sci_fi"].id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={"subgenre": "hard_sf"},
    )
    db_session.add(valid_project_profile)
    db_session.commit()

    profiles["sci_fi"].contract_version = "world.contract.v0"
    db_session.commit()

    with pytest.raises(ValueError, match="contract_version mismatch"):
        get_checker_pack_for_project_profile(
            db=db_session,
            project_profile_version_id="ppv-drifted",
        )

    with pytest.raises(ValueError, match="contract_version mismatch"):
        run_checks_for_project_profile(
            db=db_session,
            project_profile_version_id="ppv-drifted",
            events=[_communication_event()],
        )


def test_project_profile_checker_pack_rejects_same_version_checker_config_drift(db_session):
    from app.core.world_checker_registry import (
        get_checker_pack_for_project_profile,
        load_official_genre_profiles,
    )

    project = Project(name="Checker Pack Fingerprint Drift")
    db_session.add(project)
    db_session.commit()

    profiles = {profile.canonical_id: profile for profile in load_official_genre_profiles(db_session)}
    project_profile = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=profiles["sci_fi"].id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={"subgenre": "hard_sf"},
    )
    db_session.add(project_profile)
    db_session.commit()

    profiles["sci_fi"].checker_config = {
        "pack_version": "world.contract.v1",
        "layers": {
            **profiles["sci_fi"].checker_config["layers"],
            "L4 Profile Rules": [
                "profile_event_type_guard",
                "technology_boundary",
                "energy_supply_closure",
                "auth_bypassability",
            ],
        },
    }
    db_session.commit()

    with pytest.raises(ValueError, match="checker_config fingerprint mismatch"):
        get_checker_pack_for_project_profile(
            db=db_session,
            project_profile_version_id=project_profile.id,
        )


def test_project_profile_checker_pack_rejects_same_version_bad_checker_config_value_type(db_session):
    from app.core.world_checker_registry import (
        get_checker_pack_for_project_profile,
        load_official_genre_profiles,
    )

    project = Project(name="Checker Pack Bad Config Type")
    db_session.add(project)
    db_session.commit()

    profiles = {profile.canonical_id: profile for profile in load_official_genre_profiles(db_session)}
    project_profile = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=profiles["mystery"].id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={"subgenre": "whodunit"},
    )
    db_session.add(project_profile)
    db_session.commit()

    profiles["mystery"].checker_config = {
        "pack_version": "world.contract.v1",
        "layers": {
            **profiles["mystery"].checker_config["layers"],
            "L4 Profile Rules": "mystery_time_window",
        },
    }
    db_session.commit()

    with pytest.raises(ValueError, match="must be a sequence of checker names"):
        get_checker_pack_for_project_profile(
            db=db_session,
            project_profile_version_id=project_profile.id,
        )


def test_build_pack_rejects_unknown_layer_names():
    from app.core.world_checker_registry import WorldCheckerRegistry

    profile = GenreProfile(
        canonical_id="broken-layers",
        display_name="坏配置",
        contract_version="world.contract.v1",
        checker_config={
            "layers": {
                "L0 Schema Gate": ["schema_gate"],
                "L4 Profile Rules ": ["profile_event_type_guard"],
            }
        },
    )

    with pytest.raises(ValueError, match="unknown checker layer"):
        WorldCheckerRegistry().build_pack(profile)


def test_build_pack_rejects_checker_layer_value_strings():
    from app.core.world_checker_registry import WorldCheckerRegistry

    profile = GenreProfile(
        canonical_id="broken-layer-values",
        display_name="坏配置值",
        contract_version="world.contract.v1",
        checker_config={
            "pack_version": "world.contract.v1",
            "layers": {
                "L0 Schema Gate": ["schema_gate"],
                "L4 Profile Rules": "profile_event_type_guard",
            },
        },
    )

    with pytest.raises(ValueError, match="must be a sequence of checker names"):
        WorldCheckerRegistry().build_pack(profile)


def test_build_pack_rejects_empty_checker_config():
    from app.core.world_checker_registry import WorldCheckerRegistry

    profile = GenreProfile(
        canonical_id="empty-pack",
        display_name="空 pack",
        contract_version="world.contract.v1",
        checker_config={},
    )

    with pytest.raises(ValueError, match="required checker layers"):
        WorldCheckerRegistry().build_pack(profile)


def test_build_pack_rejects_half_empty_checker_config():
    from app.core.world_checker_registry import WorldCheckerRegistry

    profile = GenreProfile(
        canonical_id="half-empty-pack",
        display_name="半空 pack",
        contract_version="world.contract.v1",
        checker_config={
            "pack_version": "world.contract.v1",
            "layers": {
                "L0 Schema Gate": ["schema_gate"],
                "L1 Event Ledger Gate": ["event_ledger_gate"],
                "L2 Deterministic Replay": ["deterministic_replay"],
                "L3 Cross-Entity Rules": [],
                "L4 Profile Rules": [],
            },
        },
    )

    with pytest.raises(ValueError, match="required checker layers"):
        WorldCheckerRegistry().build_pack(profile)


def test_schema_gate_handles_dirty_input_without_crashing():
    from app.core.world_checker_registry import WorldCheckerRegistry, get_official_genre_profile

    result = WorldCheckerRegistry().run(
        profile=get_official_genre_profile("generic"),
        events=[{"chapter_index": 1, "intra_chapter_seq": 1, "payload": {"entity_ref": "char.hero"}}],
        facts=[
            {
                "subject_ref": "char.hero",
                "predicate": "status",
                "object_ref_or_value": "alive",
                "claim_layer": "truth",
                "claim_status": "confirmed",
            }
        ],
    )

    assert result.layer_trace == ["L0 Schema Gate"]
    assert {issue.code for issue in result.issues} >= {
        "missing_event_id",
        "missing_event_type",
        "missing_claim_id",
    }
    assert "entity_uniqueness" not in result.checker_trace


def test_schema_gate_failure_stops_later_layers():
    from app.core.world_checker_registry import WorldCheckerRegistry, get_official_genre_profile

    result = WorldCheckerRegistry().run(
        profile=get_official_genre_profile("generic"),
        events=[{"event_type": "entity_introduced", "chapter_index": 1, "payload": {}}],
    )

    assert result.layer_trace == ["L0 Schema Gate"]
    assert "event_ledger_gate" not in result.checker_trace
    assert any(issue.code == "missing_event_id" for issue in result.issues)


def test_ledger_gate_failure_stops_replay_and_later_layers():
    from app.core.world_checker_registry import WorldCheckerRegistry, get_official_genre_profile

    result = WorldCheckerRegistry().run(
        profile=get_official_genre_profile("generic"),
        events=[
            LedgerEvent(
                event_id="evt.hero.introduced.1",
                event_type="entity_introduced",
                chapter_index=1,
                intra_chapter_seq=1,
                payload={
                    "entity_ref": "char.hero",
                    "entity_type": "character",
                    "attributes": {"name": "林昼"},
                },
                idempotency_key="duplicate-idem",
            ),
            LedgerEvent(
                event_id="evt.hero.introduced.2",
                event_type="entity_introduced",
                chapter_index=1,
                intra_chapter_seq=2,
                payload={
                    "entity_ref": "char.sidekick",
                    "entity_type": "character",
                    "attributes": {"name": "沈砚"},
                },
                idempotency_key="duplicate-idem",
            ),
        ],
    )

    assert result.layer_trace == ["L0 Schema Gate", "L1 Event Ledger Gate"]
    assert "deterministic_replay" not in result.checker_trace
    assert any(issue.code == "duplicate_idempotency_key" for issue in result.issues)


def test_replay_gate_failure_stops_cross_entity_and_profile_layers():
    from app.core.world_checker_registry import WorldCheckerRegistry, get_official_genre_profile

    result = WorldCheckerRegistry().run(
        profile=get_official_genre_profile("generic"),
        events=[
            LedgerEvent(
                event_id="evt.hero.introduced",
                event_type="entity_introduced",
                chapter_index=1,
                intra_chapter_seq=1,
                payload={
                    "entity_ref": "char.hero",
                    "entity_type": "character",
                    "attributes": {"name": "林昼"},
                },
                idempotency_key="idem.hero",
            ),
            LedgerEvent(
                event_id="evt.hero.retcon",
                event_type="retcon_applied",
                chapter_index=2,
                intra_chapter_seq=1,
                payload={
                    "replacement_event_type": "attribute_mutated",
                    "entity_ref": "char.hero",
                    "attribute": "status",
                    "value": "wounded",
                },
                supersedes_event_ref="evt.missing",
                idempotency_key="idem.retcon",
            ),
        ],
    )

    assert result.layer_trace == [
        "L0 Schema Gate",
        "L1 Event Ledger Gate",
        "L2 Deterministic Replay",
    ]
    assert "entity_uniqueness" not in result.checker_trace
    assert any(issue.code == "deterministic_replay_failure" for issue in result.issues)


def test_relationship_mutex_ignores_inactive_relation_cleanup():
    from app.core.world_checker_registry import WorldCheckerRegistry, get_official_genre_profile

    result = WorldCheckerRegistry().run(
        profile=get_official_genre_profile("generic"),
        events=[
            LedgerEvent(
                event_id="evt.rel.enemy.active",
                event_type="relation_mutated",
                chapter_index=1,
                intra_chapter_seq=1,
                payload={
                    "relation_id": "rel.1",
                    "source_entity_ref": "char.hero",
                    "target_entity_ref": "char.rival",
                    "relation_type": "enemy",
                    "status": "active",
                },
                idempotency_key="idem.rel.enemy.active",
            ),
            LedgerEvent(
                event_id="evt.rel.enemy.inactive",
                event_type="relation_mutated",
                chapter_index=1,
                intra_chapter_seq=2,
                payload={
                    "relation_id": "rel.1",
                    "source_entity_ref": "char.hero",
                    "target_entity_ref": "char.rival",
                    "relation_type": "enemy",
                    "status": "inactive",
                },
                idempotency_key="idem.rel.enemy.inactive",
            ),
            LedgerEvent(
                event_id="evt.rel.ally.active",
                event_type="relation_mutated",
                chapter_index=1,
                intra_chapter_seq=3,
                payload={
                    "relation_id": "rel.2",
                    "source_entity_ref": "char.hero",
                    "target_entity_ref": "char.rival",
                    "relation_type": "ally",
                    "status": "active",
                },
                idempotency_key="idem.rel.ally.active",
            ),
        ],
    )

    assert all(issue.code != "relationship_mutex" for issue in result.issues)


def test_relationship_mutex_does_not_clear_other_active_relation_types():
    from app.core.world_checker_registry import WorldCheckerRegistry, get_official_genre_profile

    result = WorldCheckerRegistry().run(
        profile=get_official_genre_profile("generic"),
        events=[
            LedgerEvent(
                event_id="evt.rel.enemy.active",
                event_type="relation_mutated",
                chapter_index=1,
                intra_chapter_seq=1,
                payload={
                    "relation_id": "rel.1",
                    "source_entity_ref": "char.hero",
                    "target_entity_ref": "char.rival",
                    "relation_type": "enemy",
                    "status": "active",
                },
                idempotency_key="idem.rel.enemy.active",
            ),
            LedgerEvent(
                event_id="evt.rel.ally.inactive",
                event_type="relation_mutated",
                chapter_index=1,
                intra_chapter_seq=2,
                payload={
                    "relation_id": "rel.2",
                    "source_entity_ref": "char.hero",
                    "target_entity_ref": "char.rival",
                    "relation_type": "ally",
                    "status": "inactive",
                },
                idempotency_key="idem.rel.ally.inactive",
            ),
            LedgerEvent(
                event_id="evt.rel.romantic.active",
                event_type="relation_mutated",
                chapter_index=1,
                intra_chapter_seq=3,
                payload={
                    "relation_id": "rel.3",
                    "source_entity_ref": "char.hero",
                    "target_entity_ref": "char.rival",
                    "relation_type": "romantic",
                    "status": "active",
                },
                idempotency_key="idem.rel.romantic.active",
            ),
        ],
    )

    assert any(issue.code == "relationship_mutex" for issue in result.issues)


def test_relationship_mutex_inactive_only_clears_matching_relation_id():
    from app.core.world_checker_registry import WorldCheckerRegistry, get_official_genre_profile

    result = WorldCheckerRegistry().run(
        profile=get_official_genre_profile("generic"),
        events=[
            LedgerEvent(
                event_id="evt.rel.enemy.rel1.active",
                event_type="relation_mutated",
                chapter_index=1,
                intra_chapter_seq=1,
                payload={
                    "relation_id": "rel.enemy.1",
                    "source_entity_ref": "char.hero",
                    "target_entity_ref": "char.rival",
                    "relation_type": "enemy",
                    "status": "active",
                },
                idempotency_key="idem.rel.enemy.rel1.active",
            ),
            LedgerEvent(
                event_id="evt.rel.enemy.rel2.active",
                event_type="relation_mutated",
                chapter_index=1,
                intra_chapter_seq=2,
                payload={
                    "relation_id": "rel.enemy.2",
                    "source_entity_ref": "char.hero",
                    "target_entity_ref": "char.rival",
                    "relation_type": "enemy",
                    "status": "active",
                },
                idempotency_key="idem.rel.enemy.rel2.active",
            ),
            LedgerEvent(
                event_id="evt.rel.enemy.rel1.inactive",
                event_type="relation_mutated",
                chapter_index=1,
                intra_chapter_seq=3,
                payload={
                    "relation_id": "rel.enemy.1",
                    "source_entity_ref": "char.hero",
                    "target_entity_ref": "char.rival",
                    "relation_type": "enemy",
                    "status": "inactive",
                },
                idempotency_key="idem.rel.enemy.rel1.inactive",
            ),
            LedgerEvent(
                event_id="evt.rel.romantic.active",
                event_type="relation_mutated",
                chapter_index=1,
                intra_chapter_seq=4,
                payload={
                    "relation_id": "rel.romantic.1",
                    "source_entity_ref": "char.hero",
                    "target_entity_ref": "char.rival",
                    "relation_type": "romantic",
                    "status": "active",
                },
                idempotency_key="idem.rel.romantic.active",
            ),
        ],
    )

    assert any(issue.code == "relationship_mutex" for issue in result.issues)


def test_profile_rules_handle_bad_numeric_and_window_types_without_crashing():
    from app.core.world_checker_registry import WorldCheckerRegistry, get_official_genre_profile

    sci_fi_result = WorldCheckerRegistry().run(
        profile=get_official_genre_profile("sci_fi"),
        events=[
            {
                "event_id": "evt.signal.bad-types",
                "event_type": "communication_sent",
                "chapter_index": 1,
                "intra_chapter_seq": 1,
                "payload": {
                    "sender_ref": "ship.daedalus",
                    "receiver_ref": "base.luna",
                    "distance_au": "far",
                    "channel_speed_au_per_hour": {"bad": "type"},
                    "declared_delay_hours": [],
                },
            }
        ],
    )
    mystery_result = WorldCheckerRegistry().run(
        profile=get_official_genre_profile("mystery"),
        events=[
            {
                "event_id": "evt.alibi.bad-types",
                "event_type": "alibi_declared",
                "chapter_index": 1,
                "intra_chapter_seq": 1,
                "payload": {
                    "subject_ref": "char.hero",
                    "window_start": {"bad": "type"},
                    "window_end": "late",
                    "observed_at": [],
                },
            }
        ],
    )

    assert any(issue.code == "invalid_numeric_payload" for issue in sci_fi_result.issues)
    assert any(issue.code == "invalid_time_window_type" for issue in mystery_result.issues)


def test_profile_rules_reject_nan_inf_and_bool_numeric_inputs():
    from app.core.world_checker_registry import WorldCheckerRegistry, get_official_genre_profile

    sci_fi_result = WorldCheckerRegistry().run(
        profile=get_official_genre_profile("sci_fi"),
        events=[
            {
                "event_id": "evt.signal.nan-bool",
                "event_type": "communication_sent",
                "chapter_index": 1,
                "intra_chapter_seq": 1,
                "payload": {
                    "sender_ref": "ship.daedalus",
                    "receiver_ref": "base.luna",
                    "distance_au": float("nan"),
                    "channel_speed_au_per_hour": True,
                    "declared_delay_hours": float("inf"),
                },
            }
        ],
    )
    mystery_result = WorldCheckerRegistry().run(
        profile=get_official_genre_profile("mystery"),
        events=[
            {
                "event_id": "evt.alibi.bool-window",
                "event_type": "alibi_declared",
                "chapter_index": 1,
                "intra_chapter_seq": 1,
                "payload": {
                    "subject_ref": "char.hero",
                    "window_start": True,
                    "window_end": 5,
                    "observed_at": False,
                },
            }
        ],
    )

    assert any(issue.code == "invalid_numeric_payload" for issue in sci_fi_result.issues)
    assert any(issue.code == "invalid_time_window_type" for issue in mystery_result.issues)

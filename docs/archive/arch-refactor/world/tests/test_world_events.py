import pytest
from sqlalchemy.exc import IntegrityError

from app.core.world_replay import (
    BrokenSupersedesChainError,
    DuplicateEventError,
    LedgerEvent,
    ledger_events_from_world_events,
    replay_events,
)
from app.models import GenreProfile, Project, ProjectProfileVersion, WorldEvent, WorldTimelineAnchor


def _seed_project_profile_and_anchors(db_session):
    project = Project(name="World Event Replay")
    genre_profile = GenreProfile(
        canonical_id="generic-world-events",
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

    anchor_base = WorldTimelineAnchor(
        project_id=project.id,
        profile_version=1,
        anchor_id="anchor.base",
        chapter_index=1,
        intra_chapter_seq=1,
        world_time_label="",
        normalized_tick_or_range="0001.0001",
        precision="beat",
        relative_to_anchor_ref=None,
        ordering_key="0001.0001.0000",
        contract_version="world.contract.v1",
    )
    anchor_later = WorldTimelineAnchor(
        project_id=project.id,
        profile_version=1,
        anchor_id="anchor.later",
        chapter_index=1,
        intra_chapter_seq=1,
        world_time_label="同章稍后",
        normalized_tick_or_range="0001.0001.0001",
        precision="beat",
        relative_to_anchor_ref="anchor.base",
        ordering_key="0001.0001.0001",
        contract_version="world.contract.v1",
    )
    db_session.add_all([anchor_base, anchor_later])
    db_session.commit()
    return project, profile_version, anchor_base, anchor_later


def test_replay_applies_event_primitives_into_expected_state():
    events = [
        LedgerEvent(
            event_id="evt.hero.introduced",
            event_type="entity_introduced",
            chapter_index=1,
            intra_chapter_seq=1,
            payload={
                "entity_ref": "char.hero",
                "entity_type": "character",
                "attributes": {"name": "林昼", "status": "alive"},
            },
            idempotency_key="idem-1",
        ),
        LedgerEvent(
            event_id="evt.hero.status",
            event_type="attribute_mutated",
            chapter_index=1,
            intra_chapter_seq=2,
            payload={
                "entity_ref": "char.hero",
                "attribute": "status",
                "value": "wounded",
            },
            idempotency_key="idem-2",
        ),
        LedgerEvent(
            event_id="evt.hero.relation",
            event_type="relation_mutated",
            chapter_index=1,
            intra_chapter_seq=3,
            payload={
                "relation_id": "rel.hero.scrapyard",
                "source_entity_ref": "char.hero",
                "target_entity_ref": "faction.scrapyard",
                "relation_type": "member_of",
                "status": "active",
            },
            idempotency_key="idem-3",
        ),
        LedgerEvent(
            event_id="evt.hero.presence",
            event_type="presence_shifted",
            chapter_index=1,
            intra_chapter_seq=4,
            payload={
                "entity_ref": "char.hero",
                "location_ref": "loc.dock-7",
                "presence_status": "onsite",
                "known_by_refs": ["char.detective"],
            },
            idempotency_key="idem-4",
        ),
        LedgerEvent(
            event_id="evt.incident.lockdown",
            event_type="event_occurred",
            chapter_index=1,
            intra_chapter_seq=5,
            payload={
                "event_ref": "incident.lockdown",
                "participants": ["char.hero"],
                "location_ref": "loc.dock-7",
            },
            idempotency_key="idem-5",
        ),
        LedgerEvent(
            event_id="evt.incident.blackout",
            event_type="event_occurred",
            chapter_index=1,
            intra_chapter_seq=6,
            payload={
                "event_ref": "incident.blackout",
                "participants": ["loc.dock-7"],
                "location_ref": "loc.dock-7",
            },
            idempotency_key="idem-6",
        ),
        LedgerEvent(
            event_id="evt.incident.link",
            event_type="event_linked",
            chapter_index=1,
            intra_chapter_seq=7,
            payload={
                "source_event_ref": "incident.lockdown",
                "target_event_ref": "incident.blackout",
                "link_type": "caused",
            },
            idempotency_key="idem-7",
        ),
        LedgerEvent(
            event_id="evt.claim.review",
            event_type="fact_reviewed",
            chapter_index=1,
            intra_chapter_seq=8,
            payload={
                "claim_id": "claim.lockdown-real",
                "review_status": "confirmed",
                "reviewer_ref": "editor.alpha",
            },
            idempotency_key="idem-8",
        ),
    ]

    state = replay_events(events)

    assert state.entities["char.hero"]["entity_type"] == "character"
    assert state.entities["char.hero"]["attributes"]["name"] == "林昼"
    assert state.entities["char.hero"]["attributes"]["status"] == "wounded"
    assert state.relations["rel.hero.scrapyard"]["relation_type"] == "member_of"
    assert state.relations["rel.hero.scrapyard"]["status"] == "active"
    assert state.presence["char.hero"]["location_ref"] == "loc.dock-7"
    assert state.presence["char.hero"]["presence_status"] == "onsite"
    assert state.occurred_events["incident.lockdown"]["location_ref"] == "loc.dock-7"
    assert state.event_links["incident.lockdown"] == [
        {"target_event_ref": "incident.blackout", "link_type": "caused"}
    ]
    assert state.fact_reviews["claim.lockdown-real"]["review_status"] == "confirmed"
    assert state.active_event_ids == [
        "evt.hero.introduced",
        "evt.hero.status",
        "evt.hero.relation",
        "evt.hero.presence",
        "evt.incident.lockdown",
        "evt.incident.blackout",
        "evt.incident.link",
        "evt.claim.review",
    ]


def test_retcon_applied_uses_supersedes_chain_without_overwriting_history():
    events = [
        LedgerEvent(
            event_id="evt.hero.introduced",
            event_type="entity_introduced",
            chapter_index=1,
            intra_chapter_seq=1,
            payload={
                "entity_ref": "char.hero",
                "entity_type": "character",
                "attributes": {"rank": "cadet"},
            },
            idempotency_key="idem-hero",
        ),
        LedgerEvent(
            event_id="evt.hero.rank-original",
            event_type="attribute_mutated",
            chapter_index=2,
            intra_chapter_seq=1,
            payload={
                "entity_ref": "char.hero",
                "attribute": "rank",
                "value": "captain",
            },
            idempotency_key="idem-rank-original",
        ),
        LedgerEvent(
            event_id="evt.hero.rank-retcon",
            event_type="retcon_applied",
            chapter_index=3,
            intra_chapter_seq=1,
            supersedes_event_ref="evt.hero.rank-original",
            payload={
                "replacement_event_type": "attribute_mutated",
                "entity_ref": "char.hero",
                "attribute": "rank",
                "value": "commander",
            },
            idempotency_key="idem-rank-retcon",
        ),
    ]

    state = replay_events(events)

    assert state.entities["char.hero"]["attributes"]["rank"] == "commander"
    assert state.ledger["evt.hero.rank-original"].payload["value"] == "captain"
    assert state.ledger["evt.hero.rank-retcon"].supersedes_event_ref == "evt.hero.rank-original"
    assert state.inactive_event_ids == ["evt.hero.rank-original"]
    assert state.active_event_ids == ["evt.hero.introduced", "evt.hero.rank-retcon"]


def test_duplicate_idempotency_events_are_rejected():
    events = [
        LedgerEvent(
            event_id="evt.hero.introduced",
            event_type="entity_introduced",
            chapter_index=1,
            intra_chapter_seq=1,
            payload={
                "entity_ref": "char.hero",
                "entity_type": "character",
                "attributes": {"status": "alive"},
            },
            idempotency_key="duplicate-key",
        ),
        LedgerEvent(
            event_id="evt.hero.duplicate",
            event_type="attribute_mutated",
            chapter_index=1,
            intra_chapter_seq=2,
            payload={
                "entity_ref": "char.hero",
                "attribute": "status",
                "value": "wounded",
            },
            idempotency_key="duplicate-key",
        ),
    ]

    with pytest.raises(DuplicateEventError):
        replay_events(events)


def test_duplicate_event_id_is_rejected_even_with_different_idempotency_keys():
    events = [
        LedgerEvent(
            event_id="evt.hero.duplicate",
            event_type="entity_introduced",
            chapter_index=1,
            intra_chapter_seq=1,
            payload={
                "entity_ref": "char.hero",
                "entity_type": "character",
                "attributes": {"status": "alive"},
            },
            idempotency_key="duplicate-id-1",
        ),
        LedgerEvent(
            event_id="evt.hero.duplicate",
            event_type="attribute_mutated",
            chapter_index=1,
            intra_chapter_seq=2,
            payload={
                "entity_ref": "char.hero",
                "attribute": "status",
                "value": "wounded",
            },
            idempotency_key="duplicate-id-2",
        ),
    ]

    with pytest.raises(DuplicateEventError):
        replay_events(events)


def test_non_retcon_event_with_supersedes_is_rejected_without_revision_semantics():
    events = [
        LedgerEvent(
            event_id="evt.hero.introduced",
            event_type="entity_introduced",
            chapter_index=1,
            intra_chapter_seq=1,
            payload={
                "entity_ref": "char.hero",
                "entity_type": "character",
                "attributes": {"status": "alive"},
            },
            idempotency_key="idem-non-retcon-1",
        ),
        LedgerEvent(
            event_id="evt.hero.misused-supersedes",
            event_type="attribute_mutated",
            chapter_index=1,
            intra_chapter_seq=2,
            supersedes_event_ref="evt.hero.introduced",
            payload={
                "entity_ref": "char.hero",
                "attribute": "status",
                "value": "wounded",
            },
            idempotency_key="idem-non-retcon-2",
        ),
    ]

    with pytest.raises(BrokenSupersedesChainError):
        replay_events(events)


def test_broken_supersedes_chain_is_rejected():
    events = [
        LedgerEvent(
            event_id="evt.retcon.broken",
            event_type="retcon_applied",
            chapter_index=1,
            intra_chapter_seq=1,
            supersedes_event_ref="evt.missing",
            payload={
                "replacement_event_type": "attribute_mutated",
                "entity_ref": "char.hero",
                "attribute": "status",
                "value": "dead",
            },
            idempotency_key="idem-broken-retcon",
        ),
    ]

    with pytest.raises(BrokenSupersedesChainError):
        replay_events(events)


def test_same_story_time_replay_uses_stable_event_id_tie_break():
    events = [
        LedgerEvent(
            event_id="evt.hero.status.b",
            event_type="attribute_mutated",
            chapter_index=1,
            intra_chapter_seq=1,
            payload={
                "entity_ref": "char.hero",
                "attribute": "status",
                "value": "wounded",
            },
            idempotency_key="tie-break-b",
        ),
        LedgerEvent(
            event_id="evt.hero.introduced",
            event_type="entity_introduced",
            chapter_index=1,
            intra_chapter_seq=0,
            payload={
                "entity_ref": "char.hero",
                "entity_type": "character",
                "attributes": {"status": "alive"},
            },
            idempotency_key="tie-break-intro",
        ),
        LedgerEvent(
            event_id="evt.hero.status.a",
            event_type="attribute_mutated",
            chapter_index=1,
            intra_chapter_seq=1,
            payload={
                "entity_ref": "char.hero",
                "attribute": "status",
                "value": "stable",
            },
            idempotency_key="tie-break-a",
        ),
    ]

    state = replay_events(events)

    assert state.entities["char.hero"]["attributes"]["status"] == "wounded"
    assert state.active_event_ids[-2:] == ["evt.hero.status.a", "evt.hero.status.b"]


def test_supersedes_persistence_roundtrip_uses_logical_event_ref(db_session):
    project, profile_version, anchor_base, anchor_later = _seed_project_profile_and_anchors(db_session)
    original = WorldEvent(
        project_id=project.id,
        profile_version=1,
        project_profile_version_id=profile_version.id,
        event_id="evt.rank.original",
        idempotency_key="persist-idem-1",
        timeline_anchor_id=anchor_base.anchor_id,
        chapter_index=1,
        intra_chapter_seq=1,
        event_type="attribute_mutated",
        primitive_payload={
            "entity_ref": "char.hero",
            "attribute": "rank",
            "value": "captain",
        },
        truth_layer="canonical_truth",
        disclosure_layer="reader_visible",
        contract_version_refs=["world.contract.v1"],
        contract_version="world.contract.v1",
    )
    retcon = WorldEvent(
        project_id=project.id,
        profile_version=1,
        project_profile_version_id=profile_version.id,
        event_id="evt.rank.retcon",
        idempotency_key="persist-idem-2",
        timeline_anchor_id=anchor_later.anchor_id,
        chapter_index=1,
        intra_chapter_seq=1,
        event_type="retcon_applied",
        supersedes_event_ref="evt.rank.original",
        primitive_payload={
            "replacement_event_type": "attribute_mutated",
            "entity_ref": "char.hero",
            "attribute": "rank",
            "value": "commander",
        },
        truth_layer="canonical_truth",
        disclosure_layer="reader_visible",
        contract_version_refs=["world.contract.v1"],
        contract_version="world.contract.v1",
    )
    db_session.add_all([original, retcon])
    db_session.commit()

    saved_events = (
        db_session.query(WorldEvent)
        .filter(WorldEvent.project_id == project.id)
        .order_by(WorldEvent.event_id.asc())
        .all()
    )
    saved_anchors = (
        db_session.query(WorldTimelineAnchor)
        .filter(WorldTimelineAnchor.project_id == project.id)
        .order_by(WorldTimelineAnchor.anchor_id.asc())
        .all()
    )

    ledger_events = ledger_events_from_world_events(saved_events, saved_anchors)
    state = replay_events(ledger_events)

    assert saved_events[1].supersedes_event_ref == "evt.rank.original"
    assert state.entities["char.hero"]["attributes"]["rank"] == "commander"
    assert state.inactive_event_ids == ["evt.rank.original"]


def test_world_event_persistence_rejects_duplicate_idempotency_key(db_session):
    project, profile_version, anchor_base, _ = _seed_project_profile_and_anchors(db_session)
    first = WorldEvent(
        project_id=project.id,
        profile_version=1,
        project_profile_version_id=profile_version.id,
        event_id="evt.persist.one",
        idempotency_key="persist-duplicate-key",
        timeline_anchor_id=anchor_base.anchor_id,
        chapter_index=1,
        intra_chapter_seq=1,
        event_type="event_occurred",
        primitive_payload={"event_ref": "incident.one"},
        truth_layer="canonical_truth",
        disclosure_layer="reader_visible",
        contract_version_refs=["world.contract.v1"],
        contract_version="world.contract.v1",
    )
    duplicate = WorldEvent(
        project_id=project.id,
        profile_version=1,
        project_profile_version_id=profile_version.id,
        event_id="evt.persist.two",
        idempotency_key="persist-duplicate-key",
        timeline_anchor_id=anchor_base.anchor_id,
        chapter_index=1,
        intra_chapter_seq=2,
        event_type="event_occurred",
        primitive_payload={"event_ref": "incident.two"},
        truth_layer="canonical_truth",
        disclosure_layer="reader_visible",
        contract_version_refs=["world.contract.v1"],
        contract_version="world.contract.v1",
    )
    db_session.add_all([first, duplicate])

    with pytest.raises(IntegrityError):
        db_session.commit()

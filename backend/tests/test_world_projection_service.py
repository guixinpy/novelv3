from app.core import world_projection_service
from app.core.world_projection_service import build_world_projection_overview
from app.models import (
    GenreProfile,
    Project,
    ProjectProfileVersion,
    WorldEvent,
    WorldFactClaim,
    WorldTimelineAnchor,
)


def _seed_world(db_session):
    project = Project(name="Projection Service")
    genre_profile = GenreProfile(
        canonical_id="generic-projection-service",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    profile = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={"theme": "雾港城"},
    )
    db_session.add(profile)
    db_session.commit()

    db_session.add_all([
        WorldTimelineAnchor(
            project_id=project.id,
            profile_version=profile.version,
            anchor_id="anchor.ch1.s1",
            chapter_index=1,
            intra_chapter_seq=1,
            ordering_key="001:001",
            contract_version="world.contract.v1",
        ),
        WorldTimelineAnchor(
            project_id=project.id,
            profile_version=profile.version,
            anchor_id="anchor.ch2.s1",
            chapter_index=2,
            intra_chapter_seq=1,
            ordering_key="002:001",
            contract_version="world.contract.v1",
        ),
        WorldEvent(
            project_id=project.id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            event_id="evt.hero.introduced",
            idempotency_key="idem.hero.introduced",
            timeline_anchor_id="anchor.ch1.s1",
            chapter_index=1,
            intra_chapter_seq=1,
            event_type="entity_introduced",
            primitive_payload={
                "entity_ref": "char.hero",
                "entity_type": "character",
                "attributes": {"status": "alive"},
            },
            truth_layer="truth",
            disclosure_layer="public",
            contract_version="world.contract.v1",
        ),
        WorldEvent(
            project_id=project.id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            event_id="evt.hero.presence",
            idempotency_key="idem.hero.presence",
            timeline_anchor_id="anchor.ch2.s1",
            chapter_index=2,
            intra_chapter_seq=1,
            event_type="presence_shifted",
            primitive_payload={
                "entity_ref": "char.hero",
                "location_ref": "loc.safehouse",
                "presence_status": "hidden",
                "known_by_refs": ["char.detective"],
            },
            truth_layer="truth",
            disclosure_layer="limited",
            contract_version="world.contract.v1",
        ),
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            claim_id="claim.hero.rank.truth",
            chapter_index=2,
            intra_chapter_seq=2,
            subject_ref="char.hero",
            predicate="rank",
            object_ref_or_value="captain",
            claim_layer="truth",
            claim_status="confirmed",
            valid_from_anchor_id="anchor.ch2.s1",
            authority_type="authoritative_structured",
            confidence=1.0,
            contract_version="world.contract.v1",
        ),
    ])
    db_session.commit()
    return project, profile


def test_projection_service_builds_all_frontend_views_from_shared_source(db_session):
    project, profile = _seed_world(db_session)

    truth = build_world_projection_overview(
        db=db_session,
        project_id=project.id,
        profile=profile,
        view_type="current_truth",
    )
    subject = build_world_projection_overview(
        db=db_session,
        project_id=project.id,
        profile=profile,
        view_type="subject_knowledge",
        subject_ref="char.detective",
    )
    snapshot = build_world_projection_overview(
        db=db_session,
        project_id=project.id,
        profile=profile,
        view_type="chapter_snapshot",
        chapter_index=1,
    )

    assert truth.project_profile.id == profile.id
    assert truth.projection.view_type == "current_truth"
    assert truth.projection.facts["char.hero"]["rank"] == "captain"

    assert subject.projection.view_type == "subject_knowledge"
    assert subject.projection.facts["char.hero"]["rank"] == "captain"
    assert subject.projection.presence["char.hero"]["location_ref"] == "loc.safehouse"

    assert snapshot.projection.view_type == "chapter_snapshot"
    assert snapshot.projection.entities["char.hero"]["attributes"]["status"] == "alive"
    assert snapshot.projection.facts == {}


def test_projection_service_returns_empty_overview_without_profile(db_session):
    project = Project(name="No Profile")
    db_session.add(project)
    db_session.commit()

    overview = build_world_projection_overview(
        db=db_session,
        project_id=project.id,
        profile=None,
        view_type="current_truth",
    )

    assert overview.project_profile is None
    assert overview.projection is None


def test_projection_service_reuses_local_projection_cache(monkeypatch, db_session):
    project, profile = _seed_world(db_session)
    load_count = 0
    original_loader = world_projection_service.load_world_projection_source

    def counting_loader(**kwargs):
        nonlocal load_count
        load_count += 1
        return original_loader(**kwargs)

    monkeypatch.setattr(world_projection_service, "load_world_projection_source", counting_loader)

    first = build_world_projection_overview(
        db=db_session,
        project_id=project.id,
        profile=profile,
        view_type="current_truth",
    )
    second = build_world_projection_overview(
        db=db_session,
        project_id=project.id,
        profile=profile,
        view_type="current_truth",
    )

    assert first.projection.facts == second.projection.facts
    assert load_count == 1

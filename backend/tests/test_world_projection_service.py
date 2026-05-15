from sqlalchemy import event

from app.core import world_projection_service
from app.core.world_projection_service import build_world_projection_overview
from app.models import (
    GenreProfile,
    Project,
    ProjectProfileVersion,
    WorldCharacter,
    WorldEvent,
    WorldFactClaim,
    WorldLocation,
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


def test_projection_service_includes_profile_entity_catalog_without_intro_events(db_session):
    project = Project(name="Catalog Projection")
    genre_profile = GenreProfile(
        canonical_id="catalog-projection",
        display_name="Catalog Projection",
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
    db_session.add(profile)
    db_session.commit()
    db_session.add_all([
        WorldCharacter(
            project_id=project.id,
            profile_version=profile.version,
            character_id="hero",
            canonical_id="char.hero",
            primary_alias="林舟",
            name="林舟",
            aliases=["守夜人"],
            role_type="character",
            identity_anchor="林舟",
            origin_background="雾港守夜人",
            core_traits=["谨慎"],
            core_drives=["查清真相"],
            contract_version=profile.contract_version,
        ),
        WorldLocation(
            project_id=project.id,
            profile_version=profile.version,
            location_id="fog-harbor",
            canonical_id="loc.fog-harbor",
            primary_alias="雾港城",
            name="雾港城",
            aliases=[],
            location_type="city",
            spatial_scope="主舞台",
            contract_version=profile.contract_version,
        ),
    ])
    db_session.commit()

    overview = build_world_projection_overview(
        db=db_session,
        project_id=project.id,
        profile=profile,
        view_type="current_truth",
    )

    assert overview.projection.entities["char.hero"]["entity_type"] == "character"
    assert overview.projection.entities["char.hero"]["attributes"]["name"] == "林舟"
    assert overview.projection.entities["loc.fog-harbor"]["entity_type"] == "location"
    assert overview.projection.entities["loc.fog-harbor"]["attributes"]["spatial_scope"] == "主舞台"

    subject = build_world_projection_overview(
        db=db_session,
        project_id=project.id,
        profile=profile,
        view_type="subject_knowledge",
        subject_ref="char.hero",
    )

    assert "char.hero" in subject.projection.entities
    assert "loc.fog-harbor" not in subject.projection.entities


def test_chapter_snapshot_projection_source_filters_future_event_and_fact_rows(db_session):
    project, profile = _seed_world(db_session)
    world_projection_service.clear_world_projection_cache()
    db_session.add_all([
        WorldTimelineAnchor(
            project_id=project.id,
            profile_version=profile.version,
            anchor_id="anchor.ch50.s1",
            chapter_index=50,
            intra_chapter_seq=1,
            ordering_key="050:001",
            contract_version="world.contract.v1",
        ),
        WorldEvent(
            project_id=project.id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            event_id="evt.future",
            idempotency_key="idem.future",
            timeline_anchor_id="anchor.ch50.s1",
            chapter_index=50,
            intra_chapter_seq=1,
            event_type="entity_introduced",
            primitive_payload={
                "entity_ref": "char.future",
                "entity_type": "character",
                "attributes": {"status": "future"},
            },
            truth_layer="truth",
            disclosure_layer="public",
            contract_version="world.contract.v1",
        ),
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            claim_id="claim.future.rank.truth",
            chapter_index=50,
            intra_chapter_seq=2,
            subject_ref="char.future",
            predicate="rank",
            object_ref_or_value="admiral",
            claim_layer="truth",
            claim_status="confirmed",
            valid_from_anchor_id="anchor.ch50.s1",
            authority_type="authoritative_structured",
            confidence=1.0,
            contract_version="world.contract.v1",
        ),
    ])
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        overview = build_world_projection_overview(
            db=db_session,
            project_id=project.id,
            profile=profile,
            view_type="chapter_snapshot",
            chapter_index=1,
        )
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert "char.future" not in overview.projection.entities
    assert "char.future" not in overview.projection.facts
    event_selects = [
        statement
        for statement in statements
        if "select world_events.id" in statement and "from world_events" in statement
    ]
    fact_selects = [
        statement
        for statement in statements
        if "select world_fact_claims.id" in statement and "from world_fact_claims" in statement
    ]
    assert any("world_events.chapter_index <=" in statement for statement in event_selects)
    assert any("world_fact_claims.chapter_index <=" in statement for statement in fact_selects)


def test_projection_source_filters_unconfirmed_fact_rows_in_sql(db_session):
    project, profile = _seed_world(db_session)
    world_projection_service.clear_world_projection_cache()
    db_session.add(
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            claim_id="claim.hero.false-rank.pending",
            chapter_index=2,
            intra_chapter_seq=3,
            subject_ref="char.hero",
            predicate="false_rank",
            object_ref_or_value="admiral",
            claim_layer="truth",
            claim_status="pending",
            valid_from_anchor_id="anchor.ch2.s1",
            authority_type="authoritative_structured",
            confidence=0.3,
            contract_version="world.contract.v1",
        )
    )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        overview = build_world_projection_overview(
            db=db_session,
            project_id=project.id,
            profile=profile,
            view_type="current_truth",
        )
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert "false_rank" not in overview.projection.facts["char.hero"]
    fact_selects = [
        statement
        for statement in statements
        if "select world_fact_claims.id" in statement and "from world_fact_claims" in statement
    ]
    assert any("world_fact_claims.claim_status =" in statement for statement in fact_selects)


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


def test_projection_service_evicts_old_entries_when_local_cache_is_full(monkeypatch, db_session):
    project, profile = _seed_world(db_session)
    world_projection_service.clear_world_projection_cache()
    monkeypatch.setattr(world_projection_service, "WORLD_PROJECTION_CACHE_MAX_ENTRIES", 2)
    load_count = 0
    original_loader = world_projection_service.load_world_projection_source

    def counting_loader(**kwargs):
        nonlocal load_count
        load_count += 1
        return original_loader(**kwargs)

    monkeypatch.setattr(world_projection_service, "load_world_projection_source", counting_loader)

    build_world_projection_overview(
        db=db_session,
        project_id=project.id,
        profile=profile,
        view_type="current_truth",
    )
    build_world_projection_overview(
        db=db_session,
        project_id=project.id,
        profile=profile,
        view_type="subject_knowledge",
        subject_ref="char.detective",
    )
    build_world_projection_overview(
        db=db_session,
        project_id=project.id,
        profile=profile,
        view_type="subject_knowledge",
        subject_ref="char.editor",
    )
    build_world_projection_overview(
        db=db_session,
        project_id=project.id,
        profile=profile,
        view_type="current_truth",
    )

    assert load_count == 4

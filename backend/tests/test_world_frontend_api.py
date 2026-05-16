from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy import event

from app.api import world_model as world_model_api
from app.core.world_proposal_service import (
    calculate_bundle_impact_scope,
    create_bundle,
    review_proposal_item,
    write_candidate_fact,
)
from app.models import (
    ChapterContent,
    GenreProfile,
    Project,
    ProjectProfileVersion,
    Setup,
    WorldCharacter,
    WorldEvent,
    WorldFactClaim,
    WorldProposalBundle,
    WorldProposalItem,
    WorldRelation,
    WorldRule,
    WorldTimelineAnchor,
)
from app.schemas.world_proposals import ProposalCandidateFactCreate


def _seed_profile(db_session):
    project = Project(name="World Frontend API")
    genre_profile = GenreProfile(
        canonical_id="generic-world-frontend-api",
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
        profile_payload={"theme": "轨道城废墟"},
    )
    db_session.add(profile_version)
    db_session.commit()
    return project, profile_version


def _candidate_payload(
    *,
    claim_id: str,
    subject_ref: str,
    predicate: str,
    value: object,
    chapter_index: int | None = None,
) -> ProposalCandidateFactCreate:
    return ProposalCandidateFactCreate(
        project_id="ignored-by-service",
        profile_version=1,
        claim_id=claim_id,
        chapter_index=chapter_index,
        subject_ref=subject_ref,
        predicate=predicate,
        object_ref_or_value=value,
        claim_layer="truth",
        authority_type="authoritative_structured",
        confidence=0.95,
        contract_version="world.contract.v1",
        evidence_refs=["evidence.scene"],
    )


def test_get_world_model_overview_returns_current_profile_and_truth_projection(client, db_session):
    project, profile_version = _seed_profile(db_session)
    db_session.add_all([
        WorldTimelineAnchor(
            project_id=project.id,
            profile_version=profile_version.version,
            anchor_id="anchor.ch1.s1",
            chapter_index=1,
            intra_chapter_seq=1,
            ordering_key="001:001",
            contract_version="world.contract.v1",
        ),
        WorldEvent(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            event_id="evt.hero.introduced",
            idempotency_key="idem.hero.introduced",
            timeline_anchor_id="anchor.ch1.s1",
            chapter_index=1,
            intra_chapter_seq=1,
            event_type="entity_introduced",
            primitive_payload={
                "entity_ref": "char.hero",
                "entity_type": "character",
                "attributes": {"status": "alive", "title": "档案修复员"},
            },
            truth_layer="truth",
            disclosure_layer="public",
            contract_version="world.contract.v1",
        ),
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            claim_id="claim.hero.rank.truth",
            chapter_index=1,
            intra_chapter_seq=2,
            subject_ref="char.hero",
            predicate="rank",
            object_ref_or_value="captain",
            claim_layer="truth",
            claim_status="confirmed",
            valid_from_anchor_id="anchor.ch1.s1",
            authority_type="authoritative_structured",
            confidence=1.0,
            contract_version="world.contract.v1",
        ),
    ])
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}/world-model")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_profile"]["id"] == profile_version.id
    assert payload["project_profile"]["version"] == 1
    assert payload["projection"]["view_type"] == "current_truth"
    assert payload["projection"]["entities"]["char.hero"]["attributes"]["title"] == "档案修复员"
    assert payload["projection"]["facts"]["char.hero"]["rank"] == "captain"


def test_get_world_model_overview_returns_bounded_projection_window(client, db_session):
    project, profile_version = _seed_profile(db_session)
    anchors = []
    events = []
    facts = []
    for index in range(1, 151):
        anchor_id = f"anchor.ch{index}.s1"
        entity_ref = f"char.{index:03d}"
        event_ref = f"incident.{index:03d}"
        anchors.append(
            WorldTimelineAnchor(
                project_id=project.id,
                profile_version=profile_version.version,
                anchor_id=anchor_id,
                chapter_index=index,
                intra_chapter_seq=1,
                ordering_key=f"{index:03d}:001",
                contract_version="world.contract.v1",
            )
        )
        events.extend([
            WorldEvent(
                project_id=project.id,
                project_profile_version_id=profile_version.id,
                profile_version=profile_version.version,
                event_id=f"evt.{entity_ref}.introduced",
                idempotency_key=f"idem.{entity_ref}.introduced",
                timeline_anchor_id=anchor_id,
                chapter_index=index,
                intra_chapter_seq=1,
                event_type="entity_introduced",
                primitive_payload={
                    "entity_ref": entity_ref,
                    "entity_type": "character",
                    "attributes": {"status": "active"},
                },
                truth_layer="truth",
                disclosure_layer="public",
                contract_version="world.contract.v1",
            ),
            WorldEvent(
                project_id=project.id,
                project_profile_version_id=profile_version.id,
                profile_version=profile_version.version,
                event_id=f"evt.{event_ref}.occurred",
                idempotency_key=f"idem.{event_ref}.occurred",
                timeline_anchor_id=anchor_id,
                chapter_index=index,
                intra_chapter_seq=2,
                event_type="event_occurred",
                primitive_payload={
                    "event_ref": event_ref,
                    "title": f"事件 {index:03d}",
                },
                truth_layer="truth",
                disclosure_layer="public",
                contract_version="world.contract.v1",
            ),
        ])
        facts.append(
            WorldFactClaim(
                project_id=project.id,
                project_profile_version_id=profile_version.id,
                profile_version=profile_version.version,
                claim_id=f"claim.{entity_ref}.rank",
                chapter_index=index,
                intra_chapter_seq=3,
                subject_ref=entity_ref,
                predicate="rank",
                object_ref_or_value=f"rank-{index:03d}",
                claim_layer="truth",
                claim_status="confirmed",
                authority_type="authoritative_structured",
                confidence=1.0,
                contract_version="world.contract.v1",
            )
        )
    db_session.add_all([*anchors, *events, *facts])
    db_session.commit()

    response = client.get(
        f"/api/v1/projects/{project.id}/world-model"
        "?entity_offset=5&entity_limit=10"
        "&event_offset=3&event_limit=7"
        "&fact_subject_offset=4&fact_subject_limit=9"
    )

    assert response.status_code == 200
    projection = response.json()["projection"]
    assert list(projection["entities"]) == [f"char.{index:03d}" for index in range(6, 16)]
    assert projection["entities_total"] == 150
    assert projection["entities_offset"] == 5
    assert projection["entities_limit"] == 10
    assert projection["entities_has_more"] is True
    assert list(projection["occurred_events"]) == [f"incident.{index:03d}" for index in range(4, 11)]
    assert projection["occurred_events_total"] == 150
    assert projection["occurred_events_offset"] == 3
    assert projection["occurred_events_limit"] == 7
    assert projection["occurred_events_has_more"] is True
    assert list(projection["facts"]) == [f"char.{index:03d}" for index in range(5, 14)]
    assert projection["facts_total"] == 150
    assert projection["facts_offset"] == 4
    assert projection["facts_limit"] == 9
    assert projection["facts_has_more"] is True


def test_list_world_fact_claims_returns_current_profile_metadata(client, db_session):
    project, older_profile = _seed_profile(db_session)
    current_profile = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=older_profile.genre_profile_id,
        version=2,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add(current_profile)
    db_session.commit()
    db_session.add_all([
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=current_profile.id,
            profile_version=current_profile.version,
            claim_id="claim.hero.secret.current",
            chapter_index=2,
            intra_chapter_seq=1,
            subject_ref="char.hero",
            predicate="secret",
            object_ref_or_value={"value": "潮汐门钥匙"},
            claim_layer="truth",
            claim_status="confirmed",
            perspective_ref="char.hero",
            disclosed_to_refs=["char.hero", "char.mentor"],
            valid_from_anchor_id="anchor.ch2.s1",
            source_event_ref="event.hero.secret",
            evidence_refs=["chapter.02"],
            authority_type="authoritative_structured",
            confidence=0.8,
            notes="披露测试",
            contract_version="world.contract.v1",
        ),
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=older_profile.id,
            profile_version=older_profile.version,
            claim_id="claim.hero.secret.old",
            chapter_index=1,
            intra_chapter_seq=1,
            subject_ref="char.hero",
            predicate="secret",
            object_ref_or_value="旧版本",
            claim_layer="truth",
            claim_status="confirmed",
            authority_type="authoritative_structured",
            confidence=1.0,
            contract_version="world.contract.v1",
        ),
    ])
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}/world-model/facts")

    assert response.status_code == 200
    payload = response.json()
    assert [item["claim_id"] for item in payload["claims"]] == ["claim.hero.secret.current"]
    assert payload["claims"][0]["object_ref_or_value"] == {"value": "潮汐门钥匙"}
    assert payload["claims"][0]["perspective_ref"] == "char.hero"
    assert payload["claims"][0]["disclosed_to_refs"] == ["char.hero", "char.mentor"]
    assert payload["claims"][0]["evidence_refs"] == ["chapter.02"]


def test_list_world_fact_claims_count_does_not_select_large_json_columns(client, db_session):
    project, profile_version = _seed_profile(db_session)
    db_session.add_all([
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            claim_id=f"claim.heavy.{index}",
            chapter_index=index,
            intra_chapter_seq=1,
            subject_ref="char.hero",
            predicate="memory_payload",
            object_ref_or_value={"payload": ["长事实"] * 100},
            claim_layer="truth",
            claim_status="confirmed",
            disclosed_to_refs=["char.hero"] * 50,
            evidence_refs=["evidence.long"] * 50,
            authority_type="authoritative_structured",
            confidence=1.0,
            notes="长备注" * 200,
            contract_version="world.contract.v1",
        )
        for index in range(1, 4)
    ])
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/world-model/facts?limit=1")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    fact_count_statements = [
        statement
        for statement in statements
        if "count(" in statement and "world_fact_claims" in statement
    ]
    assert fact_count_statements
    assert all("world_fact_claims.object_ref_or_value" not in statement for statement in fact_count_statements)
    assert all("world_fact_claims.disclosed_to_refs" not in statement for statement in fact_count_statements)
    assert all("world_fact_claims.evidence_refs" not in statement for statement in fact_count_statements)
    assert all("world_fact_claims.notes" not in statement for statement in fact_count_statements)


def test_list_world_fact_claims_returns_bounded_page_with_total(client, db_session):
    project, profile_version = _seed_profile(db_session)
    db_session.add_all([
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            claim_id=f"claim.hero.rank.{index:02d}",
            chapter_index=index,
            intra_chapter_seq=1,
            subject_ref="char.hero",
            predicate="rank",
            object_ref_or_value=f"rank-{index}",
            claim_layer="truth",
            claim_status="confirmed",
            authority_type="authoritative_structured",
            confidence=1.0,
            contract_version="world.contract.v1",
        )
        for index in range(1, 13)
    ])
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}/world-model/facts?offset=5&limit=4")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 12
    assert payload["offset"] == 5
    assert payload["limit"] == 4
    assert payload["has_more"] is True
    assert [item["claim_id"] for item in payload["claims"]] == [
        "claim.hero.rank.06",
        "claim.hero.rank.07",
        "claim.hero.rank.08",
        "claim.hero.rank.09",
    ]


def test_athena_timeline_endpoint_uses_current_world_event_fields(client, db_session):
    project, profile_version = _seed_profile(db_session)
    db_session.add_all([
        WorldTimelineAnchor(
            project_id=project.id,
            profile_version=profile_version.version,
            anchor_id="anchor.ch1.scene1",
            chapter_index=1,
            intra_chapter_seq=1,
            world_time_label="第一章第一幕",
            ordering_key="001:001",
            contract_version=profile_version.contract_version,
        ),
        WorldEvent(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            event_id="event.chapter.1.summary",
            idempotency_key="event.chapter.1.summary",
            timeline_anchor_id="anchor.ch1.scene1",
            chapter_index=1,
            intra_chapter_seq=1,
            event_type="event_occurred",
            primitive_payload={
                "event_ref": "event.chapter.1.summary",
                "title": "旧灯塔重新点亮",
                "summary": "主角第一次看见旧灯塔的信号。",
            },
            truth_layer="truth",
            disclosure_layer="public",
            contract_version=profile_version.contract_version,
        ),
    ])
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}/athena/state/timeline")

    assert response.status_code == 200
    payload = response.json()
    assert payload["anchors"][0]["label"] == "第一章第一幕"
    assert payload["events"][0]["description"] == "旧灯塔重新点亮：主角第一次看见旧灯塔的信号。"


def test_athena_timeline_endpoint_returns_latest_bounded_window(client, db_session):
    project, profile_version = _seed_profile(db_session)
    for index in range(1, 13):
        db_session.add(
            WorldTimelineAnchor(
                project_id=project.id,
                profile_version=profile_version.version,
                anchor_id=f"anchor.ch{index}.scene1",
                chapter_index=index,
                intra_chapter_seq=1,
                world_time_label=f"第{index}章",
                ordering_key=f"{index:03d}:001",
                contract_version=profile_version.contract_version,
            )
        )
        db_session.add(
            WorldEvent(
                project_id=project.id,
                project_profile_version_id=profile_version.id,
                profile_version=profile_version.version,
                event_id=f"event.chapter.{index}",
                idempotency_key=f"event.chapter.{index}",
                timeline_anchor_id=f"anchor.ch{index}.scene1",
                chapter_index=index,
                intra_chapter_seq=1,
                event_type="event_occurred",
                primitive_payload={"event_ref": f"chapter-{index}", "summary": f"第{index}章事件"},
                truth_layer="truth",
                disclosure_layer="public",
                contract_version=profile_version.contract_version,
            )
        )
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}/athena/state/timeline?latest=true&limit=4")

    assert response.status_code == 200
    payload = response.json()
    assert payload["events_total"] == 12
    assert payload["events_limit"] == 4
    assert payload["events_has_more"] is True
    assert [event["chapter_index"] for event in payload["events"]] == [9, 10, 11, 12]
    assert [anchor["chapter_index"] for anchor in payload["anchors"]] == [9, 10, 11, 12]


def test_athena_timeline_count_does_not_select_event_payload_json(client, db_session):
    project, profile_version = _seed_profile(db_session)
    for index in range(1, 6):
        db_session.add(
            WorldTimelineAnchor(
                project_id=project.id,
                profile_version=profile_version.version,
                anchor_id=f"anchor.chapter.{index}",
                chapter_index=index,
                intra_chapter_seq=1,
                ordering_key=f"{index:03d}:001",
                contract_version=profile_version.contract_version,
            )
        )
        db_session.add(
            WorldEvent(
                project_id=project.id,
                project_profile_version_id=profile_version.id,
                profile_version=profile_version.version,
                event_id=f"event.chapter.{index}",
                idempotency_key=f"event.chapter.{index}",
                timeline_anchor_id=f"anchor.chapter.{index}",
                chapter_index=index,
                intra_chapter_seq=1,
                event_type="event_occurred",
                primitive_payload={"summary": "长事件摘要" * 200},
                notes="事件备注" * 200,
                truth_layer="truth",
                disclosure_layer="public",
                contract_version=profile_version.contract_version,
            )
        )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/athena/state/timeline?latest=true&limit=2")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    event_count_statements = [
        statement
        for statement in statements
        if "count(" in statement and "world_events" in statement
    ]
    assert event_count_statements
    assert all("world_events.primitive_payload" not in statement for statement in event_count_statements)
    assert all("world_events.notes" not in statement for statement in event_count_statements)


def test_athena_timeline_rows_do_not_select_non_display_heavy_fields(client, db_session):
    project, profile_version = _seed_profile(db_session)
    for index in range(1, 4):
        db_session.add(
            WorldTimelineAnchor(
                project_id=project.id,
                profile_version=profile_version.version,
                anchor_id=f"anchor.heavy.{index}",
                chapter_index=index,
                intra_chapter_seq=1,
                world_time_label=f"第{index}章",
                normalized_tick_or_range="无关时间精度" * 100,
                precision="chapter",
                relative_to_anchor_ref="anchor.previous",
                ordering_key=f"{index:03d}:001",
                notes="锚点备注" * 200,
                contract_version=profile_version.contract_version,
            )
        )
        db_session.add(
            WorldEvent(
                project_id=project.id,
                project_profile_version_id=profile_version.id,
                profile_version=profile_version.version,
                event_id=f"event.heavy.{index}",
                idempotency_key=f"event.heavy.{index}",
                timeline_anchor_id=f"anchor.heavy.{index}",
                chapter_index=index,
                intra_chapter_seq=1,
                event_type="event_occurred",
                participant_refs=[f"char.{i}" for i in range(100)],
                location_refs=[f"loc.{i}" for i in range(100)],
                precondition_event_refs=[f"event.pre.{i}" for i in range(100)],
                caused_event_refs=[f"event.caused.{i}" for i in range(100)],
                primitive_payload={"summary": "长事件摘要" * 200},
                state_diffs=[{"field": "status", "value": i} for i in range(100)],
                evidence_refs=[f"chapter.{i:03d}" for i in range(100)],
                contract_version_refs=[f"world.contract.{i}" for i in range(20)],
                notes="事件备注" * 200,
                truth_layer="truth",
                disclosure_layer="public",
                contract_version=profile_version.contract_version,
            )
        )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/athena/state/timeline?limit=2")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    assert response.json()["events"][0]["description"].startswith("长事件摘要")
    anchor_selects = [
        statement
        for statement in statements
        if statement.startswith("select")
        and "from world_timeline_anchors" in statement
        and "count(" not in statement
    ]
    event_selects = [
        statement
        for statement in statements
        if statement.startswith("select")
        and "from world_events" in statement
        and "count(" not in statement
    ]
    assert anchor_selects
    assert event_selects
    assert all("world_timeline_anchors.normalized_tick_or_range" not in statement for statement in anchor_selects)
    assert all("world_timeline_anchors.precision" not in statement for statement in anchor_selects)
    assert all("world_timeline_anchors.relative_to_anchor_ref" not in statement for statement in anchor_selects)
    assert all("world_timeline_anchors.notes" not in statement for statement in anchor_selects)
    assert all("world_timeline_anchors.updated_at" not in statement for statement in anchor_selects)
    assert all("world_events.participant_refs" not in statement for statement in event_selects)
    assert all("world_events.location_refs" not in statement for statement in event_selects)
    assert all("world_events.precondition_event_refs" not in statement for statement in event_selects)
    assert all("world_events.caused_event_refs" not in statement for statement in event_selects)
    assert all("world_events.state_diffs" not in statement for statement in event_selects)
    assert all("world_events.evidence_refs" not in statement for statement in event_selects)
    assert all("world_events.contract_version_refs" not in statement for statement in event_selects)


def test_athena_timeline_forward_window_uses_stable_tie_breakers(client, db_session):
    project, profile_version = _seed_profile(db_session)
    for suffix in ["b", "a"]:
        db_session.add(
            WorldTimelineAnchor(
                project_id=project.id,
                profile_version=profile_version.version,
                anchor_id=f"anchor.same.{suffix}",
                chapter_index=1,
                intra_chapter_seq=1,
                ordering_key=f"001:001:{suffix}",
                contract_version=profile_version.contract_version,
            )
        )
        db_session.add(
            WorldEvent(
                project_id=project.id,
                project_profile_version_id=profile_version.id,
                profile_version=profile_version.version,
                event_id=f"event.same.{suffix}",
                idempotency_key=f"event.same.{suffix}",
                timeline_anchor_id=f"anchor.same.{suffix}",
                chapter_index=1,
                intra_chapter_seq=1,
                event_type="event_occurred",
                primitive_payload={"summary": suffix},
                truth_layer="truth",
                disclosure_layer="public",
                contract_version=profile_version.contract_version,
            )
        )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/athena/state/timeline?limit=2")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    payload = response.json()
    assert [anchor["anchor_id"] for anchor in payload["anchors"]] == ["anchor.same.a", "anchor.same.b"]
    assert [event["event_id"] for event in payload["events"]] == ["event.same.a", "event.same.b"]
    assert any(
        "order by world_timeline_anchors.chapter_index asc, world_timeline_anchors.intra_chapter_seq asc, world_timeline_anchors.anchor_id asc"
        in statement
        for statement in statements
    )
    assert any(
        "order by world_events.chapter_index asc, world_events.intra_chapter_seq asc, world_events.event_id asc"
        in statement
        for statement in statements
    )


def test_athena_ontology_endpoint_uses_relation_entity_refs(client, db_session):
    project, profile_version = _seed_profile(db_session)
    db_session.add_all([
        WorldCharacter(
            project_id=project.id,
            profile_version=profile_version.version,
            character_id="hero",
            canonical_id="char.hero",
            name="主角",
            role_type="character",
            identity_anchor="主角",
            contract_version=profile_version.contract_version,
        ),
        WorldRelation(
            project_id=project.id,
            profile_version=profile_version.version,
            relation_id="rel.hero.tower",
            source_entity_ref="char.hero",
            target_entity_ref="loc.tower",
            relation_type="located_at",
            directionality="directed",
            status="active",
            visibility_layer="public",
            contract_version=profile_version.contract_version,
        ),
    ])
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}/athena/ontology")

    assert response.status_code == 200
    assert response.json()["entities"]["characters"][0]["canonical_id"] == "char.hero"
    assert response.json()["relations"] == [
        {
            "id": db_session.query(WorldRelation).one().id,
            "source_ref": "char.hero",
            "target_ref": "loc.tower",
            "relation_type": "located_at",
        }
    ]


def test_athena_ontology_endpoint_returns_bounded_world_model_windows(client, db_session):
    project, profile_version = _seed_profile(db_session)
    rows = []
    for index in range(1, 13):
        rows.append(
            WorldCharacter(
                project_id=project.id,
                profile_version=profile_version.version,
                character_id=f"character-{index:02d}",
                canonical_id=f"char.{index:02d}",
                name=f"角色{index:02d}",
                role_type="supporting",
                identity_anchor=f"角色{index:02d}",
                contract_version=profile_version.contract_version,
            )
        )
    for index in range(1, 8):
        rows.append(
            WorldRelation(
                project_id=project.id,
                profile_version=profile_version.version,
                relation_id=f"rel.{index:02d}",
                source_entity_ref=f"char.{index:02d}",
                target_entity_ref=f"char.{index + 1:02d}",
                relation_type="knows",
                directionality="directed",
                status="active",
                visibility_layer="public",
                contract_version=profile_version.contract_version,
            )
        )
    for index in range(1, 5):
        rows.append(
            WorldRule(
                project_id=project.id,
                profile_version=profile_version.version,
                rule_id=f"rule.{index:02d}",
                canonical_id=f"rule.{index:02d}",
                name=f"规则{index:02d}",
                rule_type="world_law",
                statement=f"第{index:02d}条规则",
                contract_version=profile_version.contract_version,
            )
        )
    db_session.add_all(rows)
    db_session.commit()

    response = client.get(
        f"/api/v1/projects/{project.id}/athena/ontology"
        "?entity_limit=5&relation_limit=3&rule_limit=2"
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["canonical_id"] for item in payload["entities"]["characters"]] == [
        "char.01",
        "char.02",
        "char.03",
        "char.04",
        "char.05",
    ]
    assert [item["source_ref"] for item in payload["relations"]] == ["char.01", "char.02", "char.03"]
    assert [item["rule_id"] for item in payload["rules"]] == ["rule.01", "rule.02"]
    assert payload["pagination"]["entities"]["characters"] == {
        "total": 12,
        "offset": 0,
        "limit": 5,
        "has_more": True,
    }
    assert payload["pagination"]["relations"] == {
        "total": 7,
        "offset": 0,
        "limit": 3,
        "has_more": True,
    }
    assert payload["pagination"]["rules"] == {
        "total": 4,
        "offset": 0,
        "limit": 2,
        "has_more": True,
    }


def test_legacy_athena_ontology_auxiliary_endpoints_are_bounded(client, db_session):
    project, profile_version = _seed_profile(db_session)
    rows = []
    for index in range(1, 13):
        rows.append(
            WorldCharacter(
                project_id=project.id,
                profile_version=profile_version.version,
                character_id=f"character-{index:02d}",
                canonical_id=f"char.{index:02d}",
                name=f"角色{index:02d}",
                role_type="supporting",
                identity_anchor=f"角色{index:02d}",
                contract_version=profile_version.contract_version,
            )
        )
    for index in range(1, 6):
        rows.append(
            WorldRule(
                project_id=project.id,
                profile_version=profile_version.version,
                rule_id=f"rule.{index:02d}",
                canonical_id=f"rule.{index:02d}",
                name=f"规则{index:02d}",
                rule_type="world_law",
                statement=f"第{index:02d}条规则",
                contract_version=profile_version.contract_version,
            )
        )
    db_session.add_all(rows)
    db_session.commit()

    entities_response = client.get(
        f"/api/v1/projects/{project.id}/athena/ontology/entities"
        "?entity_offset=5&entity_limit=4"
    )
    rules_response = client.get(
        f"/api/v1/projects/{project.id}/athena/ontology/rules"
        "?offset=2&limit=2"
    )

    assert entities_response.status_code == 200
    entities_payload = entities_response.json()
    assert [item["canonical_id"] for item in entities_payload["characters"]] == [
        "char.06",
        "char.07",
        "char.08",
        "char.09",
    ]
    assert entities_payload["pagination"]["entities"]["characters"] == {
        "total": 12,
        "offset": 5,
        "limit": 4,
        "has_more": True,
    }
    assert rules_response.status_code == 200
    assert [item["rule_id"] for item in rules_response.json()] == ["rule.03", "rule.04"]


def test_athena_ontology_counts_do_not_select_large_json_columns(client, db_session):
    project, profile_version = _seed_profile(db_session)
    db_session.add_all([
        WorldCharacter(
            project_id=project.id,
            profile_version=profile_version.version,
            character_id="character-heavy",
            canonical_id="char.heavy",
            name="重载角色",
            aliases=["别名"] * 50,
            role_type="supporting",
            identity_anchor="重载角色",
            core_traits=["性格"] * 100,
            hidden_truths=["秘密"] * 100,
            contract_version=profile_version.contract_version,
        ),
        WorldRule(
            project_id=project.id,
            profile_version=profile_version.version,
            rule_id="rule.heavy",
            canonical_id="rule.heavy",
            name="重载规则",
            rule_type="world_law",
            statement="规则正文",
            constraints=["约束"] * 100,
            exceptions=["例外"] * 100,
            contract_version=profile_version.contract_version,
        ),
    ])
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/athena/ontology?entity_limit=1&rule_limit=1")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    count_statements = [
        statement
        for statement in statements
        if "count(" in statement and ("world_characters" in statement or "world_rules" in statement)
    ]
    assert count_statements
    assert all("world_characters.core_traits" not in statement for statement in count_statements)
    assert all("world_characters.hidden_truths" not in statement for statement in count_statements)
    assert all("world_rules.constraints" not in statement for statement in count_statements)
    assert all("world_rules.exceptions" not in statement for statement in count_statements)


def test_athena_ontology_with_profile_does_not_select_setup_json(client, db_session):
    project, profile_version = _seed_profile(db_session)
    db_session.add_all([
        Setup(
            project_id=project.id,
            status="generated",
            characters=[{"name": f"角色{index}", "description": "长角色设定" * 100} for index in range(100)],
            world_building={"rules": "长世界规则" * 1000},
            core_concept={"summary": "长核心概念" * 1000},
        ),
        WorldCharacter(
            project_id=project.id,
            profile_version=profile_version.version,
            character_id="character-profile",
            canonical_id="char.profile",
            name="已入库角色",
            role_type="supporting",
            identity_anchor="已入库角色",
            contract_version=profile_version.contract_version,
        ),
    ])
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/athena/ontology?entity_limit=1")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile_version"] == profile_version.version
    assert payload["setup_summary"] is None
    assert [item["canonical_id"] for item in payload["entities"]["characters"]] == ["char.profile"]
    setup_selects = [statement for statement in statements if " from setups" in statement]
    assert setup_selects == []


def test_athena_ontology_current_profile_lookup_skips_profile_payload(client, db_session):
    project = Project(name="Profile Payload Projection")
    genre_profile = GenreProfile(
        canonical_id="profile-payload-projection",
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
        profile_payload={"large_contract_notes": "长 profile payload" * 1000},
    )
    db_session.add(profile_version)
    db_session.flush()
    db_session.add(
        WorldCharacter(
            project_id=project.id,
            profile_version=profile_version.version,
            character_id="character-profile-payload",
            canonical_id="char.profile_payload",
            name="Profile Payload 角色",
            role_type="supporting",
            identity_anchor="Profile Payload 角色",
            contract_version=profile_version.contract_version,
        )
    )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/athena/ontology?entity_limit=1")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    assert response.json()["profile_version"] == 1
    profile_selects = [
        statement.split(" from project_profile_versions", 1)[0]
        for statement in statements
        if " from project_profile_versions" in statement
    ]
    assert profile_selects
    assert all("profile_payload" not in select_clause for select_clause in profile_selects)


def test_world_fact_list_current_profile_lookup_skips_profile_payload(client, db_session):
    project = Project(name="World Facts Profile Projection")
    genre_profile = GenreProfile(
        canonical_id="facts-profile-payload-projection",
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
        profile_payload={"large_contract_notes": "长 profile payload" * 1000},
    )
    db_session.add(profile_version)
    db_session.flush()
    db_session.add(
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            claim_id="claim.profile.payload",
            subject_ref="char.profile_payload",
            predicate="status",
            object_ref_or_value="active",
            claim_layer="truth",
            claim_status="confirmed",
            authority_type="authoritative_structured",
            confidence=0.8,
            contract_version=profile_version.contract_version,
        )
    )
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/world-model/facts?limit=1")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    assert response.json()["claims"][0]["claim_id"] == "claim.profile.payload"
    profile_selects = [
        statement.split(" from project_profile_versions", 1)[0]
        for statement in statements
        if " from project_profile_versions" in statement
    ]
    assert profile_selects
    assert all("profile_payload" not in select_clause for select_clause in profile_selects)


def test_subject_knowledge_persists_belief_claims_approved_from_proposals(client, db_session):
    project, profile_version = _seed_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Subject belief candidates",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=ProposalCandidateFactCreate(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            contract_version=profile_version.contract_version,
            claim_id="claim.detective.hero.rank.belief",
            chapter_index=1,
            intra_chapter_seq=1,
            subject_ref="char.hero",
            predicate="rank",
            object_ref_or_value="smuggler",
            claim_layer="belief",
            perspective_ref="char.detective",
            disclosed_to_refs=[],
            authority_type="authoritative_structured",
            confidence=0.85,
            evidence_refs=["chapter.01"],
        ),
    )
    cached_empty_subject_response = client.get(
        f"/api/v1/projects/{project.id}/world-model/subject-knowledge?subject_ref=char.detective"
    )

    approve_response = client.post(
        f"/api/v1/projects/{project.id}/world-model/proposal-items/{item.id}/review",
        json={
            "reviewer_ref": "editor.alpha",
            "action": "approve",
            "reason": "侦探视角确认",
            "evidence_refs": ["chapter.01"],
            "edited_fields": {},
        },
    )
    truth_response = client.get(f"/api/v1/projects/{project.id}/world-model")
    subject_response = client.get(
        f"/api/v1/projects/{project.id}/world-model/subject-knowledge?subject_ref=char.detective"
    )

    assert cached_empty_subject_response.status_code == 200
    assert cached_empty_subject_response.json()["projection"]["facts"] == {}
    assert approve_response.status_code == 200
    assert truth_response.status_code == 200
    assert truth_response.json()["projection"]["facts"] == {}
    assert subject_response.status_code == 200
    assert subject_response.json()["projection"]["facts"]["char.hero"]["rank"] == "smuggler"


def test_proposal_conflicts_use_current_truth_projection_not_expired_history(client, db_session):
    project, profile_version = _seed_profile(db_session)
    db_session.add_all([
        WorldTimelineAnchor(
            project_id=project.id,
            profile_version=profile_version.version,
            anchor_id="anchor.ch1",
            chapter_index=1,
            intra_chapter_seq=1,
            ordering_key="001:001",
            contract_version=profile_version.contract_version,
        ),
        WorldTimelineAnchor(
            project_id=project.id,
            profile_version=profile_version.version,
            anchor_id="anchor.ch2",
            chapter_index=2,
            intra_chapter_seq=1,
            ordering_key="002:001",
            contract_version=profile_version.contract_version,
        ),
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            claim_id="claim.hero.rank.old",
            chapter_index=1,
            intra_chapter_seq=1,
            subject_ref="char.hero",
            predicate="rank",
            object_ref_or_value="lieutenant",
            claim_layer="truth",
            claim_status="confirmed",
            valid_from_anchor_id="anchor.ch1",
            valid_to_anchor_id="anchor.ch2",
            authority_type="authoritative_structured",
            confidence=1.0,
            contract_version=profile_version.contract_version,
        ),
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            claim_id="claim.hero.rank.current",
            chapter_index=2,
            intra_chapter_seq=1,
            subject_ref="char.hero",
            predicate="rank",
            object_ref_or_value="captain",
            claim_layer="truth",
            claim_status="confirmed",
            valid_from_anchor_id="anchor.ch2",
            authority_type="authoritative_structured",
            confidence=1.0,
            contract_version=profile_version.contract_version,
        ),
    ])
    db_session.commit()
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Current truth candidate",
    )
    write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rank.candidate",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ),
    )

    response = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-bundles/{bundle.id}")

    assert response.status_code == 200
    assert response.json()["conflicts"] == []


def test_proposal_detail_does_not_conflict_presence_count_across_chapters(client, db_session):
    project, profile_version = _seed_profile(db_session)
    db_session.add(
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            claim_id="claim.chapter.1.char.hero.presence_count",
            chapter_index=1,
            intra_chapter_seq=0,
            subject_ref="char.hero",
            predicate="presence_count",
            object_ref_or_value={"count": 51, "chapter_index": 1},
            claim_layer="truth",
            claim_status="confirmed",
            authority_type="derived",
            confidence=0.85,
            contract_version=profile_version.contract_version,
        )
    )
    db_session.commit()
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Chapter 20 presence candidate",
    )
    write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.chapter.20.char.hero.presence_count",
            subject_ref="char.hero",
            predicate="presence_count",
            chapter_index=20,
            value={"count": 48, "chapter_index": 20},
        ),
    )
    calculate_bundle_impact_scope(db=db_session, bundle_id=bundle.id)

    response = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-bundles/{bundle.id}")

    assert response.status_code == 200
    assert response.json()["conflicts"] == []


def test_proposal_detail_skips_full_projection_for_chapter_scoped_conflicts(client, db_session, monkeypatch):
    project, profile_version = _seed_profile(db_session)
    db_session.add(
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            claim_id="claim.chapter.1.char.hero.presence_count",
            chapter_index=1,
            intra_chapter_seq=0,
            subject_ref="char.hero",
            predicate="presence_count",
            object_ref_or_value={"count": 51, "chapter_index": 1},
            claim_layer="truth",
            claim_status="confirmed",
            authority_type="derived",
            confidence=0.85,
            contract_version=profile_version.contract_version,
        )
    )
    db_session.commit()
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Chapter 20 presence candidate",
    )
    write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.chapter.20.char.hero.presence_count",
            subject_ref="char.hero",
            predicate="presence_count",
            chapter_index=20,
            value={"count": 48, "chapter_index": 20},
        ),
    )

    projection_calls = 0

    def count_full_projection_calls(**_kwargs):
        nonlocal projection_calls
        projection_calls += 1
        return SimpleNamespace(projection=SimpleNamespace(facts={}))

    monkeypatch.setattr("app.api.world_model.build_world_projection_overview", count_full_projection_calls)

    response = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-bundles/{bundle.id}")

    assert response.status_code == 200
    assert response.json()["conflicts"] == []
    assert projection_calls == 0


def test_proposal_detail_skips_full_projection_for_targeted_truth_conflicts(client, db_session, monkeypatch):
    project, profile_version = _seed_profile(db_session)
    db_session.add(
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            claim_id="claim.hero.rank.current",
            chapter_index=12,
            intra_chapter_seq=1,
            subject_ref="char.hero",
            predicate="rank",
            object_ref_or_value="captain",
            claim_layer="truth",
            claim_status="confirmed",
            authority_type="authoritative_structured",
            confidence=1.0,
            notes="长事实备注" * 300,
            evidence_refs=["chapter.12"] * 100,
            contract_version=profile_version.contract_version,
        )
    )
    db_session.commit()
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Targeted truth conflict candidate",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rank.pending",
            subject_ref="char.hero",
            predicate="rank",
            value="admiral",
        ),
    )

    def fail_full_projection(**_kwargs):
        raise AssertionError("proposal detail should not build the full truth projection")

    monkeypatch.setattr("app.api.world_model.build_world_projection_overview", fail_full_projection)

    response = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-bundles/{bundle.id}")

    assert response.status_code == 200
    conflicts = response.json()["conflicts"]
    assert conflicts == [
        {
            "item_id": item.id,
            "conflict_type": "truth_conflict",
            "detail": "与现有真相冲突：char.hero.rank = captain",
            "existing_claim_id": db_session.query(WorldFactClaim.id).filter_by(claim_id="claim.hero.rank.current").scalar(),
        }
    ]


def test_proposal_detail_conflicts_only_include_actionable_items(client, db_session):
    project, profile_version = _seed_profile(db_session)
    for index, value in enumerate(["captain", "lieutenant", "commander"], start=1):
        db_session.add(
            WorldFactClaim(
                project_id=project.id,
                project_profile_version_id=profile_version.id,
                profile_version=profile_version.version,
                claim_id=f"claim.hero.rank.existing.{index}",
                chapter_index=index,
                intra_chapter_seq=1,
                subject_ref="char.hero",
                predicate="rank",
                object_ref_or_value=value,
                claim_layer="truth",
                claim_status="confirmed",
                authority_type="authoritative_structured",
                confidence=1.0,
                contract_version=profile_version.contract_version,
            )
        )
    db_session.commit()
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Terminal conflict candidate",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rank.terminal-candidate",
            subject_ref="char.hero",
            predicate="rank",
            value="admiral",
        ),
    )
    calculate_bundle_impact_scope(db=db_session, bundle_id=bundle.id)
    review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="mark_uncertain",
        reason="证据冲突，暂不采纳",
        evidence_refs=["chapter.03"],
    )

    response = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-bundles/{bundle.id}")

    assert response.status_code == 200
    assert response.json()["conflicts"] == []


def test_proposal_detail_returns_only_latest_impact_snapshot(client, db_session):
    project, profile_version = _seed_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Repeated impact snapshots",
    )
    write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rank.pending",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ),
    )
    for _index in range(3):
        calculate_bundle_impact_scope(db=db_session, bundle_id=bundle.id)

    response = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-bundles/{bundle.id}")

    assert response.status_code == 200
    assert len(response.json()["impact_snapshots"]) == 1


def test_proposal_detail_paginates_large_item_lists(client, db_session):
    project, profile_version = _seed_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Large proposal bundle",
    )
    for index in range(150):
        write_candidate_fact(
            db=db_session,
            bundle_id=bundle.id,
            created_by="writer.alpha",
            candidate=_candidate_payload(
                claim_id=f"claim.hero.rank.{index + 1}",
                subject_ref=f"char.hero.{index + 1}",
                predicate="rank",
                value=f"rank-{index + 1}",
            ),
        )
    calculate_bundle_impact_scope(db=db_session, bundle_id=bundle.id)

    first_page = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-bundles/{bundle.id}")
    second_page = client.get(
        f"/api/v1/projects/{project.id}/world-model/proposal-bundles/{bundle.id}?item_offset=100&item_limit=25"
    )

    assert first_page.status_code == 200
    assert len(first_page.json()["items"]) == 100
    assert first_page.json()["items_total"] == 150
    assert first_page.json()["items_offset"] == 0
    assert first_page.json()["items_limit"] == 100

    assert second_page.status_code == 200
    assert len(second_page.json()["items"]) == 25
    assert second_page.json()["items_total"] == 150
    assert second_page.json()["items_offset"] == 100
    assert second_page.json()["items_limit"] == 25


def test_world_model_overview_returns_nulls_when_project_has_no_world_data(client):
    create_response = client.post("/api/v1/projects", json={"name": "No World Data"})
    project_id = create_response.json()["id"]

    response = client.get(f"/api/v1/projects/{project_id}/world-model")

    assert response.status_code == 200
    assert response.json() == {
        "project_profile": None,
        "projection": None,
    }


def test_world_model_dashboard_returns_operational_counts_and_next_action(client, db_session):
    project, profile_version = _seed_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Dashboard candidates",
    )
    write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rank.dashboard",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ),
    )

    response = client.get(f"/api/v1/projects/{project.id}/world-model/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_profile"]["id"] == profile_version.id
    assert payload["metrics"]["pending_bundle_count"] == 1
    assert payload["metrics"]["pending_item_count"] == 1
    assert payload["next_action"]["action"] == "review_proposals"


def test_world_model_dashboard_pending_counts_do_not_select_heavy_item_fields(client, db_session):
    project, profile_version = _seed_profile(db_session)
    bundles = [
        create_bundle(
            db=db_session,
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            created_by="writer.alpha",
            title=f"Dashboard heavy bundle {index}",
        )
        for index in range(1, 3)
    ]
    for index in range(1, 4):
        write_candidate_fact(
            db=db_session,
            bundle_id=bundles[index % 2].id,
            created_by="writer.alpha",
            candidate=ProposalCandidateFactCreate(
                project_id=project.id,
                project_profile_version_id=profile_version.id,
                profile_version=profile_version.version,
                contract_version=profile_version.contract_version,
                claim_id=f"claim.dashboard.heavy.{index}",
                chapter_index=index,
                subject_ref=f"char.dashboard.heavy.{index}",
                predicate="memory_trace",
                object_ref_or_value={"fragments": ["记忆碎片"] * 200},
                claim_layer="truth",
                disclosed_to_refs=[f"char.reader.{i}" for i in range(100)],
                authority_type="authoritative_structured",
                confidence=0.9,
                evidence_refs=[f"chapter.{i:03d}" for i in range(100)],
                notes="长审阅备注" * 300,
            ),
        )
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/world-model/dashboard")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    payload = response.json()
    assert payload["metrics"]["pending_bundle_count"] == 2
    assert payload["metrics"]["pending_item_count"] == 3
    item_count_statements = [
        statement
        for statement in statements
        if "count(" in statement and "world_proposal_items" in statement
    ]
    assert item_count_statements
    assert all("world_proposal_items.object_ref_or_value" not in statement for statement in item_count_statements)
    assert all("world_proposal_items.disclosed_to_refs" not in statement for statement in item_count_statements)
    assert all("world_proposal_items.evidence_refs" not in statement for statement in item_count_statements)
    assert all("world_proposal_items.notes" not in statement for statement in item_count_statements)


def test_world_model_dashboard_counts_only_bundles_with_actionable_items(client, db_session):
    project, profile_version = _seed_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Closed partial bundle",
    )
    approved_item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rank.closed-partial",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ),
    )
    rejected_item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.home.closed-partial",
            subject_ref="char.hero",
            predicate="home",
            value="dock-7",
        ),
    )
    review_proposal_item(
        db=db_session,
        proposal_item_id=approved_item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="确认角色军衔",
        evidence_refs=["chapter.01"],
    )
    review_proposal_item(
        db=db_session,
        proposal_item_id=rejected_item.id,
        reviewer_ref="editor.alpha",
        action="reject",
        reason="地点证据不足",
        evidence_refs=["chapter.01"],
    )

    response = client.get(f"/api/v1/projects/{project.id}/world-model/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["metrics"]["pending_bundle_count"] == 0
    assert payload["metrics"]["pending_item_count"] == 0
    assert payload["next_action"]["action"] == "inspect_projection"


def test_world_model_dashboard_uses_aggregate_metrics_without_loading_projection_rows(client, db_session):
    project, profile_version = _seed_profile(db_session)
    facts = [
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            claim_id=f"claim.dashboard.metric.{index}",
            chapter_index=index,
            intra_chapter_seq=1,
            subject_ref=f"char.dashboard.{index}",
            predicate="status",
            object_ref_or_value="active",
            claim_layer="truth",
            claim_status="confirmed",
            authority_type="authoritative_structured",
            confidence=0.95,
            contract_version="world.contract.v1",
            evidence_refs=[f"chapter.{index:03d}"],
        )
        for index in range(1, 251)
    ]
    db_session.add_all(facts)
    db_session.commit()

    statements: list[str] = []

    def capture_statement(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        statements.append(" ".join(statement.lower().split()))

    bind = db_session.get_bind()
    event.listen(bind, "before_cursor_execute", capture_statement)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/world-model/dashboard")
    finally:
        event.remove(bind, "before_cursor_execute", capture_statement)

    assert response.status_code == 200
    payload = response.json()
    assert payload["metrics"]["fact_count"] == 250
    assert payload["next_action"]["action"] == "inspect_projection"
    full_fact_selects = [
        statement
        for statement in statements
        if "select world_fact_claims.id" in statement and "from world_fact_claims" in statement
    ]
    assert full_fact_selects == []


def test_world_model_snapshot_validates_chapter_index_before_empty_projection(client, db_session):
    project = Project(name="World Snapshot Boundary")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="第一章",
            content="雾港城入夜。",
        )
    )
    db_session.commit()

    valid_response = client.get(f"/api/v1/projects/{project.id}/world-model/snapshot?chapter_index=1")
    negative_response = client.get(f"/api/v1/projects/{project.id}/world-model/snapshot?chapter_index=-1")
    zero_response = client.get(f"/api/v1/projects/{project.id}/world-model/snapshot?chapter_index=0")
    missing_response = client.get(f"/api/v1/projects/{project.id}/world-model/snapshot?chapter_index=999")
    athena_negative_response = client.get(f"/api/v1/projects/{project.id}/athena/state/snapshot?chapter_index=-1")
    athena_zero_response = client.get(f"/api/v1/projects/{project.id}/athena/state/snapshot?chapter_index=0")

    assert valid_response.status_code == 200
    assert valid_response.json() == {"project_profile": None, "projection": None}
    assert negative_response.status_code == 422
    assert zero_response.status_code == 422
    assert missing_response.status_code == 404
    assert athena_negative_response.status_code == 422
    assert athena_zero_response.status_code == 422


def test_world_model_snapshot_chapter_existence_check_skips_content(client, db_session):
    project = Project(name="World Snapshot Existence Projection")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="第一章",
            content="很长的章节正文" * 1000,
        )
    )
    db_session.commit()
    statements: list[str] = []

    def capture_statement(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        statements.append(" ".join(statement.lower().split()))

    bind = db_session.get_bind()
    event.listen(bind, "before_cursor_execute", capture_statement)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/world-model/snapshot?chapter_index=1")
    finally:
        event.remove(bind, "before_cursor_execute", capture_statement)

    assert response.status_code == 200
    chapter_selects = [
        statement.split(" from chapter_contents", 1)[0]
        for statement in statements
        if " from chapter_contents" in statement
    ]
    assert chapter_selects
    assert all("chapter_contents.content" not in select_clause for select_clause in chapter_selects)


def test_athena_facade_routes_remain_compatible_after_router_split(client, db_session):
    project = Project(name="Athena Facade Routes")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add(
        Setup(
            project_id=project.id,
            status="generated",
            characters=[{"name": "林舟"}],
            world_building={"rules": "旧灯塔熄灭时，亡者不能被直接召回。"},
            core_concept={"theme": "记忆与真相"},
        )
    )
    db_session.commit()

    checks = [
        client.get(f"/api/v1/projects/{project.id}/athena/optimization"),
        client.get(f"/api/v1/projects/{project.id}/athena/ontology"),
        client.get(f"/api/v1/projects/{project.id}/athena/ontology/import-setup/preview"),
        client.get(f"/api/v1/projects/{project.id}/athena/state"),
        client.get(f"/api/v1/projects/{project.id}/athena/evolution/proposals"),
        client.get(f"/api/v1/projects/{project.id}/athena/retrieval/diagnostics"),
        client.get(f"/api/v1/projects/{project.id}/athena/dialog/messages"),
        client.get(f"/api/v1/projects/{project.id}/athena/context/chapter/1"),
    ]

    assert [response.status_code for response in checks] == [200] * len(checks)
    assert checks[2].json()["status"] == "preview"
    assert "rules" in checks[1].json()


def test_world_model_proposal_bundle_count_does_not_select_summary(client, db_session):
    project, profile_version = _seed_profile(db_session)
    for index in range(1, 4):
        create_bundle(
            db=db_session,
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            created_by="writer.alpha",
            title=f"Heavy bundle {index}",
            summary="长提案摘要" * 300,
        )
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-bundles?limit=1")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    bundle_count_statements = [
        statement
        for statement in statements
        if "count(" in statement and "world_proposal_bundles" in statement
    ]
    assert bundle_count_statements
    assert all("world_proposal_bundles.summary" not in statement for statement in bundle_count_statements)


def test_list_world_proposal_bundles_uses_id_tie_breaker_for_stable_pages(client, db_session):
    project, profile_version = _seed_profile(db_session)
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    db_session.add_all([
        WorldProposalBundle(
            id=f"bundle-{index:02d}",
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            created_by="writer.alpha",
            title=f"Bundle {index:02d}",
            created_at=created_at,
            updated_at=created_at,
        )
        for index in range(1, 7)
    ])
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-bundles?offset=0&limit=3")

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["items"]] == ["bundle-06", "bundle-05", "bundle-04"]


def test_world_model_bundle_detail_item_count_does_not_select_heavy_item_fields(client, db_session):
    project, profile_version = _seed_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Heavy proposal items",
    )
    for index in range(1, 4):
        write_candidate_fact(
            db=db_session,
            bundle_id=bundle.id,
            created_by="writer.alpha",
            candidate=ProposalCandidateFactCreate(
                project_id=project.id,
                project_profile_version_id=profile_version.id,
                profile_version=profile_version.version,
                contract_version=profile_version.contract_version,
                claim_id=f"claim.heavy.{index}",
                chapter_index=index,
                subject_ref=f"char.heavy.{index}",
                predicate="memory_trace",
                object_ref_or_value={"fragments": ["记忆碎片"] * 200},
                claim_layer="truth",
                disclosed_to_refs=[f"char.reader.{i}" for i in range(100)],
                authority_type="authoritative_structured",
                confidence=0.9,
                evidence_refs=[f"chapter.{i:03d}" for i in range(100)],
                notes="长审阅备注" * 300,
            ),
        )
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-bundles/{bundle.id}?item_limit=1")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    item_count_statements = [
        statement
        for statement in statements
        if "count(" in statement and "world_proposal_items" in statement
    ]
    assert item_count_statements
    assert all("world_proposal_items.object_ref_or_value" not in statement for statement in item_count_statements)
    assert all("world_proposal_items.disclosed_to_refs" not in statement for statement in item_count_statements)
    assert all("world_proposal_items.evidence_refs" not in statement for statement in item_count_statements)
    assert all("world_proposal_items.notes" not in statement for statement in item_count_statements)


def test_find_current_truth_claim_id_projects_only_id_and_value(db_session):
    project, profile = _seed_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        created_by="athena",
        title="Truth conflict projection",
    )
    claims = [
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            claim_id=f"claim.hero.rank.{index}",
            chapter_index=index,
            intra_chapter_seq=0,
            subject_ref="char.hero",
            predicate="rank",
            object_ref_or_value="target" if index == 20 else f"rank-{index}",
            claim_layer="truth",
            claim_status="confirmed",
            evidence_refs=[f"chapter.{index}"],
            authority_type="authoritative_structured",
            confidence=0.9,
            notes="heavy truth notes" * 500,
            contract_version="world.contract.v1",
        )
        for index in range(1, 21)
    ]
    db_session.add_all(claims)
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        claim_id = world_model_api._find_current_truth_claim_id(
            db=db_session,
            project_id=project.id,
            bundle=bundle,
            subject_ref="char.hero",
            predicate="rank",
            value="target",
        )
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert claim_id == claims[-1].id
    fact_select_clauses = [
        statement.split("from world_fact_claims", 1)[0]
        for statement in statements
        if "from world_fact_claims" in statement
    ]
    assert fact_select_clauses
    assert all("world_fact_claims.id" in clause for clause in fact_select_clauses)
    assert all("world_fact_claims.object_ref_or_value" in clause for clause in fact_select_clauses)
    assert all("world_fact_claims.notes" not in clause for clause in fact_select_clauses)
    assert all("world_fact_claims.evidence_refs" not in clause for clause in fact_select_clauses)


def test_world_model_bundle_endpoints_support_review_split_and_rollback(client, db_session):
    project, profile_version = _seed_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Dock-7 candidates",
    )
    first_item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rank.pending",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ),
    )
    second_item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.cover.pending",
            subject_ref="char.hero",
            predicate="cover",
            value="archivist",
        ),
    )
    calculate_bundle_impact_scope(db=db_session, bundle_id=bundle.id)

    list_response = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-bundles")
    assert list_response.status_code == 200
    listed_bundles = list_response.json()
    assert [item["id"] for item in listed_bundles["items"]] == [bundle.id]

    detail_response = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-bundles/{bundle.id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["bundle"]["id"] == bundle.id
    assert len(detail_payload["items"]) == 2
    assert len(detail_payload["impact_snapshots"]) == 1

    approve_response = client.post(
        f"/api/v1/projects/{project.id}/world-model/proposal-items/{first_item.id}/review",
        json={
            "reviewer_ref": "editor.alpha",
            "action": "approve_with_edits",
            "reason": "确认事实，但补充证据备注",
            "evidence_refs": ["chapter.12"],
            "edited_fields": {"notes": "来自 Dock-7 审讯记录"},
        },
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["review_action"] == "approve_with_edits"

    reject_response = client.post(
        f"/api/v1/projects/{project.id}/world-model/proposal-items/{second_item.id}/review",
        json={
            "reviewer_ref": "editor.alpha",
            "action": "mark_uncertain",
            "reason": "掩护身份证据不足",
            "evidence_refs": ["chapter.13"],
            "edited_fields": {},
        },
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["review_action"] == "mark_uncertain"

    bundle_detail_after_reviews = client.get(
        f"/api/v1/projects/{project.id}/world-model/proposal-bundles/{bundle.id}"
    )
    assert bundle_detail_after_reviews.status_code == 200
    reviewed_payload = bundle_detail_after_reviews.json()
    assert reviewed_payload["bundle"]["bundle_status"] == "partially_approved"
    assert {item["item_status"] for item in reviewed_payload["items"]} == {
        "approved_with_edits",
        "uncertain",
    }
    approval_review = next(
        review
        for review in reviewed_payload["reviews"]
        if review["proposal_item_id"] == first_item.id and review["review_action"] == "approve_with_edits"
    )

    split_bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.beta",
        title="Split candidates",
    )
    split_item = write_candidate_fact(
        db=db_session,
        bundle_id=split_bundle.id,
        created_by="writer.beta",
        candidate=_candidate_payload(
            claim_id="claim.loc.safehouse.status",
            subject_ref="loc.safehouse",
            predicate="status",
            value="compromised",
        ),
    )

    split_response = client.post(
        f"/api/v1/projects/{project.id}/world-model/proposal-bundles/{split_bundle.id}/split",
        json={
            "reviewer_ref": "editor.split",
            "reason": "拆到单独 bundle 继续审",
            "evidence_refs": ["chapter.14"],
            "item_ids": [split_item.id],
        },
    )
    assert split_response.status_code == 200
    split_payload = split_response.json()
    assert split_payload["bundle"]["parent_bundle_id"] == split_bundle.id
    assert len(split_payload["items"]) == 1

    rollback_response = client.post(
        f"/api/v1/projects/{project.id}/world-model/reviews/{approval_review['id']}/rollback",
        json={
            "reviewer_ref": "editor.alpha",
            "reason": "新证据推翻旧结论",
            "evidence_refs": ["chapter.15"],
        },
    )
    assert rollback_response.status_code == 200
    assert rollback_response.json()["review_action"] == "rollback"

    bundle_detail_after_rollback = client.get(
        f"/api/v1/projects/{project.id}/world-model/proposal-bundles/{bundle.id}"
    )
    assert bundle_detail_after_rollback.status_code == 200
    rollback_payload = bundle_detail_after_rollback.json()
    rolled_back_item = next(item for item in rollback_payload["items"] if item["id"] == first_item.id)
    assert rolled_back_item["item_status"] == "rolled_back"


def test_world_model_proposal_review_queue_clusters_low_risk_and_prioritizes_high_risk(client, db_session):
    project, profile_version = _seed_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Review queue candidates",
    )
    low_first = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.presence.queue",
            subject_ref="char.hero",
            predicate="presence_count",
            value={"chapter_index": 1, "mention_count": 3},
            chapter_index=1,
        ),
    )
    low_second = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.sidekick.presence.queue",
            subject_ref="char.sidekick",
            predicate="presence_count",
            value={"chapter_index": 1, "mention_count": 1},
            chapter_index=1,
        ),
    )
    high_item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.status.queue",
            subject_ref="char.hero",
            predicate="status",
            value="失踪",
            chapter_index=1,
        ),
    )

    response = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-review-queue")
    athena_response = client.get(f"/api/v1/projects/{project.id}/athena/evolution/proposal-review-queue")

    assert response.status_code == 200
    assert athena_response.status_code == 200
    payload = response.json()
    assert payload == athena_response.json()
    assert payload["total_items"] == 3
    assert payload["clusters"][0]["risk_level"] == "high"
    assert payload["clusters"][0]["review_mode"] == "individual"
    assert payload["clusters"][0]["item_ids"] == [high_item.id]
    low_cluster = next(cluster for cluster in payload["clusters"] if cluster["risk_level"] == "low")
    assert low_cluster["predicate"] == "presence_count"
    assert low_cluster["review_mode"] == "batch"
    assert low_cluster["candidate_count"] == 2
    assert set(low_cluster["item_ids"]) == {low_first.id, low_second.id}
    assert low_cluster["chapter_range"] == {"start": 1, "end": 1}
    assert {
        item.item_status
        for item in db_session.query(WorldProposalItem).filter(WorldProposalItem.bundle_id == bundle.id).all()
    } == {"pending"}


def test_world_model_proposal_review_queue_limits_large_backlog(client, db_session):
    project, profile_version = _seed_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Large review queue",
    )
    item_ids = []
    for index in range(1, 6):
        item = write_candidate_fact(
            db=db_session,
            bundle_id=bundle.id,
            created_by="writer.alpha",
            candidate=_candidate_payload(
                claim_id=f"claim.hero.status.queue.{index}",
                subject_ref=f"char.hero.{index}",
                predicate="status",
                value="失踪",
                chapter_index=index,
            ),
        )
        item_ids.append(item.id)

    response = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-review-queue?limit=2")
    athena_response = client.get(f"/api/v1/projects/{project.id}/athena/evolution/proposal-review-queue?limit=2")

    assert response.status_code == 200
    assert athena_response.status_code == 200
    payload = response.json()
    assert payload == athena_response.json()
    assert payload["total_items"] == 5
    assert payload["returned_items"] == 2
    assert payload["limit"] == 2
    assert payload["has_more"] is True
    assert [cluster["item_ids"][0] for cluster in payload["clusters"]] == item_ids[:2]


def test_world_model_proposal_review_queue_supports_offset_window(client, db_session):
    project, profile_version = _seed_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Offset review queue",
    )
    item_ids = []
    for index in range(1, 6):
        item = write_candidate_fact(
            db=db_session,
            bundle_id=bundle.id,
            created_by="writer.alpha",
            candidate=_candidate_payload(
                claim_id=f"claim.hero.status.offset.queue.{index}",
                subject_ref=f"char.hero.offset.{index}",
                predicate="status",
                value="失踪",
                chapter_index=index,
            ),
        )
        item_ids.append(item.id)

    response = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-review-queue?offset=2&limit=2")
    athena_response = client.get(
        f"/api/v1/projects/{project.id}/athena/evolution/proposal-review-queue?offset=2&limit=2"
    )

    assert response.status_code == 200
    assert athena_response.status_code == 200
    payload = response.json()
    assert payload == athena_response.json()
    assert payload["total_items"] == 5
    assert payload["returned_items"] == 2
    assert payload["offset"] == 2
    assert payload["limit"] == 2
    assert payload["has_more"] is True
    assert [cluster["item_ids"][0] for cluster in payload["clusters"]] == item_ids[2:4]


def test_world_model_proposal_review_queue_count_does_not_select_heavy_item_fields(client, db_session):
    project, profile_version = _seed_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Heavy review queue",
    )
    for index in range(1, 4):
        write_candidate_fact(
            db=db_session,
            bundle_id=bundle.id,
            created_by="writer.alpha",
            candidate=ProposalCandidateFactCreate(
                project_id=project.id,
                project_profile_version_id=profile_version.id,
                profile_version=profile_version.version,
                contract_version=profile_version.contract_version,
                claim_id=f"claim.queue.heavy.{index}",
                chapter_index=index,
                subject_ref=f"char.queue.heavy.{index}",
                predicate="status",
                object_ref_or_value={"fragments": ["记忆碎片"] * 200},
                claim_layer="truth",
                disclosed_to_refs=[f"char.reader.{i}" for i in range(100)],
                authority_type="authoritative_structured",
                confidence=0.9,
                evidence_refs=[f"chapter.{i:03d}" for i in range(100)],
                notes="长审阅备注" * 300,
            ),
        )
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-review-queue?limit=1")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_items"] == 3
    assert payload["returned_items"] == 1
    item_count_statements = [
        statement
        for statement in statements
        if "count(" in statement and "world_proposal_items" in statement
    ]
    assert item_count_statements
    assert all("world_proposal_items.object_ref_or_value" not in statement for statement in item_count_statements)
    assert all("world_proposal_items.disclosed_to_refs" not in statement for statement in item_count_statements)
    assert all("world_proposal_items.evidence_refs" not in statement for statement in item_count_statements)
    assert all("world_proposal_items.notes" not in statement for statement in item_count_statements)


def test_world_model_proposal_review_queue_rows_do_not_select_heavy_item_fields(client, db_session):
    project, profile_version = _seed_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Heavy review queue row projection",
    )
    for index in range(1, 4):
        write_candidate_fact(
            db=db_session,
            bundle_id=bundle.id,
            created_by="writer.alpha",
            candidate=ProposalCandidateFactCreate(
                project_id=project.id,
                project_profile_version_id=profile_version.id,
                profile_version=profile_version.version,
                contract_version=profile_version.contract_version,
                claim_id=f"claim.queue.row.heavy.{index}",
                chapter_index=index,
                subject_ref=f"char.queue.row.heavy.{index}",
                predicate="status",
                object_ref_or_value={"fragments": ["记忆碎片"] * 200},
                claim_layer="truth",
                disclosed_to_refs=[f"char.reader.{i}" for i in range(100)],
                authority_type="authoritative_structured",
                confidence=0.9,
                evidence_refs=[f"chapter.{i:03d}" for i in range(100)],
                notes="长审阅备注" * 300,
            ),
        )
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-review-queue?limit=2")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    assert response.json()["returned_items"] == 2
    row_selects = [
        statement
        for statement in statements
        if statement.startswith("select")
        and "from world_proposal_items" in statement
        and "count(" not in statement
    ]
    assert row_selects
    assert all("world_proposal_items.object_ref_or_value" not in statement for statement in row_selects)
    assert all("world_proposal_items.disclosed_to_refs" not in statement for statement in row_selects)
    assert all("world_proposal_items.evidence_refs" not in statement for statement in row_selects)
    assert all("world_proposal_items.notes" not in statement for statement in row_selects)


def test_world_model_proposal_bundle_pagination_rejects_invalid_bounds(client, db_session):
    project, _profile_version = _seed_profile(db_session)

    negative_offset_response = client.get(
        f"/api/v1/projects/{project.id}/world-model/proposal-bundles?offset=-1"
    )
    assert negative_offset_response.status_code == 422

    excessive_limit_response = client.get(
        f"/api/v1/projects/{project.id}/world-model/proposal-bundles?limit=101"
    )
    assert excessive_limit_response.status_code == 422


def test_world_model_routes_lock_to_current_profile_and_reject_cross_profile_access(client, db_session):
    project = Project(name="World Frontend Profile Scope")
    genre_profile = GenreProfile(
        canonical_id="generic-world-frontend-scope",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    profile_v1 = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={"theme": "旧港废墟"},
    )
    profile_v2 = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=2,
        contract_version="world.contract.v1",
        profile_payload={"theme": "新港自治领"},
    )
    db_session.add_all([profile_v1, profile_v2])
    db_session.commit()

    db_session.add_all([
        WorldTimelineAnchor(
            project_id=project.id,
            profile_version=profile_v1.version,
            anchor_id="anchor.v1",
            chapter_index=1,
            intra_chapter_seq=1,
            ordering_key="001:001",
            contract_version="world.contract.v1",
        ),
        WorldTimelineAnchor(
            project_id=project.id,
            profile_version=profile_v2.version,
            anchor_id="anchor.v2",
            chapter_index=1,
            intra_chapter_seq=1,
            ordering_key="001:001",
            contract_version="world.contract.v1",
        ),
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile_v1.id,
            profile_version=profile_v1.version,
            claim_id="claim.hero.rank.v1",
            chapter_index=1,
            intra_chapter_seq=1,
            subject_ref="char.hero",
            predicate="rank",
            object_ref_or_value="captain",
            claim_layer="truth",
            claim_status="confirmed",
            valid_from_anchor_id="anchor.v1",
            authority_type="authoritative_structured",
            confidence=1.0,
            contract_version="world.contract.v1",
        ),
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile_v2.id,
            profile_version=profile_v2.version,
            claim_id="claim.hero.rank.v2",
            chapter_index=1,
            intra_chapter_seq=1,
            subject_ref="char.hero",
            predicate="rank",
            object_ref_or_value="commodore",
            claim_layer="truth",
            claim_status="confirmed",
            valid_from_anchor_id="anchor.v2",
            authority_type="authoritative_structured",
            confidence=1.0,
            contract_version="world.contract.v1",
        ),
    ])
    db_session.commit()

    old_pending_bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_v1.id,
        profile_version=profile_v1.version,
        created_by="writer.alpha",
        title="Old pending bundle",
    )
    old_pending_item = write_candidate_fact(
        db=db_session,
        bundle_id=old_pending_bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.alias.v1.pending",
            subject_ref="char.hero",
            predicate="alias",
            value="ghost",
        ).model_copy(update={
            "profile_version": profile_v1.version,
            "project_profile_version_id": profile_v1.id,
        }),
    )

    old_approved_bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_v1.id,
        profile_version=profile_v1.version,
        created_by="writer.alpha",
        title="Old approved bundle",
    )
    old_approved_item = write_candidate_fact(
        db=db_session,
        bundle_id=old_approved_bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.cover.v1.pending",
            subject_ref="char.hero",
            predicate="cover",
            value="archivist",
        ).model_copy(update={
            "profile_version": profile_v1.version,
            "project_profile_version_id": profile_v1.id,
        }),
    )
    old_approval_review = review_proposal_item(
        db=db_session,
        proposal_item_id=old_approved_item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="历史 profile 里的审批",
        evidence_refs=["chapter.01"],
    )

    current_bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_v2.id,
        profile_version=profile_v2.version,
        created_by="writer.beta",
        title="Current bundle",
    )
    current_item = write_candidate_fact(
        db=db_session,
        bundle_id=current_bundle.id,
        created_by="writer.beta",
        candidate=_candidate_payload(
            claim_id="claim.hero.alias.v2.pending",
            subject_ref="char.hero",
            predicate="alias",
            value="archivist",
        ).model_copy(update={
            "profile_version": profile_v2.version,
            "project_profile_version_id": profile_v2.id,
        }),
    )
    assert current_item.profile_version == 2

    overview_response = client.get(f"/api/v1/projects/{project.id}/world-model")
    assert overview_response.status_code == 200
    assert overview_response.json()["project_profile"]["version"] == 2
    assert overview_response.json()["projection"]["facts"]["char.hero"]["rank"] == "commodore"

    list_response = client.get(f"/api/v1/projects/{project.id}/world-model/proposal-bundles")
    assert list_response.status_code == 200
    assert [bundle["id"] for bundle in list_response.json()["items"]] == [current_bundle.id]

    current_detail_response = client.get(
        f"/api/v1/projects/{project.id}/world-model/proposal-bundles/{current_bundle.id}"
    )
    assert current_detail_response.status_code == 200
    assert current_detail_response.json()["bundle"]["id"] == current_bundle.id

    old_detail_response = client.get(
        f"/api/v1/projects/{project.id}/world-model/proposal-bundles/{old_pending_bundle.id}"
    )
    assert old_detail_response.status_code == 409
    assert "current profile version" in old_detail_response.json()["detail"]

    old_review_response = client.post(
        f"/api/v1/projects/{project.id}/world-model/proposal-items/{old_pending_item.id}/review",
        json={
            "reviewer_ref": "editor.alpha",
            "action": "approve",
            "reason": "不该允许跨 profile 审批",
            "evidence_refs": ["chapter.02"],
            "edited_fields": {},
        },
    )
    assert old_review_response.status_code == 409
    assert "current profile version" in old_review_response.json()["detail"]

    old_split_response = client.post(
        f"/api/v1/projects/{project.id}/world-model/proposal-bundles/{old_pending_bundle.id}/split",
        json={
            "reviewer_ref": "editor.alpha",
            "reason": "不该允许跨 profile 拆分",
            "evidence_refs": ["chapter.03"],
            "item_ids": [old_pending_item.id],
        },
    )
    assert old_split_response.status_code == 409
    assert "current profile version" in old_split_response.json()["detail"]

    old_rollback_response = client.post(
        f"/api/v1/projects/{project.id}/world-model/reviews/{old_approval_review.id}/rollback",
        json={
            "reviewer_ref": "editor.alpha",
            "reason": "不该允许跨 profile 回滚",
            "evidence_refs": ["chapter.04"],
        },
    )
    assert old_rollback_response.status_code == 409
    assert "current profile version" in old_rollback_response.json()["detail"]


def test_world_model_overview_surfaces_projection_value_error_as_business_4xx(client, db_session):
    project, profile_version = _seed_profile(db_session)
    db_session.add(
        WorldEvent(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            event_id="evt.hero.missing-anchor",
            idempotency_key="idem.hero.missing-anchor",
            timeline_anchor_id="anchor.typo",
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
        )
    )
    db_session.commit()

    response = client.get(f"/api/v1/projects/{project.id}/world-model")

    assert response.status_code == 400
    assert "anchor.typo" in response.json()["detail"]

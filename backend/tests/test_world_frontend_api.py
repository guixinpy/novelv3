from sqlalchemy import event

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
    WorldProposalItem,
    WorldRelation,
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
    assert [item["claim_id"] for item in payload] == ["claim.hero.secret.current"]
    assert payload[0]["object_ref_or_value"] == {"value": "潮汐门钥匙"}
    assert payload[0]["perspective_ref"] == "char.hero"
    assert payload[0]["disclosed_to_refs"] == ["char.hero", "char.mentor"]
    assert payload[0]["evidence_refs"] == ["chapter.02"]


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

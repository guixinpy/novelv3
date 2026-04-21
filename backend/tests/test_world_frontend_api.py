from app.core.world_proposal_service import (
    calculate_bundle_impact_scope,
    create_bundle,
    review_proposal_item,
    write_candidate_fact,
)
from app.models import (
    GenreProfile,
    Project,
    ProjectProfileVersion,
    WorldEvent,
    WorldFactClaim,
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


def _candidate_payload(*, claim_id: str, subject_ref: str, predicate: str, value: str) -> ProposalCandidateFactCreate:
    return ProposalCandidateFactCreate(
        project_id="ignored-by-service",
        profile_version=1,
        claim_id=claim_id,
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


def test_world_model_overview_returns_nulls_when_project_has_no_world_data(client):
    create_response = client.post("/api/v1/projects", json={"name": "No World Data"})
    project_id = create_response.json()["id"]

    response = client.get(f"/api/v1/projects/{project_id}/world-model")

    assert response.status_code == 200
    assert response.json() == {
        "project_profile": None,
        "projection": None,
    }


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
    assert [item["id"] for item in listed_bundles] == [bundle.id]

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
    assert [bundle["id"] for bundle in list_response.json()] == [current_bundle.id]

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

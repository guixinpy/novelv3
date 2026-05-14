import sqlite3

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.world_projection import FactRecord, project_world_truth
from app.core.world_proposal_service import (
    assemble_bundle,
    calculate_bundle_impact_scope,
    create_bundle,
    list_authoritative_truth_claims,
    review_proposal_item,
    rollback_review,
    split_bundle,
    write_candidate_fact,
)
from app.models import (
    GenreProfile,
    Project,
    ProjectProfileVersion,
    WorldFactClaim,
    WorldProposalBundle,
    WorldProposalImpactScopeSnapshot,
    WorldProposalItem,
    WorldProposalReview,
)
from app.schemas.world_proposals import ProposalCandidateFactCreate


def _seed_project_profile(db_session):
    project = Project(name="World Proposal Review")
    genre_profile = GenreProfile(
        canonical_id="generic-world-proposals",
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


def test_candidate_layer_is_physically_isolated_from_truth_layer(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Dock-7 truth candidates",
    )

    item = write_candidate_fact(
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

    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
    authoritative_claims = list_authoritative_truth_claims(
        db=db_session,
        project_id=project.id,
        profile_version=profile_version.version,
    )

    assert db_session.query(WorldProposalBundle).count() == 1
    assert db_session.query(WorldProposalItem).count() == 1
    assert db_session.query(WorldFactClaim).count() == 0
    assert stored_item.bundle_id == bundle.id
    assert authoritative_claims == []


def test_write_candidate_fact_rejects_contract_version_drift_against_bundle_profile(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Contract drift candidate",
    )

    with pytest.raises(ValueError, match="contract_version"):
        write_candidate_fact(
            db=db_session,
            bundle_id=bundle.id,
            created_by="writer.alpha",
            candidate=_candidate_payload(
                claim_id="claim.hero.rank.bad-contract",
                subject_ref="char.hero",
                predicate="rank",
                value="captain",
            ).model_copy(update={"contract_version": "world.contract.v2"}),
        )

    assert db_session.query(WorldProposalItem).count() == 0


def test_write_candidate_fact_rejects_missing_bundle_id_as_business_error(db_session):
    with pytest.raises(ValueError, match="proposal bundle bundle.missing.write-candidate does not exist"):
        write_candidate_fact(
            db=db_session,
            bundle_id="bundle.missing.write-candidate",
            created_by="writer.alpha",
            candidate=_candidate_payload(
                claim_id="claim.hero.rank.missing-bundle",
                subject_ref="char.hero",
                predicate="rank",
                value="captain",
            ),
        )

    assert db_session.query(WorldProposalItem).count() == 0


def test_calculate_bundle_impact_scope_rejects_missing_bundle_id_as_business_error(db_session):
    with pytest.raises(ValueError, match="proposal bundle bundle.missing.impact-scope does not exist"):
        calculate_bundle_impact_scope(
            db=db_session,
            bundle_id="bundle.missing.impact-scope",
        )

    assert db_session.query(WorldProposalImpactScopeSnapshot).count() == 0


def test_review_proposal_item_rejects_missing_item_id_as_business_error(db_session):
    with pytest.raises(ValueError, match="proposal item proposal-item.missing.review does not exist"):
        review_proposal_item(
            db=db_session,
            proposal_item_id="proposal-item.missing.review",
            reviewer_ref="editor.alpha",
            action="approve",
            reason="不存在的条目不能审阅",
            evidence_refs=["chapter.00"],
        )

    assert db_session.query(WorldProposalReview).count() == 0


def test_review_proposal_item_rejects_item_profile_binding_drift_against_bundle(db_session):
    project = Project(name="World Proposal Review Binding Drift")
    genre_profile = GenreProfile(
        canonical_id="generic-world-proposals-binding-drift",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    profile_version_one = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    profile_version_two = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=2,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add_all([profile_version_one, profile_version_two])
    db_session.commit()

    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version_one.id,
        profile_version=profile_version_one.version,
        created_by="writer.alpha",
        title="Binding drift bundle",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rank.binding-drift",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ),
    )

    raw_conn = db_session.get_bind().raw_connection()
    try:
        raw_conn.execute("PRAGMA foreign_keys=OFF")
        raw_conn.execute(
            "UPDATE world_proposal_items "
            "SET project_profile_version_id = ?, profile_version = ? "
            "WHERE id = ?",
            (profile_version_two.id, profile_version_two.version, item.id),
        )
        raw_conn.commit()
        raw_conn.execute("PRAGMA foreign_keys=ON")
    finally:
        raw_conn.close()

    db_session.expire_all()

    with pytest.raises(ValueError, match="profile binding mismatch"):
        review_proposal_item(
            db=db_session,
            proposal_item_id=item.id,
            reviewer_ref="editor.alpha",
            action="approve",
            reason="试图审阅脏数据",
            evidence_refs=["chapter.12"],
        )

    assert db_session.query(WorldProposalReview).count() == 0
    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
    assert stored_item.project_profile_version_id == profile_version_two.id
    assert stored_item.profile_version == profile_version_two.version


def test_world_proposal_item_rejects_bundle_profile_binding_drift_at_db_level(db_session):
    project = Project(name="World Proposal DB Binding Drift")
    genre_profile = GenreProfile(
        canonical_id="generic-world-proposals-db-binding-drift",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    profile_version_one = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    profile_version_two = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=2,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add_all([profile_version_one, profile_version_two])
    db_session.commit()

    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version_one.id,
        profile_version=profile_version_one.version,
        created_by="writer.alpha",
        title="DB binding drift bundle",
    )

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                "INSERT INTO world_proposal_items "
                "(id, project_id, project_profile_version_id, profile_version, bundle_id, parent_item_id, item_status, "
                "claim_id, chapter_index, intra_chapter_seq, subject_ref, predicate, object_ref_or_value, claim_layer, "
                "valid_from_anchor_id, valid_to_anchor_id, source_event_ref, evidence_refs, authority_type, confidence, "
                "notes, contract_version, created_by, approved_claim_id, created_at, updated_at) "
                "VALUES (:id, :project_id, :project_profile_version_id, :profile_version, :bundle_id, NULL, :item_status, "
                ":claim_id, NULL, :intra_chapter_seq, :subject_ref, :predicate, :object_ref_or_value, :claim_layer, "
                "NULL, NULL, NULL, :evidence_refs, :authority_type, :confidence, :notes, :contract_version, :created_by, "
                "NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": "proposal-item-db-drift",
                "project_id": project.id,
                "project_profile_version_id": profile_version_two.id,
                "profile_version": profile_version_two.version,
                "bundle_id": bundle.id,
                "item_status": "pending",
                "claim_id": "claim.hero.rank.db-drift",
                "intra_chapter_seq": 0,
                "subject_ref": "char.hero",
                "predicate": "rank",
                "object_ref_or_value": '"captain"',
                "claim_layer": "truth",
                "evidence_refs": '["evidence.scene"]',
                "authority_type": "authoritative_structured",
                "confidence": 0.95,
                "notes": "",
                "contract_version": "world.contract.v1",
                "created_by": "writer.alpha",
            },
        )
        db_session.commit()
    db_session.rollback()

    assert db_session.query(WorldProposalItem).count() == 0


def test_world_proposal_bundle_rejects_cross_profile_parent_bundle_binding_at_db_level(db_session):
    project = Project(name="World Proposal Parent Bundle Drift")
    genre_profile = GenreProfile(
        canonical_id="generic-world-proposals-parent-bundle-drift",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    profile_version_one = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    profile_version_two = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=2,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add_all([profile_version_one, profile_version_two])
    db_session.commit()

    parent_bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version_one.id,
        profile_version=profile_version_one.version,
        created_by="writer.alpha",
        title="Parent bundle",
    )

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                "INSERT INTO world_proposal_bundles "
                "(id, project_id, project_profile_version_id, profile_version, parent_bundle_id, bundle_status, "
                "title, summary, created_by, created_at, updated_at) "
                "VALUES (:id, :project_id, :project_profile_version_id, :profile_version, :parent_bundle_id, "
                ":bundle_status, :title, :summary, :created_by, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": "bundle-cross-profile-parent",
                "project_id": project.id,
                "project_profile_version_id": profile_version_two.id,
                "profile_version": profile_version_two.version,
                "parent_bundle_id": parent_bundle.id,
                "bundle_status": "pending",
                "title": "Child bundle",
                "summary": "",
                "created_by": "writer.beta",
            },
        )
        db_session.commit()
    db_session.rollback()

    assert db_session.query(WorldProposalBundle).count() == 1


def test_world_proposal_item_rejects_parent_item_outside_bundle_lineage_at_db_level(db_session):
    project, profile_version = _seed_project_profile(db_session)
    source_bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Source bundle",
    )
    unrelated_bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.beta",
        title="Unrelated bundle",
    )
    parent_item = write_candidate_fact(
        db=db_session,
        bundle_id=source_bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.parent-lineage",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ),
    )

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                "INSERT INTO world_proposal_items "
                "(id, project_id, project_profile_version_id, profile_version, bundle_id, parent_item_id, item_status, "
                "claim_id, chapter_index, intra_chapter_seq, subject_ref, predicate, object_ref_or_value, claim_layer, "
                "valid_from_anchor_id, valid_to_anchor_id, source_event_ref, evidence_refs, authority_type, confidence, "
                "notes, contract_version, created_by, approved_claim_id, created_at, updated_at) "
                "VALUES (:id, :project_id, :project_profile_version_id, :profile_version, :bundle_id, :parent_item_id, "
                ":item_status, :claim_id, NULL, :intra_chapter_seq, :subject_ref, :predicate, :object_ref_or_value, "
                ":claim_layer, NULL, NULL, NULL, :evidence_refs, :authority_type, :confidence, :notes, "
                ":contract_version, :created_by, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": "proposal-item-cross-lineage",
                "project_id": project.id,
                "project_profile_version_id": profile_version.id,
                "profile_version": profile_version.version,
                "bundle_id": unrelated_bundle.id,
                "parent_item_id": parent_item.id,
                "item_status": "pending",
                "claim_id": "claim.hero.child-lineage",
                "intra_chapter_seq": 0,
                "subject_ref": "char.hero",
                "predicate": "rank",
                "object_ref_or_value": '"commander"',
                "claim_layer": "truth",
                "evidence_refs": '["evidence.scene"]',
                "authority_type": "authoritative_structured",
                "confidence": 0.95,
                "notes": "",
                "contract_version": "world.contract.v1",
                "created_by": "writer.beta",
            },
        )
        db_session.commit()
    db_session.rollback()

    assert db_session.query(WorldProposalItem).count() == 1


def test_bundle_supports_split_and_partial_approval(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Mixed canon candidates",
    )
    approved_item = write_candidate_fact(
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
    split_item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.loc.status.pending",
            subject_ref="loc.dock-7",
            predicate="status",
            value="sealed",
        ),
    )

    child_bundle = split_bundle(
        db=db_session,
        bundle_id=bundle.id,
        item_ids=[split_item.id],
        reviewer_ref="editor.alpha",
        reason="地点状态需要单独审阅",
        evidence_refs=["chapter.12"],
    )
    review = review_proposal_item(
        db=db_session,
        proposal_item_id=approved_item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="角色军衔已由证据确认",
        evidence_refs=["chapter.12", "evidence.scene"],
    )

    db_session.refresh(bundle)
    db_session.refresh(child_bundle)
    db_session.refresh(split_item)
    db_session.refresh(approved_item)

    truth_claims = db_session.query(WorldFactClaim).order_by(WorldFactClaim.claim_id).all()

    assert child_bundle.parent_bundle_id == bundle.id
    assert bundle.bundle_status == "partially_approved"
    assert approved_item.item_status == "approved"
    assert split_item.item_status == "split"
    assert child_bundle.bundle_status == "pending"
    assert [claim.claim_id for claim in truth_claims] == ["claim.hero.rank.pending"]
    assert review.review_action == "approve"


def test_rollback_keeps_history_instead_of_silently_erasing_it(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Rollback candidate",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.allegiance.pending",
            subject_ref="char.hero",
            predicate="allegiance",
            value="faction.scrapyard",
        ),
    )
    approval = review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="先并入 canon",
        evidence_refs=["chapter.15"],
    )

    rollback = rollback_review(
        db=db_session,
        review_id=approval.id,
        reviewer_ref="editor.beta",
        reason="后续证据推翻该结论",
        evidence_refs=["chapter.16"],
    )

    claim = db_session.query(WorldFactClaim).filter_by(claim_id="claim.hero.allegiance.pending").one()
    reviews = (
        db_session.query(WorldProposalReview)
        .filter(WorldProposalReview.proposal_item_id == item.id)
        .order_by(WorldProposalReview.created_at.asc())
        .all()
    )

    assert claim.claim_status == "rolled_back"
    assert len(reviews) == 2
    assert reviews[0].id == approval.id
    assert reviews[1].id == rollback.id
    assert rollback.rollback_to_review_id == approval.id


def test_unconfirmed_candidates_cannot_enter_truth_layer_or_projection(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Uncertain candidate",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rank.uncertain",
            subject_ref="char.hero",
            predicate="rank",
            value="commander",
        ),
    )

    review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="mark_uncertain",
        reason="证据互相冲突",
        evidence_refs=["chapter.18"],
    )

    authoritative_claims = list_authoritative_truth_claims(
        db=db_session,
        project_id=project.id,
        profile_version=profile_version.version,
    )
    projection = project_world_truth(
        events=[],
        facts=[
            FactRecord(
                claim_id=claim.claim_id,
                subject_ref=claim.subject_ref,
                predicate=claim.predicate,
                object_ref_or_value=claim.object_ref_or_value,
                claim_layer=claim.claim_layer,
                claim_status=claim.claim_status,
                chapter_index=claim.chapter_index,
                intra_chapter_seq=claim.intra_chapter_seq,
                valid_from_anchor_id=claim.valid_from_anchor_id,
                valid_to_anchor_id=claim.valid_to_anchor_id,
            )
            for claim in authoritative_claims
        ],
    )

    assert db_session.query(WorldFactClaim).count() == 0
    assert authoritative_claims == []
    assert projection["facts"] == {}


def test_bundle_mixed_terminal_rejections_do_not_fall_back_to_pending(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Mixed terminal candidate decisions",
    )
    rejected_item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rank.rejected-terminal",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ),
    )
    uncertain_item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.home.uncertain-terminal",
            subject_ref="char.hero",
            predicate="home",
            value="dock-7",
        ),
    )

    review_proposal_item(
        db=db_session,
        proposal_item_id=rejected_item.id,
        reviewer_ref="editor.alpha",
        action="reject",
        reason="证据不足，驳回",
        evidence_refs=["chapter.18"],
    )
    review_proposal_item(
        db=db_session,
        proposal_item_id=uncertain_item.id,
        reviewer_ref="editor.alpha",
        action="mark_uncertain",
        reason="证据互相冲突，暂不进入真相层",
        evidence_refs=["chapter.18"],
    )

    db_session.refresh(bundle)

    assert bundle.bundle_status == "rejected"


def test_review_records_include_reviewer_time_reason_evidence_and_rollback_point(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Review metadata",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.status.pending",
            subject_ref="char.hero",
            predicate="status",
            value="wounded",
        ),
    )

    impact = calculate_bundle_impact_scope(db=db_session, bundle_id=bundle.id)
    approval = review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="approve_with_edits",
        reason="措辞需改成更稳妥表述",
        evidence_refs=["chapter.20", "scene.log"],
        edited_fields={"notes": "需等待下一章复核"},
    )
    rollback = rollback_review(
        db=db_session,
        review_id=approval.id,
        reviewer_ref="editor.beta",
        reason="新证据显示只是轻伤",
        evidence_refs=["chapter.21"],
    )

    saved_impact = db_session.query(WorldProposalImpactScopeSnapshot).filter_by(id=impact.id).one()
    saved_approval = db_session.query(WorldProposalReview).filter_by(id=approval.id).one()
    saved_rollback = db_session.query(WorldProposalReview).filter_by(id=rollback.id).one()

    assert impact.id == saved_impact.id
    assert saved_approval.reviewer_ref == "editor.alpha"
    assert saved_approval.reason == "措辞需改成更稳妥表述"
    assert saved_approval.evidence_refs == ["chapter.20", "scene.log"]
    assert saved_approval.edited_fields == {"notes": "需等待下一章复核"}
    assert saved_approval.created_at is not None
    assert saved_rollback.rollback_to_review_id == approval.id
    assert saved_rollback.reason == "新证据显示只是轻伤"


def test_impact_scope_ignores_rolled_back_truth_claims(db_session):
    project, profile_version = _seed_project_profile(db_session)
    db_session.add(
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            claim_id="claim.hero.status.rolled-back",
            chapter_index=1,
            intra_chapter_seq=0,
            subject_ref="char.hero",
            predicate="status",
            object_ref_or_value="wounded",
            claim_layer="truth",
            claim_status="rolled_back",
            evidence_refs=["chapter.01"],
            authority_type="authoritative_structured",
            confidence=0.8,
            notes="rolled back truth",
            contract_version="world.contract.v1",
        )
    )
    db_session.commit()
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Impact should ignore rolled back truth",
    )
    write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.status.new",
            subject_ref="char.hero",
            predicate="status",
            value="recovered",
        ),
    )

    impact = calculate_bundle_impact_scope(db=db_session, bundle_id=bundle.id)

    assert impact.affected_truth_claim_ids == []
    assert impact.summary["existing_truth_count"] == 0


def test_impact_scope_does_not_select_heavy_candidate_or_truth_fields(db_session):
    project, profile_version = _seed_project_profile(db_session)
    db_session.add(
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            claim_id="claim.hero.status.confirmed",
            chapter_index=1,
            intra_chapter_seq=0,
            subject_ref="char.hero",
            predicate="status",
            object_ref_or_value={"fragments": ["真相碎片"] * 200},
            claim_layer="truth",
            claim_status="confirmed",
            evidence_refs=[f"chapter.{index:03d}" for index in range(100)],
            authority_type="authoritative_structured",
            confidence=0.8,
            notes="长事实备注" * 300,
            contract_version="world.contract.v1",
        )
    )
    db_session.commit()
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Heavy impact candidates",
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
                claim_id=f"claim.hero.status.pending.{index}",
                chapter_index=index,
                subject_ref="char.hero",
                predicate="status",
                object_ref_or_value={"fragments": ["候选碎片"] * 200},
                claim_layer="truth",
                disclosed_to_refs=[f"char.reader.{i}" for i in range(100)],
                authority_type="authoritative_structured",
                confidence=0.9,
                evidence_refs=[f"chapter.{i:03d}" for i in range(100)],
                notes="长候选备注" * 300,
            ),
        )
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        impact = calculate_bundle_impact_scope(db=db_session, bundle_id=bundle.id)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert impact.summary["candidate_count"] == 3
    assert impact.summary["existing_truth_count"] == 1
    item_selects = [
        statement.split("from world_proposal_items", 1)[0]
        for statement in statements
        if statement.startswith("select") and "from world_proposal_items" in statement
    ]
    truth_selects = [
        statement.split("from world_fact_claims", 1)[0]
        for statement in statements
        if statement.startswith("select") and "from world_fact_claims" in statement
    ]
    assert item_selects
    assert truth_selects
    for column in ["object_ref_or_value", "disclosed_to_refs", "evidence_refs", "notes"]:
        assert all(f"world_proposal_items.{column}" not in clause for clause in item_selects)
    for column in ["object_ref_or_value", "disclosed_to_refs", "evidence_refs", "notes"]:
        assert all(f"world_fact_claims.{column}" not in clause for clause in truth_selects)


def test_impact_scope_treats_presence_count_as_chapter_scoped(db_session):
    project, profile_version = _seed_project_profile(db_session)
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
            evidence_refs=["chapter:1"],
            authority_type="derived",
            confidence=0.85,
            notes="chapter 1 presence",
            contract_version="world.contract.v1",
        )
    )
    db_session.commit()
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Chapter scoped presence",
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

    impact = calculate_bundle_impact_scope(db=db_session, bundle_id=bundle.id)

    assert impact.affected_truth_claim_ids == []
    assert impact.summary["existing_truth_count"] == 0


def test_impact_scope_keeps_presence_count_conflicts_within_same_chapter(db_session):
    project, profile_version = _seed_project_profile(db_session)
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
            evidence_refs=["chapter:1"],
            authority_type="derived",
            confidence=0.85,
            notes="chapter 1 presence",
            contract_version="world.contract.v1",
        )
    )
    db_session.commit()
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Same chapter presence",
    )
    write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.chapter.1.char.hero.presence_count.recount",
            subject_ref="char.hero",
            predicate="presence_count",
            chapter_index=1,
            value={"count": 52, "chapter_index": 1},
        ),
    )

    impact = calculate_bundle_impact_scope(db=db_session, bundle_id=bundle.id)

    assert impact.affected_truth_claim_ids == ["claim.chapter.1.char.hero.presence_count"]
    assert impact.summary["existing_truth_count"] == 1


def test_review_and_rollback_create_fresh_impact_snapshots(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Impact refresh",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.status.refresh",
            subject_ref="char.hero",
            predicate="status",
            value="wounded",
        ),
    )
    initial = calculate_bundle_impact_scope(db=db_session, bundle_id=bundle.id)

    approval = review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="确认",
        evidence_refs=["chapter.20"],
    )
    after_approval = (
        db_session.query(WorldProposalImpactScopeSnapshot)
        .filter_by(bundle_id=bundle.id)
        .order_by(WorldProposalImpactScopeSnapshot.created_at.desc(), WorldProposalImpactScopeSnapshot.id.desc())
        .first()
    )
    rollback_review(
        db=db_session,
        review_id=approval.id,
        reviewer_ref="editor.beta",
        reason="撤回",
        evidence_refs=["chapter.21"],
    )
    snapshots = db_session.query(WorldProposalImpactScopeSnapshot).filter_by(bundle_id=bundle.id).all()

    assert after_approval is not None
    assert after_approval.id != initial.id
    assert after_approval.summary["existing_truth_count"] == 1
    assert len(snapshots) == 3
    assert any(snapshot.id != initial.id and snapshot.summary["existing_truth_count"] == 1 for snapshot in snapshots)
    assert any(
        snapshot.id not in {initial.id, after_approval.id}
        and snapshot.summary["existing_truth_count"] == 0
        for snapshot in snapshots
    )


def test_approved_item_cannot_be_rejected_or_marked_uncertain_without_explicit_rollback(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Terminal review guard",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rank.finalized",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ),
    )
    review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="证据充分",
        evidence_refs=["chapter.30"],
    )

    with pytest.raises(ValueError, match="rollback"):
        review_proposal_item(
            db=db_session,
            proposal_item_id=item.id,
            reviewer_ref="editor.beta",
            action="reject",
            reason="想直接否掉",
            evidence_refs=["chapter.31"],
        )

    with pytest.raises(ValueError, match="rollback"):
        review_proposal_item(
            db=db_session,
            proposal_item_id=item.id,
            reviewer_ref="editor.beta",
            action="mark_uncertain",
            reason="想改成不确定",
            evidence_refs=["chapter.31"],
        )

    assert db_session.query(WorldProposalReview).filter_by(proposal_item_id=item.id).count() == 1


def test_edited_fields_cannot_override_guarded_protocol_fields(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Guarded fields",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.status.guarded",
            subject_ref="char.hero",
            predicate="status",
            value="alive",
        ),
    )

    with pytest.raises(ValueError, match="edited_fields"):
        review_proposal_item(
            db=db_session,
            proposal_item_id=item.id,
            reviewer_ref="editor.alpha",
            action="approve_with_edits",
            reason="试图改协议字段",
            evidence_refs=["chapter.32"],
            edited_fields={
                "claim_layer": "belief",
                "project_id": "other-project",
            },
        )

    assert db_session.query(WorldFactClaim).count() == 0


def test_approve_with_edits_can_update_claim_object_value(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Editable object value",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.status.edited-object",
            subject_ref="char.hero",
            predicate="status",
            value="unknown",
        ),
    )

    review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="approve_with_edits",
        reason="候选值需要按证据修正",
        evidence_refs=["chapter.32"],
        edited_fields={"object_ref_or_value": {"status": "wounded", "severity": "minor"}},
    )

    saved_claim = db_session.query(WorldFactClaim).filter_by(claim_id="claim.hero.status.edited-object").one()
    saved_review = db_session.query(WorldProposalReview).filter_by(proposal_item_id=item.id).one()

    assert saved_claim.object_ref_or_value == {"status": "wounded", "severity": "minor"}
    assert saved_review.edited_fields == {"object_ref_or_value": {"status": "wounded", "severity": "minor"}}


def test_world_intake_candidate_cannot_be_directly_approved(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="athena.dialog",
        title="Dialog intake",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="athena.dialog",
        candidate=ProposalCandidateFactCreate(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            contract_version=profile_version.contract_version,
            claim_id="athena.dialog.raw-intake",
            subject_ref="project.world_intake",
            predicate="user_proposed_update",
            object_ref_or_value="把林舟设定为旧灯塔守夜人",
            claim_layer="truth",
            authority_type="annotation",
            confidence=0.5,
            evidence_refs=["dialog:athena"],
        ),
    )

    with pytest.raises(ValueError, match="atomic"):
        review_proposal_item(
            db=db_session,
            proposal_item_id=item.id,
            reviewer_ref="editor.alpha",
            action="approve",
            reason="不能直接通过原始自然语言 intake",
            evidence_refs=["dialog:athena"],
        )

    assert db_session.query(WorldFactClaim).count() == 0


def test_world_intake_candidate_can_be_approved_after_atomizing_fields(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="athena.dialog",
        title="Dialog intake",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="athena.dialog",
        candidate=ProposalCandidateFactCreate(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            contract_version=profile_version.contract_version,
            claim_id="athena.dialog.atomized-intake",
            subject_ref="project.world_intake",
            predicate="user_proposed_update",
            object_ref_or_value="把林舟设定为旧灯塔守夜人",
            claim_layer="truth",
            authority_type="annotation",
            confidence=0.5,
            evidence_refs=["dialog:athena"],
        ),
    )

    review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="approve_with_edits",
        reason="编辑为原子事实后通过",
        evidence_refs=["dialog:athena"],
        edited_fields={
            "subject_ref": "char.林舟",
            "predicate": "role",
            "object_ref_or_value": "旧灯塔守夜人",
        },
    )

    saved_claim = db_session.query(WorldFactClaim).filter_by(claim_id="athena.dialog.atomized-intake").one()
    saved_review = db_session.query(WorldProposalReview).filter_by(proposal_item_id=item.id).one()

    assert saved_claim.subject_ref == "char.林舟"
    assert saved_claim.predicate == "role"
    assert saved_claim.object_ref_or_value == "旧灯塔守夜人"
    assert saved_review.edited_fields == {
        "subject_ref": "char.林舟",
        "predicate": "role",
        "object_ref_or_value": "旧灯塔守夜人",
    }


def test_split_bundle_rejects_invalid_item_ids(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Split validation",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.location.split",
            subject_ref="char.hero",
            predicate="location",
            value="loc.dock-7",
        ),
    )

    with pytest.raises(ValueError, match="item_ids"):
        split_bundle(
            db=db_session,
            bundle_id=bundle.id,
            item_ids=[item.id, "missing-item"],
            reviewer_ref="editor.alpha",
            reason="夹带了不存在的条目",
            evidence_refs=["chapter.33"],
        )

    assert db_session.query(WorldProposalBundle).count() == 1


def test_split_bundle_rejects_missing_bundle_id_as_business_error(db_session):
    with pytest.raises(ValueError, match="proposal bundle bundle.missing.split does not exist"):
        split_bundle(
            db=db_session,
            bundle_id="bundle.missing.split",
            item_ids=["proposal-item.any"],
            reviewer_ref="editor.alpha",
            reason="不存在的 bundle 不能拆分",
            evidence_refs=["chapter.32"],
        )

    assert db_session.query(WorldProposalBundle).count() == 0


def test_approved_item_cannot_be_split(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Split terminal guard",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.resource.approved",
            subject_ref="char.hero",
            predicate="resource",
            value="artifact.black-box",
        ),
    )
    review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="先通过",
        evidence_refs=["chapter.34"],
    )

    with pytest.raises(ValueError, match="split"):
        split_bundle(
            db=db_session,
            bundle_id=bundle.id,
            item_ids=[item.id],
            reviewer_ref="editor.beta",
            reason="再去拆分",
            evidence_refs=["chapter.35"],
        )


def test_approval_persists_claim_when_retrieval_sync_fails(db_session, monkeypatch):
    import app.core.world_proposal_service as proposal_service

    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Retrieval sync isolation",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rank.sync-failure",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ),
    )

    def raise_sync_error(*args, **kwargs):
        raise RuntimeError("retrieval sync failed")

    monkeypatch.setattr(proposal_service, "sync_fact_retrieval_document", raise_sync_error)

    review = review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="事实审批不能被索引副作用阻断",
        evidence_refs=["chapter.34"],
    )

    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
    stored_claim = db_session.query(WorldFactClaim).filter_by(claim_id="claim.hero.rank.sync-failure").one()
    assert review.created_truth_claim_id == "claim.hero.rank.sync-failure"
    assert stored_item.item_status == "approved"
    assert stored_claim.claim_status == "confirmed"
    assert db_session.query(WorldProposalReview).filter_by(proposal_item_id=item.id).count() == 1


def test_rollback_persists_business_state_when_retrieval_delete_fails(db_session, monkeypatch):
    import app.core.world_proposal_service as proposal_service

    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Rollback retrieval isolation",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rank.rollback-sync-failure",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ),
    )
    approval = review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="先通过",
        evidence_refs=["chapter.34"],
    )

    def raise_delete_error(*args, **kwargs):
        raise RuntimeError("retrieval delete failed")

    monkeypatch.setattr(proposal_service, "delete_fact_retrieval_document", raise_delete_error)

    rollback = rollback_review(
        db=db_session,
        review_id=approval.id,
        reviewer_ref="editor.beta",
        reason="撤回事实审批不能被索引副作用阻断",
        evidence_refs=["chapter.35"],
    )

    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
    stored_claim = db_session.query(WorldFactClaim).filter_by(claim_id="claim.hero.rank.rollback-sync-failure").one()
    assert rollback.review_action == "rollback"
    assert stored_item.item_status == "rolled_back"
    assert stored_claim.claim_status == "rolled_back"
    assert db_session.query(WorldProposalReview).filter_by(rollback_to_review_id=approval.id).count() == 1


def test_approve_preserves_candidate_claim_layer_for_subject_knowledge(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Subject belief approval",
    )
    candidate = _candidate_payload(
        claim_id="claim.hero.cover-story",
        subject_ref="char.hero",
        predicate="cover_story",
        value="dock-worker",
    ).model_copy(update={"claim_layer": "belief", "perspective_ref": "char.detective"})
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=candidate,
    )

    review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="保留主体认知层",
        evidence_refs=["chapter.36"],
    )

    saved_claim = db_session.query(WorldFactClaim).filter_by(claim_id="claim.hero.cover-story").one()

    assert item.claim_layer == "belief"
    assert saved_claim.claim_layer == "belief"
    assert saved_claim.perspective_ref == "char.detective"
    assert saved_claim.claim_status == "confirmed"


def test_review_proposal_item_translates_existing_truth_claim_id_conflict_to_business_error(db_session):
    project, profile_version = _seed_project_profile(db_session)
    db_session.add(
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            claim_id="claim.hero.rank.conflict",
            chapter_index=1,
            intra_chapter_seq=0,
            subject_ref="char.hero",
            predicate="rank",
            object_ref_or_value="captain",
            claim_layer="truth",
            claim_status="confirmed",
            evidence_refs=["chapter.36-existing"],
            authority_type="authoritative_structured",
            confidence=0.95,
            notes="existing truth",
            contract_version="world.contract.v1",
        )
    )
    db_session.commit()

    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Claim id conflict guard",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rank.conflict",
            subject_ref="char.hero",
            predicate="rank",
            value="commander",
        ),
    )

    with pytest.raises(ValueError, match="claim_id .* already exists"):
        review_proposal_item(
            db=db_session,
            proposal_item_id=item.id,
            reviewer_ref="editor.alpha",
            action="approve",
            reason="冲突 claim_id 不该炸 500",
            evidence_refs=["chapter.36-conflict"],
        )

    db_session.expire_all()

    assert db_session.query(WorldProposalReview).count() == 0
    assert db_session.query(WorldFactClaim).filter_by(project_id=project.id, claim_id=item.claim_id).count() == 1
    assert db_session.query(WorldProposalItem).filter_by(id=item.id).one().item_status == "pending"


def test_review_proposal_item_rejects_contract_version_drift_before_writing_truth_claim(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Approval contract drift guard",
    )
    item = WorldProposalItem(
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        bundle_id=bundle.id,
        item_status="pending",
        claim_id="claim.hero.rank.review-drift",
        chapter_index=None,
        intra_chapter_seq=0,
        subject_ref="char.hero",
        predicate="rank",
        object_ref_or_value="captain",
        claim_layer="truth",
        evidence_refs=["evidence.scene"],
        authority_type="authoritative_structured",
        confidence=0.95,
        notes="manual bad seed",
        contract_version="world.contract.v2",
        created_by="writer.alpha",
    )
    db_session.add(item)
    db_session.commit()

    with pytest.raises(ValueError, match="contract_version"):
        review_proposal_item(
            db=db_session,
            proposal_item_id=item.id,
            reviewer_ref="editor.alpha",
            action="approve",
            reason="不该把漂移版本写进 truth",
            evidence_refs=["chapter.36"],
        )

    assert db_session.query(WorldFactClaim).count() == 0
    assert db_session.query(WorldProposalReview).count() == 0


def test_approve_with_edits_rejects_invalid_values_for_editable_fields(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Editable value validation",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.timeline.invalid-edit",
            subject_ref="char.hero",
            predicate="timeline_note",
            value="arrived",
        ),
    )

    with pytest.raises(ValueError, match="edited_fields"):
        review_proposal_item(
            db=db_session,
            proposal_item_id=item.id,
            reviewer_ref="editor.alpha",
            action="approve_with_edits",
            reason="非法 patch",
            evidence_refs=["chapter.37"],
            edited_fields={"intra_chapter_seq": -1},
        )

    with pytest.raises(ValueError, match="edited_fields"):
        review_proposal_item(
            db=db_session,
            proposal_item_id=item.id,
            reviewer_ref="editor.alpha",
            action="approve_with_edits",
            reason="非法 evidence 类型",
            evidence_refs=["chapter.37"],
            edited_fields={"evidence_refs": "not-a-list"},
        )

    assert db_session.query(WorldFactClaim).count() == 0


def test_approve_rejects_edited_fields_and_requires_approve_with_edits(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Approve path guard",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.note.approve-guard",
            subject_ref="char.hero",
            predicate="status_note",
            value="stable",
        ),
    )

    with pytest.raises(ValueError, match="approve_with_edits"):
        review_proposal_item(
            db=db_session,
            proposal_item_id=item.id,
            reviewer_ref="editor.alpha",
            action="approve",
            reason="试图在 approve 偷改 payload",
            evidence_refs=["chapter.38"],
            edited_fields={"notes": "should fail"},
        )

    assert db_session.query(WorldFactClaim).count() == 0
    assert db_session.query(WorldProposalReview).filter_by(proposal_item_id=item.id).count() == 0


def test_rollback_review_rejects_duplicate_rollback_for_same_approval(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Rollback idempotency",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rank.rollback-once",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ),
    )
    approval = review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="先通过",
        evidence_refs=["chapter.39"],
    )
    rollback_review(
        db=db_session,
        review_id=approval.id,
        reviewer_ref="editor.beta",
        reason="第一次回滚",
        evidence_refs=["chapter.40"],
    )

    with pytest.raises(ValueError, match="already been rolled back"):
        rollback_review(
            db=db_session,
            review_id=approval.id,
            reviewer_ref="editor.gamma",
            reason="第二次回滚",
            evidence_refs=["chapter.41"],
        )

    assert db_session.query(WorldProposalReview).filter_by(review_action="rollback").count() == 1


def test_rollback_review_rejects_missing_review_id_as_business_error(db_session):
    with pytest.raises(ValueError, match="does not exist"):
        rollback_review(
            db=db_session,
            review_id="review.missing.rollback",
            reviewer_ref="editor.alpha",
            reason="不存在的 review 不能回滚",
            evidence_refs=["chapter.39z"],
        )

    assert db_session.query(WorldProposalReview).filter_by(review_action="rollback").count() == 0


def test_create_bundle_rejects_missing_parent_bundle_id_as_business_error(db_session):
    project, profile_version = _seed_project_profile(db_session)

    with pytest.raises(ValueError, match="proposal bundle bundle.missing.parent does not exist"):
        create_bundle(
            db=db_session,
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            created_by="writer.alpha",
            title="Missing parent bundle",
            parent_bundle_id="bundle.missing.parent",
        )

    assert db_session.query(WorldProposalBundle).count() == 0


@pytest.mark.parametrize("bundle_factory", [create_bundle, assemble_bundle], ids=["create_bundle", "assemble_bundle"])
def test_bundle_factories_reject_missing_project_profile_version_id_as_business_error(db_session, bundle_factory):
    project, profile_version = _seed_project_profile(db_session)

    with pytest.raises(ValueError, match="project profile version ppv.missing.bundle does not exist"):
        bundle_factory(
            db=db_session,
            project_id=project.id,
            project_profile_version_id="ppv.missing.bundle",
            profile_version=profile_version.version,
            created_by="writer.alpha",
            title="Missing project profile version",
        )

    assert db_session.query(WorldProposalBundle).count() == 0


@pytest.mark.parametrize("bundle_factory", [create_bundle, assemble_bundle], ids=["create_bundle", "assemble_bundle"])
def test_bundle_factories_reject_dangling_project_profile_version_binding_as_business_error(db_session, bundle_factory):
    project, profile_version = _seed_project_profile(db_session)
    version_two = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=profile_version.genre_profile_id,
        version=2,
        contract_version=profile_version.contract_version,
        profile_payload={},
    )
    db_session.add(version_two)
    db_session.commit()

    with pytest.raises(ValueError, match="bundle profile binding mismatch"):
        bundle_factory(
            db=db_session,
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=version_two.version,
            created_by="writer.alpha",
            title="Dangling project profile version binding",
        )

    assert db_session.query(WorldProposalBundle).count() == 0


@pytest.mark.parametrize(
    ("proposal_item_id", "expected_error"),
    [
        (None, "missing proposal_item_id"),
        ("proposal-item.missing.rollback", "missing proposal item"),
    ],
)
def test_rollback_review_rejects_missing_or_dangling_proposal_item_id(
    db_session,
    proposal_item_id,
    expected_error,
):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Rollback missing proposal item binding",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rollback.missing-item",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ),
    )
    approval = review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="先通过",
        evidence_refs=["chapter.39y"],
    )

    if proposal_item_id is None:
        approval.proposal_item_id = None
        db_session.commit()
    else:
        raw_conn = db_session.get_bind().raw_connection()
        try:
            raw_conn.execute("PRAGMA foreign_keys=OFF")
            raw_conn.execute(
                "UPDATE world_proposal_reviews SET proposal_item_id = ? WHERE id = ?",
                (proposal_item_id, approval.id),
            )
            raw_conn.commit()
            raw_conn.execute("PRAGMA foreign_keys=ON")
        finally:
            raw_conn.close()

    db_session.expire_all()

    with pytest.raises(ValueError, match=expected_error):
        rollback_review(
            db=db_session,
            review_id=approval.id,
            reviewer_ref="editor.beta",
            reason="脏 review 不允许回滚",
            evidence_refs=["chapter.39x"],
        )

    assert db_session.query(WorldProposalReview).filter_by(review_action="rollback").count() == 0
    assert db_session.query(WorldProposalItem).filter_by(id=item.id).one().item_status == "approved"
    assert db_session.query(WorldFactClaim).filter_by(claim_id=approval.created_truth_claim_id).one().claim_status == "confirmed"


def test_rollback_review_rejects_source_review_binding_drift(db_session):
    project = Project(name="World Proposal Rollback Review Drift")
    genre_profile = GenreProfile(
        canonical_id="generic-world-proposals-rollback-review-drift",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    profile_version_one = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    profile_version_two = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=2,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add_all([profile_version_one, profile_version_two])
    db_session.commit()

    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version_one.id,
        profile_version=profile_version_one.version,
        created_by="writer.alpha",
        title="Rollback review drift source",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rollback-review-drift",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ),
    )
    approval = review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="先通过",
        evidence_refs=["chapter.40"],
    )

    raw_conn = db_session.get_bind().raw_connection()
    try:
        raw_conn.execute("PRAGMA foreign_keys=OFF")
        raw_conn.execute(
            "UPDATE world_proposal_reviews "
            "SET project_profile_version_id = ?, profile_version = ? "
            "WHERE id = ?",
            (profile_version_two.id, profile_version_two.version, approval.id),
        )
        raw_conn.commit()
        raw_conn.execute("PRAGMA foreign_keys=ON")
    finally:
        raw_conn.close()

    db_session.expire_all()

    with pytest.raises(ValueError, match="binding drift"):
        rollback_review(
            db=db_session,
            review_id=approval.id,
            reviewer_ref="editor.beta",
            reason="脏 review 不允许回滚",
            evidence_refs=["chapter.41"],
        )

    assert db_session.query(WorldProposalReview).filter_by(review_action="rollback").count() == 0


def test_rollback_review_rejects_created_truth_claim_binding_drift_to_wrong_profile(db_session):
    project = Project(name="World Proposal Rollback Claim Wrong Profile")
    genre_profile = GenreProfile(
        canonical_id="generic-world-proposals-rollback-claim-wrong-profile",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()

    profile_version_one = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    profile_version_two = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=2,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add_all([profile_version_one, profile_version_two])
    db_session.commit()

    bundle_one = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version_one.id,
        profile_version=profile_version_one.version,
        created_by="writer.alpha",
        title="Rollback wrong profile source",
    )
    item_one = write_candidate_fact(
        db=db_session,
        bundle_id=bundle_one.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rollback.wrong-profile.source",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ).model_copy(update={"profile_version": profile_version_one.version}),
    )
    approval_one = review_proposal_item(
        db=db_session,
        proposal_item_id=item_one.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="profile one 通过",
        evidence_refs=["chapter.40a"],
    )

    bundle_two = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version_two.id,
        profile_version=profile_version_two.version,
        created_by="writer.beta",
        title="Rollback wrong profile target",
    )
    item_two = write_candidate_fact(
        db=db_session,
        bundle_id=bundle_two.id,
        created_by="writer.beta",
        candidate=_candidate_payload(
            claim_id="claim.hero.rollback.wrong-profile.target",
            subject_ref="char.hero",
            predicate="rank",
            value="marshal",
        ).model_copy(update={"profile_version": profile_version_two.version}),
    )
    approval_two = review_proposal_item(
        db=db_session,
        proposal_item_id=item_two.id,
        reviewer_ref="editor.beta",
        action="approve",
        reason="profile two 通过",
        evidence_refs=["chapter.40b"],
    )

    approval_one.created_truth_claim_id = approval_two.created_truth_claim_id
    db_session.commit()
    db_session.expire_all()

    with pytest.raises(ValueError, match="claim binding drift"):
        rollback_review(
            db=db_session,
            review_id=approval_one.id,
            reviewer_ref="editor.gamma",
            reason="脏 claim 指针不允许跨 profile 回滚",
            evidence_refs=["chapter.41"],
        )

    assert db_session.query(WorldProposalReview).filter_by(review_action="rollback").count() == 0
    assert (
        db_session.query(WorldFactClaim)
        .filter_by(claim_id="claim.hero.rollback.wrong-profile.source")
        .one()
        .claim_status
        == "confirmed"
    )
    assert (
        db_session.query(WorldFactClaim)
        .filter_by(claim_id="claim.hero.rollback.wrong-profile.target")
        .one()
        .claim_status
        == "confirmed"
    )


def test_rollback_review_rejects_created_truth_claim_binding_drift_to_wrong_claim(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Rollback wrong claim source",
    )
    source_item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rollback.wrong-claim.source",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ),
    )
    source_approval = review_proposal_item(
        db=db_session,
        proposal_item_id=source_item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="源 claim 通过",
        evidence_refs=["chapter.41a"],
    )
    target_item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.beta",
        candidate=_candidate_payload(
            claim_id="claim.hero.rollback.wrong-claim.target",
            subject_ref="char.hero",
            predicate="allegiance",
            value="faction.scrapyard",
        ),
    )
    target_approval = review_proposal_item(
        db=db_session,
        proposal_item_id=target_item.id,
        reviewer_ref="editor.beta",
        action="approve",
        reason="目标 claim 通过",
        evidence_refs=["chapter.41b"],
    )

    source_approval.created_truth_claim_id = target_approval.created_truth_claim_id
    db_session.commit()
    db_session.expire_all()

    with pytest.raises(ValueError, match="claim binding drift"):
        rollback_review(
            db=db_session,
            review_id=source_approval.id,
            reviewer_ref="editor.gamma",
            reason="脏 claim 指针不允许回滚别的 claim",
            evidence_refs=["chapter.41c"],
        )

    assert db_session.query(WorldProposalReview).filter_by(review_action="rollback").count() == 0
    assert (
        db_session.query(WorldFactClaim)
        .filter_by(claim_id="claim.hero.rollback.wrong-claim.source")
        .one()
        .claim_status
        == "confirmed"
    )
    assert (
        db_session.query(WorldFactClaim)
        .filter_by(claim_id="claim.hero.rollback.wrong-claim.target")
        .one()
        .claim_status
        == "confirmed"
    )


@pytest.mark.parametrize(
    ("created_truth_claim_id", "expected_error"),
    [
        (None, "missing created_truth_claim_id"),
        ("claim.hero.rollback.missing", "missing truth claim"),
    ],
)
def test_rollback_review_rejects_missing_or_dangling_created_truth_claim_id(
    db_session,
    created_truth_claim_id,
    expected_error,
):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Rollback missing truth claim binding",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rollback.missing-source",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ),
    )
    approval = review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="先通过",
        evidence_refs=["chapter.41d"],
    )

    approval.created_truth_claim_id = created_truth_claim_id
    db_session.commit()
    db_session.expire_all()

    with pytest.raises(ValueError, match=expected_error):
        rollback_review(
            db=db_session,
            review_id=approval.id,
            reviewer_ref="editor.beta",
            reason="脏 claim 指针不允许回滚",
            evidence_refs=["chapter.41e"],
        )

    assert db_session.query(WorldProposalReview).filter_by(review_action="rollback").count() == 0
    assert (
        db_session.query(WorldProposalItem)
        .filter_by(id=item.id)
        .one()
        .item_status
        == "approved"
    )
    assert (
        db_session.query(WorldFactClaim)
        .filter_by(claim_id="claim.hero.rollback.missing-source")
        .one()
        .claim_status
        == "confirmed"
    )


def test_rollback_review_does_not_mask_non_duplicate_integrity_error_as_already_rolled_back(
    db_session,
    monkeypatch,
):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Rollback commit failure classification",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rollback-fk-failure",
            subject_ref="char.hero",
            predicate="allegiance",
            value="faction.scrapyard",
        ),
    )
    approval = review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="先通过",
        evidence_refs=["chapter.42"],
    )

    def fake_commit():
        raise IntegrityError(
            "INSERT INTO world_proposal_reviews ...",
            {},
            sqlite3.IntegrityError("FOREIGN KEY constraint failed"),
        )

    monkeypatch.setattr(db_session, "commit", fake_commit)

    with pytest.raises(ValueError, match="FOREIGN KEY constraint failed") as exc_info:
        rollback_review(
            db=db_session,
            review_id=approval.id,
            reviewer_ref="editor.beta",
            reason="模拟非唯一约束失败",
            evidence_refs=["chapter.43"],
        )

    assert "already been rolled back" not in str(exc_info.value)
    assert db_session.query(WorldProposalReview).filter_by(review_action="rollback").count() == 0
    assert db_session.query(WorldProposalItem).filter_by(id=item.id).one().item_status == "approved"
    assert db_session.query(WorldFactClaim).filter_by(claim_id=approval.created_truth_claim_id).one().claim_status == "confirmed"


def test_approve_with_edits_rejects_stringified_numbers_when_patch_is_strict(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Strict patch typing",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.seq.strict",
            subject_ref="char.hero",
            predicate="seq_note",
            value="entered",
        ),
    )

    with pytest.raises(ValueError, match="edited_fields"):
        review_proposal_item(
            db=db_session,
            proposal_item_id=item.id,
            reviewer_ref="editor.alpha",
            action="approve_with_edits",
            reason="字符串数字不应自动转成 int",
            evidence_refs=["chapter.42"],
            edited_fields={"intra_chapter_seq": "7"},
        )


def test_concurrent_review_from_stale_session_must_fail(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Concurrent review guard",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.concurrent-review",
            subject_ref="char.hero",
            predicate="rank",
            value="captain",
        ),
    )

    local_session = sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind())
    session_a = local_session()
    session_b = local_session()
    try:
        session_b.query(WorldProposalItem).filter_by(id=item.id).one()

        review_proposal_item(
            db=session_a,
            proposal_item_id=item.id,
            reviewer_ref="editor.alpha",
            action="approve",
            reason="先抢到审批",
            evidence_refs=["chapter.43"],
        )

        with pytest.raises(ValueError, match="approved|updated by another session"):
            review_proposal_item(
                db=session_b,
                proposal_item_id=item.id,
                reviewer_ref="editor.beta",
                action="reject",
                reason="陈旧 session 还想继续写",
                evidence_refs=["chapter.44"],
            )
    finally:
        session_a.close()
        session_b.close()

    reviews = db_session.query(WorldProposalReview).filter_by(proposal_item_id=item.id).all()
    claim = db_session.query(WorldFactClaim).filter_by(claim_id="claim.hero.concurrent-review").one()

    assert len(reviews) == 1
    assert reviews[0].review_action == "approve"
    assert claim.claim_status == "confirmed"


def test_rollback_to_review_id_has_database_level_unique_constraint(db_session):
    project, profile_version = _seed_project_profile(db_session)
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Rollback uniqueness",
    )
    item = write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rollback-unique",
            subject_ref="char.hero",
            predicate="allegiance",
            value="faction.scrapyard",
        ),
    )
    approval = review_proposal_item(
        db=db_session,
        proposal_item_id=item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="先通过",
        evidence_refs=["chapter.45"],
    )
    first_rollback = rollback_review(
        db=db_session,
        review_id=approval.id,
        reviewer_ref="editor.beta",
        reason="第一次回滚",
        evidence_refs=["chapter.46"],
    )

    duplicate = WorldProposalReview(
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        bundle_id=bundle.id,
        proposal_item_id=item.id,
        review_action="rollback",
        reviewer_ref="editor.gamma",
        reason="硬插第二条 rollback",
        evidence_refs=["chapter.47"],
        created_truth_claim_id=first_rollback.created_truth_claim_id,
        rollback_to_review_id=approval.id,
        metadata_snapshot={"rollback_point": approval.id},
    )
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_rollback_to_review_id_rejects_cross_bundle_binding_at_db_level(db_session):
    project, profile_version = _seed_project_profile(db_session)
    source_bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.alpha",
        title="Rollback source bundle",
    )
    source_item = write_candidate_fact(
        db=db_session,
        bundle_id=source_bundle.id,
        created_by="writer.alpha",
        candidate=_candidate_payload(
            claim_id="claim.hero.rollback-source",
            subject_ref="char.hero",
            predicate="allegiance",
            value="faction.scrapyard",
        ),
    )
    approval = review_proposal_item(
        db=db_session,
        proposal_item_id=source_item.id,
        reviewer_ref="editor.alpha",
        action="approve",
        reason="源 bundle 通过",
        evidence_refs=["chapter.48"],
    )

    unrelated_bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        created_by="writer.beta",
        title="Rollback unrelated bundle",
    )
    unrelated_item = write_candidate_fact(
        db=db_session,
        bundle_id=unrelated_bundle.id,
        created_by="writer.beta",
        candidate=_candidate_payload(
            claim_id="claim.hero.rollback-unrelated",
            subject_ref="char.hero",
            predicate="rank",
            value="marshal",
        ),
    )

    with pytest.raises(IntegrityError):
        db_session.add(
            WorldProposalReview(
                project_id=project.id,
                project_profile_version_id=profile_version.id,
                profile_version=profile_version.version,
                bundle_id=unrelated_bundle.id,
                proposal_item_id=unrelated_item.id,
                review_action="rollback",
                reviewer_ref="editor.beta",
                reason="试图跨 bundle 回滚",
                evidence_refs=["chapter.49"],
                created_truth_claim_id=approval.created_truth_claim_id,
                rollback_to_review_id=approval.id,
                metadata_snapshot={"rollback_point": approval.id},
            )
        )
        db_session.commit()
    db_session.rollback()

    assert db_session.query(WorldProposalReview).filter_by(review_action="rollback").count() == 0

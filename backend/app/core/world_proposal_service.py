from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    GenreProfile,
    ProjectProfileVersion,
    WorldFactClaim,
    WorldProposalBundle,
    WorldProposalImpactScopeSnapshot,
    WorldProposalItem,
    WorldProposalReview,
)
from app.schemas.world_proposals import ProposalCandidateFactCreate, ProposalClaimEditPatch


APPROVE_ACTIONS = {"approve", "approve_with_edits"}
NON_MERGE_ACTIONS = {"reject", "mark_uncertain"}
ACTIONABLE_REVIEW_ITEM_STATUSES = {"pending", "needs_edit"}
APPROVED_ITEM_STATUSES = {"approved", "approved_with_edits"}
TERMINAL_ITEM_STATUSES = APPROVED_ITEM_STATUSES | {"rejected", "uncertain", "split", "rolled_back"}
SPLITTABLE_ITEM_STATUSES = {"pending", "needs_edit"}
EDITABLE_CLAIM_FIELDS = {
    "chapter_index",
    "intra_chapter_seq",
    "valid_from_anchor_id",
    "valid_to_anchor_id",
    "source_event_ref",
    "evidence_refs",
    "notes",
}


def create_bundle(
    *,
    db: Session,
    project_id: str,
    project_profile_version_id: str,
    profile_version: int,
    created_by: str,
    title: str,
    summary: str = "",
    parent_bundle_id: str | None = None,
) -> WorldProposalBundle:
    _resolve_project_profile_binding_or_error(
        db=db,
        project_id=project_id,
        project_profile_version_id=project_profile_version_id,
        profile_version=profile_version,
        context="bundle",
    )
    _validate_parent_bundle_lineage(
        db=db,
        parent_bundle_id=parent_bundle_id,
        project_id=project_id,
        project_profile_version_id=project_profile_version_id,
        profile_version=profile_version,
    )
    bundle = WorldProposalBundle(
        project_id=project_id,
        project_profile_version_id=project_profile_version_id,
        profile_version=profile_version,
        parent_bundle_id=parent_bundle_id,
        bundle_status="pending",
        title=title,
        summary=summary,
        created_by=created_by,
    )
    db.add(bundle)
    db.commit()
    db.refresh(bundle)
    return bundle


def assemble_bundle(
    *,
    db: Session,
    project_id: str,
    project_profile_version_id: str,
    profile_version: int,
    created_by: str,
    title: str,
    summary: str = "",
    parent_bundle_id: str | None = None,
) -> WorldProposalBundle:
    return create_bundle(
        db=db,
        project_id=project_id,
        project_profile_version_id=project_profile_version_id,
        profile_version=profile_version,
        created_by=created_by,
        title=title,
        summary=summary,
        parent_bundle_id=parent_bundle_id,
    )


def write_candidate_fact(
    *,
    db: Session,
    bundle_id: str,
    created_by: str,
    candidate: ProposalCandidateFactCreate,
) -> WorldProposalItem:
    bundle = _get_bundle_or_error(db=db, bundle_id=bundle_id)
    expected_contract_version = _resolve_bundle_contract_version(db=db, bundle=bundle)
    if candidate.profile_version is not None and candidate.profile_version != bundle.profile_version:
        raise ValueError("candidate profile_version does not match bundle profile_version")
    if (
        candidate.project_profile_version_id is not None
        and candidate.project_profile_version_id != bundle.project_profile_version_id
    ):
        raise ValueError("candidate project_profile_version_id does not match bundle binding")
    _validate_contract_version_match(
        actual_contract_version=candidate.contract_version,
        expected_contract_version=expected_contract_version,
        context="candidate/bundle/profile contract_version mismatch",
    )
    item = WorldProposalItem(
        project_id=bundle.project_id,
        project_profile_version_id=bundle.project_profile_version_id,
        profile_version=bundle.profile_version,
        bundle_id=bundle.id,
        item_status="pending",
        claim_id=candidate.claim_id,
        chapter_index=candidate.chapter_index,
        intra_chapter_seq=candidate.intra_chapter_seq,
        subject_ref=candidate.subject_ref,
        predicate=candidate.predicate,
        object_ref_or_value=candidate.object_ref_or_value,
        claim_layer=candidate.claim_layer,
        valid_from_anchor_id=candidate.valid_from_anchor_id,
        valid_to_anchor_id=candidate.valid_to_anchor_id,
        source_event_ref=candidate.source_event_ref,
        evidence_refs=candidate.evidence_refs,
        authority_type=candidate.authority_type,
        confidence=candidate.confidence,
        notes=candidate.notes,
        contract_version=candidate.contract_version,
        created_by=created_by,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def calculate_bundle_impact_scope(*, db: Session, bundle_id: str) -> WorldProposalImpactScopeSnapshot:
    bundle = _get_bundle_or_error(db=db, bundle_id=bundle_id)
    items = db.query(WorldProposalItem).filter(WorldProposalItem.bundle_id == bundle_id).all()
    affected_subject_refs = sorted({item.subject_ref for item in items})
    affected_predicates = sorted({item.predicate for item in items})
    candidate_item_ids = [item.id for item in items]

    truth_claims = []
    for item in items:
        truth_claims.extend(
            db.query(WorldFactClaim)
            .filter(
                WorldFactClaim.project_id == bundle.project_id,
                WorldFactClaim.profile_version == bundle.profile_version,
                WorldFactClaim.subject_ref == item.subject_ref,
                WorldFactClaim.predicate == item.predicate,
                WorldFactClaim.claim_layer == "truth",
            )
            .all()
        )

    snapshot = WorldProposalImpactScopeSnapshot(
        project_id=bundle.project_id,
        project_profile_version_id=bundle.project_profile_version_id,
        profile_version=bundle.profile_version,
        bundle_id=bundle.id,
        affected_subject_refs=affected_subject_refs,
        affected_predicates=affected_predicates,
        affected_truth_claim_ids=sorted({claim.claim_id for claim in truth_claims}),
        candidate_item_ids=candidate_item_ids,
        summary={
            "candidate_count": len(items),
            "existing_truth_count": len({claim.claim_id for claim in truth_claims}),
        },
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def review_proposal_item(
    *,
    db: Session,
    proposal_item_id: str,
    reviewer_ref: str,
    action: str,
    reason: str,
    evidence_refs: Iterable[str],
    edited_fields: dict[str, Any] | None = None,
) -> WorldProposalReview:
    if action not in APPROVE_ACTIONS | NON_MERGE_ACTIONS:
        raise ValueError(f"unsupported review action: {action}")
    if action == "approve" and edited_fields:
        raise ValueError("approve does not accept edited_fields; use approve_with_edits instead")

    item_snapshot = _get_item_snapshot(db=db, proposal_item_id=proposal_item_id)
    _ensure_item_allows_review(status=item_snapshot["item_status"], item_id=proposal_item_id, action=action)
    bundle = _get_bundle_or_error(
        db=db,
        bundle_id=item_snapshot["bundle_id"],
        not_found_message=(
            f"proposal item {proposal_item_id} references missing bundle {item_snapshot['bundle_id']}"
        ),
    )
    _validate_item_bundle_profile_binding(item_snapshot=item_snapshot, bundle=bundle)
    expected_contract_version = _resolve_bundle_contract_version(db=db, bundle=bundle)
    edited_fields = _validate_edited_fields(edited_fields or {})
    next_item_status = "approved" if action == "approve" else "approved_with_edits"
    if action == "reject":
        next_item_status = "rejected"
    elif action == "mark_uncertain":
        next_item_status = "uncertain"
    _validate_contract_version_match(
        actual_contract_version=item_snapshot["contract_version"],
        expected_contract_version=expected_contract_version,
        context="proposal item/bundle/profile/claim contract_version mismatch",
    )
    review = WorldProposalReview(
        project_id=item_snapshot["project_id"],
        project_profile_version_id=item_snapshot["project_profile_version_id"],
        profile_version=item_snapshot["profile_version"],
        bundle_id=item_snapshot["bundle_id"],
        proposal_item_id=item_snapshot["id"],
        review_action=action,
        reviewer_ref=reviewer_ref,
        reason=reason,
        evidence_refs=list(evidence_refs),
        edited_fields=edited_fields,
    )

    rowcount = db.execute(
        update(WorldProposalItem)
        .where(
            WorldProposalItem.id == proposal_item_id,
            WorldProposalItem.item_status.in_(ACTIONABLE_REVIEW_ITEM_STATUSES),
        )
        .values(
            item_status=next_item_status,
            updated_at=datetime.now(timezone.utc),
        )
    ).rowcount
    if rowcount != 1:
        db.rollback()
        raise ValueError(f"proposal item {proposal_item_id} was updated by another session and can no longer be reviewed")

    try:
        if action in APPROVE_ACTIONS:
            claim_payload = {
                "claim_id": item_snapshot["claim_id"],
                "chapter_index": item_snapshot["chapter_index"],
                "intra_chapter_seq": item_snapshot["intra_chapter_seq"],
                "subject_ref": item_snapshot["subject_ref"],
                "predicate": item_snapshot["predicate"],
                "object_ref_or_value": item_snapshot["object_ref_or_value"],
                "claim_layer": "truth",
                "valid_from_anchor_id": item_snapshot["valid_from_anchor_id"],
                "valid_to_anchor_id": item_snapshot["valid_to_anchor_id"],
                "source_event_ref": item_snapshot["source_event_ref"],
                "evidence_refs": item_snapshot["evidence_refs"],
                "authority_type": item_snapshot["authority_type"],
                "confidence": item_snapshot["confidence"],
                "notes": item_snapshot["notes"],
                "contract_version": item_snapshot["contract_version"],
            }
            claim_payload.update(edited_fields)
            claim = WorldFactClaim(
                project_id=item_snapshot["project_id"],
                project_profile_version_id=item_snapshot["project_profile_version_id"],
                profile_version=item_snapshot["profile_version"],
                claim_status="confirmed",
                **claim_payload,
            )
            db.add(claim)
            db.flush()
            db.execute(
                update(WorldProposalItem)
                .where(
                    WorldProposalItem.id == proposal_item_id,
                    WorldProposalItem.item_status == next_item_status,
                )
                .values(
                    approved_claim_id=claim.claim_id,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            review.created_truth_claim_id = claim.claim_id

        db.add(review)
        _refresh_bundle_status(db=db, bundle=bundle)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _translate_review_integrity_error(
            exc=exc,
            proposal_item_id=proposal_item_id,
            claim_id=item_snapshot["claim_id"],
        ) from exc
    db.refresh(review)
    db.refresh(bundle)
    return review


def split_bundle(
    *,
    db: Session,
    bundle_id: str,
    item_ids: list[str],
    reviewer_ref: str,
    reason: str,
    evidence_refs: Iterable[str],
) -> WorldProposalBundle:
    bundle = _get_bundle_or_error(db=db, bundle_id=bundle_id)
    requested_item_ids = list(item_ids)
    if not requested_item_ids:
        raise ValueError("item_ids must not be empty when splitting a bundle")
    unique_item_ids = set(requested_item_ids)
    items = (
        db.query(WorldProposalItem)
        .filter(
            WorldProposalItem.bundle_id == bundle_id,
            WorldProposalItem.id.in_(unique_item_ids),
        )
        .all()
    )
    found_item_ids = {item.id for item in items}
    missing_item_ids = [item_id for item_id in requested_item_ids if item_id not in found_item_ids]
    if missing_item_ids:
        raise ValueError(f"item_ids contains unknown items for bundle {bundle_id}: {missing_item_ids}")
    invalid_items = [item.id for item in items if item.item_status not in SPLITTABLE_ITEM_STATUSES]
    if invalid_items:
        raise ValueError(
            f"split is only allowed for items in {sorted(SPLITTABLE_ITEM_STATUSES)}; blocked item_ids: {invalid_items}"
        )
    for item in items:
        _validate_item_bundle_profile_binding(
            item_snapshot={
                "id": item.id,
                "project_id": item.project_id,
                "project_profile_version_id": item.project_profile_version_id,
                "profile_version": item.profile_version,
                "bundle_id": item.bundle_id,
            },
            bundle=bundle,
        )
    child_bundle = WorldProposalBundle(
        project_id=bundle.project_id,
        project_profile_version_id=bundle.project_profile_version_id,
        profile_version=bundle.profile_version,
        parent_bundle_id=bundle.id,
        bundle_status="pending",
        title=f"{bundle.title} / split",
        summary=reason,
        created_by=reviewer_ref,
    )
    db.add(child_bundle)
    db.flush()

    for item in items:
        child_item = WorldProposalItem(
            project_id=item.project_id,
            project_profile_version_id=item.project_profile_version_id,
            profile_version=item.profile_version,
            bundle_id=child_bundle.id,
            parent_item_id=item.id,
            item_status="pending",
            claim_id=item.claim_id,
            chapter_index=item.chapter_index,
            intra_chapter_seq=item.intra_chapter_seq,
            subject_ref=item.subject_ref,
            predicate=item.predicate,
            object_ref_or_value=item.object_ref_or_value,
            claim_layer=item.claim_layer,
            valid_from_anchor_id=item.valid_from_anchor_id,
            valid_to_anchor_id=item.valid_to_anchor_id,
            source_event_ref=item.source_event_ref,
            evidence_refs=item.evidence_refs,
            authority_type=item.authority_type,
            confidence=item.confidence,
            notes=item.notes,
            contract_version=item.contract_version,
            created_by=reviewer_ref,
        )
        item.item_status = "split"
        db.add(child_item)
        db.add(
            WorldProposalReview(
                project_id=item.project_id,
                project_profile_version_id=item.project_profile_version_id,
                profile_version=item.profile_version,
                bundle_id=item.bundle_id,
                proposal_item_id=item.id,
                review_action="split",
                reviewer_ref=reviewer_ref,
                reason=reason,
                evidence_refs=list(evidence_refs),
                metadata_snapshot={"child_bundle_id": child_bundle.id},
            )
        )

    _refresh_bundle_status(db=db, bundle=bundle)
    db.commit()
    db.refresh(child_bundle)
    return child_bundle


def rollback_review(
    *,
    db: Session,
    review_id: str,
    reviewer_ref: str,
    reason: str,
    evidence_refs: Iterable[str],
) -> WorldProposalReview:
    review = db.query(WorldProposalReview).filter(WorldProposalReview.id == review_id).one_or_none()
    if review is None:
        raise ValueError(f"approval review {review_id} does not exist")
    if review.review_action not in APPROVE_ACTIONS:
        raise ValueError("only approval reviews can be rolled back")
    existing_rollback = (
        db.query(WorldProposalReview)
        .filter(WorldProposalReview.rollback_to_review_id == review.id)
        .first()
    )
    if existing_rollback is not None:
        raise ValueError(f"approval review {review.id} has already been rolled back")

    if review.proposal_item_id is None:
        raise ValueError(f"approval review {review.id} is missing proposal_item_id and cannot be rolled back")
    item = db.query(WorldProposalItem).filter(WorldProposalItem.id == review.proposal_item_id).one_or_none()
    if item is None:
        raise ValueError(
            f"approval review {review.id} references missing proposal item {review.proposal_item_id}"
        )
    bundle = _get_bundle_or_error(
        db=db,
        bundle_id=item.bundle_id,
        not_found_message=f"proposal item {item.id} references missing bundle {item.bundle_id}",
    )
    _validate_item_bundle_profile_binding(
        item_snapshot={
            "id": item.id,
            "project_id": item.project_id,
            "project_profile_version_id": item.project_profile_version_id,
            "profile_version": item.profile_version,
            "bundle_id": item.bundle_id,
        },
        bundle=bundle,
    )
    _validate_review_source_binding(review=review, item=item, bundle=bundle)
    claim = _resolve_rollback_truth_claim(
        db=db,
        review=review,
        item=item,
        bundle=bundle,
    )
    if item.item_status == "rolled_back" or claim.claim_status == "rolled_back":
        raise ValueError(f"approval review {review.id} has already been rolled back")
    claim.claim_status = "rolled_back"
    item.item_status = "rolled_back"

    rollback = WorldProposalReview(
        project_id=item.project_id,
        project_profile_version_id=item.project_profile_version_id,
        profile_version=item.profile_version,
        bundle_id=item.bundle_id,
        proposal_item_id=item.id,
        review_action="rollback",
        reviewer_ref=reviewer_ref,
        reason=reason,
        evidence_refs=list(evidence_refs),
        created_truth_claim_id=claim.claim_id,
        rollback_to_review_id=review.id,
        metadata_snapshot={"rollback_point": review.id},
    )
    db.add(rollback)
    _refresh_bundle_status(db=db, bundle=bundle)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _is_duplicate_rollback_integrity_error(exc):
            raise ValueError(f"approval review {review.id} has already been rolled back") from exc
        raise ValueError(f"rollback review {review.id} failed to commit: {_describe_integrity_error(exc)}") from exc
    db.refresh(rollback)
    return rollback


def list_authoritative_truth_claims(
    *,
    db: Session,
    project_id: str,
    profile_version: int,
) -> list[WorldFactClaim]:
    return (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.profile_version == profile_version,
            WorldFactClaim.claim_layer == "truth",
            WorldFactClaim.claim_status == "confirmed",
        )
        .order_by(WorldFactClaim.chapter_index.asc(), WorldFactClaim.intra_chapter_seq.asc(), WorldFactClaim.claim_id.asc())
        .all()
    )


def _refresh_bundle_status(*, db: Session, bundle: WorldProposalBundle) -> None:
    items = db.query(WorldProposalItem).filter(WorldProposalItem.bundle_id == bundle.id).all()
    statuses = {item.item_status for item in items}
    if not statuses:
        bundle.bundle_status = "pending"
        return
    if statuses <= {"approved", "approved_with_edits"}:
        bundle.bundle_status = "approved"
        return
    if "approved" in statuses or "approved_with_edits" in statuses:
        bundle.bundle_status = "partially_approved"
        return
    if statuses == {"rolled_back"}:
        bundle.bundle_status = "rolled_back"
        return
    if statuses == {"rejected"}:
        bundle.bundle_status = "rejected"
        return
    if statuses == {"uncertain"}:
        bundle.bundle_status = "uncertain"
        return
    bundle.bundle_status = "pending"


def _get_item_snapshot(*, db: Session, proposal_item_id: str) -> dict[str, Any]:
    row = db.execute(
        select(
            WorldProposalItem.id,
            WorldProposalItem.project_id,
            WorldProposalItem.project_profile_version_id,
            WorldProposalItem.profile_version,
            WorldProposalItem.bundle_id,
            WorldProposalItem.item_status,
            WorldProposalItem.claim_id,
            WorldProposalItem.chapter_index,
            WorldProposalItem.intra_chapter_seq,
            WorldProposalItem.subject_ref,
            WorldProposalItem.predicate,
            WorldProposalItem.object_ref_or_value,
            WorldProposalItem.valid_from_anchor_id,
            WorldProposalItem.valid_to_anchor_id,
            WorldProposalItem.source_event_ref,
            WorldProposalItem.evidence_refs,
            WorldProposalItem.authority_type,
            WorldProposalItem.confidence,
            WorldProposalItem.notes,
            WorldProposalItem.contract_version,
        ).where(WorldProposalItem.id == proposal_item_id)
    ).mappings().one_or_none()
    if row is None:
        raise ValueError(f"proposal item {proposal_item_id} does not exist")
    return dict(row)


def _ensure_item_allows_review(*, status: str, item_id: str, action: str) -> None:
    if status in ACTIONABLE_REVIEW_ITEM_STATUSES:
        return
    if status in APPROVED_ITEM_STATUSES:
        raise ValueError(
            f"item {item_id} is already {status}; use explicit rollback before action {action}"
        )
    if status in TERMINAL_ITEM_STATUSES:
        raise ValueError(f"item {item_id} is in terminal status {status} and cannot accept action {action}")
    raise ValueError(f"item {item_id} is in unsupported status {status}")


def _validate_edited_fields(edited_fields: dict[str, Any]) -> None:
    invalid_fields = sorted(set(edited_fields) - EDITABLE_CLAIM_FIELDS)
    if invalid_fields:
        raise ValueError(
            "edited_fields contains forbidden keys; allowed keys are "
            f"{sorted(EDITABLE_CLAIM_FIELDS)}. Got invalid keys: {invalid_fields}"
        )
    try:
        patch = ProposalClaimEditPatch(**edited_fields)
    except Exception as exc:  # pydantic normalizes all supported value checks here
        raise ValueError(f"edited_fields contains invalid values: {exc}") from exc
    return patch.model_dump(exclude_unset=True)


def _validate_item_bundle_profile_binding(*, item_snapshot: dict[str, Any], bundle: WorldProposalBundle) -> None:
    if (
        item_snapshot["project_id"] != bundle.project_id
        or item_snapshot["project_profile_version_id"] != bundle.project_profile_version_id
        or item_snapshot["profile_version"] != bundle.profile_version
        or item_snapshot["bundle_id"] != bundle.id
    ):
        raise ValueError(
            "proposal item/bundle profile binding mismatch: "
            f"item={item_snapshot['project_profile_version_id']}/{item_snapshot['profile_version']} "
            f"bundle={bundle.project_profile_version_id}/{bundle.profile_version}"
        )


def _validate_review_source_binding(
    *,
    review: WorldProposalReview,
    item: WorldProposalItem,
    bundle: WorldProposalBundle,
) -> None:
    if (
        review.project_id != item.project_id
        or review.project_profile_version_id != item.project_profile_version_id
        or review.profile_version != item.profile_version
        or review.bundle_id != item.bundle_id
        or review.project_id != bundle.project_id
        or review.project_profile_version_id != bundle.project_profile_version_id
        or review.profile_version != bundle.profile_version
        or review.bundle_id != bundle.id
    ):
        raise ValueError(
            "approval review/source binding drift: "
            f"review={review.project_id}/{review.project_profile_version_id}/{review.profile_version}/{review.bundle_id}, "
            f"item={item.project_id}/{item.project_profile_version_id}/{item.profile_version}/{item.bundle_id}, "
            f"bundle={bundle.project_id}/{bundle.project_profile_version_id}/{bundle.profile_version}/{bundle.id}"
        )


def _resolve_rollback_truth_claim(
    *,
    db: Session,
    review: WorldProposalReview,
    item: WorldProposalItem,
    bundle: WorldProposalBundle,
) -> WorldFactClaim:
    if review.created_truth_claim_id is None:
        raise ValueError(f"approval review {review.id} is missing created_truth_claim_id and cannot be rolled back")

    claim = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == item.project_id,
            WorldFactClaim.claim_id == review.created_truth_claim_id,
        )
        .one_or_none()
    )
    if claim is None:
        raise ValueError(
            f"approval review {review.id} references missing truth claim {review.created_truth_claim_id}"
        )

    if (
        claim.project_profile_version_id != item.project_profile_version_id
        or claim.profile_version != item.profile_version
        or claim.claim_id != item.claim_id
        or claim.claim_layer != "truth"
        or claim.project_id != review.project_id
        or claim.project_id != bundle.project_id
    ):
        raise ValueError(
            "approval review/created truth claim binding drift: "
            f"review={review.project_id}/{review.project_profile_version_id}/{review.profile_version}/{review.bundle_id}/{review.created_truth_claim_id}, "
            f"item={item.project_id}/{item.project_profile_version_id}/{item.profile_version}/{item.bundle_id}/{item.claim_id}, "
            f"bundle={bundle.project_id}/{bundle.project_profile_version_id}/{bundle.profile_version}/{bundle.id}, "
            f"claim={claim.project_id}/{claim.project_profile_version_id}/{claim.profile_version}/{claim.claim_id}/{claim.claim_layer}"
        )
    return claim


def _is_duplicate_rollback_integrity_error(exc: IntegrityError) -> bool:
    message = f"{exc.orig} {exc}".lower()
    rollback_constraint_hit = (
        "rollback_to_review_id" in message
        or "uq_world_proposal_reviews_rollback_to_review_id" in message
    )
    duplicate_semantics_hit = (
        "unique constraint failed" in message
        or "duplicate key value violates unique constraint" in message
    )
    return rollback_constraint_hit and duplicate_semantics_hit


def _describe_integrity_error(exc: IntegrityError) -> str:
    if exc.orig is not None:
        return str(exc.orig)
    return str(exc)


def _translate_review_integrity_error(
    *,
    exc: IntegrityError,
    proposal_item_id: str,
    claim_id: str,
) -> ValueError:
    if _is_duplicate_truth_claim_id_integrity_error(exc):
        return ValueError(
            f"proposal item {proposal_item_id} cannot be approved because truth claim_id {claim_id} already exists"
        )
    return ValueError(
        f"proposal review for item {proposal_item_id} failed to persist: {_describe_integrity_error(exc)}"
    )


def _is_duplicate_truth_claim_id_integrity_error(exc: IntegrityError) -> bool:
    message = f"{exc.orig} {exc}".lower()
    constraint_hit = (
        "uq_world_fact_claims_project_claim_id" in message
        or "world_fact_claims.project_id, world_fact_claims.claim_id" in message
    )
    duplicate_semantics_hit = (
        "unique constraint failed" in message
        or "duplicate key value violates unique constraint" in message
    )
    return constraint_hit and duplicate_semantics_hit


def _resolve_bundle_contract_version(*, db: Session, bundle: WorldProposalBundle) -> str:
    project_profile = _resolve_project_profile_binding_or_error(
        db=db,
        project_id=bundle.project_id,
        project_profile_version_id=bundle.project_profile_version_id,
        profile_version=bundle.profile_version,
        context=f"proposal bundle {bundle.id}",
    )
    genre_profile = _get_genre_profile_or_error(
        db=db,
        genre_profile_id=project_profile.genre_profile_id,
        not_found_message=(
            f"project profile version {project_profile.id} references missing genre profile "
            f"{project_profile.genre_profile_id}"
        ),
    )
    _validate_contract_version_match(
        actual_contract_version=project_profile.contract_version,
        expected_contract_version=genre_profile.contract_version,
        context="bundle/profile contract_version mismatch",
    )
    return project_profile.contract_version


def _validate_contract_version_match(
    *,
    actual_contract_version: str,
    expected_contract_version: str,
    context: str,
) -> None:
    if actual_contract_version != expected_contract_version:
        raise ValueError(f"{context}: expected {expected_contract_version}, got {actual_contract_version}")


def _validate_parent_bundle_lineage(
    *,
    db: Session,
    parent_bundle_id: str | None,
    project_id: str,
    project_profile_version_id: str,
    profile_version: int,
) -> None:
    if parent_bundle_id is None:
        return
    parent_bundle = _get_bundle_or_error(db=db, bundle_id=parent_bundle_id)
    if (
        parent_bundle.project_id != project_id
        or parent_bundle.project_profile_version_id != project_profile_version_id
        or parent_bundle.profile_version != profile_version
    ):
        raise ValueError(
            "parent bundle lineage mismatch: "
            f"parent={parent_bundle.project_id}/{parent_bundle.project_profile_version_id}/{parent_bundle.profile_version}, "
            f"child={project_id}/{project_profile_version_id}/{profile_version}"
        )


def _get_bundle_or_error(
    *,
    db: Session,
    bundle_id: str,
    not_found_message: str | None = None,
) -> WorldProposalBundle:
    bundle = db.query(WorldProposalBundle).filter(WorldProposalBundle.id == bundle_id).one_or_none()
    if bundle is None:
        raise ValueError(not_found_message or f"proposal bundle {bundle_id} does not exist")
    return bundle


def _get_project_profile_version_or_error(
    *,
    db: Session,
    project_profile_version_id: str,
    not_found_message: str | None = None,
) -> ProjectProfileVersion:
    project_profile = (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.id == project_profile_version_id)
        .one_or_none()
    )
    if project_profile is None:
        raise ValueError(
            not_found_message
            or f"project profile version {project_profile_version_id} does not exist"
        )
    return project_profile


def _resolve_project_profile_binding_or_error(
    *,
    db: Session,
    project_id: str,
    project_profile_version_id: str,
    profile_version: int,
    context: str,
) -> ProjectProfileVersion:
    project_profile = _get_project_profile_version_or_error(
        db=db,
        project_profile_version_id=project_profile_version_id,
        not_found_message=(
            f"{context} references missing project profile version {project_profile_version_id}"
            if context.startswith("proposal bundle ")
            else f"project profile version {project_profile_version_id} does not exist"
        ),
    )
    if project_profile.project_id != project_id or project_profile.version != profile_version:
        raise ValueError(
            "bundle profile binding mismatch: "
            f"bundle={project_profile_version_id}/{profile_version}, "
            f"project_profile={project_profile.id}/{project_profile.version}"
        )
    return project_profile


def _get_genre_profile_or_error(
    *,
    db: Session,
    genre_profile_id: str,
    not_found_message: str | None = None,
) -> GenreProfile:
    genre_profile = db.query(GenreProfile).filter(GenreProfile.id == genre_profile_id).one_or_none()
    if genre_profile is None:
        raise ValueError(not_found_message or f"genre profile {genre_profile_id} does not exist")
    return genre_profile


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.world_projection import FactRecord, project_snapshot, project_subject_knowledge, project_world_truth
from app.core.world_proposal_service import (
    calculate_bundle_impact_scope,
    review_proposal_item,
    rollback_review,
    split_bundle,
)
from app.core.world_replay import ledger_event_from_world_event
from app.core.world_time_normalizer import build_anchor_time_index
from app.db import get_db
from app.models import (
    Project,
    ChapterContent,
    ProjectProfileVersion,
    WorldEvent,
    WorldFactClaim,
    WorldProposalBundle,
    WorldProposalImpactScopeSnapshot,
    WorldProposalItem,
    WorldProposalReview,
    WorldTimelineAnchor,
)
from app.schemas import (
    PaginatedProposalBundlesOut,
    ProjectWorldOverviewOut,
    ProposalBundleDetailOut,
    ProposalBundleOut,
    ProposalBundleSplitCreate,
    ProposalReviewCreate,
    ProposalReviewOut,
    ProposalReviewRollbackCreate,
    WorldProjectionOut,
)

router = APIRouter(prefix="/api/v1/projects/{project_id}/world-model", tags=["world-model"])


@router.get("", response_model=ProjectWorldOverviewOut)
def get_world_model_overview(project_id: str, db: Session = Depends(get_db)):
    _require_project(db=db, project_id=project_id)
    profile = _get_current_profile(db=db, project_id=project_id)
    if profile is None:
        return ProjectWorldOverviewOut(project_profile=None, projection=None)

    anchors = (
        db.query(WorldTimelineAnchor)
        .filter(
            WorldTimelineAnchor.project_id == project_id,
            WorldTimelineAnchor.profile_version == profile.version,
        )
        .order_by(
            WorldTimelineAnchor.chapter_index.asc(),
            WorldTimelineAnchor.intra_chapter_seq.asc(),
            WorldTimelineAnchor.anchor_id.asc(),
        )
        .all()
    )
    events = (
        db.query(WorldEvent)
        .filter(
            WorldEvent.project_id == project_id,
            WorldEvent.project_profile_version_id == profile.id,
            WorldEvent.profile_version == profile.version,
        )
        .order_by(
            WorldEvent.chapter_index.asc(),
            WorldEvent.intra_chapter_seq.asc(),
            WorldEvent.event_id.asc(),
        )
        .all()
    )
    facts = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.project_profile_version_id == profile.id,
            WorldFactClaim.profile_version == profile.version,
        )
        .order_by(
            WorldFactClaim.chapter_index.asc(),
            WorldFactClaim.intra_chapter_seq.asc(),
            WorldFactClaim.claim_id.asc(),
        )
        .all()
    )
    try:
        anchor_index = build_anchor_time_index(anchors)
        projection = project_world_truth(
            events=[ledger_event_from_world_event(event, anchor_index=anchor_index) for event in events],
            facts=[_fact_record_from_model(fact) for fact in facts],
            anchors=anchors,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProjectWorldOverviewOut(
        project_profile=profile,
        projection=WorldProjectionOut(
            view_type="current_truth",
            **projection,
        ),
    )


@router.get("/subject-knowledge", response_model=ProjectWorldOverviewOut)
def get_subject_knowledge(
    project_id: str,
    subject_ref: str,
    db: Session = Depends(get_db),
):
    _require_project(db=db, project_id=project_id)
    profile = _get_current_profile(db=db, project_id=project_id)
    if profile is None:
        return ProjectWorldOverviewOut(project_profile=None, projection=None)

    anchors = (
        db.query(WorldTimelineAnchor)
        .filter(
            WorldTimelineAnchor.project_id == project_id,
            WorldTimelineAnchor.profile_version == profile.version,
        )
        .order_by(
            WorldTimelineAnchor.chapter_index.asc(),
            WorldTimelineAnchor.intra_chapter_seq.asc(),
            WorldTimelineAnchor.anchor_id.asc(),
        )
        .all()
    )
    events = (
        db.query(WorldEvent)
        .filter(
            WorldEvent.project_id == project_id,
            WorldEvent.project_profile_version_id == profile.id,
            WorldEvent.profile_version == profile.version,
        )
        .order_by(
            WorldEvent.chapter_index.asc(),
            WorldEvent.intra_chapter_seq.asc(),
            WorldEvent.event_id.asc(),
        )
        .all()
    )
    facts = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.project_profile_version_id == profile.id,
            WorldFactClaim.profile_version == profile.version,
        )
        .order_by(
            WorldFactClaim.chapter_index.asc(),
            WorldFactClaim.intra_chapter_seq.asc(),
            WorldFactClaim.claim_id.asc(),
        )
        .all()
    )
    try:
        anchor_index = build_anchor_time_index(anchors)
        projection = project_subject_knowledge(
            subject_ref=subject_ref,
            events=[ledger_event_from_world_event(event, anchor_index=anchor_index) for event in events],
            facts=[_fact_record_from_model(fact) for fact in facts],
            anchors=anchors,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProjectWorldOverviewOut(
        project_profile=profile,
        projection=WorldProjectionOut(
            view_type="subject_knowledge",
            **projection,
        ),
    )


@router.get("/snapshot", response_model=ProjectWorldOverviewOut)
def get_chapter_snapshot(
    project_id: str,
    chapter_index: int = Query(..., ge=1),
    db: Session = Depends(get_db),
):
    _require_project(db=db, project_id=project_id)
    _require_chapter(db=db, project_id=project_id, chapter_index=chapter_index)
    profile = _get_current_profile(db=db, project_id=project_id)
    if profile is None:
        return ProjectWorldOverviewOut(project_profile=None, projection=None)

    anchors = (
        db.query(WorldTimelineAnchor)
        .filter(
            WorldTimelineAnchor.project_id == project_id,
            WorldTimelineAnchor.profile_version == profile.version,
        )
        .order_by(
            WorldTimelineAnchor.chapter_index.asc(),
            WorldTimelineAnchor.intra_chapter_seq.asc(),
            WorldTimelineAnchor.anchor_id.asc(),
        )
        .all()
    )
    events = (
        db.query(WorldEvent)
        .filter(
            WorldEvent.project_id == project_id,
            WorldEvent.project_profile_version_id == profile.id,
            WorldEvent.profile_version == profile.version,
        )
        .order_by(
            WorldEvent.chapter_index.asc(),
            WorldEvent.intra_chapter_seq.asc(),
            WorldEvent.event_id.asc(),
        )
        .all()
    )
    facts = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.project_profile_version_id == profile.id,
            WorldFactClaim.profile_version == profile.version,
        )
        .order_by(
            WorldFactClaim.chapter_index.asc(),
            WorldFactClaim.intra_chapter_seq.asc(),
            WorldFactClaim.claim_id.asc(),
        )
        .all()
    )
    try:
        anchor_index = build_anchor_time_index(anchors)
        projection = project_snapshot(
            events=[ledger_event_from_world_event(event, anchor_index=anchor_index) for event in events],
            facts=[_fact_record_from_model(fact) for fact in facts],
            chapter_index=chapter_index,
            anchors=anchors,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProjectWorldOverviewOut(
        project_profile=profile,
        projection=WorldProjectionOut(
            view_type="chapter_snapshot",
            **projection,
        ),
    )


@router.get("/proposal-bundles", response_model=PaginatedProposalBundlesOut)
def list_world_proposal_bundles(
    project_id: str,
    offset: int = 0,
    limit: int = 20,
    bundle_status: str | None = None,
    item_status: str | None = None,
    profile_version: int | None = None,
    db: Session = Depends(get_db),
):
    _require_project(db=db, project_id=project_id)
    current_profile = _get_current_profile(db=db, project_id=project_id)
    if current_profile is None:
        return PaginatedProposalBundlesOut(items=[], total=0, offset=offset, limit=limit)
    query = db.query(WorldProposalBundle).filter(
        WorldProposalBundle.project_id == project_id,
        WorldProposalBundle.project_profile_version_id == current_profile.id,
        WorldProposalBundle.profile_version == current_profile.version,
    )
    if bundle_status is not None:
        query = query.filter(WorldProposalBundle.bundle_status == bundle_status)
    if profile_version is not None:
        query = query.filter(WorldProposalBundle.profile_version == profile_version)
    if item_status is not None:
        subq = (
            db.query(WorldProposalItem.bundle_id)
            .filter(WorldProposalItem.item_status == item_status)
            .subquery()
        )
        query = query.filter(WorldProposalBundle.id.in_(subq))
    total = query.count()
    items = (
        query.order_by(WorldProposalBundle.updated_at.desc(), WorldProposalBundle.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return PaginatedProposalBundlesOut(items=items, total=total, offset=offset, limit=limit)


@router.get("/proposal-bundles/{bundle_id}", response_model=ProposalBundleDetailOut)
def get_world_proposal_bundle(project_id: str, bundle_id: str, db: Session = Depends(get_db)):
    _require_project(db=db, project_id=project_id)
    bundle = _get_project_bundle_or_404(db=db, project_id=project_id, bundle_id=bundle_id)
    _require_current_profile_scope(
        db=db,
        project_id=project_id,
        project_profile_version_id=bundle.project_profile_version_id,
        profile_version=bundle.profile_version,
        resource_label="Proposal bundle",
    )
    return _build_bundle_detail(db=db, project_id=project_id, bundle_id=bundle_id)


@router.post("/proposal-items/{proposal_item_id}/review", response_model=ProposalReviewOut)
def review_world_proposal_item(
    project_id: str,
    proposal_item_id: str,
    payload: ProposalReviewCreate,
    db: Session = Depends(get_db),
):
    item = (
        db.query(WorldProposalItem)
        .filter(
            WorldProposalItem.id == proposal_item_id,
            WorldProposalItem.project_id == project_id,
        )
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Proposal item not found")
    _require_current_profile_scope(
        db=db,
        project_id=project_id,
        project_profile_version_id=item.project_profile_version_id,
        profile_version=item.profile_version,
        resource_label="Proposal item",
    )
    try:
        return review_proposal_item(
            db=db,
            proposal_item_id=proposal_item_id,
            reviewer_ref=payload.reviewer_ref,
            action=payload.action,
            reason=payload.reason,
            evidence_refs=payload.evidence_refs,
            edited_fields=payload.edited_fields,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/proposal-bundles/{bundle_id}/split", response_model=ProposalBundleDetailOut)
def split_world_proposal_bundle(
    project_id: str,
    bundle_id: str,
    payload: ProposalBundleSplitCreate,
    db: Session = Depends(get_db),
):
    bundle = (
        db.query(WorldProposalBundle)
        .filter(
            WorldProposalBundle.id == bundle_id,
            WorldProposalBundle.project_id == project_id,
        )
        .first()
    )
    if bundle is None:
        raise HTTPException(status_code=404, detail="Proposal bundle not found")
    _require_current_profile_scope(
        db=db,
        project_id=project_id,
        project_profile_version_id=bundle.project_profile_version_id,
        profile_version=bundle.profile_version,
        resource_label="Proposal bundle",
    )
    try:
        child_bundle = split_bundle(
            db=db,
            bundle_id=bundle_id,
            item_ids=payload.item_ids,
            reviewer_ref=payload.reviewer_ref,
            reason=payload.reason,
            evidence_refs=payload.evidence_refs,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _build_bundle_detail(db=db, project_id=project_id, bundle_id=child_bundle.id)


@router.post("/reviews/{review_id}/rollback", response_model=ProposalReviewOut)
def rollback_world_proposal_review(
    project_id: str,
    review_id: str,
    payload: ProposalReviewRollbackCreate,
    db: Session = Depends(get_db),
):
    review = (
        db.query(WorldProposalReview)
        .filter(
            WorldProposalReview.id == review_id,
            WorldProposalReview.project_id == project_id,
        )
        .first()
    )
    if review is None:
        raise HTTPException(status_code=404, detail="Proposal review not found")
    _require_current_profile_scope(
        db=db,
        project_id=project_id,
        project_profile_version_id=review.project_profile_version_id,
        profile_version=review.profile_version,
        resource_label="Proposal review",
    )
    try:
        return rollback_review(
            db=db,
            review_id=review_id,
            reviewer_ref=payload.reviewer_ref,
            reason=payload.reason,
            evidence_refs=payload.evidence_refs,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _require_project(*, db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _require_chapter(*, db: Session, project_id: str, chapter_index: int) -> ChapterContent:
    chapter = (
        db.query(ChapterContent)
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.chapter_index == chapter_index,
        )
        .first()
    )
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


def _get_current_profile(*, db: Session, project_id: str) -> ProjectProfileVersion | None:
    return (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc(), ProjectProfileVersion.created_at.desc())
        .first()
    )


def _get_project_bundle_or_404(*, db: Session, project_id: str, bundle_id: str) -> WorldProposalBundle:
    bundle = (
        db.query(WorldProposalBundle)
        .filter(
            WorldProposalBundle.id == bundle_id,
            WorldProposalBundle.project_id == project_id,
        )
        .first()
    )
    if bundle is None:
        raise HTTPException(status_code=404, detail="Proposal bundle not found")
    return bundle


def _require_current_profile_scope(
    *,
    db: Session,
    project_id: str,
    project_profile_version_id: str,
    profile_version: int,
    resource_label: str,
) -> ProjectProfileVersion:
    current_profile = _get_current_profile(db=db, project_id=project_id)
    if current_profile is None:
        raise HTTPException(status_code=409, detail="Current profile version is not available")
    if (
        current_profile.id != project_profile_version_id
        or current_profile.version != profile_version
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                f"{resource_label} does not belong to current profile version "
                f"{current_profile.version}"
            ),
        )
    return current_profile


def _fact_record_from_model(fact: WorldFactClaim) -> FactRecord:
    return FactRecord(
        claim_id=fact.claim_id,
        subject_ref=fact.subject_ref,
        predicate=fact.predicate,
        object_ref_or_value=fact.object_ref_or_value,
        claim_layer=fact.claim_layer,
        claim_status=fact.claim_status,
        chapter_index=fact.chapter_index,
        intra_chapter_seq=fact.intra_chapter_seq,
        valid_from_anchor_id=fact.valid_from_anchor_id,
        valid_to_anchor_id=fact.valid_to_anchor_id,
    )


def _detect_item_conflicts(
    *,
    db: Session,
    project_id: str,
    items: list,
    impact_snapshots: list,
) -> list[dict]:
    conflicts: list[dict] = []
    for item in items:
        if item.item_status in ("approved", "approved_with_edits", "rejected", "rolled_back"):
            continue
        existing = (
            db.query(WorldFactClaim)
            .filter(
                WorldFactClaim.project_id == project_id,
                WorldFactClaim.subject_ref == item.subject_ref,
                WorldFactClaim.predicate == item.predicate,
                WorldFactClaim.claim_status == "confirmed",
                WorldFactClaim.claim_layer == "truth",
            )
            .first()
        )
        if existing is not None:
            existing_val = existing.object_ref_or_value
            proposed_val = item.object_ref_or_value
            if existing_val != proposed_val:
                conflicts.append({
                    "item_id": item.id,
                    "conflict_type": "truth_conflict",
                    "detail": f"与现有真相冲突：{item.subject_ref}.{item.predicate} = {existing_val}",
                    "existing_claim_id": existing.id,
                })
    for snapshot in impact_snapshots:
        if len(snapshot.affected_truth_claim_ids) >= 3:
            for candidate_id in snapshot.candidate_item_ids:
                if not any(c["item_id"] == candidate_id and c["conflict_type"] == "high_impact" for c in conflicts):
                    conflicts.append({
                        "item_id": candidate_id,
                        "conflict_type": "high_impact",
                        "detail": f"高影响：涉及 {len(snapshot.affected_truth_claim_ids)} 条关联事实",
                        "existing_claim_id": None,
                    })
    return conflicts


def _build_bundle_detail(*, db: Session, project_id: str, bundle_id: str) -> ProposalBundleDetailOut:
    bundle = _get_project_bundle_or_404(db=db, project_id=project_id, bundle_id=bundle_id)
    items = (
        db.query(WorldProposalItem)
        .filter(
            WorldProposalItem.project_id == project_id,
            WorldProposalItem.project_profile_version_id == bundle.project_profile_version_id,
            WorldProposalItem.profile_version == bundle.profile_version,
            WorldProposalItem.bundle_id == bundle_id,
        )
        .order_by(WorldProposalItem.created_at.asc(), WorldProposalItem.id.asc())
        .all()
    )
    reviews = (
        db.query(WorldProposalReview)
        .filter(
            WorldProposalReview.project_id == project_id,
            WorldProposalReview.project_profile_version_id == bundle.project_profile_version_id,
            WorldProposalReview.profile_version == bundle.profile_version,
            WorldProposalReview.bundle_id == bundle_id,
        )
        .order_by(WorldProposalReview.created_at.asc(), WorldProposalReview.id.asc())
        .all()
    )
    impact_snapshots = (
        db.query(WorldProposalImpactScopeSnapshot)
        .filter(
            WorldProposalImpactScopeSnapshot.project_id == project_id,
            WorldProposalImpactScopeSnapshot.project_profile_version_id == bundle.project_profile_version_id,
            WorldProposalImpactScopeSnapshot.profile_version == bundle.profile_version,
            WorldProposalImpactScopeSnapshot.bundle_id == bundle_id,
        )
        .order_by(
            WorldProposalImpactScopeSnapshot.created_at.desc(),
            WorldProposalImpactScopeSnapshot.id.desc(),
        )
        .all()
    )
    if not impact_snapshots and items:
        impact_snapshots = [calculate_bundle_impact_scope(db=db, bundle_id=bundle_id)]
    conflicts = _detect_item_conflicts(
        db=db, project_id=project_id, items=items, impact_snapshots=impact_snapshots,
    )
    return ProposalBundleDetailOut(
        bundle=bundle,
        items=items,
        reviews=reviews,
        impact_snapshots=impact_snapshots,
        conflicts=conflicts,
    )

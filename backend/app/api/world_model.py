
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.world_fact_scope import is_chapter_scoped_truth_predicate
from app.core.world_projection_service import build_world_projection_overview
from app.core.world_proposal_review_queue import build_proposal_review_queue
from app.core.world_proposal_service import (
    calculate_bundle_impact_scope,
    review_proposal_item,
    rollback_review,
    split_bundle,
)
from app.db import get_db
from app.models import (
    Project,
    ChapterContent,
    ProjectProfileVersion,
    WorldArtifact,
    WorldCharacter,
    WorldEvent,
    WorldFactClaim,
    WorldFaction,
    WorldLocation,
    WorldProposalBundle,
    WorldProposalImpactScopeSnapshot,
    WorldProposalItem,
    WorldProposalReview,
    WorldResource,
)
from app.schemas import (
    PaginatedProposalBundlesOut,
    ProjectWorldOverviewOut,
    ProposalBundleDetailOut,
    ProposalBundleOut,
    ProposalBundleSplitCreate,
    ProposalReviewCreate,
    ProposalReviewOut,
    ProposalReviewQueueOut,
    ProposalReviewRollbackCreate,
    WorldFactClaimOut,
    WorldModelDashboardOut,
)

router = APIRouter(prefix="/api/v1/projects/{project_id}/world-model", tags=["world-model"])
ACTIONABLE_PROPOSAL_ITEM_STATUSES = ("pending", "needs_edit")


@router.get("", response_model=ProjectWorldOverviewOut)
def get_world_model_overview(project_id: str, db: Session = Depends(get_db)):
    _require_project(db=db, project_id=project_id)
    profile = _get_current_profile(db=db, project_id=project_id)
    try:
        return build_world_projection_overview(
            db=db,
            project_id=project_id,
            profile=profile,
            view_type="current_truth",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/dashboard", response_model=WorldModelDashboardOut)
def get_world_model_dashboard(project_id: str, db: Session = Depends(get_db)):
    _require_project(db=db, project_id=project_id)
    profile = _get_current_profile(db=db, project_id=project_id)
    if profile is None:
        return WorldModelDashboardOut(
            project_profile=None,
            metrics={},
            next_action={
                "action": "import_setup",
                "label": "导入 Setup，建立正式世界模型",
            },
        )

    pending_item_count = (
        db.query(WorldProposalItem)
        .filter(
            WorldProposalItem.project_id == project_id,
            WorldProposalItem.project_profile_version_id == profile.id,
            WorldProposalItem.profile_version == profile.version,
            WorldProposalItem.item_status.in_(("pending", "needs_edit")),
        )
        .count()
    )
    pending_bundle_count = (
        db.query(WorldProposalItem.bundle_id)
        .filter(
            WorldProposalItem.project_id == project_id,
            WorldProposalItem.project_profile_version_id == profile.id,
            WorldProposalItem.profile_version == profile.version,
            WorldProposalItem.item_status.in_(("pending", "needs_edit")),
        )
        .distinct()
        .count()
    )
    metrics = _dashboard_projection_metrics(db=db, project_id=project_id, profile=profile)
    fact_count = metrics["fact_count"]
    event_count = metrics["event_count"]
    if pending_item_count:
        next_action = {"action": "review_proposals", "label": "处理待审世界模型提案"}
    elif fact_count == 0 and event_count == 0:
        next_action = {"action": "analyze_chapter", "label": "分析章节，生成候选事实"}
    else:
        next_action = {"action": "inspect_projection", "label": "检查真相投影"}
    return WorldModelDashboardOut(
        project_profile=profile,
        metrics={
            **metrics,
            "pending_bundle_count": pending_bundle_count,
            "pending_item_count": pending_item_count,
        },
        next_action=next_action,
    )


@router.get("/subject-knowledge", response_model=ProjectWorldOverviewOut)
def get_subject_knowledge(
    project_id: str,
    subject_ref: str,
    db: Session = Depends(get_db),
):
    _require_project(db=db, project_id=project_id)
    profile = _get_current_profile(db=db, project_id=project_id)
    try:
        return build_world_projection_overview(
            db=db,
            project_id=project_id,
            profile=profile,
            view_type="subject_knowledge",
            subject_ref=subject_ref,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/snapshot", response_model=ProjectWorldOverviewOut)
def get_chapter_snapshot(
    project_id: str,
    chapter_index: int = Query(..., ge=1),
    db: Session = Depends(get_db),
):
    _require_project(db=db, project_id=project_id)
    _require_chapter(db=db, project_id=project_id, chapter_index=chapter_index)
    profile = _get_current_profile(db=db, project_id=project_id)
    try:
        return build_world_projection_overview(
            db=db,
            project_id=project_id,
            profile=profile,
            view_type="chapter_snapshot",
            chapter_index=chapter_index,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/facts", response_model=list[WorldFactClaimOut])
def list_world_fact_claims(
    project_id: str,
    claim_status: str | None = "confirmed",
    claim_layer: str | None = None,
    subject_ref: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    _require_project(db=db, project_id=project_id)
    current_profile = _get_current_profile(db=db, project_id=project_id)
    if current_profile is None:
        return []
    query = db.query(WorldFactClaim).filter(
        WorldFactClaim.project_id == project_id,
        WorldFactClaim.project_profile_version_id == current_profile.id,
        WorldFactClaim.profile_version == current_profile.version,
    )
    if claim_status and claim_status != "all":
        query = query.filter(WorldFactClaim.claim_status == claim_status)
    if claim_layer:
        query = query.filter(WorldFactClaim.claim_layer == claim_layer)
    if subject_ref:
        query = query.filter(WorldFactClaim.subject_ref == subject_ref)
    return (
        query.order_by(
            WorldFactClaim.chapter_index.asc(),
            WorldFactClaim.intra_chapter_seq.asc(),
            WorldFactClaim.claim_id.asc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/proposal-bundles", response_model=PaginatedProposalBundlesOut)
def list_world_proposal_bundles(
    project_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
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
            .filter(
                WorldProposalItem.project_id == project_id,
                WorldProposalItem.project_profile_version_id == current_profile.id,
                WorldProposalItem.profile_version == current_profile.version,
                WorldProposalItem.item_status == item_status,
            )
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


@router.get("/proposal-review-queue", response_model=ProposalReviewQueueOut)
def get_world_model_proposal_review_queue(project_id: str, db: Session = Depends(get_db)):
    _require_project(db=db, project_id=project_id)
    profile = _get_current_profile(db=db, project_id=project_id)
    return build_proposal_review_queue(db=db, project_id=project_id, profile=profile)


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


def _dashboard_projection_metrics(
    *,
    db: Session,
    project_id: str,
    profile: ProjectProfileVersion,
) -> dict[str, int]:
    catalog_entity_count = sum(
        db.query(model.id)
        .filter(
            model.project_id == project_id,
            model.profile_version == profile.version,
        )
        .count()
        for model in (
            WorldCharacter,
            WorldLocation,
            WorldFaction,
            WorldArtifact,
            WorldResource,
        )
    )
    introduced_entity_count = _count_distinct_event_payload_ref(
        db=db,
        project_id=project_id,
        profile=profile,
        event_type="entity_introduced",
        payload_key="entity_ref",
    )
    return {
        "entity_count": catalog_entity_count + introduced_entity_count,
        "fact_count": _dashboard_fact_count(db=db, project_id=project_id, profile=profile),
        "presence_count": _count_distinct_event_payload_ref(
            db=db,
            project_id=project_id,
            profile=profile,
            event_type="presence_shifted",
            payload_key="entity_ref",
        ),
        "event_count": _count_distinct_event_payload_ref(
            db=db,
            project_id=project_id,
            profile=profile,
            event_type="event_occurred",
            payload_key="event_ref",
        ),
    }


def _dashboard_fact_count(
    *,
    db: Session,
    project_id: str,
    profile: ProjectProfileVersion,
) -> int:
    return (
        db.query(WorldFactClaim.subject_ref, WorldFactClaim.predicate)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.project_profile_version_id == profile.id,
            WorldFactClaim.profile_version == profile.version,
            WorldFactClaim.claim_layer == "truth",
            WorldFactClaim.claim_status == "confirmed",
        )
        .distinct()
        .count()
    )


def _count_distinct_event_payload_ref(
    *,
    db: Session,
    project_id: str,
    profile: ProjectProfileVersion,
    event_type: str,
    payload_key: str,
) -> int:
    payload_ref = WorldEvent.primitive_payload[payload_key].as_string()
    return (
        db.query(payload_ref)
        .filter(
            WorldEvent.project_id == project_id,
            WorldEvent.project_profile_version_id == profile.id,
            WorldEvent.profile_version == profile.version,
            WorldEvent.event_type == event_type,
            payload_ref.isnot(None),
        )
        .distinct()
        .count()
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


def _detect_item_conflicts(
    *,
    db: Session,
    project_id: str,
    bundle: WorldProposalBundle,
    items: list,
    impact_snapshots: list,
) -> list[dict]:
    conflicts: list[dict] = []
    profile = _get_current_profile(db=db, project_id=project_id)
    projection_facts = {}
    if profile is not None:
        overview = build_world_projection_overview(
            db=db,
            project_id=project_id,
            profile=profile,
            view_type="current_truth",
        )
        projection_facts = overview.projection.facts if overview.projection else {}
    actionable_item_ids = {
        item.id
        for item in items
        if item.item_status in ACTIONABLE_PROPOSAL_ITEM_STATUSES
    }
    for item in items:
        if item.id not in actionable_item_ids:
            continue
        if item.claim_layer != "truth":
            continue
        if is_chapter_scoped_truth_predicate(item.predicate):
            existing_claim = _find_current_scoped_truth_claim(
                db=db,
                project_id=project_id,
                bundle=bundle,
                subject_ref=item.subject_ref,
                predicate=item.predicate,
                chapter_index=item.chapter_index,
            )
            if existing_claim is not None and existing_claim.object_ref_or_value != item.object_ref_or_value:
                conflicts.append({
                    "item_id": item.id,
                    "conflict_type": "truth_conflict",
                    "detail": (
                        f"与第{item.chapter_index}章现有真相冲突："
                        f"{item.subject_ref}.{item.predicate} = {existing_claim.object_ref_or_value}"
                    ),
                    "existing_claim_id": existing_claim.id,
                })
            continue
        subject_facts = projection_facts.get(item.subject_ref, {})
        if item.predicate in subject_facts:
            existing_val = subject_facts[item.predicate]
            proposed_val = item.object_ref_or_value
            if existing_val != proposed_val:
                conflicts.append({
                    "item_id": item.id,
                    "conflict_type": "truth_conflict",
                    "detail": f"与现有真相冲突：{item.subject_ref}.{item.predicate} = {existing_val}",
                    "existing_claim_id": _find_current_truth_claim_id(
                        db=db,
                        project_id=project_id,
                        bundle=bundle,
                        subject_ref=item.subject_ref,
                        predicate=item.predicate,
                        value=existing_val,
                    ),
                })
    for snapshot in impact_snapshots:
        if len(snapshot.affected_truth_claim_ids) >= 3:
            for candidate_id in snapshot.candidate_item_ids:
                if candidate_id not in actionable_item_ids:
                    continue
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
        db=db, project_id=project_id, bundle=bundle, items=items, impact_snapshots=impact_snapshots,
    )
    return ProposalBundleDetailOut(
        bundle=bundle,
        items=items,
        reviews=reviews,
        impact_snapshots=impact_snapshots,
        conflicts=conflicts,
    )


def _find_current_truth_claim_id(
    *,
    db: Session,
    project_id: str,
    bundle: WorldProposalBundle,
    subject_ref: str,
    predicate: str,
    value,
) -> str | None:
    candidates = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.project_profile_version_id == bundle.project_profile_version_id,
            WorldFactClaim.profile_version == bundle.profile_version,
            WorldFactClaim.subject_ref == subject_ref,
            WorldFactClaim.predicate == predicate,
            WorldFactClaim.claim_status == "confirmed",
            WorldFactClaim.claim_layer == "truth",
        )
        .order_by(
            WorldFactClaim.chapter_index.desc().nullslast(),
            WorldFactClaim.intra_chapter_seq.desc(),
            WorldFactClaim.claim_id.desc(),
        )
        .all()
    )
    for claim in candidates:
        if claim.object_ref_or_value == value:
            return claim.id
    return None


def _find_current_scoped_truth_claim(
    *,
    db: Session,
    project_id: str,
    bundle: WorldProposalBundle,
    subject_ref: str,
    predicate: str,
    chapter_index: int | None,
) -> WorldFactClaim | None:
    query = db.query(WorldFactClaim).filter(
        WorldFactClaim.project_id == project_id,
        WorldFactClaim.project_profile_version_id == bundle.project_profile_version_id,
        WorldFactClaim.profile_version == bundle.profile_version,
        WorldFactClaim.subject_ref == subject_ref,
        WorldFactClaim.predicate == predicate,
        WorldFactClaim.claim_status == "confirmed",
        WorldFactClaim.claim_layer == "truth",
    )
    if chapter_index is not None:
        query = query.filter(WorldFactClaim.chapter_index == chapter_index)
    return (
        query.order_by(
            WorldFactClaim.chapter_index.desc().nullslast(),
            WorldFactClaim.intra_chapter_seq.desc(),
            WorldFactClaim.claim_id.desc(),
        )
        .first()
    )

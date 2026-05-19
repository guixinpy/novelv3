from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.world_contracts import AUTHORITATIVE_STRUCTURED, DERIVED
from app.core.world_proposal_service import create_bundle, write_candidate_fact
from app.core.world_proposal_state import ACTIONABLE_REVIEW_ITEM_STATUSES
from app.models import ProjectProfileVersion, WorldFactClaim, WorldProposalItem
from app.schemas.world_proposals import ProposalCandidateFactCreate

CREATED_BY = "writing_agent.phase27.continuity_anchor_seed"
CONTINUITY_ANCHOR_PREDICATES = {
    "father_name",
    "military_tag_number",
    "identifier_meaning",
    "event_date",
    "relative_event_date",
}


@dataclass(frozen=True)
class ContinuityAnchorSeed:
    claim_id: str
    subject_ref: str
    predicate: str
    object_ref_or_value: Any
    chapter_index: int | None
    evidence_refs: tuple[str, ...]
    authority_type: str = AUTHORITATIVE_STRUCTURED
    confidence: float = 1.0
    notes: str = ""


CONTINUITY_ANCHOR_SEEDS = (
    ContinuityAnchorSeed(
        claim_id="claim.continuity.linshen.father_name",
        subject_ref="林深",
        predicate="father_name",
        object_ref_or_value="林建国",
        chapter_index=10,
        evidence_refs=("chapter:10", "chapter:11", "chapter:13"),
        notes="稳定连续性锚点：林深父亲姓名。",
    ),
    ContinuityAnchorSeed(
        claim_id="claim.continuity.guyan.military_tag_number",
        subject_ref="顾衍",
        predicate="military_tag_number",
        object_ref_or_value="N-017",
        chapter_index=4,
        evidence_refs=("chapter:4", "chapter:12", "chapter:13"),
        notes="稳定连续性锚点：顾衍军牌正面编号。",
    ),
    ContinuityAnchorSeed(
        claim_id="claim.continuity.identifier.n07.meaning",
        subject_ref="identifier.N-07",
        predicate="identifier_meaning",
        object_ref_or_value={
            "value": "实验代号/实验体编号",
            "not_values": ["顾衍军牌编号"],
            "status": "confirmed_limited",
        },
        chapter_index=12,
        evidence_refs=("chapter:12", "chapter:13"),
        authority_type=DERIVED,
        confidence=0.95,
        notes="N-07 不是顾衍军牌编号；具体对象仍保持未解。",
    ),
    ContinuityAnchorSeed(
        claim_id="claim.continuity.fog_disaster.date",
        subject_ref="event.fog_disaster",
        predicate="event_date",
        object_ref_or_value="2045年8月12日",
        chapter_index=7,
        evidence_refs=("chapter:7", "chapter:8"),
        notes="稳定连续性锚点：雾灾日期。",
    ),
    ContinuityAnchorSeed(
        claim_id="claim.continuity.fog_disaster.minus_3_days",
        subject_ref="event.fog_disaster.minus_3_days",
        predicate="relative_event_date",
        object_ref_or_value="2045年8月9日",
        chapter_index=5,
        evidence_refs=("chapter:5", "chapter:11", "chapter:12"),
        notes="稳定连续性锚点：雾灾发生前三天。",
    ),
)


def seed_continuity_anchor_proposals(db: Session, project_id: str) -> dict[str, Any]:
    profile = _current_profile(db, project_id)
    if profile is None:
        return {
            "status": "missing_profile",
            "project_id": project_id,
            "profile_version": None,
            "created_item_count": 0,
            "pending_anchor_count": 0,
            "created_items": [],
            "should_generate_next_chapter": False,
            "recommended_actions": ["import_setup_world_model"],
        }

    created_items: list[dict[str, Any]] = []
    seeds_to_create = [seed for seed in CONTINUITY_ANCHOR_SEEDS if not _anchor_exists(db, project_id, profile, seed)]
    bundle = None
    if seeds_to_create:
        bundle = create_bundle(
            db=db,
            project_id=project_id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            created_by=CREATED_BY,
            title="稳定连续性锚点",
            summary="由 Writing Agent 补齐的高显著连续性锚点候选事实。",
            commit=False,
        )
        for seed in seeds_to_create:
            item = write_candidate_fact(
                db=db,
                bundle_id=bundle.id,
                created_by=CREATED_BY,
                candidate=ProposalCandidateFactCreate(
                    project_id=project_id,
                    project_profile_version_id=profile.id,
                    profile_version=profile.version,
                    claim_id=seed.claim_id,
                    chapter_index=seed.chapter_index,
                    subject_ref=seed.subject_ref,
                    predicate=seed.predicate,
                    object_ref_or_value=seed.object_ref_or_value,
                    claim_layer="truth",
                    evidence_refs=list(seed.evidence_refs),
                    authority_type=seed.authority_type,
                    confidence=seed.confidence,
                    notes=seed.notes,
                    contract_version=profile.contract_version,
                ),
                commit=False,
            )
            created_items.append(_item_summary(item))
        db.commit()

    pending_anchor_count = _pending_anchor_count(db, project_id, profile)
    should_generate_next_chapter = pending_anchor_count == 0
    return {
        "status": "ready" if should_generate_next_chapter else "blocked",
        "project_id": project_id,
        "profile_version": profile.version,
        "proposal_bundle_id": bundle.id if bundle is not None else None,
        "created_item_count": len(created_items),
        "created_items": created_items,
        "pending_anchor_count": pending_anchor_count,
        "should_generate_next_chapter": should_generate_next_chapter,
        "recommended_actions": ["preflight_writing"] if should_generate_next_chapter else ["apply_world_model_proposal_resolution"],
    }


def is_continuity_anchor_item(item: WorldProposalItem) -> bool:
    return item.created_by == CREATED_BY and item.predicate in CONTINUITY_ANCHOR_PREDICATES


def _current_profile(db: Session, project_id: str) -> ProjectProfileVersion | None:
    return (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc(), ProjectProfileVersion.created_at.desc())
        .first()
    )


def _anchor_exists(db: Session, project_id: str, profile: ProjectProfileVersion, seed: ContinuityAnchorSeed) -> bool:
    confirmed = (
        db.query(WorldFactClaim.id)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.project_profile_version_id == profile.id,
            WorldFactClaim.profile_version == profile.version,
            WorldFactClaim.claim_status == "confirmed",
            WorldFactClaim.claim_layer == "truth",
            WorldFactClaim.subject_ref == seed.subject_ref,
            WorldFactClaim.predicate == seed.predicate,
        )
        .first()
    )
    if confirmed is not None:
        return True
    actionable = (
        db.query(WorldProposalItem.id)
        .filter(
            WorldProposalItem.project_id == project_id,
            WorldProposalItem.project_profile_version_id == profile.id,
            WorldProposalItem.profile_version == profile.version,
            WorldProposalItem.item_status.in_(ACTIONABLE_REVIEW_ITEM_STATUSES),
            WorldProposalItem.subject_ref == seed.subject_ref,
            WorldProposalItem.predicate == seed.predicate,
        )
        .first()
    )
    return actionable is not None


def _pending_anchor_count(db: Session, project_id: str, profile: ProjectProfileVersion) -> int:
    return int(
        db.query(func.count(WorldProposalItem.id))
        .filter(
            WorldProposalItem.project_id == project_id,
            WorldProposalItem.project_profile_version_id == profile.id,
            WorldProposalItem.profile_version == profile.version,
            WorldProposalItem.item_status.in_(ACTIONABLE_REVIEW_ITEM_STATUSES),
            WorldProposalItem.created_by == CREATED_BY,
            WorldProposalItem.predicate.in_(CONTINUITY_ANCHOR_PREDICATES),
        )
        .scalar()
        or 0
    )


def _item_summary(item: WorldProposalItem) -> dict[str, Any]:
    return {
        "proposal_item_id": item.id,
        "claim_id": item.claim_id,
        "subject_ref": item.subject_ref,
        "predicate": item.predicate,
        "chapter_index": item.chapter_index,
    }

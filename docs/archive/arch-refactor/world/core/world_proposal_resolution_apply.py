from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.continuity_anchor_proposals import is_continuity_anchor_item
from app.core.world_proposal_resolution_preview import preview_world_model_proposal_resolution
from app.core.world_proposal_service import review_proposal_item
from app.core.world_proposal_state import ACTIONABLE_REVIEW_ITEM_STATUSES, NON_MERGE_ACTIONS
from app.models import ProjectProfileVersion, WorldProposalItem

REVIEWER_REF = "writing_agent.phase13"


def apply_world_model_proposal_resolution(
    db: Session,
    project_id: str,
    decisions: list[dict[str, Any]],
    *,
    confirm_apply: bool,
) -> dict[str, Any]:
    preview = preview_world_model_proposal_resolution(db, project_id, decisions)
    before_actionable_items = int(preview.get("total_actionable_items") or 0)
    valid_decisions = list(preview.get("valid_decisions") or [])
    invalid_decisions = list(preview.get("invalid_decisions") or [])

    if preview.get("status") == "missing_profile":
        return _result(
            project_id=project_id,
            profile_version=preview.get("profile_version"),
            before_actionable_items=before_actionable_items,
            after_actionable_items=before_actionable_items,
            applied_reviews=[],
            invalid_decisions=invalid_decisions,
            requires_confirmation=False,
            status="missing_profile",
            should_generate_next_chapter=False,
            recommended_actions=["import_setup_world_model"],
        )

    for decision in valid_decisions:
        if decision.get("action") not in NON_MERGE_ACTIONS and not _is_continuity_anchor_decision(
            db,
            project_id=project_id,
            proposal_item_id=str(decision.get("proposal_item_id") or ""),
        ):
            invalid_decisions.append(
                _invalid_from_valid(
                    decision,
                    "approval_not_supported_in_guarded_apply",
                    "guarded apply only supports reject/mark_uncertain and whitelisted continuity-anchor approvals",
                )
            )

    if invalid_decisions:
        return _result(
            project_id=project_id,
            profile_version=preview.get("profile_version"),
            before_actionable_items=before_actionable_items,
            after_actionable_items=before_actionable_items,
            applied_reviews=[],
            invalid_decisions=invalid_decisions,
            requires_confirmation=False,
            status="blocked",
        )
    if valid_decisions and not confirm_apply:
        return _result(
            project_id=project_id,
            profile_version=preview.get("profile_version"),
            before_actionable_items=before_actionable_items,
            after_actionable_items=before_actionable_items,
            applied_reviews=[],
            invalid_decisions=[],
            requires_confirmation=True,
            status="blocked",
        )

    applied_reviews: list[dict[str, Any]] = []
    try:
        for decision in valid_decisions:
            review = review_proposal_item(
                db=db,
                proposal_item_id=decision["proposal_item_id"],
                reviewer_ref=REVIEWER_REF,
                action=decision["action"],
                reason=decision["reason"] or "Writing Agent guarded apply",
                evidence_refs=decision["evidence_refs"],
                edited_fields=None,
                commit=False,
            )
            applied_reviews.append(
                {
                    "review_id": review.id,
                    "proposal_item_id": review.proposal_item_id,
                    "action": review.review_action,
                }
            )
        db.commit()
    except ValueError as exc:
        db.rollback()
        return _result(
            project_id=project_id,
            profile_version=preview.get("profile_version"),
            before_actionable_items=before_actionable_items,
            after_actionable_items=before_actionable_items,
            applied_reviews=[],
            invalid_decisions=[
                {
                    "decision_index": None,
                    "proposal_item_id": None,
                    "action": None,
                    "code": "apply_failed",
                    "message": str(exc),
                }
            ],
            requires_confirmation=False,
            status="blocked",
        )

    after_actionable_items = _current_actionable_count(db, project_id)
    return _result(
        project_id=project_id,
        profile_version=preview.get("profile_version"),
        before_actionable_items=before_actionable_items,
        after_actionable_items=after_actionable_items,
        applied_reviews=applied_reviews,
        invalid_decisions=[],
        requires_confirmation=False,
    )


def _current_actionable_count(db: Session, project_id: str) -> int:
    profile = (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc(), ProjectProfileVersion.created_at.desc())
        .first()
    )
    if profile is None:
        return 0
    return int(
        db.query(func.count(WorldProposalItem.id))
        .filter(
            WorldProposalItem.project_id == project_id,
            WorldProposalItem.project_profile_version_id == profile.id,
            WorldProposalItem.profile_version == profile.version,
            WorldProposalItem.item_status.in_(ACTIONABLE_REVIEW_ITEM_STATUSES),
        )
        .scalar()
        or 0
    )


def _is_continuity_anchor_decision(db: Session, *, project_id: str, proposal_item_id: str) -> bool:
    item = (
        db.query(WorldProposalItem)
        .filter(WorldProposalItem.project_id == project_id, WorldProposalItem.id == proposal_item_id)
        .one_or_none()
    )
    return item is not None and is_continuity_anchor_item(item)


def _result(
    *,
    project_id: str,
    profile_version: object,
    before_actionable_items: int,
    after_actionable_items: int,
    applied_reviews: list[dict[str, Any]],
    invalid_decisions: list[dict[str, Any]],
    requires_confirmation: bool,
    status: str | None = None,
    should_generate_next_chapter: bool | None = None,
    recommended_actions: list[str] | None = None,
) -> dict[str, Any]:
    if should_generate_next_chapter is None:
        should_generate_next_chapter = after_actionable_items == 0 and not invalid_decisions and not requires_confirmation
    return {
        "status": status or ("ready" if should_generate_next_chapter else "blocked"),
        "project_id": project_id,
        "profile_version": profile_version,
        "before_actionable_items": before_actionable_items,
        "after_actionable_items": after_actionable_items,
        "applied_count": len(applied_reviews),
        "applied_reviews": applied_reviews,
        "invalid_decision_count": len(invalid_decisions),
        "invalid_decisions": invalid_decisions,
        "requires_confirmation": requires_confirmation,
        "can_auto_apply": False,
        "should_generate_next_chapter": should_generate_next_chapter,
        "recommended_actions": recommended_actions or _recommended_actions(
            after_actionable_items=after_actionable_items,
            invalid_decisions=invalid_decisions,
            requires_confirmation=requires_confirmation,
        ),
    }


def _invalid_from_valid(decision: dict[str, Any], code: str, message: str) -> dict[str, Any]:
    return {
        "decision_index": decision.get("decision_index"),
        "proposal_item_id": decision.get("proposal_item_id"),
        "action": decision.get("action"),
        "code": code,
        "message": message,
    }


def _recommended_actions(
    *,
    after_actionable_items: int,
    invalid_decisions: list[dict[str, Any]],
    requires_confirmation: bool,
) -> list[str]:
    if invalid_decisions:
        return ["fix_invalid_resolution_decisions"]
    if requires_confirmation:
        return ["confirm_apply_world_model_proposal_resolution"]
    if after_actionable_items == 0:
        return ["preflight_writing"]
    return ["continue_world_model_proposal_resolution"]

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.world_proposal_state import ACTIONABLE_REVIEW_ITEM_STATUSES
from app.models import ProjectProfileVersion, WorldProposalItem

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
HIGH_VALUE_PREDICATE_POLICIES: dict[str, dict[str, str]] = {
    "identifier_meaning_hypothesis": {
        "policy_id": "plot_signal_identifier_hypothesis",
        "reason": "编号语义变化会影响后续推理，但当前应保留为待证推断，不直接确认为世界真相。",
    },
    "access_permission_anomaly": {
        "policy_id": "plot_signal_access_permission_anomaly",
        "reason": "权限异常是高价值身份线索，应先标为未定事实，避免过早确认角色身份。",
    },
    "investigation_lead": {
        "policy_id": "plot_signal_investigation_lead",
        "reason": "调查线索会影响下一步行动，但应保留为待证方向，不直接确认为世界真相。",
    },
}


def draft_high_value_world_proposal_resolution_decisions(
    db: Session,
    project_id: str,
    *,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    profile = _current_profile(db, project_id)
    if profile is None:
        return {
            "status": "missing_profile",
            "project_id": project_id,
            "profile_version": None,
            "inspected_item_count": 0,
            "draft_decision_count": 0,
            "skipped_item_count": 0,
            "draft_decisions": [],
            "skipped_items": [],
            "requires_confirmation": False,
            "can_auto_apply": False,
            "should_generate_next_chapter": False,
            "recommended_next_tools": ["import_setup_world_model"],
            "report_only": True,
        }

    clamped_limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
    items = (
        db.query(WorldProposalItem)
        .filter(
            WorldProposalItem.project_id == project_id,
            WorldProposalItem.project_profile_version_id == profile.id,
            WorldProposalItem.profile_version == profile.version,
            WorldProposalItem.item_status.in_(ACTIONABLE_REVIEW_ITEM_STATUSES),
        )
        .order_by(
            WorldProposalItem.chapter_index.asc().nullsfirst(),
            WorldProposalItem.predicate.asc(),
            WorldProposalItem.subject_ref.asc(),
            WorldProposalItem.id.asc(),
        )
        .limit(clamped_limit)
        .all()
    )

    draft_decisions: list[dict[str, Any]] = []
    skipped_items: list[dict[str, Any]] = []
    for item in items:
        policy = HIGH_VALUE_PREDICATE_POLICIES.get(item.predicate)
        if policy is None:
            skipped_items.append(_item_summary(item, reason="predicate_not_high_value_plot_signal"))
            continue
        draft_decisions.append(
            {
                "proposal_item_id": item.id,
                "action": "mark_uncertain",
                "reason": policy["reason"],
                "evidence_refs": [f"proposal:{item.id}", f"policy:{policy['policy_id']}"],
                "policy_id": policy["policy_id"],
                "predicate": item.predicate,
                "subject_ref": item.subject_ref,
                "chapter_index": item.chapter_index,
            }
        )

    return {
        "status": "ready" if not items else "blocked",
        "project_id": project_id,
        "profile_version": profile.version,
        "inspected_item_count": len(items),
        "draft_decision_count": len(draft_decisions),
        "skipped_item_count": len(skipped_items),
        "draft_decisions": draft_decisions,
        "skipped_items": skipped_items,
        "requires_confirmation": bool(draft_decisions),
        "can_auto_apply": False,
        "should_generate_next_chapter": len(items) == 0,
        "recommended_next_tools": _recommended_next_tools(items, draft_decisions),
        "report_only": True,
    }


def _current_profile(db: Session, project_id: str) -> ProjectProfileVersion | None:
    return (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc(), ProjectProfileVersion.created_at.desc())
        .first()
    )


def _item_summary(item: WorldProposalItem, *, reason: str) -> dict[str, Any]:
    return {
        "proposal_item_id": item.id,
        "predicate": item.predicate,
        "subject_ref": item.subject_ref,
        "chapter_index": item.chapter_index,
        "confidence": item.confidence,
        "reason": reason,
    }


def _recommended_next_tools(items: list[WorldProposalItem], draft_decisions: list[dict[str, Any]]) -> list[str]:
    if not items:
        return ["preflight_writing"]
    if draft_decisions:
        return ["apply_world_model_proposal_resolution"]
    return ["plan_world_model_proposal_resolution"]

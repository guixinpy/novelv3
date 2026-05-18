from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.world_proposal_state import ACTIONABLE_REVIEW_ITEM_STATUSES, NON_MERGE_ACTIONS
from app.models import ProjectProfileVersion, WorldProposalItem

DEFAULT_LIMIT = 50
MAX_LIMIT = 200

DEFAULT_PREDICATE_POLICIES: dict[str, dict[str, Any]] = {
    "presence_count": {
        "action": "reject",
        "policy_id": "derived_metadata_not_truth",
        "reason": "presence_count is diagnostic extraction metadata, not durable world truth.",
    },
    "mentioned_in_chapter": {
        "action": "reject",
        "policy_id": "textual_mention_not_truth",
        "reason": "mentioned_in_chapter is textual mention metadata, not world truth.",
    },
    "present_at_location": {
        "action": "mark_uncertain",
        "policy_id": "location_inference_needs_review",
        "reason": "present_at_location is a derived location inference and needs confirmation before truth merge.",
    },
    "event_summary": {
        "action": "mark_uncertain",
        "policy_id": "summary_requires_curation",
        "reason": "event_summary is useful compression but needs curation before entering the truth layer.",
    },
}


def draft_world_model_proposal_resolution_decisions(
    db: Session,
    project_id: str,
    *,
    limit: int = DEFAULT_LIMIT,
    predicate_policies: dict[str, Any] | None = None,
    include_unclassified: bool = False,
) -> dict[str, Any]:
    profile = _current_profile(db, project_id)
    if profile is None:
        return {
            "status": "missing_profile",
            "project_id": project_id,
            "profile_version": None,
            "inspected_item_count": 0,
            "draft_decision_count": 0,
            "unclassified_item_count": 0,
            "draft_decisions": [],
            "unclassified_items": [],
            "requires_confirmation": False,
            "can_auto_apply": False,
            "should_generate_next_chapter": False,
            "recommended_next_tools": ["import_setup_world_model"],
            "report_only": True,
        }

    policies = _merge_policies(predicate_policies or {})
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
            WorldProposalItem.chapter_index.asc(),
            WorldProposalItem.predicate.asc(),
            WorldProposalItem.subject_ref.asc(),
            WorldProposalItem.id.asc(),
        )
        .limit(clamped_limit)
        .all()
    )
    draft_decisions: list[dict[str, Any]] = []
    unclassified_items: list[dict[str, Any]] = []
    for item in items:
        policy = policies.get(item.predicate)
        if policy is None:
            if include_unclassified:
                unclassified_items.append(_item_summary(item))
            continue
        draft_decisions.append(
            {
                "proposal_item_id": item.id,
                "action": policy["action"],
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
        "unclassified_item_count": len(unclassified_items),
        "draft_decisions": draft_decisions,
        "unclassified_items": unclassified_items,
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


def _merge_policies(overrides: dict[str, Any]) -> dict[str, dict[str, Any]]:
    policies = {key: value.copy() for key, value in DEFAULT_PREDICATE_POLICIES.items()}
    for predicate, raw_policy in overrides.items():
        if not isinstance(raw_policy, dict):
            continue
        action = str(raw_policy.get("action") or "").strip()
        if action not in NON_MERGE_ACTIONS:
            continue
        policy_id = str(raw_policy.get("policy_id") or f"custom:{predicate}").strip()
        reason = str(raw_policy.get("reason") or f"Custom policy for {predicate}.").strip()
        policies[str(predicate)] = {"action": action, "policy_id": policy_id, "reason": reason}
    return policies


def _item_summary(item: WorldProposalItem) -> dict[str, Any]:
    return {
        "proposal_item_id": item.id,
        "predicate": item.predicate,
        "subject_ref": item.subject_ref,
        "chapter_index": item.chapter_index,
        "confidence": item.confidence,
    }


def _recommended_next_tools(items: list[WorldProposalItem], draft_decisions: list[dict[str, Any]]) -> list[str]:
    if not items:
        return ["preflight_writing"]
    if draft_decisions:
        return ["apply_world_model_proposal_resolution"]
    return ["plan_world_model_proposal_resolution"]

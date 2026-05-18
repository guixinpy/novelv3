from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.world_proposal_state import (
    ACTIONABLE_REVIEW_ITEM_STATUSES,
    APPROVE_ACTIONS,
    NON_MERGE_ACTIONS,
    ensure_world_intake_review_is_atomized,
    validate_edited_fields,
)
from app.models import ProjectProfileVersion, WorldProposalItem

SUPPORTED_ACTIONS = APPROVE_ACTIONS | NON_MERGE_ACTIONS


def preview_world_model_proposal_resolution(
    db: Session,
    project_id: str,
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    profile = _current_profile(db, project_id)
    if profile is None:
        return _empty_result(project_id, status="missing_profile", decisions=decisions)
    total_actionable_items = _total_actionable_items(db, project_id, profile)
    valid_decisions: list[dict[str, Any]] = []
    invalid_decisions: list[dict[str, Any]] = []
    seen_item_ids: set[str] = set()

    for index, raw_decision in enumerate(decisions):
        decision = raw_decision if isinstance(raw_decision, dict) else {}
        proposal_item_id = str(decision.get("proposal_item_id") or "").strip()
        action = str(decision.get("action") or "").strip()
        if not proposal_item_id:
            invalid_decisions.append(_invalid(index, proposal_item_id, action, "missing_item_id", "proposal_item_id is required"))
            continue
        if proposal_item_id in seen_item_ids:
            invalid_decisions.append(_invalid(index, proposal_item_id, action, "duplicate_decision", "duplicate proposal_item_id"))
            continue
        seen_item_ids.add(proposal_item_id)
        item = (
            db.query(WorldProposalItem)
            .filter(WorldProposalItem.project_id == project_id, WorldProposalItem.id == proposal_item_id)
            .first()
        )
        if item is None:
            invalid_decisions.append(_invalid(index, proposal_item_id, action, "missing_item", "proposal item not found"))
            continue
        if item.project_profile_version_id != profile.id or item.profile_version != profile.version:
            invalid_decisions.append(_invalid(index, proposal_item_id, action, "profile_mismatch", "proposal item is not in current profile"))
            continue
        if item.item_status not in ACTIONABLE_REVIEW_ITEM_STATUSES:
            invalid_decisions.append(_invalid(index, proposal_item_id, action, "non_actionable_item", f"proposal item is {item.item_status}"))
            continue
        if action not in SUPPORTED_ACTIONS:
            invalid_decisions.append(_invalid(index, proposal_item_id, action, "unsupported_action", f"unsupported action: {action}"))
            continue
        edited_fields = decision.get("edited_fields") if isinstance(decision.get("edited_fields"), dict) else {}
        if action == "approve" and edited_fields:
            invalid_decisions.append(_invalid(index, proposal_item_id, action, "approve_with_edits_required", "approve does not accept edited_fields"))
            continue
        try:
            normalized_edits = validate_edited_fields(edited_fields)
            ensure_world_intake_review_is_atomized(
                item_snapshot={"subject_ref": item.subject_ref, "predicate": item.predicate},
                action=action,
                edited_fields=normalized_edits,
            )
        except ValueError as exc:
            code = "world_intake_not_atomized" if "world intake" in str(exc) else "invalid_edited_fields"
            invalid_decisions.append(_invalid(index, proposal_item_id, action, code, str(exc)))
            continue
        valid_decisions.append(
            {
                "decision_index": index,
                "proposal_item_id": proposal_item_id,
                "bundle_id": item.bundle_id,
                "action": action,
                "reason": str(decision.get("reason") or "").strip(),
                "evidence_refs": _normalize_evidence_refs(decision.get("evidence_refs")),
                "edited_fields": normalized_edits,
                "would_create_fact": action in APPROVE_ACTIONS,
            }
        )

    covered_item_ids = {decision["proposal_item_id"] for decision in valid_decisions}
    remaining_after_preview = max(total_actionable_items - len(covered_item_ids), 0)
    would_unblock_generation = (
        total_actionable_items > 0
        and remaining_after_preview == 0
        and not invalid_decisions
    )
    has_preview_decisions = bool(decisions)
    return {
        "status": "ready" if total_actionable_items == 0 and not has_preview_decisions else "blocked",
        "project_id": project_id,
        "profile_version": profile.version,
        "total_actionable_items": total_actionable_items,
        "valid_decision_count": len(valid_decisions),
        "invalid_decision_count": len(invalid_decisions),
        "would_create_review_count": len(valid_decisions),
        "would_create_fact_count": sum(1 for decision in valid_decisions if decision["would_create_fact"]),
        "would_resolve_item_count": len(covered_item_ids),
        "remaining_actionable_item_count_after_preview": remaining_after_preview,
        "would_unblock_generation": would_unblock_generation,
        "should_generate_next_chapter": total_actionable_items == 0 and not has_preview_decisions,
        "valid_decisions": valid_decisions,
        "invalid_decisions": invalid_decisions,
        "recommended_actions": _recommended_actions(
            total_actionable_items=total_actionable_items,
            invalid_decisions=invalid_decisions,
            would_unblock_generation=would_unblock_generation,
        ),
        "preview_only": True,
        "requires_confirmation": bool(valid_decisions),
        "can_auto_apply": False,
        "report_only": True,
    }


def _current_profile(db: Session, project_id: str) -> ProjectProfileVersion | None:
    return (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc(), ProjectProfileVersion.created_at.desc())
        .first()
    )


def _total_actionable_items(db: Session, project_id: str, profile: ProjectProfileVersion) -> int:
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


def _empty_result(project_id: str, *, status: str, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    invalid_decisions = []
    for index, raw_decision in enumerate(decisions):
        decision = raw_decision if isinstance(raw_decision, dict) else {}
        invalid_decisions.append(
            _invalid(
                index,
                str(decision.get("proposal_item_id") or ""),
                str(decision.get("action") or ""),
                "missing_profile",
                "current profile is missing",
            )
        )
    return {
        "status": status,
        "project_id": project_id,
        "profile_version": None,
        "total_actionable_items": 0,
        "valid_decision_count": 0,
        "invalid_decision_count": len(decisions),
        "would_create_review_count": 0,
        "would_create_fact_count": 0,
        "would_resolve_item_count": 0,
        "remaining_actionable_item_count_after_preview": 0,
        "would_unblock_generation": False,
        "should_generate_next_chapter": False,
        "valid_decisions": [],
        "invalid_decisions": invalid_decisions,
        "recommended_actions": ["import_setup_world_model"],
        "preview_only": True,
        "requires_confirmation": False,
        "can_auto_apply": False,
        "report_only": True,
    }


def _invalid(index: int, proposal_item_id: str, action: str, code: str, message: str) -> dict[str, Any]:
    return {
        "decision_index": index,
        "proposal_item_id": proposal_item_id,
        "action": action,
        "code": code,
        "message": message,
    }


def _normalize_evidence_refs(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _recommended_actions(
    *,
    total_actionable_items: int,
    invalid_decisions: list[dict[str, Any]],
    would_unblock_generation: bool,
) -> list[str]:
    if invalid_decisions:
        return ["fix_invalid_resolution_decisions"]
    if total_actionable_items == 0:
        return ["preflight_writing"]
    if would_unblock_generation:
        return ["apply_confirmed_world_model_proposal_resolution"]
    return ["add_missing_resolution_decisions"]

from __future__ import annotations

from typing import Any

from app.schemas.world_proposals import ProposalClaimEditPatch

APPROVE_ACTIONS = {"approve", "approve_with_edits"}
NON_MERGE_ACTIONS = {"reject", "mark_uncertain"}
ACTIONABLE_REVIEW_ITEM_STATUSES = {"pending", "needs_edit"}
APPROVED_ITEM_STATUSES = {"approved", "approved_with_edits"}
TERMINAL_ITEM_STATUSES = APPROVED_ITEM_STATUSES | {"rejected", "uncertain", "split", "rolled_back"}
SPLITTABLE_ITEM_STATUSES = {"pending", "needs_edit"}
EDITABLE_CLAIM_FIELDS = {
    "subject_ref",
    "predicate",
    "chapter_index",
    "intra_chapter_seq",
    "object_ref_or_value",
    "valid_from_anchor_id",
    "valid_to_anchor_id",
    "source_event_ref",
    "perspective_ref",
    "disclosed_to_refs",
    "evidence_refs",
    "notes",
}
WORLD_INTAKE_SUBJECT_REF = "project.world_intake"
WORLD_INTAKE_PREDICATE = "user_proposed_update"


def ensure_item_allows_review(*, status: str, item_id: str, action: str) -> None:
    if status in ACTIONABLE_REVIEW_ITEM_STATUSES:
        return
    if status in APPROVED_ITEM_STATUSES:
        raise ValueError(
            f"item {item_id} is already {status}; use explicit rollback before action {action}"
        )
    if status in TERMINAL_ITEM_STATUSES:
        raise ValueError(f"item {item_id} is in terminal status {status} and cannot accept action {action}")
    raise ValueError(f"item {item_id} is in unsupported status {status}")


def validate_edited_fields(edited_fields: dict[str, Any]) -> dict[str, Any]:
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


def ensure_world_intake_review_is_atomized(
    *,
    item_snapshot: dict[str, Any],
    action: str,
    edited_fields: dict[str, Any],
) -> None:
    if not is_world_intake_item(item_snapshot):
        return
    if action == "approve":
        raise ValueError("world intake proposals must be converted to atomic facts with approve_with_edits before approval")
    if action != "approve_with_edits":
        return

    next_subject_ref = edited_fields.get("subject_ref", item_snapshot["subject_ref"])
    next_predicate = edited_fields.get("predicate", item_snapshot["predicate"])
    if next_subject_ref == WORLD_INTAKE_SUBJECT_REF or next_predicate == WORLD_INTAKE_PREDICATE:
        raise ValueError("world intake proposals must be converted to atomic facts with concrete subject_ref and predicate")


def is_world_intake_item(item_snapshot: dict[str, Any]) -> bool:
    return (
        item_snapshot.get("subject_ref") == WORLD_INTAKE_SUBJECT_REF
        and item_snapshot.get("predicate") == WORLD_INTAKE_PREDICATE
    )

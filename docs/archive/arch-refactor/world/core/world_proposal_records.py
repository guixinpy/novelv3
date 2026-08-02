from __future__ import annotations

from typing import Any

from app.models import WorldProposalItem

CLAIM_PAYLOAD_FIELDS = (
    "claim_id",
    "chapter_index",
    "intra_chapter_seq",
    "subject_ref",
    "predicate",
    "object_ref_or_value",
    "claim_layer",
    "perspective_ref",
    "disclosed_to_refs",
    "valid_from_anchor_id",
    "valid_to_anchor_id",
    "source_event_ref",
    "evidence_refs",
    "authority_type",
    "confidence",
    "notes",
    "contract_version",
)


def claim_payload_from_item_snapshot(
    item_snapshot: dict[str, Any],
    edited_fields: dict[str, Any],
) -> dict[str, Any]:
    payload = {field: item_snapshot[field] for field in CLAIM_PAYLOAD_FIELDS}
    payload.update(edited_fields)
    return payload


def child_item_from_parent(
    parent: WorldProposalItem,
    *,
    child_bundle_id: str,
    created_by: str,
) -> WorldProposalItem:
    return WorldProposalItem(
        project_id=parent.project_id,
        project_profile_version_id=parent.project_profile_version_id,
        profile_version=parent.profile_version,
        bundle_id=child_bundle_id,
        parent_item_id=parent.id,
        item_status="pending",
        claim_id=parent.claim_id,
        chapter_index=parent.chapter_index,
        intra_chapter_seq=parent.intra_chapter_seq,
        subject_ref=parent.subject_ref,
        predicate=parent.predicate,
        object_ref_or_value=parent.object_ref_or_value,
        claim_layer=parent.claim_layer,
        perspective_ref=parent.perspective_ref,
        disclosed_to_refs=parent.disclosed_to_refs,
        valid_from_anchor_id=parent.valid_from_anchor_id,
        valid_to_anchor_id=parent.valid_to_anchor_id,
        source_event_ref=parent.source_event_ref,
        evidence_refs=parent.evidence_refs,
        authority_type=parent.authority_type,
        confidence=parent.confidence,
        notes=parent.notes,
        contract_version=parent.contract_version,
        created_by=created_by,
    )

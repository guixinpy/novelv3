from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.world_proposal_state import ACTIONABLE_REVIEW_ITEM_STATUSES
from app.models import ProjectProfileVersion, WorldProposalItem

LOW_RISK_PREDICATES = {"presence_count", "mentioned_in_chapter", "present_at_location"}
HIGH_RISK_PREDICATES = {"status", "identity", "role", "event_summary", "rule", "relationship"}
RISK_ORDER = {"high": 0, "medium": 1, "low": 2}


def build_proposal_review_queue(
    *,
    db: Session,
    project_id: str,
    profile: ProjectProfileVersion | None,
    limit: int = 200,
) -> dict[str, Any]:
    if profile is None:
        return {
            "project_id": project_id,
            "profile_version": None,
            "total_items": 0,
            "returned_items": 0,
            "limit": limit,
            "has_more": False,
            "clusters": [],
        }
    query = (
        db.query(WorldProposalItem)
        .filter(
            WorldProposalItem.project_id == project_id,
            WorldProposalItem.project_profile_version_id == profile.id,
            WorldProposalItem.profile_version == profile.version,
            WorldProposalItem.item_status.in_(ACTIONABLE_REVIEW_ITEM_STATUSES),
        )
    )
    total_items = query.count()
    items = (
        query
        .order_by(
            WorldProposalItem.chapter_index.asc().nullsfirst(),
            WorldProposalItem.predicate.asc(),
            WorldProposalItem.subject_ref.asc(),
            WorldProposalItem.id.asc(),
        )
        .limit(limit)
        .all()
    )
    clusters: dict[str, dict[str, Any]] = {}
    for item in items:
        risk_level = _risk_level(item)
        review_mode = "batch" if risk_level == "low" else "individual"
        cluster_id = _cluster_id(item, risk_level=risk_level, review_mode=review_mode)
        cluster = clusters.setdefault(
            cluster_id,
            {
                "cluster_id": cluster_id,
                "risk_level": risk_level,
                "review_mode": review_mode,
                "candidate_count": 0,
                "item_ids": [],
                "bundle_ids": [],
                "subject_refs": [],
                "predicate": item.predicate,
                "chapter_range": {"start": item.chapter_index, "end": item.chapter_index},
                "reason": _risk_reason(risk_level),
            },
        )
        _append_item(cluster, item)

    ordered_clusters = sorted(
        clusters.values(),
        key=lambda cluster: (
            RISK_ORDER[cluster["risk_level"]],
            cluster["chapter_range"]["start"] if cluster["chapter_range"]["start"] is not None else -1,
            cluster["predicate"],
            cluster["cluster_id"],
        ),
    )
    return {
        "project_id": project_id,
        "profile_version": profile.version,
        "total_items": total_items,
        "returned_items": len(items),
        "limit": limit,
        "has_more": total_items > len(items),
        "clusters": ordered_clusters,
    }


def _risk_level(item: WorldProposalItem) -> str:
    predicate = item.predicate or ""
    if predicate in LOW_RISK_PREDICATES:
        return "low"
    if predicate in HIGH_RISK_PREDICATES or "death" in predicate.lower():
        return "high"
    return "medium"


def _cluster_id(item: WorldProposalItem, *, risk_level: str, review_mode: str) -> str:
    if review_mode == "batch":
        chapter_part = f"chapter:{item.chapter_index}" if item.chapter_index is not None else "global"
        return f"{risk_level}:{item.predicate}:{chapter_part}"
    return f"{risk_level}:{item.predicate}:{item.id}"


def _append_item(cluster: dict[str, Any], item: WorldProposalItem) -> None:
    cluster["candidate_count"] += 1
    cluster["item_ids"].append(item.id)
    if item.bundle_id not in cluster["bundle_ids"]:
        cluster["bundle_ids"].append(item.bundle_id)
    if item.subject_ref not in cluster["subject_refs"]:
        cluster["subject_refs"].append(item.subject_ref)
    start = cluster["chapter_range"]["start"]
    end = cluster["chapter_range"]["end"]
    if item.chapter_index is not None:
        cluster["chapter_range"]["start"] = item.chapter_index if start is None else min(start, item.chapter_index)
        cluster["chapter_range"]["end"] = item.chapter_index if end is None else max(end, item.chapter_index)


def _risk_reason(risk_level: str) -> str:
    return {
        "low": "章节内出场、提及或位置类候选通常只补充局部证据，可按批次审阅。",
        "medium": "普通事实候选可能影响设定连续性，建议单独确认。",
        "high": "状态、身份、事件、关系或规则类候选会改变后续叙事，应单独审阅。",
    }[risk_level]

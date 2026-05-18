from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.world_proposal_review_queue import build_proposal_review_queue
from app.models import ProjectProfileVersion

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def build_world_proposal_agent_report(
    db: Session,
    project_id: str,
    *,
    offset: int = 0,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    clamped_offset = max(offset, 0)
    clamped_limit = min(max(limit, 1), MAX_LIMIT)
    profile = (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc(), ProjectProfileVersion.created_at.desc())
        .first()
    )
    queue = build_proposal_review_queue(
        db=db,
        project_id=project_id,
        profile=profile,
        offset=clamped_offset,
        limit=clamped_limit,
    )
    clusters = queue.get("clusters") if isinstance(queue.get("clusters"), list) else []
    total_items = int(queue.get("total_items") or 0)
    profile_version = queue.get("profile_version")
    status = _status(profile_version=profile_version, total_items=total_items)
    return {
        "status": status,
        "project_id": project_id,
        "profile_version": profile_version,
        "total_items": total_items,
        "returned_items": int(queue.get("returned_items") or 0),
        "offset": int(queue.get("offset") or clamped_offset),
        "limit": int(queue.get("limit") or clamped_limit),
        "has_more": bool(queue.get("has_more")),
        "risk_counts": _risk_counts(clusters),
        "review_mode_counts": _review_mode_counts(clusters),
        "clusters": [_compact_cluster(cluster) for cluster in clusters],
        "recommended_actions": _recommended_actions(status, clusters),
        "should_generate_next_chapter": status == "ready",
        "report_only": True,
    }


def _status(*, profile_version: object, total_items: int) -> str:
    if profile_version is None:
        return "missing_profile"
    return "blocked" if total_items > 0 else "ready"


def _risk_counts(clusters: list[Any]) -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0}
    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        risk_level = str(cluster.get("risk_level") or "")
        if risk_level in counts:
            counts[risk_level] += int(cluster.get("candidate_count") or 0)
    return counts


def _review_mode_counts(clusters: list[Any]) -> dict[str, int]:
    counts = {"individual": 0, "batch": 0}
    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        review_mode = str(cluster.get("review_mode") or "")
        if review_mode in counts:
            counts[review_mode] += int(cluster.get("candidate_count") or 0)
    return counts


def _compact_cluster(cluster: Any) -> dict[str, Any]:
    if not isinstance(cluster, dict):
        return {}
    return {
        "cluster_id": cluster.get("cluster_id"),
        "risk_level": cluster.get("risk_level"),
        "review_mode": cluster.get("review_mode"),
        "candidate_count": int(cluster.get("candidate_count") or 0),
        "item_ids": _bounded_list(cluster.get("item_ids")),
        "bundle_ids": _bounded_list(cluster.get("bundle_ids")),
        "subject_refs": _bounded_list(cluster.get("subject_refs")),
        "predicate": cluster.get("predicate"),
        "chapter_range": cluster.get("chapter_range") or {"start": None, "end": None},
        "reason": cluster.get("reason"),
    }


def _bounded_list(value: object, *, limit: int = 10) -> list[Any]:
    if not isinstance(value, list):
        return []
    return value[:limit]


def _recommended_actions(status: str, clusters: list[Any]) -> list[str]:
    if status == "ready":
        return ["preflight_writing"]
    if status == "missing_profile":
        return ["import_setup_world_model"]
    actions = ["pause_generation_until_proposals_resolved"]
    if any(isinstance(cluster, dict) and cluster.get("risk_level") == "high" for cluster in clusters):
        actions.append("review_high_risk_proposals")
    if any(isinstance(cluster, dict) and cluster.get("review_mode") == "batch" for cluster in clusters):
        actions.append("batch_review_low_risk_proposals")
    return actions

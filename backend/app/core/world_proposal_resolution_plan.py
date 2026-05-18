from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.world_proposal_agent_report import build_world_proposal_agent_report

DEFAULT_LIMIT = 50


def build_world_proposal_resolution_plan(
    db: Session,
    project_id: str,
    *,
    offset: int = 0,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    report = build_world_proposal_agent_report(db, project_id, offset=offset, limit=limit, compact=False)
    clusters = report.get("clusters") if isinstance(report.get("clusters"), list) else []
    resolution_steps = _resolution_steps(clusters)
    return {
        "status": report.get("status"),
        "project_id": project_id,
        "profile_version": report.get("profile_version"),
        "total_items": int(report.get("total_items") or 0),
        "returned_items": int(report.get("returned_items") or 0),
        "offset": int(report.get("offset") or 0),
        "limit": int(report.get("limit") or limit),
        "has_more": bool(report.get("has_more")),
        "risk_counts": report.get("risk_counts") or {"high": 0, "medium": 0, "low": 0},
        "review_mode_counts": report.get("review_mode_counts") or {"individual": 0, "batch": 0},
        "resolution_steps": resolution_steps,
        "high_priority_step_count": sum(1 for step in resolution_steps if step["risk_level"] == "high"),
        "batch_step_count": sum(1 for step in resolution_steps if step["action_type"] == "review_batch"),
        "requires_human_confirmation": bool(resolution_steps),
        "can_auto_apply": False,
        "recommended_actions": _recommended_actions(report, resolution_steps),
        "recommended_next_tools": _recommended_next_tools(report, resolution_steps),
        "should_generate_next_chapter": report.get("should_generate_next_chapter") is True,
        "plan_only": True,
        "report_only": True,
    }


def _resolution_steps(clusters: list[Any]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        review_mode = str(cluster.get("review_mode") or "")
        action_type = "review_batch" if review_mode == "batch" else "review_individual"
        steps.append(
            {
                "step_index": len(steps) + 1,
                "action_type": action_type,
                "recommended_resolution": "batch_review" if action_type == "review_batch" else "manual_individual_review",
                "requires_human_confirmation": True,
                "risk_level": cluster.get("risk_level"),
                "review_mode": review_mode,
                "cluster_id": cluster.get("cluster_id"),
                "candidate_count": int(cluster.get("candidate_count") or 0),
                "item_ids": list(cluster.get("item_ids") or []),
                "bundle_ids": list(cluster.get("bundle_ids") or []),
                "subject_refs": list(cluster.get("subject_refs") or []),
                "predicate": cluster.get("predicate"),
                "chapter_range": cluster.get("chapter_range") or {"start": None, "end": None},
                "reason": cluster.get("reason"),
                "allowed_actions": ["approve", "approve_with_edits", "reject", "mark_uncertain"],
            }
        )
    ordered_steps = sorted(
        steps,
        key=lambda step: (
            0 if step["action_type"] == "review_individual" else 1,
            step["step_index"],
        ),
    )
    for index, step in enumerate(ordered_steps, start=1):
        step["step_index"] = index
    return ordered_steps


def _recommended_actions(report: dict[str, Any], steps: list[dict[str, Any]]) -> list[str]:
    if report.get("status") == "ready":
        return ["preflight_writing"]
    if report.get("status") == "missing_profile":
        return ["import_setup_world_model"]
    actions = ["pause_generation_until_proposals_resolved"]
    if any(step["action_type"] == "review_individual" for step in steps):
        actions.append("resolve_individual_proposals_first")
    if any(step["action_type"] == "review_batch" for step in steps):
        actions.append("resolve_batch_proposals_after_individuals")
    return actions


def _recommended_next_tools(report: dict[str, Any], steps: list[dict[str, Any]]) -> list[str]:
    if report.get("status") == "ready":
        return ["preflight_writing"]
    if report.get("status") == "missing_profile":
        return ["import_setup_world_model"]
    return ["review_world_model_proposals"] if steps else []

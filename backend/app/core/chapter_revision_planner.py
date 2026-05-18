from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.chapter_quality_review import review_chapter_quality
from app.core.world_proposal_review_queue import build_proposal_review_queue
from app.models import ProjectProfileVersion


def plan_chapter_revision(db: Session, project_id: str, chapter_index: int) -> dict[str, Any]:
    review = review_chapter_quality(db, project_id, chapter_index)
    findings = review.get("findings") if isinstance(review.get("findings"), list) else []
    revision_actions = _revision_actions(findings)
    proposal_pressure = _world_model_proposal_pressure(db, project_id)
    recommended_next_tools = _recommended_next_tools(review, revision_actions, proposal_pressure)
    blocker_count = int(review.get("blocker_count") or 0)
    status = "blocked" if blocker_count else "warning" if revision_actions or proposal_pressure["total_items"] else "ready"
    return {
        "status": status,
        "chapter_index": chapter_index,
        "should_generate_next_chapter": status == "ready",
        "review": review,
        "revision_actions": revision_actions,
        "world_model_proposal_pressure": proposal_pressure,
        "recommended_next_tools": recommended_next_tools,
    }


def _revision_actions(findings: list[Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        mapped = _action_for_finding(finding)
        if mapped is None or mapped["action"] in seen:
            continue
        seen.add(mapped["action"])
        actions.append(mapped)
    return actions


def _action_for_finding(finding: dict[str, Any]) -> dict[str, Any] | None:
    code = str(finding.get("code") or "")
    severity = str(finding.get("severity") or "warning")
    message = str(finding.get("message") or "")
    if code == "generic_chapter_title":
        return {
            "action": "retitle_chapter",
            "severity": severity,
            "source_finding": code,
            "reason": message,
        }
    if code == "chapter_over_target":
        return {
            "action": "compress_chapter",
            "severity": severity,
            "source_finding": code,
            "reason": message,
            "target": "压缩到项目章节目标字数范围内，保留核心场景和必要情绪推进。",
        }
    if code == "chapter_under_target":
        return {
            "action": "expand_chapter",
            "severity": severity,
            "source_finding": code,
            "reason": message,
            "target": "补足场景密度、人物反应和有效冲突，不用解释性大纲灌水。",
        }
    if code == "future_outline_overlap":
        return {
            "action": "defer_future_reveals",
            "severity": severity,
            "source_finding": code,
            "reason": message,
            "target": "移除或弱化提前消耗的后续章节信息，改为保留悬念或轻量暗示。",
            "evidence": finding.get("evidence") or {},
        }
    if code == "missing_outline_chapter":
        return {
            "action": "repair_outline_gap",
            "severity": severity,
            "source_finding": code,
            "reason": message,
        }
    return None


def _world_model_proposal_pressure(db: Session, project_id: str) -> dict[str, Any]:
    profile = (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc(), ProjectProfileVersion.created_at.desc())
        .first()
    )
    queue = build_proposal_review_queue(db=db, project_id=project_id, profile=profile, limit=10)
    clusters = queue.get("clusters") if isinstance(queue.get("clusters"), list) else []
    risk_counts = {"high": 0, "medium": 0, "low": 0}
    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        risk_level = str(cluster.get("risk_level") or "")
        if risk_level in risk_counts:
            risk_counts[risk_level] += int(cluster.get("candidate_count") or 0)
    return {
        "profile_version": queue.get("profile_version"),
        "total_items": int(queue.get("total_items") or 0),
        "returned_items": int(queue.get("returned_items") or 0),
        "has_more": bool(queue.get("has_more")),
        "risk_counts": risk_counts,
        "top_clusters": clusters[:5],
    }


def _recommended_next_tools(
    review: dict[str, Any],
    revision_actions: list[dict[str, Any]],
    proposal_pressure: dict[str, Any],
) -> list[str]:
    tools: list[str] = []
    if revision_actions:
        tools.append("revise_chapter")
    if int(proposal_pressure.get("total_items") or 0) > 0:
        tools.append("review_world_model_proposals")
    if review.get("status") == "ready" and not tools:
        tools.append("preflight_writing")
    return tools

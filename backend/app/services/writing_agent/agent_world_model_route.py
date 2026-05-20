from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.world_proposal_agent_report import build_world_proposal_agent_report
from app.models import Project, ProjectProfileVersion, WorldFactClaim

AGENT_WORLD_MODEL_ROUTE_VERSION = "phase74.agent_world_model_route.v1"
DEFAULT_FACT_LIMIT = 20
MAX_FACT_LIMIT = 100


def inspect_agent_world_model_route(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
    subject_ref: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    _require_project(db, project_id)
    clamped_limit = _clamp_limit(limit)
    profile = _current_profile(db, project_id)
    if profile is None:
        return _json_safe_output(
            {
                "status": "completed",
                "project_id": project_id,
                "chapter_index": chapter_index,
                "subject_ref": _clean_subject(subject_ref),
                "profile": None,
                "route": {
                    "status": "blocked",
                    "reason": "missing_world_model_profile",
                    "can_use_world_model": False,
                },
                "fact_summary": {"total_confirmed_facts": 0, "returned_facts": 0},
                "facts": [],
                "proposal_pressure": {"status": "missing_profile", "total_items": 0, "risk_counts": {}},
                "recommended_actions": ["import_setup_world_model"],
                "diagnostics": [
                    {
                        "code": "missing_world_model_profile",
                        "severity": "warning",
                        "message": "项目尚未建立世界模型 profile，Agent 应先导入设定或建立世界模型。",
                    }
                ],
                "trace": _route_trace_metadata(),
            }
        )

    proposal_pressure = build_world_proposal_agent_report(db, project_id, limit=clamped_limit)
    facts, total_facts = _confirmed_fact_preview(
        db,
        project_id,
        profile=profile,
        chapter_index=chapter_index,
        subject_ref=_clean_subject(subject_ref),
        limit=clamped_limit,
    )
    route = _route_decision(proposal_pressure=proposal_pressure)
    recommended_actions = _recommended_actions(route["status"], route["reason"])
    return _json_safe_output(
        {
            "status": "completed",
            "project_id": project_id,
            "chapter_index": chapter_index,
            "subject_ref": _clean_subject(subject_ref),
            "profile": {
                "id": profile.id,
                "version": profile.version,
                "contract_version": profile.contract_version,
            },
            "route": route,
            "fact_summary": {
                "total_confirmed_facts": total_facts,
                "returned_facts": len(facts),
                "limit": clamped_limit,
            },
            "facts": facts,
            "proposal_pressure": {
                "status": proposal_pressure.get("status"),
                "total_items": int(proposal_pressure.get("total_items") or 0),
                "risk_counts": proposal_pressure.get("risk_counts") or {},
                "review_mode_counts": proposal_pressure.get("review_mode_counts") or {},
                "clusters": proposal_pressure.get("clusters") or [],
            },
            "recommended_actions": recommended_actions,
            "diagnostics": _diagnostics(route=route, proposal_pressure=proposal_pressure),
            "trace": _route_trace_metadata(),
        }
    )


def _require_project(db: Session, project_id: str) -> None:
    if db.query(Project.id).filter(Project.id == project_id).first() is None:
        raise HTTPException(status_code=404, detail="Project not found")


def _current_profile(db: Session, project_id: str) -> ProjectProfileVersion | None:
    return (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc(), ProjectProfileVersion.created_at.desc(), ProjectProfileVersion.id.desc())
        .first()
    )


def _confirmed_fact_preview(
    db: Session,
    project_id: str,
    *,
    profile: ProjectProfileVersion,
    chapter_index: int | None,
    subject_ref: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    filters = [
        WorldFactClaim.project_id == project_id,
        WorldFactClaim.project_profile_version_id == profile.id,
        WorldFactClaim.profile_version == profile.version,
        WorldFactClaim.claim_status == "confirmed",
        WorldFactClaim.claim_layer == "truth",
    ]
    if chapter_index:
        filters.append(or_(WorldFactClaim.chapter_index.is_(None), WorldFactClaim.chapter_index <= chapter_index))
    if subject_ref:
        filters.append(WorldFactClaim.subject_ref == subject_ref)
    total = db.query(func.count(WorldFactClaim.id)).filter(*filters).scalar() or 0
    rows = (
        db.query(WorldFactClaim)
        .filter(*filters)
        .order_by(
            WorldFactClaim.chapter_index.asc().nullsfirst(),
            WorldFactClaim.intra_chapter_seq.asc(),
            WorldFactClaim.claim_id.asc(),
        )
        .limit(limit)
        .all()
    )
    return [_fact_preview(row) for row in rows], int(total)


def _fact_preview(fact: WorldFactClaim) -> dict[str, Any]:
    return {
        "id": fact.id,
        "claim_id": fact.claim_id,
        "chapter_index": fact.chapter_index,
        "subject_ref": fact.subject_ref,
        "predicate": fact.predicate,
        "object_ref_or_value": fact.object_ref_or_value,
        "claim_layer": fact.claim_layer,
        "claim_status": fact.claim_status,
        "confidence": fact.confidence,
        "evidence_refs": fact.evidence_refs or [],
    }


def _route_decision(*, proposal_pressure: dict[str, Any]) -> dict[str, Any]:
    total_items = int(proposal_pressure.get("total_items") or 0)
    if total_items > 0:
        return {
            "status": "blocked",
            "reason": "pending_world_model_proposals",
            "can_use_world_model": True,
            "pending_proposal_count": total_items,
        }
    return {
        "status": "ready",
        "reason": "world_model_ready",
        "can_use_world_model": True,
        "pending_proposal_count": 0,
    }


def _recommended_actions(status: str, reason: str) -> list[str]:
    if status == "ready":
        return ["preflight_writing"]
    if reason == "pending_world_model_proposals":
        return ["review_world_model_proposals"]
    return ["inspect_agent_trace_audit"]


def _diagnostics(*, route: dict[str, Any], proposal_pressure: dict[str, Any]) -> list[dict[str, Any]]:
    if route["status"] == "ready":
        return []
    return [
        {
            "code": route["reason"],
            "severity": "warning",
            "message": "世界模型存在待处理事项，Agent 应先处理后再继续生成或修订。",
            "pending_proposal_count": int(proposal_pressure.get("total_items") or 0),
        }
    ]


def _clean_subject(subject_ref: str | None) -> str | None:
    cleaned = str(subject_ref or "").strip()
    return cleaned or None


def _clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_FACT_LIMIT
    return min(max(int(limit), 1), MAX_FACT_LIMIT)


def _route_trace_metadata() -> dict[str, Any]:
    return {
        "source": "inspect_agent_world_model_route",
        "version": AGENT_WORLD_MODEL_ROUTE_VERSION,
        "mutability": "read",
    }


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ChapterContent, Storyline, WorldProposalItem, WritingAgentStep

NARRATIVE_TREND_PROJECTION_VERSION = "phase232.narrative_trend_projection.v1"
REVIEW_TOOLS = ("review_chapter_quality", "review_chapter_continuity")
STYLE_DRIFT_CODES = frozenset(
    {
        "character_profile_drift",
        "ability_boundary_drift",
        "identifier_semantic_drift",
        "style_drift",
    }
)


def inspect_narrative_trend_projection(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
) -> dict[str, Any]:
    current_chapter_index = chapter_index or _latest_chapter_index(db, project_id)
    review_findings = _review_findings(db, project_id)
    style_drift_findings = [
        finding for finding in review_findings if _is_style_drift_code(str(finding.get("code") or ""))
    ]
    pacing_risks = [_pacing_risk(finding) for finding in review_findings if _is_pacing_code(str(finding.get("code") or ""))]
    world_model_contradictions = _world_model_contradictions(db, project_id)
    overdue_foreshadowing = _overdue_foreshadowing(db, project_id, current_chapter_index)
    summary = {
        "style_drift_findings": len(style_drift_findings),
        "world_model_contradictions": len(world_model_contradictions),
        "overdue_foreshadowing": len(overdue_foreshadowing),
        "pacing_risks_requiring_human_judgment": len(pacing_risks),
    }
    status = _projection_status(summary)
    return {
        "version": NARRATIVE_TREND_PROJECTION_VERSION,
        "status": status,
        "project_id": project_id,
        "chapter_index": current_chapter_index,
        "summary": summary,
        "style_drift": {
            "status": "watch" if style_drift_findings else "ready",
            "findings": [_finding_output(finding) for finding in style_drift_findings],
        },
        "world_model": {
            "status": "watch" if world_model_contradictions else "ready",
            "contradictions": world_model_contradictions,
        },
        "foreshadowing": {
            "status": "watch" if overdue_foreshadowing else "ready",
            "overdue": overdue_foreshadowing,
        },
        "pacing": {
            "status": "needs_human_judgment" if pacing_risks else "ready",
            "automation": "not_automated",
            "risks": pacing_risks,
        },
        "recommended_next_tools": _recommended_tools(
            style_drift_findings=style_drift_findings,
            world_model_contradictions=world_model_contradictions,
            overdue_foreshadowing=overdue_foreshadowing,
            pacing_risks=pacing_risks,
        ),
        "trace": {
            "source": "inspect_narrative_trend_projection",
            "version": NARRATIVE_TREND_PROJECTION_VERSION,
            "mutability": "read",
            "runtime_behavior_changed": False,
        },
    }


def _review_findings(db: Session, project_id: str) -> list[dict[str, Any]]:
    steps = (
        db.query(WritingAgentStep)
        .filter(WritingAgentStep.project_id == project_id)
        .filter(WritingAgentStep.tool_name.in_(REVIEW_TOOLS))
        .filter(WritingAgentStep.status == "success")
        .order_by(WritingAgentStep.chapter_index.asc(), WritingAgentStep.created_at.asc(), WritingAgentStep.id.asc())
        .all()
    )
    findings: list[dict[str, Any]] = []
    for step in steps:
        output = step.output if isinstance(step.output, dict) else {}
        raw_findings = output.get("findings") if isinstance(output.get("findings"), list) else []
        for finding in raw_findings:
            if not isinstance(finding, dict):
                continue
            findings.append(
                {
                    **finding,
                    "tool_name": step.tool_name,
                    "chapter_index": _chapter_index(step, output),
                }
            )
    return findings


def _finding_output(finding: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": str(finding.get("code") or ""),
        "severity": str(finding.get("severity") or ""),
        "chapter_index": finding.get("chapter_index"),
        "tool_name": str(finding.get("tool_name") or ""),
        "message": str(finding.get("message") or finding.get("description") or ""),
    }


def _pacing_risk(finding: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": str(finding.get("code") or ""),
        "chapter_index": finding.get("chapter_index"),
        "tool_name": str(finding.get("tool_name") or ""),
        "message": str(finding.get("message") or finding.get("description") or ""),
        "resolution": "requires_human_judgment",
    }


def _world_model_contradictions(db: Session, project_id: str) -> list[dict[str, Any]]:
    items = (
        db.query(WorldProposalItem)
        .filter(WorldProposalItem.project_id == project_id)
        .filter(WorldProposalItem.item_status.in_(("pending", "uncertain")))
        .order_by(WorldProposalItem.chapter_index.asc(), WorldProposalItem.id.asc())
        .all()
    )
    return [
        {
            "proposal_item_id": item.id,
            "chapter_index": item.chapter_index,
            "subject_ref": item.subject_ref,
            "predicate": item.predicate,
            "status": item.item_status,
        }
        for item in items
        if _is_contradiction_item(item)
    ]


def _overdue_foreshadowing(
    db: Session,
    project_id: str,
    chapter_index: int | None,
) -> list[dict[str, Any]]:
    if chapter_index is None:
        return []
    storyline = (
        db.query(Storyline)
        .filter(Storyline.project_id == project_id)
        .order_by(Storyline.updated_at.desc(), Storyline.id.desc())
        .first()
    )
    if storyline is None or not isinstance(storyline.foreshadowing, list):
        return []
    overdue: list[dict[str, Any]] = []
    for item in storyline.foreshadowing:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "planted").strip()
        resolved_chapter = _optional_int(item.get("resolved_chapter") or item.get("expected_resolution_chapter"))
        if status not in {"planted", "open"} or resolved_chapter is None:
            continue
        if chapter_index <= resolved_chapter + 2:
            continue
        overdue.append(
            {
                "hint": str(item.get("hint") or item.get("title") or item.get("name") or ""),
                "planted_chapter": _optional_int(item.get("planted_chapter") or item.get("introduced_chapter")),
                "resolved_chapter": resolved_chapter,
                "current_chapter": chapter_index,
                "status": status,
            }
        )
    return overdue


def _projection_status(summary: dict[str, int]) -> str:
    if summary["pacing_risks_requiring_human_judgment"] > 0:
        return "needs_human_judgment"
    if (
        summary["style_drift_findings"] > 0
        or summary["world_model_contradictions"] > 0
        or summary["overdue_foreshadowing"] > 0
    ):
        return "watch"
    return "ready"


def _recommended_tools(
    *,
    style_drift_findings: list[dict[str, Any]],
    world_model_contradictions: list[dict[str, Any]],
    overdue_foreshadowing: list[dict[str, Any]],
    pacing_risks: list[dict[str, Any]],
) -> list[str]:
    tools: list[str] = []
    if style_drift_findings or pacing_risks:
        tools.append("review_chapter_quality")
    if style_drift_findings or overdue_foreshadowing:
        tools.append("review_chapter_continuity")
    if world_model_contradictions:
        tools.append("review_world_model_proposals")
    if style_drift_findings or overdue_foreshadowing or pacing_risks:
        tools.append("plan_chapter_revision")
    return _dedupe(tools)


def _is_style_drift_code(code: str) -> bool:
    return code in STYLE_DRIFT_CODES or code.endswith("_drift")


def _is_pacing_code(code: str) -> bool:
    return "pacing" in code or "rhythm" in code


def _is_contradiction_item(item: WorldProposalItem) -> bool:
    text = " ".join(
        [
            str(item.claim_id or ""),
            str(item.predicate or ""),
            str(item.notes or ""),
        ]
    ).lower()
    return "contradiction" in text or "conflict" in text


def _chapter_index(step: WritingAgentStep, output: dict[str, Any]) -> int | None:
    if step.chapter_index is not None:
        return _optional_int(step.chapter_index)
    return _optional_int(output.get("chapter_index"))


def _latest_chapter_index(db: Session, project_id: str) -> int | None:
    value = db.query(func.max(ChapterContent.chapter_index)).filter(ChapterContent.project_id == project_id).scalar()
    return _optional_int(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result

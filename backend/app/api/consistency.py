import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.athena_shared import get_current_profile
from app.api.deprecation import add_deprecation_header
from app.core.consistency_checker import ConsistencyChecker
from app.core.setup_projection import get_setup_character_projection
from app.core.world_checker_registry import CheckerIssue, run_checks_for_project_profile
from app.db import get_db
from app.models import (
    BackgroundTask,
    ChapterContent,
    ConsistencyCheck,
    Project,
    WorldEvent,
    WorldEvidence,
    WorldFactClaim,
)
from app.prompting.providers.storyline import SetupContextSnapshot
from app.schemas import ConsistencyIssueListResponse
from app.services.tasks.background_task_service import BackgroundTaskService
from app.services.tasks.local_task_runner import LocalTaskRunner

router = APIRouter(prefix="/api/v1/projects/{project_id}/consistency", tags=["consistency"])


@router.post("/chapters/{chapter_index}/check")
async def run_check(project_id: str, chapter_index: int, depth: str = "l1", db: Session = Depends(get_db), response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/consistency/chapters/{chapter_index}/check")
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    chapter = db.query(ChapterContent).filter(
        ChapterContent.project_id == project_id,
        ChapterContent.chapter_index == chapter_index,
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    if depth == "l2":
        task = BackgroundTaskService(db).create(
            project_id=project_id,
            task_type="consistency_deep_check",
            payload={"chapter_index": chapter_index},
        )

        async def _run_deep(dbs: Session, running_task: BackgroundTask):
            from app.core.background_analyzer import BackgroundAnalyzer

            analyzer = BackgroundAnalyzer()
            return await analyzer.run_deep_check(project_id, chapter_index)

        LocalTaskRunner().start(task.id, _run_deep)
        return {"task_id": task.id, "status": "pending"}

    profile = get_current_profile(db, project_id)
    if profile is not None:
        try:
            issues = _check_world_model_profile(
                db=db,
                project_id=project_id,
                chapter_index=chapter_index,
                profile_id=profile.id,
                profile_version=profile.version,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        checker = ConsistencyChecker()
        setup = SetupContextSnapshot(
            world_building={},
            characters=get_setup_character_projection(db, project_id),
            core_concept={},
        )
        issues = checker.check(project_id, chapter, setup)

    db.query(ConsistencyCheck).filter(
        ConsistencyCheck.project_id == project_id,
        ConsistencyCheck.chapter_index == chapter_index,
    ).delete()

    for issue in issues:
        db.add(ConsistencyCheck(**issue))

    db.commit()
    return {"issues": issues}


@router.get("/issues", response_model=ConsistencyIssueListResponse)
def list_issues(
    project_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    response: Response = None,
):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/consistency")
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    query = db.query(ConsistencyCheck).filter(ConsistencyCheck.project_id == project_id)
    total = (
        db.query(func.count(ConsistencyCheck.id))
        .filter(ConsistencyCheck.project_id == project_id)
        .scalar()
        or 0
    )
    issues = (
        query
        .order_by(ConsistencyCheck.chapter_index.asc(), ConsistencyCheck.created_at.asc(), ConsistencyCheck.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "issues": issues,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(issues) < total,
    }


def _check_world_model_profile(
    *,
    db: Session,
    project_id: str,
    chapter_index: int,
    profile_id: str,
    profile_version: int,
) -> list[dict]:
    events = (
        db.query(WorldEvent)
        .filter(
            WorldEvent.project_id == project_id,
            WorldEvent.project_profile_version_id == profile_id,
            WorldEvent.profile_version == profile_version,
            WorldEvent.chapter_index == chapter_index,
        )
        .order_by(WorldEvent.chapter_index.asc(), WorldEvent.intra_chapter_seq.asc(), WorldEvent.event_id.asc())
        .all()
    )
    facts = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.project_profile_version_id == profile_id,
            WorldFactClaim.profile_version == profile_version,
            WorldFactClaim.chapter_index == chapter_index,
        )
        .order_by(WorldFactClaim.chapter_index.asc(), WorldFactClaim.intra_chapter_seq.asc(), WorldFactClaim.claim_id.asc())
        .all()
    )
    evidence = (
        db.query(WorldEvidence)
        .filter(
            WorldEvidence.project_id == project_id,
            WorldEvidence.project_profile_version_id == profile_id,
            WorldEvidence.profile_version == profile_version,
            WorldEvidence.chapter_index == chapter_index,
        )
        .order_by(WorldEvidence.chapter_index.asc(), WorldEvidence.intra_chapter_seq.asc(), WorldEvidence.evidence_id.asc())
        .all()
    )
    result = run_checks_for_project_profile(
        db=db,
        project_profile_version_id=profile_id,
        events=events,
        facts=facts,
        evidence=evidence,
    )
    return [
        _checker_issue_to_consistency_issue(
            issue=issue,
            project_id=project_id,
            chapter_index=chapter_index,
        )
        for issue in result.issues
    ]


def _checker_issue_to_consistency_issue(
    *,
    issue: CheckerIssue,
    project_id: str,
    chapter_index: int,
) -> dict:
    return {
        "project_id": project_id,
        "chapter_index": chapter_index,
        "checker_name": issue.checker_name,
        "severity": issue.severity,
        "subject": issue.code,
        "description": issue.message,
        "evidence": json.dumps(issue.refs, ensure_ascii=False, sort_keys=True) if issue.refs else "",
        "suggested_fix": f"按 {issue.layer} / {issue.checker_name} 修正 world-model 事件、事实或证据。",
        "status": "pending",
    }

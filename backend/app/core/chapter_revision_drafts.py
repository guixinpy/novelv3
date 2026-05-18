from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ChapterContent, ChapterRevision, RevisionAnnotation, RevisionCorrection

PLAN_ACTION_PREFIX = "[PLAN_ACTION:"


def create_revision_draft_from_plan(
    db: Session,
    project_id: str,
    chapter_index: int,
    plan: dict[str, Any],
) -> dict[str, Any]:
    chapter = (
        db.query(ChapterContent)
        .filter(ChapterContent.project_id == project_id, ChapterContent.chapter_index == chapter_index)
        .first()
    )
    if chapter is None:
        return {
            "status": "failed",
            "error": f"第{chapter_index}章尚未生成。",
            "chapter_index": chapter_index,
            "revision_id": None,
            "should_generate_next_chapter": False,
            "plan": plan,
        }

    actions = plan.get("revision_actions") if isinstance(plan.get("revision_actions"), list) else []
    if not actions:
        return {
            "status": "skipped",
            "reason": "no_revision_actions",
            "chapter_index": chapter_index,
            "revision_id": None,
            "annotation_count": 0,
            "correction_count": 0,
            "should_generate_next_chapter": bool(plan.get("should_generate_next_chapter")),
            "plan": plan,
        }

    active_revision = _active_non_draft_revision(db, chapter)
    if active_revision is not None:
        return _blocked_existing_revision(
            reason="existing_active_revision",
            chapter_index=chapter_index,
            revision=active_revision,
            plan=plan,
        )

    existing_draft = _get_existing_draft(db, chapter)
    if existing_draft is not None and not _is_planner_owned_draft(db, existing_draft):
        return _blocked_existing_revision(
            reason="existing_manual_draft",
            chapter_index=chapter_index,
            revision=existing_draft,
            plan=plan,
        )
    if existing_draft is not None:
        return _draft_output(db, revision=existing_draft, chapter_index=chapter_index, plan=plan, actions=actions)

    revision = _create_draft(db, chapter)
    _replace_planner_annotations(db, revision, chapter, actions)
    db.commit()
    db.refresh(revision)
    return _draft_output(db, revision=revision, chapter_index=chapter_index, plan=plan, actions=actions)


def _draft_output(
    db: Session,
    *,
    revision: ChapterRevision,
    chapter_index: int,
    plan: dict[str, Any],
    actions: list[Any],
) -> dict[str, Any]:
    annotation_count = db.query(RevisionAnnotation).filter(RevisionAnnotation.revision_id == revision.id).count()
    correction_count = db.query(RevisionCorrection).filter(RevisionCorrection.revision_id == revision.id).count()
    return {
        "status": "drafted",
        "chapter_index": chapter_index,
        "revision_id": revision.id,
        "revision_index": revision.revision_index,
        "annotation_count": annotation_count,
        "correction_count": correction_count,
        "should_generate_next_chapter": False,
        "plan_status": plan.get("status"),
        "revision_actions": actions,
        "recommended_next_tools": plan.get("recommended_next_tools") or [],
        "world_model_proposal_pressure": plan.get("world_model_proposal_pressure") or {},
        "plan": plan,
    }


def _active_non_draft_revision(db: Session, chapter: ChapterContent) -> ChapterRevision | None:
    return (
        db.query(ChapterRevision)
        .filter(
            ChapterRevision.project_id == chapter.project_id,
            ChapterRevision.chapter_index == chapter.chapter_index,
            ChapterRevision.status.in_(["submitted", "failed"]),
        )
        .order_by(ChapterRevision.revision_index.desc(), ChapterRevision.id.desc())
        .first()
    )


def _get_existing_draft(db: Session, chapter: ChapterContent) -> ChapterRevision | None:
    return (
        db.query(ChapterRevision)
        .filter(
            ChapterRevision.project_id == chapter.project_id,
            ChapterRevision.chapter_index == chapter.chapter_index,
            ChapterRevision.status == "draft",
        )
        .order_by(ChapterRevision.revision_index.desc(), ChapterRevision.id.desc())
        .first()
    )


def _create_draft(db: Session, chapter: ChapterContent) -> ChapterRevision:
    revision = ChapterRevision(
        project_id=chapter.project_id,
        chapter_id=chapter.id,
        chapter_index=chapter.chapter_index,
        revision_index=_next_revision_index(db, chapter.project_id, chapter.chapter_index),
        status="draft",
    )
    db.add(revision)
    db.flush()
    return revision


def _is_planner_owned_draft(db: Session, revision: ChapterRevision) -> bool:
    correction_count = db.query(RevisionCorrection).filter(RevisionCorrection.revision_id == revision.id).count()
    if correction_count:
        return False
    annotations = db.query(RevisionAnnotation).filter(RevisionAnnotation.revision_id == revision.id).all()
    return all((annotation.comment or "").startswith(PLAN_ACTION_PREFIX) for annotation in annotations)


def _blocked_existing_revision(
    *,
    reason: str,
    chapter_index: int,
    revision: ChapterRevision,
    plan: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "chapter_index": chapter_index,
        "revision_id": revision.id,
        "revision_index": revision.revision_index,
        "annotation_count": 0,
        "correction_count": 0,
        "should_generate_next_chapter": False,
        "plan": plan,
    }


def _next_revision_index(db: Session, project_id: str, chapter_index: int) -> int:
    latest = (
        db.query(func.max(ChapterRevision.revision_index))
        .filter(ChapterRevision.project_id == project_id, ChapterRevision.chapter_index == chapter_index)
        .scalar()
        or 0
    )
    return int(latest) + 1


def _replace_planner_annotations(
    db: Session,
    revision: ChapterRevision,
    chapter: ChapterContent,
    actions: list[Any],
) -> None:
    (
        db.query(RevisionAnnotation)
        .filter(
            RevisionAnnotation.revision_id == revision.id,
            RevisionAnnotation.comment.like(f"{PLAN_ACTION_PREFIX}%"),
        )
        .delete(synchronize_session=False)
    )
    for action in actions:
        if not isinstance(action, dict):
            continue
        annotation = _annotation_for_action(chapter, action)
        if annotation is not None:
            db.add(RevisionAnnotation(revision_id=revision.id, **annotation))


def _annotation_for_action(chapter: ChapterContent, action: dict[str, Any]) -> dict[str, Any] | None:
    action_name = str(action.get("action") or "")
    if not action_name:
        return None
    anchor = _anchor_for_action(chapter, action)
    source = str(action.get("source_finding") or "unknown")
    return {
        **anchor,
        "comment": _comment_for_action(action_name=action_name, source=source, action=action),
    }


def _anchor_for_action(chapter: ChapterContent, action: dict[str, Any]) -> dict[str, Any]:
    content = chapter.content or ""
    selected = _selected_evidence_text(content, action) or _default_selected_text(content, chapter)
    start_offset = max(content.find(selected), 0) if content else 0
    end_offset = start_offset + max(len(selected), 1)
    return {
        "paragraph_index": 0,
        "start_offset": start_offset,
        "end_offset": end_offset,
        "selected_text": selected,
    }


def _selected_evidence_text(content: str, action: dict[str, Any]) -> str | None:
    evidence = action.get("evidence") if isinstance(action.get("evidence"), dict) else {}
    matches = evidence.get("matches") if isinstance(evidence.get("matches"), list) else []
    for match in matches:
        if not isinstance(match, dict):
            continue
        tokens = match.get("matched_tokens") if isinstance(match.get("matched_tokens"), list) else []
        for token in tokens:
            value = str(token or "").strip()
            if value and value in content:
                return value
    return None


def _default_selected_text(content: str, chapter: ChapterContent) -> str:
    stripped = content.strip()
    if stripped:
        return stripped[: min(len(stripped), 24)]
    title = (chapter.title or "").strip()
    return title or f"第{chapter.chapter_index}章"


def _comment_for_action(*, action_name: str, source: str, action: dict[str, Any]) -> str:
    if action_name == "retitle_chapter":
        message = "建议重拟章节标题，避免通用占位标题；该草稿不直接改正文。"
    elif action_name == "compress_chapter":
        message = str(action.get("target") or "压缩到项目章节目标字数范围内，保留核心场景和必要情绪推进。")
    elif action_name == "defer_future_reveals":
        message = str(action.get("target") or "移除或弱化提前消耗的后续章节信息，改为悬念或轻量暗示。")
    elif action_name == "expand_chapter":
        message = str(action.get("target") or "补足场景密度、人物反应和有效冲突。")
    elif action_name == "repair_outline_gap":
        message = "先修复章节大纲缺口，再决定是否改写正文。"
    else:
        message = str(action.get("reason") or "根据修订计划处理该问题。")
    return f"[PLAN_ACTION:{action_name}][SOURCE:{source}] {message}"

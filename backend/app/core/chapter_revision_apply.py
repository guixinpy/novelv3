from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.text_stats import count_words
from app.models import ChapterContent, ChapterRevision, Project, RevisionAnnotation, Version

PLAN_ACTION_PREFIX = "[PLAN_ACTION:"
SUPPORTED_ACTIONS = {"fix_character_profile_drift", "respect_ability_boundary"}


def apply_planner_revision_patch(
    db: Session,
    project_id: str,
    chapter_index: int,
    *,
    revision_id: str | None = None,
) -> dict[str, Any]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        return _blocked("missing_project", chapter_index, "项目不存在。")

    chapter = (
        db.query(ChapterContent)
        .filter(ChapterContent.project_id == project_id, ChapterContent.chapter_index == chapter_index)
        .first()
    )
    if chapter is None:
        return _blocked("missing_chapter", chapter_index, f"第{chapter_index}章尚未生成。")

    revision = _revision_for_patch(db, project_id=project_id, chapter_index=chapter_index, revision_id=revision_id)
    if revision is None:
        return _blocked("missing_planner_revision", chapter_index, "缺少可应用的planner修订草稿。")

    annotations = db.query(RevisionAnnotation).filter(RevisionAnnotation.revision_id == revision.id).all()
    actions = [_action_name(annotation.comment or "") for annotation in annotations]
    invalid = [annotation.comment for annotation, action in zip(annotations, actions, strict=False) if action is None]
    if invalid:
        return _blocked("non_planner_annotation", chapter_index, "修订草稿包含非planner批注，不能自动应用。", revision=revision)
    unsupported = sorted({str(action) for action in actions if action not in SUPPORTED_ACTIONS})
    if unsupported:
        return _blocked(
            "unsupported_planner_action",
            chapter_index,
            "修订草稿包含暂不支持的planner动作。",
            revision=revision,
            extra={"unsupported_actions": unsupported},
        )

    original_content = chapter.content or ""
    patched_content = original_content
    applied: list[dict[str, str]] = []
    for action in actions:
        patched_content, replacements = _apply_action(patched_content, str(action))
        applied.extend(replacements)

    if patched_content == original_content or not applied:
        return _blocked("no_supported_replacement", chapter_index, "未找到可安全替换的漂移文本。", revision=revision)

    if revision.base_version_id is None:
        base_version = _create_chapter_version(
            db,
            chapter,
            description=f"Revision {revision.revision_index} base before deterministic patch",
            author="agent",
        )
        revision.base_version_id = base_version.id

    previous_word_count = int(chapter.word_count or 0)
    chapter.content = patched_content
    chapter.word_count = count_words(patched_content)
    project.current_word_count = max(0, int(project.current_word_count or 0) - previous_word_count + int(chapter.word_count or 0))

    result_version = _create_chapter_version(
        db,
        chapter,
        description=f"Revision {revision.revision_index} deterministic patch result",
        author="agent",
    )
    revision.status = "completed"
    revision.completed_at = datetime.now(UTC)
    revision.chapter_id = chapter.id
    revision.result_version_id = result_version.id
    db.commit()
    db.refresh(chapter)
    db.refresh(revision)

    return {
        "status": "completed",
        "chapter_index": chapter_index,
        "chapter_id": chapter.id,
        "revision_id": revision.id,
        "revision_index": revision.revision_index,
        "base_version_id": revision.base_version_id,
        "result_version_id": revision.result_version_id,
        "applied_replacement_count": len(applied),
        "applied_replacements": applied,
        "word_count": chapter.word_count,
        "should_generate_next_chapter": False,
        "recommended_next_tools": ["review_chapter_quality"],
    }


def _revision_for_patch(
    db: Session,
    *,
    project_id: str,
    chapter_index: int,
    revision_id: str | None,
) -> ChapterRevision | None:
    query = db.query(ChapterRevision).filter(
        ChapterRevision.project_id == project_id,
        ChapterRevision.chapter_index == chapter_index,
        ChapterRevision.status == "draft",
    )
    if revision_id:
        return query.filter(ChapterRevision.id == revision_id).first()
    return query.order_by(ChapterRevision.revision_index.desc(), ChapterRevision.id.desc()).first()


def _action_name(comment: str) -> str | None:
    if not comment.startswith(PLAN_ACTION_PREFIX):
        return None
    rest = comment[len(PLAN_ACTION_PREFIX) :]
    return rest.split("]", 1)[0].strip() or None


def _apply_action(content: str, action: str) -> tuple[str, list[dict[str, str]]]:
    if action == "fix_character_profile_drift":
        return _replace_first(
            content,
            [
                ("他叫叶知秋，以前是雾安局的研究员", "她叫叶知秋，是雾港大学神经科学教授，曾参与政府秘密项目"),
                ("以前是雾安局研究员", "是雾港大学神经科学教授，曾参与政府秘密项目"),
                ("以前是雾安局的研究员", "是雾港大学神经科学教授，曾参与政府秘密项目"),
            ],
            action=action,
        )
    if action == "respect_ability_boundary":
        return _replace_first(content, [("制造幻觉", "扰乱雾中感知")], action=action)
    return content, []


def _replace_first(content: str, pairs: list[tuple[str, str]], *, action: str) -> tuple[str, list[dict[str, str]]]:
    for original, replacement in pairs:
        if original in content:
            return content.replace(original, replacement, 1), [
                {"action": action, "original_text": original, "replacement_text": replacement}
            ]
    return content, []


def _create_chapter_version(db: Session, chapter: ChapterContent, *, description: str, author: str) -> Version:
    version = Version(
        project_id=chapter.project_id,
        node_type="chapter",
        node_id=chapter.id,
        version_number=_next_version_number(db, chapter.project_id, chapter.id),
        content=chapter.content or "",
        description=description,
        author=author,
    )
    db.add(version)
    db.flush()
    return version


def _next_version_number(db: Session, project_id: str, chapter_id: str) -> int:
    value = (
        db.query(func.max(Version.version_number))
        .filter(Version.project_id == project_id, Version.node_type == "chapter", Version.node_id == chapter_id)
        .scalar()
        or 0
    )
    return int(value) + 1


def _blocked(
    reason: str,
    chapter_index: int,
    message: str,
    *,
    revision: ChapterRevision | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "message": message,
        "chapter_index": chapter_index,
        "revision_id": revision.id if revision else None,
        "should_generate_next_chapter": False,
        "recommended_next_tools": ["create_revision_draft"],
        **(extra or {}),
    }

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.ai_service import AIService
from app.core.deepseek_adapter import parse_json_safely
from app.core.model_call_trace import build_context_block, create_trace, mark_trace_failed, mark_trace_success, now_ms
from app.core.outline_lookup import find_outline_chapter
from app.core.text_stats import count_words
from app.core.world_proposal_state import ACTIONABLE_REVIEW_ITEM_STATUSES
from app.models import ChapterContent, ChapterRevision, Project, ProjectProfileVersion, Version, WorldProposalItem
from app.prompting.providers.chapter import project_chapter_word_range


async def expand_chapter_to_target(
    db: Session,
    project_id: str,
    chapter_index: int,
    *,
    min_word_count: int | None = None,
    extra_instruction: str = "",
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
    if chapter.status != "generated" or not (chapter.content or "").strip():
        return _blocked("chapter_not_generated", chapter_index, f"第{chapter_index}章不是可扩写的已生成正文。")

    target_range = project_chapter_word_range(project)
    target_min = min_word_count or (target_range[0] if target_range else None)
    target_max = target_range[1] if target_range else None
    if target_min is None:
        return _blocked("missing_word_target", chapter_index, "项目缺少章节目标字数，无法判断扩写目标。")

    previous_word_count = int(chapter.word_count or count_words(chapter.content or ""))
    if previous_word_count >= target_min:
        return {
            "status": "skipped",
            "reason": "chapter_already_at_target",
            "chapter_index": chapter_index,
            "previous_word_count": previous_word_count,
            "word_count": previous_word_count,
            "target_min_word_count": target_min,
            "should_generate_next_chapter": True,
            "recommended_next_tools": ["preflight_writing"],
        }

    pending_count = _pending_world_model_proposal_count(db, project_id)
    if pending_count:
        return _blocked(
            "pending_world_model_proposals",
            chapter_index,
            "世界模型仍有待审提案，扩写前需要先处理事实队列。",
            extra={"pending_world_model_proposal_count": pending_count, "recommended_next_tools": ["review_world_model_proposals"]},
        )

    messages = _expansion_messages(
        db,
        project=project,
        chapter=chapter,
        target_min=target_min,
        target_max=target_max,
        extra_instruction=extra_instruction,
    )
    max_tokens = min(8000, max(target_min + 1200, 2600))
    trace = create_trace(
        db,
        project_id=project_id,
        trace_type="chapter_expansion",
        messages=messages,
        context_blocks=[
            build_context_block(
                key="chapter_expansion_source",
                kind="chapter",
                title=f"第{chapter_index}章扩写前正文",
                content=chapter.content or "",
            )
        ],
        model=project.ai_model or "deepseek-chat",
        temperature=0.45,
        max_tokens=max_tokens,
        chapter_id=chapter.id,
        chapter_index=chapter_index,
        trace_metadata={
            "chapter_expansion": {
                "previous_word_count": previous_word_count,
                "target_min_word_count": target_min,
                "target_max_word_count": target_max,
            }
        },
    )
    db.commit()
    started_at = now_ms()

    try:
        ai_service = AIService()
        try:
            result = await ai_service.complete(
                messages,
                temperature=0.45,
                max_tokens=max_tokens,
                model=project.ai_model or "deepseek-chat",
                response_format={"type": "json_object"},
            )
        finally:
            close = getattr(ai_service, "close", None)
            if callable(close):
                await close()
        payload = parse_json_safely(result.content)
    except Exception as exc:
        mark_trace_failed(db, trace, error_message=str(exc), latency_ms=now_ms() - started_at)
        db.commit()
        return _blocked("model_call_failed", chapter_index, str(exc))

    expanded_content = _expanded_content(payload)
    expanded_word_count = count_words(expanded_content)
    if not expanded_content or expanded_word_count < target_min:
        mark_trace_failed(
            db,
            trace,
            error_message=f"expanded content under target: {expanded_word_count} < {target_min}",
            latency_ms=now_ms() - started_at,
        )
        db.commit()
        return _blocked(
            "expanded_content_under_target",
            chapter_index,
            "模型扩写结果仍低于目标字数，未写入章节。",
            extra={
                "previous_word_count": previous_word_count,
                "word_count": expanded_word_count,
                "target_min_word_count": target_min,
            },
        )

    revision = ChapterRevision(
        project_id=project_id,
        chapter_id=chapter.id,
        chapter_index=chapter_index,
        revision_index=_next_revision_index(db, project_id, chapter_index),
        status="completed",
        completed_at=datetime.now(UTC),
    )
    db.add(revision)
    db.flush()

    base_version = _create_chapter_version(
        db,
        chapter,
        description=f"Revision {revision.revision_index} base before target expansion",
        author="agent",
    )
    revision.base_version_id = base_version.id

    chapter.content = expanded_content
    chapter.word_count = expanded_word_count
    project.current_word_count = max(
        0,
        int(project.current_word_count or 0) - previous_word_count + expanded_word_count,
    )

    result_version = _create_chapter_version(
        db,
        chapter,
        description=f"Revision {revision.revision_index} target expansion result",
        author="agent",
    )
    revision.result_version_id = result_version.id
    trace.trace_metadata = {
        **(trace.trace_metadata or {}),
        "chapter_expansion": {
            **((trace.trace_metadata or {}).get("chapter_expansion") or {}),
            "word_count": expanded_word_count,
            "change_summary": str(payload.get("change_summary") or ""),
        },
    }
    mark_trace_success(
        db,
        trace,
        prompt_tokens=getattr(result, "prompt_tokens", 0),
        completion_tokens=getattr(result, "completion_tokens", 0),
        latency_ms=now_ms() - started_at,
    )
    db.commit()
    db.refresh(chapter)
    db.refresh(revision)

    warnings = _safe_reindex_chapter(db, project_id=project_id, chapter_index=chapter_index)
    return {
        "status": "completed",
        "chapter_index": chapter_index,
        "chapter_id": chapter.id,
        "revision_id": revision.id,
        "revision_index": revision.revision_index,
        "base_version_id": revision.base_version_id,
        "result_version_id": revision.result_version_id,
        "trace_id": trace.id,
        "previous_word_count": previous_word_count,
        "word_count": chapter.word_count,
        "target_min_word_count": target_min,
        "target_max_word_count": target_max,
        "change_summary": str(payload.get("change_summary") or ""),
        "warnings": warnings,
        "should_generate_next_chapter": False,
        "recommended_next_tools": ["review_chapter_quality"],
    }


def _pending_world_model_proposal_count(db: Session, project_id: str) -> int:
    profile = (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc(), ProjectProfileVersion.created_at.desc())
        .first()
    )
    if profile is None:
        return 0
    return int(
        db.query(func.count(WorldProposalItem.id))
        .filter(
            WorldProposalItem.project_id == project_id,
            WorldProposalItem.project_profile_version_id == profile.id,
            WorldProposalItem.profile_version == profile.version,
            WorldProposalItem.item_status.in_(ACTIONABLE_REVIEW_ITEM_STATUSES),
        )
        .scalar()
        or 0
    )


def _expansion_messages(
    db: Session,
    *,
    project: Project,
    chapter: ChapterContent,
    target_min: int,
    target_max: int | None,
    extra_instruction: str,
) -> list[dict[str, str]]:
    outline_text = _outline_text(db, project.id, int(chapter.chapter_index or 0))
    range_text = f"{target_min}-{target_max}字" if target_max else f"不少于{target_min}字"
    instruction = (
        f"请扩写《{project.name}》第{chapter.chapter_index}章《{chapter.title or f'第{chapter.chapter_index}章'}》。\n"
        f"当前约{int(chapter.word_count or 0)}字，扩写后正文必须控制在{range_text}，至少达到下限。\n"
        "要求：保留既有剧情事实和章节标题；不要新增世界模型事实；不要提前揭露后续大纲；"
        "通过场景动作、人物反应、环境压迫、冲突推进和段落过渡补足正文密度；"
        "输出必须是 JSON，格式为 {\"content\":\"完整扩写后的正文\", \"change_summary\":\"扩写摘要\"}。\n"
        f"{extra_instruction.strip()}"
    ).strip()
    user_content = (
        f"{instruction}\n\n"
        f"章节大纲：\n{outline_text}\n\n"
        f"当前正文：\n{chapter.content or ''}"
    )
    return [
        {"role": "system", "content": "你是专精网络小说的章节修订编辑，只做保守扩写，不改写世界真相。"},
        {"role": "user", "content": user_content},
    ]


def _outline_text(db: Session, project_id: str, chapter_index: int) -> str:
    found = find_outline_chapter(db, project_id, chapter_index)
    if found is None:
        return "未找到章节大纲。"
    _outline_id, outline = found
    parts = [
        f"标题：{outline.get('title') or ''}",
        f"摘要：{outline.get('summary') or ''}",
        f"目的：{outline.get('purpose') or ''}",
    ]
    scenes = outline.get("scenes") if isinstance(outline.get("scenes"), list) else []
    if scenes:
        parts.append("场景：" + " / ".join(str(scene) for scene in scenes[:6]))
    characters = outline.get("characters") if isinstance(outline.get("characters"), list) else []
    if characters:
        parts.append("角色：" + " / ".join(str(character) for character in characters[:8]))
    return "\n".join(part for part in parts if part.strip())


def _expanded_content(payload: dict[str, Any]) -> str:
    content = str(payload.get("content") or "").strip()
    return content


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


def _next_revision_index(db: Session, project_id: str, chapter_index: int) -> int:
    value = (
        db.query(func.max(ChapterRevision.revision_index))
        .filter(ChapterRevision.project_id == project_id, ChapterRevision.chapter_index == chapter_index)
        .scalar()
        or 0
    )
    return int(value) + 1


def _safe_reindex_chapter(db: Session, *, project_id: str, chapter_index: int) -> list[dict[str, str]]:
    try:
        from app.core.athena_retrieval import index_chapter_retrieval

        index_chapter_retrieval(db=db, project_id=project_id, chapter_index=chapter_index)
        return []
    except Exception as exc:
        db.rollback()
        return [{"code": "chapter_retrieval_index", "message": str(exc)}]


def _blocked(
    reason: str,
    chapter_index: int,
    message: str,
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "message": message,
        "chapter_index": chapter_index,
        "should_generate_next_chapter": False,
        "recommended_next_tools": ["review_chapter_quality"],
        **(extra or {}),
    }

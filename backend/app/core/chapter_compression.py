from __future__ import annotations

import re
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


MAX_COMPRESSION_ATTEMPTS = 3
NEAR_TARGET_UNDER_REPAIR_MAX_GAP = 220
NEAR_TARGET_OVER_TRIM_MAX_OVERAGE = 260
LARGE_OVER_TRIM_MAX_OVERAGE = 900
TRIM_PROTECTED_EDGE_SENTENCE_COUNT = 2
TRIM_PROTECTED_TERMS = ("林深", "苏晚晴", "灯塔", "暗河", "雾晶", "号码牌", "父亲", "陈默")
TRIM_HINT_TERMS = ("反复", "再次", "似乎", "仿佛", "仍然", "只是", "沉默", "解释")


async def compress_chapter_to_target(
    db: Session,
    project_id: str,
    chapter_index: int,
    *,
    target_max_word_count: int | None = None,
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
        return _blocked("chapter_not_generated", chapter_index, f"第{chapter_index}章不是可压缩的已生成正文。")

    target_range = project_chapter_word_range(project)
    if not target_range:
        return _blocked("missing_word_target", chapter_index, "项目缺少章节目标字数，无法判断压缩目标。")
    target_min, default_target_max = target_range
    target_max = target_max_word_count or default_target_max
    if target_max < target_min:
        return _blocked("invalid_word_target", chapter_index, "压缩目标上限不能低于章节目标下限。")

    previous_word_count = int(chapter.word_count or count_words(chapter.content or ""))
    if previous_word_count <= target_max:
        return {
            "status": "skipped",
            "reason": "chapter_already_within_target",
            "chapter_index": chapter_index,
            "previous_word_count": previous_word_count,
            "word_count": previous_word_count,
            "target_min_word_count": target_min,
            "target_max_word_count": target_max,
            "should_generate_next_chapter": True,
            "recommended_next_tools": ["preflight_writing"],
        }

    pending_count = _pending_world_model_proposal_count(db, project_id)
    if pending_count:
        return _blocked(
            "pending_world_model_proposals",
            chapter_index,
            "世界模型仍有待审提案，压缩前需要先处理事实队列。",
            extra={
                "pending_world_model_proposal_count": pending_count,
                "recommended_next_tools": ["review_world_model_proposals"],
            },
        )

    max_tokens = min(8000, max(target_max + 1000, 2600))
    failed_attempts: list[dict[str, Any]] = []
    prior_candidate = ""
    prior_word_count: int | None = None
    prior_direction = ""
    compressed_content = ""
    compressed_word_count = 0
    payload: dict[str, Any] = {}
    result: Any = None
    trace = None
    deterministic_repair_applied = False
    deterministic_trim_applied = False

    for attempt_index in range(1, MAX_COMPRESSION_ATTEMPTS + 1):
        messages = _compression_messages(
            db,
            project=project,
            chapter=chapter,
            target_min=target_min,
            target_max=target_max,
            extra_instruction=extra_instruction,
            attempt_index=attempt_index,
            prior_candidate=prior_candidate,
            prior_word_count=prior_word_count,
            prior_direction=prior_direction,
        )
        trace = create_trace(
            db,
            project_id=project_id,
            trace_type="chapter_compression",
            messages=messages,
            context_blocks=[
                build_context_block(
                    key="chapter_compression_source",
                    kind="chapter",
                    title=f"第{chapter_index}章压缩前正文",
                    content=chapter.content or "",
                )
            ],
            model=project.ai_model or "deepseek-chat",
            temperature=0.35,
            max_tokens=max_tokens,
            chapter_id=chapter.id,
            chapter_index=chapter_index,
            trace_metadata={
                "chapter_compression": {
                    "attempt_index": attempt_index,
                    "max_attempts": MAX_COMPRESSION_ATTEMPTS,
                    "previous_word_count": previous_word_count,
                    "target_min_word_count": target_min,
                    "target_max_word_count": target_max,
                    "prior_word_count": prior_word_count,
                    "prior_direction": prior_direction,
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
                    temperature=0.35,
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
            return _blocked(
                "model_call_failed",
                chapter_index,
                str(exc),
                extra={
                    "compression_attempt_count": attempt_index,
                    "failed_attempts": failed_attempts,
                },
            )

        compressed_content = str(payload.get("content") or "").strip()
        compressed_word_count = count_words(compressed_content)
        repaired_content, repaired = _repair_under_target_candidate(
            compressed_content,
            source_content=chapter.content or "",
            target_min=target_min,
            target_max=target_max,
        )
        if repaired:
            compressed_content = repaired_content
            compressed_word_count = count_words(compressed_content)
            deterministic_repair_applied = True
        else:
            trimmed_content, trimmed = _trim_over_target_candidate(
                compressed_content,
                target_min=target_min,
                target_max=target_max,
            )
            if trimmed:
                compressed_content = trimmed_content
                compressed_word_count = count_words(compressed_content)
                deterministic_trim_applied = True
        direction = _target_direction(compressed_word_count, target_min, target_max)
        if compressed_content and direction == "within_target":
            break
        if attempt_index == MAX_COMPRESSION_ATTEMPTS and direction == "under_target":
            fallback_content, fallback_trimmed = _trim_over_target_candidate(
                chapter.content or "",
                target_min=target_min,
                target_max=target_max,
            )
            if fallback_trimmed:
                compressed_content = fallback_content
                compressed_word_count = count_words(compressed_content)
                deterministic_trim_applied = True
                payload = {
                    **payload,
                    "change_summary": str(payload.get("change_summary") or "")
                    or "模型候选低于目标下限，已从原文保守裁剪到目标范围。",
                }
                break

        failed_attempt = {
            "attempt_index": attempt_index,
            "word_count": compressed_word_count,
            "direction": direction,
            "trace_id": trace.id,
        }
        failed_attempts.append(failed_attempt)
        mark_trace_failed(
            db,
            trace,
            error_message=f"compressed content outside target: {compressed_word_count} not in {target_min}-{target_max}",
            latency_ms=now_ms() - started_at,
        )
        db.commit()
        prior_candidate = compressed_content
        prior_word_count = compressed_word_count
        prior_direction = direction

    if not compressed_content or compressed_word_count < target_min or compressed_word_count > target_max or trace is None:
        return _blocked(
            "compressed_content_outside_target",
            chapter_index,
            "模型压缩结果未落入目标字数范围，未写入章节。",
            extra={
                "previous_word_count": previous_word_count,
                "word_count": compressed_word_count,
                "target_min_word_count": target_min,
                "target_max_word_count": target_max,
                "compression_attempt_count": len(failed_attempts),
                "failed_attempts": failed_attempts,
                "deterministic_repair_applied": deterministic_repair_applied,
                "deterministic_trim_applied": deterministic_trim_applied,
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
        description=f"Revision {revision.revision_index} base before target compression",
        author="agent",
    )
    revision.base_version_id = base_version.id

    chapter.content = compressed_content
    chapter.word_count = compressed_word_count
    project.current_word_count = max(
        0,
        int(project.current_word_count or 0) - previous_word_count + compressed_word_count,
    )

    result_version = _create_chapter_version(
        db,
        chapter,
        description=f"Revision {revision.revision_index} target compression result",
        author="agent",
    )
    revision.result_version_id = result_version.id
    trace.trace_metadata = {
        **(trace.trace_metadata or {}),
        "chapter_compression": {
            **((trace.trace_metadata or {}).get("chapter_compression") or {}),
            "word_count": compressed_word_count,
            "change_summary": str(payload.get("change_summary") or ""),
            "deterministic_repair_applied": deterministic_repair_applied,
            "deterministic_trim_applied": deterministic_trim_applied,
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
    warnings.extend(_safe_refresh_longform_maintenance(db, project_id=project_id, chapter_index=chapter_index))
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
        "compression_attempt_count": len(failed_attempts) + 1,
        "failed_attempts": failed_attempts,
        "deterministic_repair_applied": deterministic_repair_applied,
        "deterministic_trim_applied": deterministic_trim_applied,
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


def _target_direction(word_count: int, target_min: int, target_max: int) -> str:
    if word_count < target_min:
        return "under_target"
    if word_count > target_max:
        return "over_target"
    return "within_target"


def _repair_under_target_candidate(
    candidate: str,
    *,
    source_content: str,
    target_min: int,
    target_max: int,
) -> tuple[str, bool]:
    candidate = candidate.strip()
    current_word_count = count_words(candidate)
    gap = target_min - current_word_count
    if not candidate or gap <= 0 or gap > NEAR_TARGET_UNDER_REPAIR_MAX_GAP:
        return candidate, False

    repaired = candidate
    for sentence in reversed(_split_sentences(source_content)):
        sentence = sentence.strip()
        if not sentence or sentence in repaired:
            continue
        next_content = f"{repaired.rstrip()}\n\n{sentence}"
        next_word_count = count_words(next_content)
        if next_word_count > target_max:
            continue
        repaired = next_content
        if next_word_count >= target_min:
            return repaired, True
    return candidate, False


def _trim_over_target_candidate(
    candidate: str,
    *,
    target_min: int,
    target_max: int,
) -> tuple[str, bool]:
    candidate = candidate.strip()
    current_word_count = count_words(candidate)
    overage = current_word_count - target_max
    if not candidate or overage <= 0 or overage > LARGE_OVER_TRIM_MAX_OVERAGE:
        return candidate, False

    sentences = _split_sentences(candidate)
    edge_count = TRIM_PROTECTED_EDGE_SENTENCE_COUNT if overage > NEAR_TARGET_OVER_TRIM_MAX_OVERAGE else 1
    if len(sentences) <= edge_count * 2 + 1:
        return candidate, False

    protected_indexes = set(range(edge_count)) | set(range(len(sentences) - edge_count, len(sentences)))
    removable_indexes = [index for index in range(len(sentences)) if index not in protected_indexes]
    removable_indexes.sort(key=lambda index: _trim_sentence_rank(sentences[index], overage))

    removed: set[int] = set()
    for index in removable_indexes:
        removed.add(index)
        trimmed = "".join(sentence for sentence_index, sentence in enumerate(sentences) if sentence_index not in removed)
        trimmed_word_count = count_words(trimmed)
        if trimmed_word_count < target_min:
            removed.remove(index)
            continue
        if trimmed_word_count <= target_max:
            return trimmed.strip(), True
    return candidate, False


def _trim_sentence_rank(sentence: str, overage: int) -> tuple[int, int]:
    importance = 0
    if "“" in sentence or "”" in sentence:
        importance += 5
    if any(term in sentence for term in TRIM_PROTECTED_TERMS):
        importance += 2
    if any(term in sentence for term in TRIM_HINT_TERMS):
        importance -= 1
    return importance, abs(count_words(sentence) - overage)


def _split_sentences(content: str) -> list[str]:
    return [part.strip() for part in re.findall(r"[^。！？!?]+[。！？!?]?", content or "") if part.strip()]


def _compression_messages(
    db: Session,
    *,
    project: Project,
    chapter: ChapterContent,
    target_min: int,
    target_max: int,
    extra_instruction: str,
    attempt_index: int = 1,
    prior_candidate: str = "",
    prior_word_count: int | None = None,
    prior_direction: str = "",
) -> list[dict[str, str]]:
    outline_text = _outline_text(db, project.id, int(chapter.chapter_index or 0))
    current_word_count = int(chapter.word_count or 0)
    overage = max(0, current_word_count - target_max)
    if overage <= 300:
        preferred_low = max(target_min, target_max - 120)
        preferred_high = max(preferred_low, target_max - 20)
        scale_guidance = (
            f"本章只超出目标上限约{overage}字，只做轻量裁剪；保留所有完整场景，不要删整段关键对话；"
            f"压缩后优先落在{preferred_low}-{preferred_high}字。"
        )
    else:
        preferred_low = min(target_max, max(target_min, target_min + 100))
        preferred_high = min(target_max, max(preferred_low, target_max - 50))
        scale_guidance = (
            f"本章超出目标上限约{overage}字，可以压缩重复解释和冗余描写；"
            f"压缩后优先落在{preferred_low}-{preferred_high}字。"
        )
    retry_guidance = ""
    if attempt_index > 1 and prior_direction == "under_target":
        retry_guidance = (
            f"上一次压缩结果低于目标下限，只有{prior_word_count or 0}字。"
            "请以候选稿为基础恢复必要场景密度、动作链、对话和情绪转折，必须回到目标范围。"
        )
    elif attempt_index > 1 and prior_direction == "over_target":
        cut_size = max(0, (prior_word_count or 0) - target_max)
        retry_guidance = (
            f"上一次候选仍高于目标上限，约{prior_word_count or 0}字，需要至少删减{cut_size}字。"
            "禁止原样返回候选稿；必须合并或删除低信息密度句子；"
            "不要改变剧情事实，必须回到目标范围。"
        )
    instruction = (
        f"请压缩《{project.name}》第{chapter.chapter_index}章《{chapter.title or f'第{chapter.chapter_index}章'}》。\n"
        f"当前约{current_word_count}字，必须压缩到目标字数范围{target_min}-{target_max}字。\n"
        f"{scale_guidance}\n"
        f"{retry_guidance}\n"
        f"宁可接近上限，也绝不能低于{target_min}字。\n"
        "要求：保留既有剧情事实、章节标题、人物动机、关键冲突和章末钩子；不要新增世界模型事实；"
        "不要提前揭露后续大纲；这不是摘要，必须输出完整正文；"
        "删除重复说明、冗余心理描写、过长环境铺陈和反复解释，但保留完整场景链条、关键动作、关键对话和情绪转折；"
        "输出必须是 JSON，格式为 {\"content\":\"完整压缩后的正文\", \"change_summary\":\"压缩摘要\"}。\n"
        f"{extra_instruction.strip()}"
    ).strip()
    user_content = (
        f"{instruction}\n\n"
        f"章节大纲：\n{outline_text}\n\n"
        f"当前正文：\n{chapter.content or ''}"
    )
    if prior_candidate.strip():
        user_content = (
            f"{user_content}\n\n"
            f"上一次失败候选稿：\n{prior_candidate.strip()}"
        )
    return [
        {"role": "system", "content": "你是专精网络小说的章节修订编辑，只做保守压缩，不改写世界真相。"},
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


def _safe_refresh_longform_maintenance(db: Session, *, project_id: str, chapter_index: int) -> list[dict[str, str]]:
    try:
        from app.core.longform_memory import refresh_longform_memory_for_chapter

        refresh_result = refresh_longform_memory_for_chapter(
            db,
            project_id,
            chapter_index,
            reconcile_word_count=False,
        )
    except Exception as exc:
        db.rollback()
        return [{"code": "longform_memory_refresh", "message": str(exc)}]

    try:
        from app.core.athena_retrieval import sync_longform_memory_retrieval_documents

        sync_longform_memory_retrieval_documents(
            db,
            project_id,
            refresh_result.get("updated_memory_ids") or [],
        )
    except Exception as exc:
        db.rollback()
        return [{"code": "longform_memory_retrieval_sync", "message": str(exc)}]
    return []


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

import re
import time

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import String, func
from sqlalchemy.orm import Session

from app.config import load_api_key
from app.core.ai_service import AIService
from app.core.athena_retrieval import sync_longform_memory_retrieval_documents
from app.core.chapter_target import chapter_index_exceeds_target
from app.core.longform_memory import refresh_longform_memory_for_chapter
from app.core.model_call_trace import create_trace, mark_trace_failed, mark_trace_success, now_ms, truncate_text
from app.core.outline_lookup import find_outline_chapter
from app.core.setup_projection import get_setup_character_projection
from app.core.text_stats import count_words
from app.db import get_db
from app.models import AIModelCallTrace, ChapterContent, Project, Setup
from app.prompting.assembler import PromptAssembler
from app.prompting.providers.chapter import (
    CHAPTER_CONTEXT_CHAR_BUDGET,
    SETUP_CHARACTERS_BLOCK_CHAR_LIMIT,
    SETUP_CORE_CONCEPT_BLOCK_CHAR_LIMIT,
    SETUP_WORLD_BLOCK_CHAR_LIMIT,
    build_chapter_prompt_context_blocks,
    build_chapter_prompt_variables,
    build_chapter_trace_context_blocks,
    chapter_max_tokens,
    project_chapter_word_range,
)
from app.prompting.providers.storyline import SetupContextSnapshot
from app.prompting.tracing import build_prompt_trace_metadata
from app.schemas import ChapterOut
from app.services.writing.writing_state_service import WritingStateService

router = APIRouter(prefix="/api/v1/projects/{project_id}/chapters", tags=["chapters"])

ai_service = AIService()
prompt_assembler = PromptAssembler()
FENCED_CHAPTER_RE = re.compile(r"^\s*```(?:[A-Za-z0-9_-]+)?\s*\n(?P<body>.*?)\n?```\s*$", re.DOTALL)
CHAPTER_HEADING_RE = re.compile(
    r"^\s{0,3}#{0,6}\s*第\s*[\d零〇一二两三四五六七八九十百千]+\s*章(?:\s|[：:、.．-]|$).*$"
)
CHAPTER_OUTLINE_MARKER_RE = re.compile(
    r"^\s*(?:第\s*[\d零〇一二两三四五六七八九十百千]+\s*章|章节|场景|角色|人物|摘要|梗概|目标|冲突|伏笔|结尾|[-*•]|\d+[.、])(?:\s|[：:、.．-]|$)"
)
EMPTY_CHAPTER_CONTENT_ERROR = "Generated chapter content is empty after normalization"
POST_GENERATION_WARNING_MESSAGE_CHARS = 500
OUTLINE_LIKE_CHAPTER_WARNING_MESSAGE = "章节内容疑似大纲或摘要格式，建议改写为连续正文场景。"


def _latest_chapter_generation_trace_id(db: Session, chapter: ChapterContent) -> str | None:
    trace = (
        db.query(AIModelCallTrace)
        .filter(
            AIModelCallTrace.project_id == chapter.project_id,
            AIModelCallTrace.trace_type == "chapter_generation",
            AIModelCallTrace.chapter_index == chapter.chapter_index,
            AIModelCallTrace.chapter_id == chapter.id,
            AIModelCallTrace.status == "success",
        )
        .order_by(AIModelCallTrace.created_at.desc(), AIModelCallTrace.id.desc())
        .first()
    )
    return trace.id if trace else None


def _chapter_out(db: Session, chapter: ChapterContent) -> dict:
    payload = ChapterOut.model_validate(chapter).model_dump()
    payload["last_generation_trace_id"] = _latest_chapter_generation_trace_id(db, chapter)
    return payload


def _normalize_generated_chapter_content(content: str) -> str:
    text = (content or "").strip()
    fenced_match = FENCED_CHAPTER_RE.match(text)
    if fenced_match:
        text = fenced_match.group("body").strip()

    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and CHAPTER_HEADING_RE.match(lines[0]):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines.pop(0)
        text = "\n".join(lines).strip()
    return text


def _get_chapter_setup_context(db: Session, project_id: str) -> SetupContextSnapshot | None:
    row = (
        db.query(
            Setup.id,
            func.substr(
                func.cast(Setup.world_building, String),
                1,
                SETUP_WORLD_BLOCK_CHAR_LIMIT + 1,
            ).label("world_building"),
            func.substr(
                func.cast(Setup.characters, String),
                1,
                SETUP_CHARACTERS_BLOCK_CHAR_LIMIT + 1,
            ).label("characters"),
            func.substr(
                func.cast(Setup.core_concept, String),
                1,
                SETUP_CORE_CONCEPT_BLOCK_CHAR_LIMIT + 1,
            ).label("core_concept"),
        )
        .filter(Setup.project_id == project_id)
        .first()
    )
    if not row:
        return None
    return SetupContextSnapshot(
        world_building=row.world_building or "{}",
        characters=row.characters or "[]",
        core_concept=row.core_concept or "{}",
    )


def _build_consistency_setup(db: Session, project_id: str) -> SetupContextSnapshot:
    return SetupContextSnapshot(
        world_building={},
        characters=get_setup_character_projection(db, project_id),
        core_concept={},
    )


def _build_chapter_call_payload(
    db: Session,
    project: Project,
    setup: Setup | SetupContextSnapshot,
    chapter_index: int,
    extra_feedback: str,
) -> dict:
    prompt_context_blocks, trace_only_context_blocks = build_chapter_prompt_context_blocks(
        db,
        project,
        setup,
        chapter_index,
        extra_feedback,
    )
    build_result = prompt_assembler.build(
        "chapter.generate",
        build_chapter_prompt_variables(project, setup, chapter_index),
        context_blocks=prompt_context_blocks,
        max_context_chars=CHAPTER_CONTEXT_CHAR_BUDGET,
    )

    return {
        "messages": build_result.messages,
        "context_blocks": build_chapter_trace_context_blocks(
            build_result.content,
            build_result.context_blocks,
            trace_only_context_blocks,
        ),
        "max_tokens": chapter_max_tokens(extra_feedback, project=project),
        "trace_metadata": build_prompt_trace_metadata(build_result),
        "rendered_prompt": build_result.content,
    }


def _safe_create_chapter_trace(
    db: Session,
    *,
    project: Project,
    chapter_index: int,
    payload: dict,
) -> AIModelCallTrace | None:
    try:
        trace = create_trace(
            db,
            project_id=project.id,
            trace_type="chapter_generation",
            messages=payload["messages"],
            context_blocks=payload["context_blocks"],
            model=project.ai_model or "deepseek-chat",
            temperature=0.7,
            max_tokens=payload["max_tokens"],
            chapter_index=chapter_index,
            trace_metadata=payload["trace_metadata"],
        )
        db.commit()
        return trace
    except Exception:
        db.rollback()
        return None


def _safe_mark_chapter_trace_success(
    db: Session,
    trace: AIModelCallTrace | None,
    *,
    project: Project,
    chapter: ChapterContent,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    latency_ms: int | None,
) -> AIModelCallTrace | None:
    if trace is None:
        return None
    try:
        trace.chapter_id = chapter.id
        trace.trace_metadata = {
            **(trace.trace_metadata or {}),
            "chapter_word_target": _chapter_word_target_trace_metadata(project, chapter.word_count),
            "chapter_prose_quality": _chapter_prose_quality_trace_metadata(chapter.content or ""),
        }
        mark_trace_success(
            db,
            trace,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )
        db.commit()
        return trace
    except Exception:
        db.rollback()
        return None


def _chapter_word_target_trace_metadata(project: Project, actual_word_count: int | None) -> dict:
    actual = int(actual_word_count or 0)
    target_range = project_chapter_word_range(project)
    if not target_range:
        return {
            "actual_word_count": actual,
            "status": "untracked",
        }

    target_words = int(project.target_word_count or 0)
    target_chapters = int(project.target_chapter_count or 0)
    target_average = max(1, round(target_words / target_chapters))
    target_min, target_max = target_range
    status = "within"
    if actual < target_min:
        status = "under"
    elif actual > target_max:
        status = "over"
    return {
        "actual_word_count": actual,
        "project_target_word_count": target_words,
        "project_target_chapter_count": target_chapters,
        "target_average_word_count": target_average,
        "target_min_word_count": target_min,
        "target_max_word_count": target_max,
        "deviation_word_count": actual - target_average,
        "status": status,
    }


def _chapter_prose_quality_trace_metadata(content: str) -> dict:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    line_count = len(lines)
    outline_marker_count = sum(1 for line in lines if CHAPTER_OUTLINE_MARKER_RE.search(line))
    sentence_ending_count = len(re.findall(r"[。！？.!?]", content))
    status = "prose"
    warnings: list[dict] = []
    if line_count >= 3 and outline_marker_count >= 3 and sentence_ending_count <= max(1, line_count // 2):
        status = "outline_like"
        warnings.append(
            {
                "kind": "outline_like_output",
                "severity": "warning",
                "message": OUTLINE_LIKE_CHAPTER_WARNING_MESSAGE,
            }
        )
    return {
        "status": status,
        "line_count": line_count,
        "outline_marker_count": outline_marker_count,
        "sentence_ending_count": sentence_ending_count,
        "warnings": warnings,
    }


def _post_generation_warning(stage: str, exc: Exception) -> dict:
    return {
        "stage": stage,
        "error_type": exc.__class__.__name__,
        "message": truncate_text(str(exc), max_chars=POST_GENERATION_WARNING_MESSAGE_CHARS)["content"],
    }


def _safe_attach_post_generation_warnings(
    db: Session,
    trace: AIModelCallTrace | None,
    warnings: list[dict],
) -> AIModelCallTrace | None:
    if trace is None or not warnings:
        return trace
    try:
        trace.trace_metadata = {
            **(trace.trace_metadata or {}),
            "post_generation_warning_count": len(warnings),
            "post_generation_warnings": warnings,
        }
        db.add(trace)
        db.commit()
        return trace
    except Exception:
        db.rollback()
        return None


def _safe_mark_chapter_trace_failed(
    db: Session,
    trace: AIModelCallTrace | None,
    *,
    error_message: str,
    latency_ms: int | None,
) -> AIModelCallTrace | None:
    if trace is None:
        return None
    try:
        mark_trace_failed(
            db,
            trace,
            error_message=error_message,
            latency_ms=latency_ms,
        )
        db.commit()
        return trace
    except Exception:
        db.rollback()
        return None


def _safe_refresh_longform_maintenance(db: Session, *, project_id: str, chapter_index: int) -> list[dict]:
    warnings: list[dict] = []
    try:
        refresh_result = refresh_longform_memory_for_chapter(
            db,
            project_id,
            chapter_index,
            reconcile_word_count=False,
        )
    except Exception as exc:
        db.rollback()
        warnings.append(_post_generation_warning("longform_memory_refresh", exc))
        return warnings

    try:
        sync_longform_memory_retrieval_documents(
            db,
            project_id,
            refresh_result.get("updated_memory_ids") or [],
        )
    except Exception as exc:
        db.rollback()
        warnings.append(_post_generation_warning("longform_memory_retrieval_sync", exc))
    return warnings


@router.post("/{chapter_index}/generate", response_model=ChapterOut)
async def generate_chapter(project_id: str, chapter_index: int = Path(..., ge=1), db: Session = Depends(get_db)):
    chapter = await create_or_replace_chapter(db, project_id, chapter_index)
    return _chapter_out(db, chapter)


async def create_or_replace_chapter(
    db: Session,
    project_id: str,
    chapter_index: int,
    extra_feedback: str = "",
) -> ChapterContent:
    if not load_api_key():
        raise HTTPException(status_code=400, detail="API key not configured")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if chapter_index_exceeds_target(db, project, chapter_index):
        raise HTTPException(status_code=400, detail="Chapter index exceeds project target chapter count")

    setup = _get_chapter_setup_context(db, project_id)
    if not setup:
        raise HTTPException(status_code=400, detail="Setup not generated yet")

    existing = db.query(ChapterContent).filter(
        ChapterContent.project_id == project_id,
        ChapterContent.chapter_index == chapter_index,
    ).first()

    payload = _build_chapter_call_payload(db, project, setup, chapter_index, extra_feedback)
    trace = _safe_create_chapter_trace(db, project=project, chapter_index=chapter_index, payload=payload)
    started_at = now_ms()
    start = time.time()
    WritingStateService(db).run_chapter(project_id, chapter_index)
    try:
        result = await ai_service.complete(
            payload["messages"],
            temperature=0.7,
            max_tokens=payload["max_tokens"],
            model=project.ai_model or "deepseek-chat",
        )
    except Exception as exc:
        WritingStateService(db).mark_error(project_id, str(exc))
        _safe_mark_chapter_trace_failed(
            db,
            trace,
            error_message=str(exc),
            latency_ms=now_ms() - started_at,
        )
        raise
    elapsed = int((time.time() - start) * 1000)

    title = f"第{chapter_index}章"
    outline_chapter = find_outline_chapter(db, project_id, chapter_index)
    if outline_chapter is not None:
        _outline_id, chapter_outline = outline_chapter
        title = chapter_outline.get("title", title)

    generated_content = _normalize_generated_chapter_content(result.content)
    if not generated_content:
        WritingStateService(db).mark_error(project_id, EMPTY_CHAPTER_CONTENT_ERROR)
        _safe_mark_chapter_trace_failed(
            db,
            trace,
            error_message=EMPTY_CHAPTER_CONTENT_ERROR,
            latency_ms=now_ms() - started_at,
        )
        raise HTTPException(status_code=502, detail=EMPTY_CHAPTER_CONTENT_ERROR)

    word_count = count_words(generated_content)
    previous_word_count = int(existing.word_count or 0) if existing else 0
    if existing:
        chapter = existing
        chapter.title = title
        chapter.content = generated_content
        chapter.word_count = word_count
        chapter.status = "generated"
        chapter.model = result.model
        chapter.prompt_tokens = result.prompt_tokens
        chapter.completion_tokens = result.completion_tokens
        chapter.generation_time = elapsed
        chapter.temperature = 0.7
    else:
        chapter = ChapterContent(
            project_id=project_id,
            chapter_index=chapter_index,
            title=title,
            content=generated_content,
            word_count=word_count,
            status="generated",
            model=result.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            generation_time=elapsed,
            temperature=0.7,
        )
        db.add(chapter)

    db.flush()
    project.current_word_count = max(0, int(project.current_word_count or 0) - previous_word_count + word_count)
    project.status = "writing"
    project.current_phase = "content"

    try:
        db.commit()
        db.refresh(chapter)
    except Exception as exc:
        db.rollback()
        WritingStateService(db).mark_error(project_id, str(exc))
        raise

    WritingStateService(db).complete_chapter(project_id, chapter_index)

    _safe_mark_chapter_trace_success(
        db,
        trace,
        project=project,
        chapter=chapter,
        prompt_tokens=getattr(result, "prompt_tokens", 0),
        completion_tokens=getattr(result, "completion_tokens", 0),
        latency_ms=now_ms() - started_at,
    )

    post_generation_warnings: list[dict] = []

    # Auto-run L1 consistency check
    try:
        from app.core.consistency_checker import ConsistencyChecker
        from app.models import ConsistencyCheck
        checker = ConsistencyChecker()
        issues = checker.check(project_id, chapter, _build_consistency_setup(db, project_id))
        for issue in issues:
            db.add(ConsistencyCheck(**issue))
        db.commit()
    except Exception as exc:
        db.rollback()
        post_generation_warnings.append(_post_generation_warning("consistency_check", exc))

    athena_analysis_result = None
    try:
        from app.core.athena_longform import analyze_chapter_to_world_proposals
        athena_analysis_result = analyze_chapter_to_world_proposals(db=db, project_id=project_id, chapter_index=chapter_index)
    except Exception as exc:
        db.rollback()
        post_generation_warnings.append(_post_generation_warning("athena_analysis", exc))
    setattr(chapter, "athena_analysis_result", athena_analysis_result)

    try:
        from app.core.athena_retrieval import index_chapter_retrieval
        index_chapter_retrieval(db=db, project_id=project_id, chapter_index=chapter_index)
    except Exception as exc:
        db.rollback()
        post_generation_warnings.append(_post_generation_warning("chapter_retrieval_index", exc))

    post_generation_warnings.extend(
        _safe_refresh_longform_maintenance(db, project_id=project_id, chapter_index=chapter_index)
    )

    # Emit event for background processing
    try:
        from app.core.event_bus import event_bus
        await event_bus.emit("CHAPTER_GENERATED", {
            "project_id": project_id,
            "chapter_index": chapter_index,
        })
    except Exception as exc:
        post_generation_warnings.append(_post_generation_warning("chapter_generated_event", exc))

    _safe_attach_post_generation_warnings(db, trace, post_generation_warnings)

    return chapter


@router.get("/{chapter_index}", response_model=ChapterOut)
def get_chapter(project_id: str, chapter_index: int = Path(..., ge=1), db: Session = Depends(get_db)):
    chapter = db.query(ChapterContent).filter(
        ChapterContent.project_id == project_id,
        ChapterContent.chapter_index == chapter_index,
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return _chapter_out(db, chapter)

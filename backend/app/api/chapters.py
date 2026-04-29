import json
import re
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import load_api_key
from app.core.ai_service import AIService
from app.core.model_call_trace import build_context_block, create_trace, mark_trace_failed, mark_trace_success, now_ms
from app.core.prompt_manager import PromptManager
from app.core.prompt_optimizer import PromptOptimizer
from app.db import get_db
from app.models import AIModelCallTrace, ChapterContent, Outline, Project, Setup
from app.schemas import ChapterOut

router = APIRouter(prefix="/api/v1/projects/{project_id}/chapters", tags=["chapters"])

ai_service = AIService()
prompt_optimizer = PromptOptimizer()


def _count_words(content: str) -> int:
    ascii_words = len([w for w in re.split(r"\s+", content) if w])
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", content))
    return ascii_words + cjk_chars


def _extract_word_range(text: str) -> tuple[int, int] | None:
    match = re.search(r"(\d{3,5})\s*(?:-|~|至|到|—|－)\s*(\d{3,5})\s*字", text or "")
    if not match:
        return None
    low, high = int(match.group(1)), int(match.group(2))
    if low <= 0 or high < low:
        return None
    return low, high


def _chapter_max_tokens(extra_feedback: str) -> int:
    word_range = _extract_word_range(extra_feedback)
    if not word_range:
        return 4000
    return min(4000, max(word_range[1] + 800, 1200))


def _build_chapter_context(db: Session, project_id: str, chapter_index: int, setup: Setup) -> str:
    parts = []
    parts.append(f"世界观：{json.dumps(setup.world_building, ensure_ascii=False)[:500]}")
    parts.append(f"角色：{json.dumps(setup.characters, ensure_ascii=False)[:500]}")

    outline = db.query(Outline).filter(Outline.project_id == project_id).first()
    if outline and outline.chapters:
        for ch in outline.chapters:
            if ch.get("chapter_index") == chapter_index:
                parts.append(f"本章大纲：{ch.get('title', '')} - {ch.get('summary', '')}")
                if ch.get("scenes"):
                    parts.append(f"场景：{'、'.join(ch['scenes'])}")
                if ch.get("characters"):
                    parts.append(f"出场角色：{'、'.join(ch['characters'])}")
                break

    if chapter_index > 1:
        prev = db.query(ChapterContent).filter(
            ChapterContent.project_id == project_id,
            ChapterContent.chapter_index == chapter_index - 1,
        ).first()
        if prev and prev.content:
            summary = prev.content[:300] + "..." if len(prev.content) > 300 else prev.content
            parts.append(f"上一章摘要：{summary}")

    try:
        from app.core.athena_longform import build_chapter_context_package
        athena_context = build_chapter_context_package(db=db, project_id=project_id, chapter_index=chapter_index)
        if athena_context.get("profile_version") is not None and athena_context.get("prompt_context"):
            parts.append(f"【Athena 世界上下文】\n{athena_context['prompt_context']}")
    except Exception:
        pass

    return "\n".join(parts)


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


def _build_chapter_call_payload(
    db: Session,
    project: Project,
    setup: Setup,
    chapter_index: int,
    extra_feedback: str,
) -> dict:
    context = _build_chapter_context(db, project.id, chapter_index, setup)

    pm = PromptManager()
    prompt_template = pm.load(
        "generate_chapter",
        {
            "world_building": json.dumps(setup.world_building, ensure_ascii=False),
            "characters": json.dumps(setup.characters, ensure_ascii=False),
            "core_concept": json.dumps(setup.core_concept, ensure_ascii=False),
            "chapter_index": chapter_index,
            "language": project.language,
        },
    )
    prompt = f"{prompt_template}\n\n【章节上下文】\n{context}"
    context_blocks = [
        build_context_block(
            key="setup_world_building",
            kind="setup",
            title="世界观",
            content=json.dumps(setup.world_building, ensure_ascii=False),
        ),
        build_context_block(
            key="setup_characters",
            kind="setup",
            title="角色",
            content=json.dumps(setup.characters, ensure_ascii=False),
        ),
        build_context_block(
            key="chapter_context",
            kind="chapter_context",
            title=f"第{chapter_index}章上下文",
            content=context,
        ),
        build_context_block(
            key="generate_chapter_template",
            kind="prompt_template",
            title="章节生成模板",
            content=prompt_template,
        ),
    ]
    if extra_feedback:
        prompt = f"{prompt}\n\n【用户修订反馈】\n{extra_feedback}"
        context_blocks.append(
            build_context_block(
                key="extra_feedback",
                kind="user_feedback",
                title="用户修订反馈",
                content=extra_feedback,
            )
        )
        word_range = _extract_word_range(extra_feedback)
        if word_range:
            length_constraint = (
                f"正文长度控制在{word_range[0]}-{word_range[1]}字，"
                "不要为了解释设定而扩写，优先保证剧情推进和章节钩子。"
            )
            prompt = f"{prompt}\n\n【长度约束】\n{length_constraint}"
            context_blocks.append(
                build_context_block(
                    key="length_constraint",
                    kind="generation_constraint",
                    title="长度约束",
                    content=length_constraint,
                )
            )
    original_prompt = prompt
    prompt = prompt_optimizer.optimize(prompt, project.style_config)
    if prompt != original_prompt:
        style_rule_content = (
            prompt[len(original_prompt):].strip()
            if prompt.startswith(original_prompt)
            else prompt
        )
        context_blocks.append(
            build_context_block(
                key="style_rule",
                kind="style_rule",
                title="风格偏好规则",
                content=style_rule_content,
                sources=[
                    {
                        "source_type": "Project",
                        "source_id": project.id,
                        "label": "Project/style_config",
                        "source_ref": "Project/style_config",
                        "metadata": {"style_config": project.style_config},
                    }
                ],
            )
        )

    from app.core.few_shot_library import FewShotExampleLibrary
    fsl = FewShotExampleLibrary()
    examples = fsl.select_examples("chapter", project.genre)
    if examples:
        few_shot_prompt = fsl.format_for_prompt(examples)
        prompt += "\n\n" + few_shot_prompt
        context_blocks.append(
            build_context_block(
                key="few_shot_examples",
                kind="few_shot",
                title="章节示例",
                content=few_shot_prompt,
            )
        )

    return {
        "messages": [{"role": "user", "content": prompt}],
        "context_blocks": context_blocks,
        "max_tokens": _chapter_max_tokens(extra_feedback),
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
    chapter: ChapterContent,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    latency_ms: int | None,
) -> AIModelCallTrace | None:
    if trace is None:
        return None
    try:
        trace.chapter_id = chapter.id
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


@router.post("/{chapter_index}/generate", response_model=ChapterOut)
async def generate_chapter(project_id: str, chapter_index: int, db: Session = Depends(get_db)):
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

    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
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
    try:
        result = await ai_service.complete(
            payload["messages"],
            temperature=0.7,
            max_tokens=payload["max_tokens"],
        )
    except Exception as exc:
        _safe_mark_chapter_trace_failed(
            db,
            trace,
            error_message=str(exc),
            latency_ms=now_ms() - started_at,
        )
        raise
    elapsed = int((time.time() - start) * 1000)

    outline = db.query(Outline).filter(Outline.project_id == project_id).first()
    title = f"第{chapter_index}章"
    if outline and outline.chapters:
        for ch in outline.chapters:
            if ch.get("chapter_index") == chapter_index:
                title = ch.get("title", title)
                break

    word_count = _count_words(result.content)
    if existing:
        chapter = existing
        chapter.title = title
        chapter.content = result.content
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
            content=result.content,
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
    total_words = sum(
        c.word_count or 0
        for c in db.query(ChapterContent).filter(ChapterContent.project_id == project_id).all()
    )
    project.current_word_count = total_words
    project.status = "writing"

    try:
        db.commit()
        db.refresh(chapter)
    except Exception:
        db.rollback()
        raise

    _safe_mark_chapter_trace_success(
        db,
        trace,
        chapter=chapter,
        prompt_tokens=getattr(result, "prompt_tokens", 0),
        completion_tokens=getattr(result, "completion_tokens", 0),
        latency_ms=now_ms() - started_at,
    )

    # Auto-run L1 consistency check
    try:
        from app.core.consistency_checker import ConsistencyChecker
        from app.models import ConsistencyCheck
        checker = ConsistencyChecker()
        issues = checker.check(project_id, chapter, setup)
        for issue in issues:
            db.add(ConsistencyCheck(**issue))
        db.commit()
    except Exception:
        pass  # Don't fail chapter generation if check fails

    try:
        from app.core.athena_longform import analyze_chapter_to_world_proposals
        analyze_chapter_to_world_proposals(db=db, project_id=project_id, chapter_index=chapter_index)
    except Exception:
        pass  # Don't fail chapter generation if Athena analysis fails

    try:
        from app.core.athena_retrieval import index_chapter_retrieval
        index_chapter_retrieval(db=db, project_id=project_id, chapter_index=chapter_index)
    except Exception:
        pass  # Don't fail chapter generation if retrieval indexing fails

    # Emit event for background processing
    try:
        from app.core.event_bus import event_bus
        await event_bus.emit("CHAPTER_GENERATED", {
            "project_id": project_id,
            "chapter_index": chapter_index,
        })
    except Exception:
        pass

    return chapter


@router.get("/{chapter_index}", response_model=ChapterOut)
def get_chapter(project_id: str, chapter_index: int, db: Session = Depends(get_db)):
    chapter = db.query(ChapterContent).filter(
        ChapterContent.project_id == project_id,
        ChapterContent.chapter_index == chapter_index,
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return _chapter_out(db, chapter)

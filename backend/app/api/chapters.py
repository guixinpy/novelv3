import json
import re
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Project, Setup, Outline, ChapterContent
from app.schemas import ChapterOut
from app.config import load_api_key
from app.core.ai_service import AIService
from app.core.prompt_manager import PromptManager
from app.core.prompt_optimizer import PromptOptimizer

router = APIRouter(prefix="/api/v1/projects/{project_id}/chapters", tags=["chapters"])

ai_service = AIService()
prompt_optimizer = PromptOptimizer()


def _count_words(content: str) -> int:
    ascii_words = len([w for w in re.split(r"\s+", content) if w])
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", content))
    return ascii_words + cjk_chars


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

    return "\n".join(parts)


@router.post("/{chapter_index}/generate", response_model=ChapterOut)
async def generate_chapter(project_id: str, chapter_index: int, db: Session = Depends(get_db)):
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

    context = _build_chapter_context(db, project_id, chapter_index, setup)

    pm = PromptManager()
    prompt = pm.load(
        "generate_chapter",
        {
            "world_building": json.dumps(setup.world_building, ensure_ascii=False),
            "characters": json.dumps(setup.characters, ensure_ascii=False),
            "core_concept": json.dumps(setup.core_concept, ensure_ascii=False),
            "language": project.language,
        },
    )
    prompt = f"{prompt}\n\n【章节上下文】\n{context}"
    prompt = prompt_optimizer.optimize(prompt, project.style_config)

    start = time.time()
    result = await ai_service.complete(
        [{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4000,
    )
    elapsed = int((time.time() - start) * 1000)

    outline = db.query(Outline).filter(Outline.project_id == project_id).first()
    title = f"第{chapter_index}章"
    if outline and outline.chapters:
        for ch in outline.chapters:
            if ch.get("chapter_index") == chapter_index:
                title = ch.get("title", title)
                break

    chapter = ChapterContent(
        project_id=project_id,
        chapter_index=chapter_index,
        title=title,
        content=result.content,
        word_count=_count_words(result.content),
        status="generated",
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        generation_time=elapsed,
        temperature=0.7,
    )

    if existing:
        db.delete(existing)

    db.add(chapter)

    total_words = sum(
        c.word_count or 0 for c in db.query(ChapterContent).filter(ChapterContent.project_id == project_id).all()
    ) + chapter.word_count
    project.current_word_count = total_words
    project.status = "writing"

    try:
        db.commit()
        db.refresh(chapter)
    except Exception:
        db.rollback()
        raise

    return chapter


@router.get("/{chapter_index}", response_model=ChapterOut)
def get_chapter(project_id: str, chapter_index: int, db: Session = Depends(get_db)):
    chapter = db.query(ChapterContent).filter(
        ChapterContent.project_id == project_id,
        ChapterContent.chapter_index == chapter_index,
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter

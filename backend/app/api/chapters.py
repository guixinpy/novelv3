import json
import re
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Project, Setup, ChapterContent
from app.schemas import ChapterOut
from app.core.ai_service import AIService
from app.core.prompt_manager import PromptManager

router = APIRouter(prefix="/api/v1/projects/{project_id}/chapters", tags=["chapters"])

ai_service = AIService()


def _count_words(content: str) -> int:
    ascii_words = len([w for w in re.split(r"\s+", content) if w])
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", content))
    return ascii_words + cjk_chars


@router.post("/{chapter_index}/generate", response_model=ChapterOut)
async def generate_chapter(project_id: str, chapter_index: int, db: Session = Depends(get_db)):
    if chapter_index != 1:
        raise HTTPException(status_code=400, detail="Phase 1 only supports chapter 1")

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

    start = time.time()
    result = await ai_service.complete(
        [{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4000,
    )
    elapsed = int((time.time() - start) * 1000)

    chapter = ChapterContent(
        project_id=project_id,
        chapter_index=chapter_index,
        title=f"第{chapter_index}章",
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
    project.current_word_count = chapter.word_count
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

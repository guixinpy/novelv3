from __future__ import annotations

from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from app.core.athena_retrieval import get_retrieval_diagnostics, reindex_project_retrieval
from app.core.longform_memory import build_longform_context_package, rebuild_longform_memory
from app.models import ChapterContent, Project
from app.services.tasks.background_task_service import BackgroundTaskService


def run_longform_scale_smoke(
    db: Session,
    *,
    chapter_count: int = 1000,
    words_per_chapter: int = 1000,
    target_chapter_index: int | None = None,
    query: str = "星环钥匙",
) -> dict[str, Any]:
    if chapter_count < 1:
        raise ValueError("chapter_count must be at least 1")
    if words_per_chapter < 1:
        raise ValueError("words_per_chapter must be at least 1")
    target = target_chapter_index or chapter_count
    if target < 1 or target > chapter_count:
        raise ValueError("target_chapter_index must be within the seeded chapter range")

    started_at = perf_counter()
    project = _seed_project(db, chapter_count=chapter_count, words_per_chapter=words_per_chapter)
    task_service = BackgroundTaskService(db)
    task = task_service.create_chapter_range(
        project_id=project.id,
        task_type="longform_scale_smoke",
        start_chapter_index=1,
        end_chapter_index=chapter_count,
        payload={"target_chapter_index": target, "query": query},
        idempotency_key=f"longform-scale-smoke:{project.id}:{chapter_count}:{words_per_chapter}",
    )
    task_service.mark_running(task.id)
    for chapter_index in range(1, chapter_count + 1):
        task = task_service.mark_range_progress(task.id, completed_chapter_index=chapter_index)

    memory_report = rebuild_longform_memory(db, project.id)
    reindex_project_retrieval(db, project.id)
    retrieval_report = get_retrieval_diagnostics(db, project.id)
    context_package = build_longform_context_package(
        db,
        project.id,
        target,
        user_query=query,
    )
    progress = (task.result or {}).get("progress") or {}
    completed_task = task_service.mark_completed(
        task.id,
        {
            "progress": progress,
            "memory": memory_report,
            "retrieval": retrieval_report,
            "target_chapter_index": target,
        },
    )
    elapsed_ms = int((perf_counter() - started_at) * 1000)
    total_words = chapter_count * words_per_chapter

    return {
        "project_id": project.id,
        "project_name": project.name,
        "chapter_count": chapter_count,
        "target_chapter_index": target,
        "words_per_chapter": words_per_chapter,
        "total_words": total_words,
        "memory": memory_report,
        "retrieval": retrieval_report,
        "context": {
            "section_keys": [section["key"] for section in context_package["sections"]],
            "section_count": len(context_package["sections"]),
            "prompt_context_chars": len(context_package["prompt_context"]),
        },
        "task": {
            "id": completed_task.id,
            "status": completed_task.status,
            "progress": _compact_progress((completed_task.result or {}).get("progress") or {}),
        },
        "elapsed_ms": elapsed_ms,
    }


def _seed_project(db: Session, *, chapter_count: int, words_per_chapter: int) -> Project:
    total_words = chapter_count * words_per_chapter
    project = Project(
        name=f"Longform Scale Smoke {chapter_count}x{words_per_chapter}",
        description="Synthetic longform scale smoke project.",
        genre="悬疑长篇",
        target_chapter_count=chapter_count,
        target_word_count=total_words,
        current_word_count=0,
        status="draft",
        current_phase="scale_smoke",
    )
    db.add(project)
    db.flush()
    db.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章：星环档案{index}",
                content=_chapter_content(index, words_per_chapter),
                word_count=words_per_chapter,
                status="generated",
            )
            for index in range(1, chapter_count + 1)
        ]
    )
    db.commit()
    db.refresh(project)
    return project


def _chapter_content(chapter_index: int, words_per_chapter: int) -> str:
    arc_index = (chapter_index - 1) // 20 + 1
    volume_index = (chapter_index - 1) // 100 + 1
    base = (
        f"第{chapter_index}章位于第{volume_index}卷第{arc_index}段剧情。"
        "陆辞沿着灯塔区的旧档案追查星环钥匙，"
        "苏晚晴记录每一次记忆回潮，"
        "伏笔围绕潮汐钟、雾灯和黑匣子反复推进。"
        "本章只陈述当前章节已经发生的事实，不引用未来章节。"
    )
    repeat_count = max((words_per_chapter // len(base)) + 1, 1)
    return (base * repeat_count)[:words_per_chapter]


def _compact_progress(progress: dict[str, Any]) -> dict[str, Any]:
    completed_indexes = [int(index) for index in progress.get("completed_chapter_indexes") or []]
    compact = {
        "chapter_range": progress.get("chapter_range") or {},
        "next_chapter_index": progress.get("next_chapter_index"),
        "completed_count": progress.get("completed_count", len(completed_indexes)),
        "total_count": progress.get("total_count"),
        "can_resume": progress.get("can_resume", False),
        "checkpoint_count": len(completed_indexes),
    }
    if completed_indexes:
        compact["first_completed_chapter_index"] = completed_indexes[0]
        compact["last_completed_chapter_index"] = completed_indexes[-1]
    return compact

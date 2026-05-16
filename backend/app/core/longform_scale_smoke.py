from __future__ import annotations

from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from app.core.athena_retrieval import get_retrieval_diagnostics, reindex_project_retrieval
from app.core.longform_memory import build_longform_context_package, rebuild_longform_memory
from app.core.narrative_plan_window import get_evolution_plan_window
from app.prompting.providers.dialog import build_athena_narrative_planning_context_block
from app.models import ChapterContent, Outline, Project, Storyline
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
    timings_ms: dict[str, int] = {}
    stage_started_at = started_at
    project = _seed_project(db, chapter_count=chapter_count, words_per_chapter=words_per_chapter)
    stage_started_at = _record_timing(timings_ms, "seed_project", stage_started_at)
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
    task = task_service.mark_range_progress_many(
        task.id,
        completed_chapter_indexes=range(1, chapter_count + 1),
    )
    stage_started_at = _record_timing(timings_ms, "task_progress", stage_started_at)

    memory_report = rebuild_longform_memory(db, project.id)
    stage_started_at = _record_timing(timings_ms, "memory_rebuild", stage_started_at)
    reindex_project_retrieval(db, project.id)
    stage_started_at = _record_timing(timings_ms, "retrieval_reindex", stage_started_at)
    retrieval_report = get_retrieval_diagnostics(db, project.id)
    stage_started_at = _record_timing(timings_ms, "retrieval_diagnostics", stage_started_at)
    repeat_reindex_report = reindex_project_retrieval(db, project.id)
    stage_started_at = _record_timing(timings_ms, "retrieval_repeat_reindex", stage_started_at)
    context_package = build_longform_context_package(
        db,
        project.id,
        target,
        user_query=query,
    )
    stage_started_at = _record_timing(timings_ms, "context_build", stage_started_at)
    narrative_plan = get_evolution_plan_window(db=db, project_id=project.id)
    stage_started_at = _record_timing(timings_ms, "narrative_plan_window", stage_started_at)
    dialog_planning_context = build_athena_narrative_planning_context_block(db, project)
    stage_started_at = _record_timing(timings_ms, "dialog_planning_context", stage_started_at)
    progress = (task.result or {}).get("progress") or {}
    completed_task = task_service.mark_completed(
        task.id,
        {
            "progress": progress,
            "memory": memory_report,
            "retrieval": retrieval_report,
            "repeat_reindex": repeat_reindex_report,
            "narrative_plan": _compact_narrative_plan_window(narrative_plan),
            "dialog_planning_context": _compact_context_block(dialog_planning_context),
            "target_chapter_index": target,
        },
    )
    _record_timing(timings_ms, "task_complete", stage_started_at)
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
        "narrative_plan": _compact_narrative_plan_window(narrative_plan),
        "dialog_planning_context": _compact_context_block(dialog_planning_context),
        "task": {
            "id": completed_task.id,
            "status": completed_task.status,
            "progress": _compact_progress((completed_task.result or {}).get("progress") or {}),
        },
        "timings_ms": timings_ms,
        "elapsed_ms": elapsed_ms,
        "repeat_reindex": repeat_reindex_report,
    }


def _compact_context_block(block: dict[str, Any] | None) -> dict[str, Any]:
    if not block:
        return {
            "available": False,
            "kind": None,
            "content_chars": 0,
            "token_estimate": 0,
            "truncated": False,
        }
    content = str(block.get("content") or "")
    return {
        "available": True,
        "kind": block.get("kind"),
        "content_chars": len(content),
        "token_estimate": block.get("token_estimate", 0),
        "truncated": bool(block.get("truncated", False)),
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
    db.add(
        Outline(
            project_id=project.id,
            status="generated",
            total_chapters=chapter_count,
            chapters=[
                {
                    "chapter_index": index,
                    "title": f"第{index}章：星环档案{index}",
                    "summary": f"第{index}章推进星环钥匙与灯塔记忆主线。",
                }
                for index in range(1, chapter_count + 1)
            ],
            plotlines=[
                {
                    "name": f"大纲线{index}",
                    "type": "main" if index == 1 else "sub",
                    "milestones": [{"chapter_index": index, "title": f"大纲节点{index}"}],
                }
                for index in range(1, 61)
            ],
        )
    )
    db.add(
        Storyline(
            project_id=project.id,
            status="generated",
            plotlines=[
                {
                    "name": "主线：星环钥匙长篇谜团",
                    "type": "main",
                    "milestones": [
                        {"chapter_index": index, "title": f"主线节点{index}"}
                        for index in range(1, chapter_count + 1)
                    ],
                },
                *[
                    {
                        "name": f"支线：灯塔档案{index}",
                        "type": "sub",
                        "milestones": [{"chapter_index": index, "title": f"支线节点{index}"}],
                    }
                    for index in range(2, 61)
                ],
            ],
            foreshadowing=[
                {
                    "hint": f"伏笔{index}",
                    "planted_chapter": ((index - 1) % chapter_count) + 1,
                    "resolved_chapter": min(chapter_count, ((index - 1) % chapter_count) + 10),
                    "status": "pending",
                }
                for index in range(1, 301)
            ],
        )
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
    for field in [
        "completed_until_chapter_index",
        "first_completed_chapter_index",
        "last_completed_chapter_index",
    ]:
        if field in progress:
            compact[field] = progress[field]
    return compact


def _compact_narrative_plan_window(plan: dict[str, Any]) -> dict[str, Any]:
    outline = plan.get("outline") or {}
    storyline = plan.get("storyline") or {}
    plotlines = storyline.get("plotlines") or []
    first_plotline = plotlines[0] if plotlines and isinstance(plotlines[0], dict) else {}
    milestones = first_plotline.get("milestones") or []
    foreshadowing = storyline.get("foreshadowing") or []
    chapters = outline.get("chapters") or []
    return {
        "chapters_total": outline.get("chapters_total", 0),
        "chapters_returned": len(chapters),
        "chapters_has_more": outline.get("chapters_has_more", False),
        "plotlines_total": storyline.get("plotlines_total", 0),
        "plotlines_returned": len(plotlines),
        "plotlines_has_more": storyline.get("plotlines_has_more", False),
        "milestones_total": first_plotline.get("milestones_total", len(milestones)),
        "milestones_returned": len(milestones),
        "milestones_has_more": first_plotline.get("milestones_has_more", False),
        "foreshadowing_total": storyline.get("foreshadowing_total", 0),
        "foreshadowing_returned": len(foreshadowing),
        "foreshadowing_has_more": storyline.get("foreshadowing_has_more", False),
    }


def _record_timing(timings_ms: dict[str, int], key: str, stage_started_at: float) -> float:
    ended_at = perf_counter()
    timings_ms[key] = int((ended_at - stage_started_at) * 1000)
    return ended_at

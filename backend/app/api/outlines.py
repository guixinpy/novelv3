import json
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Response
from sqlalchemy import String, func, text
from sqlalchemy.orm import Session

from app.api.deprecation import add_deprecation_header
from app.config import load_api_key
from app.core.ai_service import AIService
from app.core.model_call_trace import create_trace, mark_trace_failed, mark_trace_success, now_ms
from app.core.narrative_plan_window import get_evolution_plan_window
from app.db import get_db
from app.models import Outline, Project, Setup, Storyline
from app.prompting.assembler import build_generation_payload
from app.prompting.providers.outline import (
    build_outline_context_blocks,
    build_outline_variables,
    outline_max_tokens,
    target_total_chapters,
)
from app.prompting.providers.storyline import (
    SETUP_CHARACTERS_CONTEXT_CHARS,
    SETUP_CORE_CONCEPT_CONTEXT_CHARS,
    SETUP_WORLD_CONTEXT_CHARS,
    SetupContextSnapshot,
)
from app.schemas import OutlineOut
from app.services.writing.writing_state_service import WritingStateService

router = APIRouter(prefix="/api/v1/projects/{project_id}/outline", tags=["outlines"])
ai_service = AIService()

STORYLINE_CONTEXT_PLOTLINE_LIMIT = 20
STORYLINE_CONTEXT_FORESHADOWING_LIMIT = 100


def _target_total_chapters(project: Project) -> int:
    return target_total_chapters(project)


def _normalize_outline_chapters(chapters: object) -> list[dict]:
    if not isinstance(chapters, list):
        return []
    normalized: list[dict] = []
    for item in chapters:
        if not isinstance(item, dict):
            continue
        chapter = dict(item)
        chapter["scenes"] = _normalize_text_list(chapter.get("scenes"), item_kind="scene")
        chapter["characters"] = _normalize_text_list(chapter.get("characters"), item_kind="character")
        normalized.append(chapter)
    return normalized


def _outline_chapter_index(chapter: dict) -> int | None:
    try:
        return int(chapter.get("chapter_index"))
    except (TypeError, ValueError):
        return None


def _merge_outline_chapter_window(
    existing_chapters: object,
    incoming_chapters: object,
    *,
    start_chapter: int,
    end_chapter: int,
) -> tuple[list[dict], dict]:
    existing = _normalize_outline_chapters(existing_chapters)
    incoming = _normalize_outline_chapters(incoming_chapters)
    existing_indexes = {
        chapter_index
        for chapter in existing
        if (chapter_index := _outline_chapter_index(chapter)) is not None
    }
    merged = list(existing)
    added = 0
    skipped_existing = 0
    skipped_out_of_window = 0
    for chapter in incoming:
        chapter_index = _outline_chapter_index(chapter)
        if chapter_index is None or chapter_index < start_chapter or chapter_index > end_chapter:
            skipped_out_of_window += 1
            continue
        if chapter_index in existing_indexes:
            skipped_existing += 1
            continue
        merged.append(chapter)
        existing_indexes.add(chapter_index)
        added += 1
    merged.sort(key=lambda chapter: _outline_chapter_index(chapter) or 10**9)
    return merged, {
        "added_chapter_count": added,
        "skipped_existing_count": skipped_existing,
        "skipped_out_of_window_count": skipped_out_of_window,
        "start_chapter": start_chapter,
        "end_chapter": end_chapter,
    }


def _normalize_text_list(value: object, *, item_kind: str) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    normalized: list[str] = []
    for item in values:
        text = _outline_item_to_text(item, item_kind=item_kind)
        if text:
            normalized.append(text)
    return normalized


def _outline_item_to_text(item: object, *, item_kind: str) -> str:
    if item is None:
        return ""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        if item_kind == "character":
            for key in ("name", "character", "title"):
                text = str(item.get(key) or "").strip()
                if text:
                    return text
        setting = str(item.get("setting") or item.get("name") or item.get("title") or "").strip()
        content = str(item.get("content") or item.get("summary") or item.get("description") or "").strip()
        parts = []
        if setting and content:
            parts.append(f"{setting}：{content.rstrip('。.!！?？')}")
        else:
            parts.append(setting or content)
        details = []
        for label, key in (("目标", "goal"), ("冲突", "conflict"), ("钩子", "hook")):
            text = str(item.get(key) or "").strip()
            if text:
                details.append(f"{label}：{text}")
        if details:
            parts.append("；".join(details))
        return "。".join(part for part in parts if part).strip()
    return str(item).strip()


def _truncate_context_text(value: object, max_chars: int = 180) -> str:
    if value is None:
        return ""
    text_value = str(value).strip()
    if len(text_value) <= max_chars:
        return text_value
    return text_value[:max_chars].rstrip() + "..."


def _build_bounded_storyline_context(
    db: Session,
    project_id: str,
    *,
    plotline_limit: int = STORYLINE_CONTEXT_PLOTLINE_LIMIT,
    foreshadowing_limit: int = STORYLINE_CONTEXT_FORESHADOWING_LIMIT,
) -> str | None:
    storyline_row = (
        db.query(
            Storyline.id,
            func.coalesce(func.json_array_length(Storyline.plotlines), 0).label("plotline_total"),
            func.coalesce(func.json_array_length(Storyline.foreshadowing), 0).label("foreshadowing_total"),
        )
        .filter(Storyline.project_id == project_id)
        .first()
    )
    if not storyline_row:
        return None

    plotline_rows = db.execute(
        text(
            """
            SELECT
                item.key AS item_index,
                json_extract(item.value, '$.name') AS name,
                json_extract(item.value, '$.type') AS type,
                json_extract(item.value, '$.summary') AS summary,
                COALESCE(json_array_length(item.value, '$.milestones'), 0) AS milestones_total
            FROM storylines, json_each(storylines.plotlines) AS item
            WHERE storylines.id = :storyline_id
            ORDER BY CAST(item.key AS INTEGER)
            LIMIT :limit
            """
        ),
        {"storyline_id": storyline_row.id, "limit": plotline_limit},
    ).mappings()
    foreshadowing_rows = db.execute(
        text(
            """
            SELECT
                item.key AS item_index,
                json_extract(item.value, '$.hint') AS hint,
                json_extract(item.value, '$.planted_chapter') AS planted_chapter,
                json_extract(item.value, '$.resolved_chapter') AS resolved_chapter,
                json_extract(item.value, '$.status') AS status
            FROM storylines, json_each(storylines.foreshadowing) AS item
            WHERE storylines.id = :storyline_id
            ORDER BY CAST(item.key AS INTEGER)
            LIMIT :limit
            """
        ),
        {"storyline_id": storyline_row.id, "limit": foreshadowing_limit},
    ).mappings()

    plotline_total = int(storyline_row.plotline_total or 0)
    foreshadowing_total = int(storyline_row.foreshadowing_total or 0)
    lines = [
        f"故事线总数：{plotline_total}（仅展示前 {min(plotline_total, plotline_limit)} 条摘要，里程碑只统计数量）",
        f"伏笔总数：{foreshadowing_total}（仅展示前 {min(foreshadowing_total, foreshadowing_limit)} 条摘要）",
        "",
        "故事线预览：",
    ]
    for row in plotline_rows:
        item_number = int(row["item_index"]) + 1
        name = _truncate_context_text(row["name"], 80) or f"故事线{item_number}"
        plotline_type = _truncate_context_text(row["type"], 40) or "未标注"
        summary = _truncate_context_text(row["summary"]) or "暂无摘要"
        milestones_total = int(row["milestones_total"] or 0)
        lines.append(f"{item_number}. {name}｜类型：{plotline_type}｜里程碑数：{milestones_total}｜摘要：{summary}")
    if plotline_total == 0:
        lines.append("- 暂无")

    lines.extend(["", "伏笔预览："])
    for row in foreshadowing_rows:
        item_number = int(row["item_index"]) + 1
        hint = _truncate_context_text(row["hint"], 120) or f"伏笔{item_number}"
        status = _truncate_context_text(row["status"], 40) or "未标注"
        planted = row["planted_chapter"] if row["planted_chapter"] is not None else "未知"
        resolved = row["resolved_chapter"] if row["resolved_chapter"] is not None else "未定"
        lines.append(f"{item_number}. {hint}｜状态：{status}｜埋设：第{planted}章｜回收：第{resolved}章")
    if foreshadowing_total == 0:
        lines.append("- 暂无")
    return "\n".join(lines)


def _get_outline_setup_context(db: Session, project_id: str) -> SetupContextSnapshot | None:
    row = (
        db.query(
            Setup.id,
            func.substr(
                func.cast(Setup.world_building, String),
                1,
                SETUP_WORLD_CONTEXT_CHARS + 1,
            ).label("world_building"),
            func.substr(
                func.cast(Setup.characters, String),
                1,
                SETUP_CHARACTERS_CONTEXT_CHARS + 1,
            ).label("characters"),
            func.substr(
                func.cast(Setup.core_concept, String),
                1,
                SETUP_CORE_CONCEPT_CONTEXT_CHARS + 1,
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


def _build_outline_call_payload(
    project: Project,
    setup: Setup | SetupContextSnapshot,
    storyline: Storyline | str,
    command_args: str | None = None,
) -> dict:
    variables = build_outline_variables(project, setup, storyline)
    return build_generation_payload(
        "outline.generate",
        variables,
        trace_context_blocks=lambda rendered_prompt: build_outline_context_blocks(
            project,
            setup,
            storyline,
            rendered_prompt=rendered_prompt,
            command_args=command_args,
        ),
        command_args=command_args,
        max_tokens=outline_max_tokens(project),
    )


@router.post("/generate", response_model=OutlineOut)
async def generate_outline(project_id: str, db: Session = Depends(get_db), command_args: str | None = None, response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/plan/generate?target=outline")
    if not load_api_key():
        raise HTTPException(status_code=400, detail="API key not configured")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    storyline_context = _build_bounded_storyline_context(db, project_id)
    if not storyline_context:
        raise HTTPException(status_code=400, detail="Storyline not generated yet")
    setup = _get_outline_setup_context(db, project_id)
    if not setup:
        raise HTTPException(status_code=400, detail="Setup not generated yet")

    payload = _build_outline_call_payload(project, setup, storyline_context, command_args=command_args)
    trace = create_trace(
        db,
        project_id=project.id,
        trace_type="outline_generation",
        messages=payload["messages"],
        context_blocks=payload["context_blocks"],
        trace_metadata=payload["trace_metadata"],
        model=project.ai_model or "deepseek-chat",
        temperature=0.7,
        max_tokens=payload["max_tokens"],
    )
    db.commit()

    started_at = now_ms()
    start = time.time()
    try:
        result = await ai_service.complete(
            payload["messages"],
            temperature=0.7,
            max_tokens=payload["max_tokens"],
            model=project.ai_model or "deepseek-chat",
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        mark_trace_failed(db, trace, error_message=str(exc), latency_ms=now_ms() - started_at)
        db.commit()
        raise
    try:
        data = ai_service.parse_json(result.content)
    except Exception as exc:
        mark_trace_failed(db, trace, error_message=str(exc), latency_ms=now_ms() - started_at)
        db.commit()
        raise

    outline = Outline(
        project_id=project_id,
        total_chapters=data.get("total_chapters", 0),
        chapters=_normalize_outline_chapters(data.get("chapters", [])),
        plotlines=data.get("plotlines", []),
        foreshadowing=data.get("foreshadowing", []),
        status="generated",
    )

    existing = db.query(Outline).filter(Outline.project_id == project_id).first()
    if existing:
        db.delete(existing)

    db.add(outline)
    project.status = "outline_generated"
    project.current_phase = "outline"
    mark_trace_success(
        db,
        trace,
        prompt_tokens=getattr(result, "prompt_tokens", 0),
        completion_tokens=getattr(result, "completion_tokens", 0),
        latency_ms=int((time.time() - start) * 1000),
    )

    try:
        db.commit()
        db.refresh(outline)
    except Exception:
        db.rollback()
        raise

    WritingStateService(db).reconcile_target(project_id)
    return outline


@router.post("/expand-window", response_model=OutlineOut)
async def expand_outline_window(
    project_id: str,
    start_chapter: int = Query(..., ge=1),
    end_chapter: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    command_args: str | None = None,
    response: Response = None,
):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/plan/generate?target=outline-window")
    if end_chapter < start_chapter:
        raise HTTPException(status_code=400, detail="end_chapter must be greater than or equal to start_chapter")
    if not load_api_key():
        raise HTTPException(status_code=400, detail="API key not configured")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    existing = db.query(Outline).filter(Outline.project_id == project_id).first()
    if not existing:
        raise HTTPException(status_code=400, detail="Outline not generated yet")

    storyline_context = _build_bounded_storyline_context(db, project_id)
    if not storyline_context:
        raise HTTPException(status_code=400, detail="Storyline not generated yet")
    setup = _get_outline_setup_context(db, project_id)
    if not setup:
        raise HTTPException(status_code=400, detail="Setup not generated yet")

    window_args = (
        f"请只生成第{start_chapter}章到第{end_chapter}章的滚动章节大纲；"
        "不要改写已存在章节；返回JSON中的chapters只包含该窗口内章节。"
    )
    if command_args:
        window_args = f"{window_args}\n附加要求：{command_args}"
    payload = _build_outline_call_payload(project, setup, storyline_context, command_args=window_args)
    trace = create_trace(
        db,
        project_id=project.id,
        trace_type="outline_expansion",
        messages=payload["messages"],
        context_blocks=payload["context_blocks"],
        trace_metadata={
            **payload["trace_metadata"],
            "outline_window": {"start_chapter": start_chapter, "end_chapter": end_chapter},
        },
        model=project.ai_model or "deepseek-chat",
        temperature=0.7,
        max_tokens=payload["max_tokens"],
    )
    db.commit()

    started_at = now_ms()
    start = time.time()
    try:
        result = await ai_service.complete(
            payload["messages"],
            temperature=0.7,
            max_tokens=payload["max_tokens"],
            model=project.ai_model or "deepseek-chat",
            response_format={"type": "json_object"},
        )
        data = ai_service.parse_json(result.content)
    except Exception as exc:
        mark_trace_failed(db, trace, error_message=str(exc), latency_ms=now_ms() - started_at)
        db.commit()
        raise

    merged_chapters, merge_result = _merge_outline_chapter_window(
        existing.chapters,
        data.get("chapters", []),
        start_chapter=start_chapter,
        end_chapter=end_chapter,
    )
    existing.chapters = merged_chapters
    existing.total_chapters = max(
        int(existing.total_chapters or 0),
        int(data.get("total_chapters") or 0),
        _target_total_chapters(project),
        end_chapter,
    )
    existing.status = "generated"
    project.status = "outline_generated"
    project.current_phase = "outline"
    mark_trace_success(
        db,
        trace,
        prompt_tokens=getattr(result, "prompt_tokens", 0),
        completion_tokens=getattr(result, "completion_tokens", 0),
        latency_ms=int((time.time() - start) * 1000),
    )

    try:
        db.commit()
        db.refresh(existing)
    except Exception:
        db.rollback()
        raise

    WritingStateService(db).reconcile_target(project_id)
    setattr(existing, "outline_expansion_result", merge_result)
    setattr(existing, "last_expansion_trace_id", trace.id)
    return existing


@router.get("", response_model=OutlineOut)
def get_outline(
    project_id: str,
    mode: str = Query("window", pattern="^(full|window)$"),
    chapter_offset: int = Query(0, ge=0),
    chapter_limit: int = Query(100, ge=1, le=500),
    plotline_offset: int = Query(0, ge=0),
    plotline_limit: int = Query(20, ge=1, le=500),
    foreshadowing_offset: int = Query(0, ge=0),
    foreshadowing_limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    response: Response = None,
):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/plan")
    if mode == "window":
        outline = get_evolution_plan_window(
            db=db,
            project_id=project_id,
            chapter_offset=chapter_offset,
            chapter_limit=chapter_limit,
            plotline_offset=plotline_offset,
            plotline_limit=plotline_limit,
            foreshadowing_offset=foreshadowing_offset,
            foreshadowing_limit=foreshadowing_limit,
        )["outline"]
        if not outline:
            raise HTTPException(status_code=404, detail="Outline not found")
        return outline
    outline = db.query(Outline).filter(Outline.project_id == project_id).first()
    if not outline:
        raise HTTPException(status_code=404, detail="Outline not found")
    return outline


from pydantic import BaseModel


class ChapterOutlineUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    scenes: list[str] | None = None
    characters: list[str] | None = None
    purpose: str | None = None


@router.patch("/chapters/{chapter_index}")
def update_chapter_outline(
    project_id: str,
    chapter_index: int = Path(..., ge=1),
    payload: ChapterOutlineUpdate = Body(...),
    db: Session = Depends(get_db),
    response: Response = None,
):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/evolution/plan/outline/chapters/{chapter_index}")
    outline_id = db.query(Outline.id).filter(Outline.project_id == project_id).scalar()
    if not outline_id:
        raise HTTPException(status_code=404, detail="Outline not found")

    chapter_key = db.execute(
        text(
            """
            SELECT item.key AS chapter_key
            FROM outlines, json_each(outlines.chapters) AS item
            WHERE outlines.id = :outline_id
            AND CAST(json_extract(item.value, '$.chapter_index') AS INTEGER) = :chapter_index
            LIMIT 1
            """
        ),
        {"outline_id": outline_id, "chapter_index": chapter_index},
    ).scalar()
    if chapter_key is None:
        raise HTTPException(status_code=404, detail="Chapter not found in outline")

    params = {
        "outline_id": outline_id,
        "chapter_key": str(chapter_key),
        "updated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" "),
    }
    updates: list[str] = []
    for field in ("title", "summary", "purpose"):
        value = getattr(payload, field)
        if value is not None:
            params[field] = value
            updates.extend([f"'$[' || :chapter_key || '].{field}'", f":{field}"])
    for field in ("scenes", "characters"):
        value = getattr(payload, field)
        if value is not None:
            param_name = f"{field}_json"
            params[param_name] = json.dumps(value, ensure_ascii=False)
            updates.extend([f"'$[' || :chapter_key || '].{field}'", f"json(:{param_name})"])

    if updates:
        db.execute(
            text(
                f"""
                UPDATE outlines
                SET chapters = json_set(chapters, {', '.join(updates)}),
                    updated_at = :updated_at
                WHERE id = :outline_id
                """
            ),
            params,
        )
    db.commit()
    return {"updated": True, "chapter_index": chapter_index}

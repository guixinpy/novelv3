import json
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.context_injection import (
    build_athena_world_context,
    build_athena_world_context_blocks,
    build_hermes_world_context,
    build_hermes_world_context_blocks,
)
from app.core.model_call_trace import build_context_block, truncate_text
from app.models import (
    ChapterContent,
    DialogMessage,
    LongformMemory,
    Outline,
    Project,
    ProjectProfileVersion,
    RetrievalDocument,
    Setup,
    Storyline,
    WorldFactClaim,
    WorldProposalBundle,
    WorldProposalItem,
)
from app.prompting.assembler import PromptAssembler
from app.prompting.tracing import build_prompt_trace_metadata

CHAT_HISTORY_LIMIT = 8
DIALOG_HISTORY_MESSAGE_CONTENT_CHARS = 2_000
MANUSCRIPT_FULL_LIST_LIMIT = 40
MANUSCRIPT_EDGE_CHAPTER_COUNT = 5
MANUSCRIPT_RECENT_EXCERPT_COUNT = 3
NARRATIVE_PLANNING_PREVIEW_LIMIT = 5
PHASE_LABELS = {
    "setup": "设定阶段",
    "storyline": "故事线阶段",
    "outline": "大纲阶段",
    "content": "正文阶段",
}
STATUS_LABELS = {
    "draft": "待补全",
    "writing": "正文写作中",
    "outline_generated": "大纲已生成",
    "storyline_generated": "故事线已生成",
    "setup_approved": "设定已确认",
}


def build_dialog_history_messages(
    db: Session,
    dialog_id: str,
    limit: int = CHAT_HISTORY_LIMIT,
) -> list[dict[str, str]]:
    history = _latest_dialog_history(db, dialog_id, limit)
    messages = []
    for item in history:
        content = _bounded_history_content(item.content)
        if item.role in ("user", "assistant"):
            messages.append({"role": item.role, "content": content})
        elif item.role == "system":
            messages.append({"role": "assistant", "content": f"[系统消息] {content}"})
    return messages


def build_dialog_history_block(
    db: Session,
    dialog_id: str,
    limit: int = CHAT_HISTORY_LIMIT,
) -> dict[str, Any]:
    history = _latest_dialog_history(db, dialog_id, limit)
    lines = []
    for item in history:
        content = _bounded_history_content(item.content)
        if item.role in ("user", "assistant"):
            lines.append(f"{item.role}: {content}")
        elif item.role == "system":
            lines.append(f"assistant: [系统消息] {content}")

    return build_context_block(
        key="dialog.history",
        kind="dialog_history",
        title="对话历史",
        content="\n".join(lines) if lines else "当前对话暂无可用历史。",
        sources=[
            {
                "source_type": "Dialog",
                "source_id": dialog_id,
            }
        ],
    )


def _bounded_history_content(content: str | None) -> str:
    return truncate_text(content or "", max_chars=DIALOG_HISTORY_MESSAGE_CONTENT_CHARS)["content"]


def build_hermes_prompt_variables(project: Project, diagnosis, world_context: str) -> dict[str, str]:
    completed_items = getattr(diagnosis, "completed_items", []) or []
    missing_items = getattr(diagnosis, "missing_items", []) or []
    return {
        "project_name": project.name or "未命名项目",
        "project_genre": project.genre or "未分类题材",
        "project_description": project.description or "暂无项目描述",
        "project_phase": _phase_label(project.current_phase),
        "project_status": _status_label(project.status),
        "current_words": str(project.current_word_count or 0),
        "target_chapters": str(project.target_chapter_count or 0),
        "target_words": str(project.target_word_count or 0),
        "completed_items": "、".join(completed_items) if completed_items else "无",
        "missing_items": "、".join(missing_items) if missing_items else "无",
        "suggested_next_step": getattr(diagnosis, "suggested_next_step", None) or "无",
        "world_context": world_context,
    }


def build_athena_prompt_variables(db: Session, project: Project, world_context: str) -> dict[str, str]:
    profile = _current_profile(db, project.id)
    return {
        "project_name": project.name or "未命名项目",
        "project_genre": project.genre or "未分类题材",
        "project_description": project.description or "暂无项目描述",
        "project_phase": _phase_label(project.current_phase),
        "profile_version": str(profile.version) if profile else "未建立",
        "world_context": world_context,
    }


def build_athena_manuscript_context_block(db: Session, project: Project) -> dict[str, Any] | None:
    chapter_count, first_chapter_index, last_chapter_index = (
        db.query(
            func.count(ChapterContent.id),
            func.min(ChapterContent.chapter_index),
            func.max(ChapterContent.chapter_index),
        )
        .filter(ChapterContent.project_id == project.id, ChapterContent.content != "")
        .one()
    )
    chapter_count = int(chapter_count or 0)
    if not chapter_count:
        return None

    total_words = int(project.current_word_count or 0)
    target_chapters = project.target_chapter_count or chapter_count
    lines = [
        f"已生成章节：{chapter_count} / 目标 {target_chapters}",
        f"当前总字数：{total_words}",
        f"章节范围：第{first_chapter_index}章 至 第{last_chapter_index}章",
    ]
    listed_chapters = _bounded_manuscript_chapter_list(db, project.id, chapter_count)
    lines.extend(listed_chapters["lines"])

    recent = (
        db.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.content != "")
        .order_by(ChapterContent.chapter_index.desc())
        .limit(MANUSCRIPT_RECENT_EXCERPT_COUNT)
        .all()
    )
    recent = list(reversed(recent))
    if recent:
        lines.append("最近章节摘录：")
        for chapter in recent:
            excerpt = " ".join((chapter.content or "").split())[:220]
            if excerpt:
                lines.append(f"- 第{chapter.chapter_index}章：{excerpt}")

    source_rows = _unique_manuscript_source_rows([*listed_chapters["sources"], *recent])
    return build_context_block(
        key="athena.manuscript_summary",
        kind="manuscript_summary",
        title="正文进度",
        content="\n".join(lines),
        sources=[
            {
                "source_type": "ChapterContent",
                "source_id": _chapter_summary_value(chapter, "id"),
                "chapter_index": _chapter_summary_value(chapter, "chapter_index"),
                "label": _chapter_summary_value(chapter, "title") or f"第{_chapter_summary_value(chapter, 'chapter_index')}章",
            }
            for chapter in source_rows
        ],
    )


def _bounded_manuscript_chapter_list(db: Session, project_id: str, chapter_count: int) -> dict[str, Any]:
    if chapter_count <= MANUSCRIPT_FULL_LIST_LIMIT:
        chapters = _chapter_summary_query(db, project_id).order_by(ChapterContent.chapter_index.asc()).limit(
            MANUSCRIPT_FULL_LIST_LIMIT
        ).all()
        return {
            "lines": ["章节清单:", *[_manuscript_chapter_line(chapter) for chapter in chapters]],
            "sources": chapters,
        }

    head = (
        _chapter_summary_query(db, project_id)
        .order_by(ChapterContent.chapter_index.asc())
        .limit(MANUSCRIPT_EDGE_CHAPTER_COUNT)
        .all()
    )
    tail = list(
        reversed(
            _chapter_summary_query(db, project_id)
            .order_by(ChapterContent.chapter_index.desc())
            .limit(MANUSCRIPT_EDGE_CHAPTER_COUNT)
            .all()
        )
    )
    folded_count = max(chapter_count - len(head) - len(tail), 0)
    lines = ["章节清单（长篇折叠）:", "开篇章节:"]
    lines.extend(_manuscript_chapter_line(chapter) for chapter in head)
    if folded_count:
        folded_start = _chapter_summary_value(head[-1], "chapter_index") + 1
        folded_end = _chapter_summary_value(tail[0], "chapter_index") - 1
        lines.append(f"- 中间章节已折叠：第{folded_start}章至第{folded_end}章，共{folded_count}章。")
    lines.append("最新章节:")
    lines.extend(_manuscript_chapter_line(chapter) for chapter in tail)
    return {"lines": lines, "sources": [*head, *tail]}


def _chapter_summary_query(db: Session, project_id: str):
    return db.query(
        ChapterContent.id,
        ChapterContent.chapter_index,
        ChapterContent.title,
        ChapterContent.word_count,
        ChapterContent.status,
    ).filter(ChapterContent.project_id == project_id, ChapterContent.content != "")


def _manuscript_chapter_line(chapter: Any) -> str:
    chapter_index = _chapter_summary_value(chapter, "chapter_index")
    title = _chapter_summary_value(chapter, "title") or "未命名章节"
    word_count = _chapter_summary_value(chapter, "word_count") or 0
    status = _chapter_summary_value(chapter, "status") or "unknown"
    return f"- 第{chapter_index}章《{title}》：{word_count}字，{status}"


def _chapter_summary_value(chapter: Any, key: str) -> Any:
    mapping = getattr(chapter, "_mapping", None)
    if mapping is not None and key in mapping:
        return mapping[key]
    return getattr(chapter, key, None)


def _unique_manuscript_source_rows(chapters: list[Any]) -> list[Any]:
    seen: set[str] = set()
    rows: list[Any] = []
    for chapter in chapters:
        chapter_id = str(_chapter_summary_value(chapter, "id") or "")
        if not chapter_id or chapter_id in seen:
            continue
        seen.add(chapter_id)
        rows.append(chapter)
    return rows


def build_athena_context_boundary_block(db: Session, project: Project) -> dict[str, Any]:
    chapter_count, first_chapter_index, last_chapter_index = (
        db.query(ChapterContent)
        .with_entities(
            func.count(ChapterContent.id),
            func.min(ChapterContent.chapter_index),
            func.max(ChapterContent.chapter_index),
        )
        .filter(ChapterContent.project_id == project.id, ChapterContent.content != "")
        .one()
    )
    profile = _current_profile(db, project.id)
    chapter_count = int(chapter_count or 0)
    target_chapters = project.target_chapter_count or chapter_count
    if chapter_count:
        chapter_line = (
            f"正文：已生成 {chapter_count} / 目标 {target_chapters}，"
            f"范围第{first_chapter_index}章至第{last_chapter_index}章"
        )
    else:
        chapter_line = f"正文：已生成 0 / 目标 {target_chapters}"

    truth_filters = [
        WorldFactClaim.project_id == project.id,
        WorldFactClaim.claim_layer == "truth",
        WorldFactClaim.claim_status == "confirmed",
    ]
    bundle_filters = [
        WorldProposalBundle.project_id == project.id,
        WorldProposalBundle.bundle_status == "pending",
    ]
    item_filters = [
        WorldProposalItem.project_id == project.id,
        WorldProposalItem.item_status == "pending",
    ]
    if profile is not None:
        truth_filters.extend(
            [
                WorldFactClaim.project_profile_version_id == profile.id,
                WorldFactClaim.profile_version == profile.version,
            ]
        )
        bundle_filters.extend(
            [
                WorldProposalBundle.project_profile_version_id == profile.id,
                WorldProposalBundle.profile_version == profile.version,
            ]
        )
        item_filters.extend(
            [
                WorldProposalItem.project_profile_version_id == profile.id,
                WorldProposalItem.profile_version == profile.version,
            ]
        )

    retrieval_count = (
        db.query(func.count(RetrievalDocument.id))
        .filter(RetrievalDocument.project_id == project.id)
        .scalar()
        or 0
    )
    truth_count = db.query(func.count(WorldFactClaim.id)).filter(*truth_filters).scalar() or 0
    bundle_count = db.query(func.count(WorldProposalBundle.id)).filter(*bundle_filters).scalar() or 0
    item_count = db.query(func.count(WorldProposalItem.id)).filter(*item_filters).scalar() or 0
    lines = [
        "已读取范围：",
        f"- {chapter_line}",
        f"- 检索索引：{retrieval_count} 个文档",
        f"- 世界事实：{truth_count} 条确认真相",
        f"- 待审提案：{bundle_count} 个批次 / {item_count} 条候选",
        "回答边界：",
        "- 回答全局质量、伏笔闭合、秘密回收、一致性判断时，必须说明依据范围。",
        "- 最近章节摘录只代表局部证据；不能据此替代全书进度、叙事规划、世界事实和待审提案。",
    ]
    return build_context_block(
        key="athena.context_boundary",
        kind="context_boundary",
        title="上下文边界",
        content="\n".join(lines),
    )


def build_athena_narrative_planning_context_block(db: Session, project: Project) -> dict[str, Any] | None:
    setup = (
        db.query(Setup.id, Setup.core_concept)
        .filter(Setup.project_id == project.id)
        .order_by(Setup.updated_at.desc())
        .first()
    )
    storyline = _latest_storyline_planning_row(db, project.id)
    outline = _latest_outline_planning_row(db, project.id)
    if setup is None and storyline is None and outline is None:
        return None

    lines = ["叙事规划摘要："]
    sources: list[dict[str, Any]] = []
    total_foreshadowing = 0
    if setup is not None:
        sources.append({"source_type": "Setup", "source_id": setup.id, "label": "Setup"})
        if setup.core_concept:
            lines.append(f"- 核心概念：{_compact_json(setup.core_concept)}")
    if outline is not None:
        chapters_count = int(outline.chapters_count or 0)
        foreshadowing_count = int(outline.foreshadowing_count or 0)
        total_foreshadowing += foreshadowing_count
        total = outline.total_chapters or chapters_count
        sources.append({"source_type": "Outline", "source_id": outline.id, "label": "Outline"})
        lines.append(f"- 大纲：{total} 章规划，已记录章节 {chapters_count} 条")
    if storyline is not None:
        plotlines_count = int(storyline.plotlines_count or 0)
        foreshadowing_count = int(storyline.foreshadowing_count or 0)
        total_foreshadowing += foreshadowing_count
        sources.append({"source_type": "Storyline", "source_id": storyline.id, "label": "Storyline"})
        lines.append(f"- 故事线：{plotlines_count} 条")
        for item in _storyline_plotline_previews(db, storyline.id):
            summary = _planning_item_summary(item)
            if summary:
                lines.append(f"  - {summary}")
    lines.append(f"- 伏笔：{total_foreshadowing} 条")
    return build_context_block(
        key="athena.narrative_planning_summary",
        kind="narrative_planning_summary",
        title="叙事规划摘要",
        content="\n".join(lines),
        sources=sources,
        max_chars=6000,
    )


def _latest_storyline_planning_row(db: Session, project_id: str):
    return (
        db.query(
            Storyline.id,
            func.coalesce(func.json_array_length(Storyline.plotlines), 0).label("plotlines_count"),
            func.coalesce(func.json_array_length(Storyline.foreshadowing), 0).label("foreshadowing_count"),
        )
        .filter(Storyline.project_id == project_id)
        .order_by(Storyline.updated_at.desc())
        .first()
    )


def _latest_outline_planning_row(db: Session, project_id: str):
    return (
        db.query(
            Outline.id,
            Outline.total_chapters,
            func.coalesce(func.json_array_length(Outline.chapters), 0).label("chapters_count"),
            func.coalesce(func.json_array_length(Outline.foreshadowing), 0).label("foreshadowing_count"),
        )
        .filter(Outline.project_id == project_id)
        .order_by(Outline.updated_at.desc())
        .first()
    )


def _storyline_plotline_previews(db: Session, storyline_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT
                json_extract(item.value, '$.title') AS title,
                json_extract(item.value, '$.name') AS name,
                json_extract(item.value, '$.plotline') AS plotline,
                json_extract(item.value, '$.id') AS id,
                json_extract(item.value, '$.summary') AS summary,
                json_extract(item.value, '$.description') AS description,
                json_extract(item.value, '$.theme') AS theme
            FROM storylines, json_each(storylines.plotlines) AS item
            WHERE storylines.id = :storyline_id
            ORDER BY CAST(item.key AS INTEGER)
            LIMIT :limit
            """
        ),
        {"storyline_id": storyline_id, "limit": NARRATIVE_PLANNING_PREVIEW_LIMIT},
    ).mappings()
    return [
        {
            "title": row["title"],
            "name": row["name"],
            "plotline": row["plotline"],
            "id": row["id"],
            "summary": row["summary"],
            "description": row["description"],
            "theme": row["theme"],
        }
        for row in rows
    ]


def build_longform_evidence_range_context_block(db: Session, project: Project) -> dict[str, Any] | None:
    rows = (
        db.query(LongformMemory.memory_type, func.count(LongformMemory.id))
        .filter(LongformMemory.project_id == project.id)
        .group_by(LongformMemory.memory_type)
        .all()
    )
    counts = {memory_type: int(count) for memory_type, count in rows}
    total_memories = sum(counts.values())
    if total_memories <= 0:
        return None
    count_line = "、".join(f"{key}: {value}" for key, value in counts.items())
    chapter_count = (
        db.query(func.count(ChapterContent.id))
        .filter(ChapterContent.project_id == project.id)
        .scalar()
        or 0
    )
    current_word_count = int(project.current_word_count or 0)
    lines = [
        "长篇依据范围：",
        f"- 已生成章节：{chapter_count}",
        f"- 当前总字数：{current_word_count}",
        f"- 分层记忆：{count_line}",
        "- 默认回答和创作建议必须基于已生成章节、长篇记忆、世界事实和显式检索命中；不能读取未来章节。",
    ]
    return build_context_block(
        key="longform.evidence_range",
        kind="longform_evidence_range",
        title="长篇依据范围",
        content="\n".join(lines),
    )


def build_dialog_call_payload(
    db: Session,
    dialog_id: str,
    project: Project,
    diagnosis,
    dialog_type: str = "hermes",
    history_limit: int = CHAT_HISTORY_LIMIT,
) -> dict[str, Any]:
    normalized_dialog_type = "athena" if dialog_type == "athena" else "hermes"
    if normalized_dialog_type == "athena":
        prompt_id = "dialog.athena"
        world_context = build_athena_world_context(db, project.id)
        context_blocks = build_athena_world_context_blocks(db, project.id)
        extra_blocks = [build_athena_context_boundary_block(db, project)]
        longform_block = build_longform_evidence_range_context_block(db, project)
        if longform_block:
            extra_blocks.append(longform_block)
        planning_block = build_athena_narrative_planning_context_block(db, project)
        if planning_block:
            extra_blocks.append(planning_block)
        manuscript_block = build_athena_manuscript_context_block(db, project)
        if manuscript_block:
            extra_blocks.append(manuscript_block)
        context_blocks.extend(extra_blocks)
        world_context = "\n\n".join(
            part for part in [
                world_context,
                *[f"## {block['title']}\n{block['content']}" for block in extra_blocks],
            ]
            if part
        )
        variables = build_athena_prompt_variables(db, project, world_context)
    else:
        prompt_id = "dialog.hermes"
        world_context = build_hermes_world_context(db, project.id)
        context_blocks = build_hermes_world_context_blocks(db, project.id)
        longform_block = build_longform_evidence_range_context_block(db, project)
        if longform_block:
            context_blocks.append(longform_block)
            world_context = "\n\n".join(
                part for part in [
                    world_context,
                    f"## {longform_block['title']}\n{longform_block['content']}",
                ]
                if part
            )
        variables = build_hermes_prompt_variables(project, diagnosis, world_context)

    context_blocks = [
        *context_blocks,
        build_dialog_history_block(db, dialog_id, limit=history_limit),
    ]
    assembler = PromptAssembler()
    rendered_result = assembler.build(
        prompt_id,
        variables,
        context_blocks=context_blocks,
        messages=[],
    )
    messages = [
        {"role": "system", "content": rendered_result.content},
        *build_dialog_history_messages(db, dialog_id, limit=history_limit),
    ]
    build_result = assembler.build(
        prompt_id,
        variables,
        context_blocks=context_blocks,
        messages=messages,
    )
    trace_metadata = build_prompt_trace_metadata(build_result)
    trace_metadata["dialog_type"] = normalized_dialog_type
    return {
        "messages": build_result.messages,
        "context_blocks": build_result.context_blocks,
        "trace_metadata": trace_metadata,
        "rendered_prompt": build_result.content,
    }


def _latest_dialog_history(db: Session, dialog_id: str, limit: int) -> list[Any]:
    history = (
        db.query(
            DialogMessage.role,
            func.substr(
                DialogMessage.content,
                1,
                DIALOG_HISTORY_MESSAGE_CONTENT_CHARS + 1,
            ).label("content"),
        )
        .filter(DialogMessage.dialog_id == dialog_id)
        .order_by(DialogMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    history.reverse()
    return history


def _current_profile(db: Session, project_id: str) -> Any | None:
    return (
        db.query(ProjectProfileVersion.id, ProjectProfileVersion.version)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc())
        .first()
    )


def _compact_json(value: Any, *, limit: int = 320) -> str:
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else f"{text[:limit]}..."


def _planning_item_summary(item: Any) -> str:
    if not isinstance(item, dict):
        return str(item)[:180]
    title = item.get("title") or item.get("name") or item.get("plotline") or item.get("id")
    summary = item.get("summary") or item.get("description") or item.get("theme")
    if title and summary:
        return f"{title}：{summary}"[:180]
    return str(title or summary or "")[:180]


def _phase_label(phase: str | None) -> str:
    return PHASE_LABELS.get(phase or "", phase or "未开始")


def _status_label(status: str | None) -> str:
    return STATUS_LABELS.get(status or "", status or "待补全")

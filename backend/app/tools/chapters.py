"""章节读取与写入工具。"""
from __future__ import annotations

from app.agent.tooling import ToolContext, ToolResult, tool
from app.models import ChapterContent, LongformMemory, Project, WorldCharacter, WorldLocation
from app.tools.registry import registry


def _chapter_summary(ch: ChapterContent) -> dict:
    return {
        "chapter_index": ch.chapter_index,
        "title": ch.title,
        "status": ch.status,
        "word_count": ch.word_count,
    }


@tool(
    registry=registry,
    name="list_chapters",
    description=(
        "列出项目的章节清单（序号、标题、状态、字数），按章节序号升序。"
        "想了解整体进度或定位某一章时先用本工具。"
    ),
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "start": {"type": "integer", "description": "起始章节序号（含），默认从第一章开始"},
            "limit": {"type": "integer", "description": "最多返回多少章，默认 50"},
        },
    },
)
async def list_chapters(ctx: ToolContext, start: int = 0, limit: int = 50) -> ToolResult:
    query = (
        ctx.db.query(ChapterContent)
        .filter(ChapterContent.project_id == ctx.project_id)
    )
    total = query.count()
    chapters = (
        query.filter(ChapterContent.chapter_index >= start)
        .order_by(ChapterContent.chapter_index.asc())
        .limit(limit)
        .all()
    )
    return ToolResult.ok({"total": total, "chapters": [_chapter_summary(c) for c in chapters]})


@tool(
    registry=registry,
    name="read_chapter",
    description="读取指定章节的完整正文与元数据。需要章节具体内容时使用。",
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "chapter_index": {"type": "integer", "description": "章节序号"},
        },
        "required": ["chapter_index"],
    },
)
async def read_chapter(ctx: ToolContext, chapter_index: int) -> ToolResult:
    chapter = (
        ctx.db.query(ChapterContent)
        .filter(
            ChapterContent.project_id == ctx.project_id,
            ChapterContent.chapter_index == chapter_index,
        )
        .first()
    )
    if chapter is None:
        existing = (
            ctx.db.query(ChapterContent.chapter_index)
            .filter(ChapterContent.project_id == ctx.project_id)
            .order_by(ChapterContent.chapter_index.asc())
            .all()
        )
        indexes = [row[0] for row in existing]
        hint = f"现有章节序号：{indexes[:50]}" if indexes else "项目还没有任何章节"
        return ToolResult.fail(
            f"第 {chapter_index} 章不存在。{hint}。可先用 list_chapters 查看章节清单。"
        )
    return ToolResult.ok(
        {
            **_chapter_summary(chapter),
            "content": chapter.content,
            "updated_at": chapter.updated_at.isoformat() if chapter.updated_at else None,
        }
    )


def _capture_entities(ctx: ToolContext, content: str, chapter_index: int) -> None:
    """从章节内容中提取已知实体名称并创建长期记忆记录。"""
    known_entities: dict[str, str] = {}
    for c in ctx.db.query(WorldCharacter).filter(WorldCharacter.project_id == ctx.project_id).all():
        known_entities[c.name] = "character"
    for l in ctx.db.query(WorldLocation).filter(WorldLocation.project_id == ctx.project_id).all():
        known_entities[l.name] = "location"

    for name, etype in known_entities.items():
        if name in content:
            existing = ctx.db.query(LongformMemory).filter(
                LongformMemory.project_id == ctx.project_id,
                LongformMemory.memory_type == "entity_state",
                LongformMemory.scope_key == name,
                LongformMemory.status == "active",
            ).first()
            if existing:
                existing.end_chapter_index = chapter_index
            else:
                ctx.db.add(LongformMemory(
                    project_id=ctx.project_id,
                    memory_type="entity_state",
                    scope_key=name,
                    title=name,
                    summary=f"「{name}」出现在第 {chapter_index} 章",
                    start_chapter_index=chapter_index,
                    status="active",
                ))


def _update_project_word_count(ctx: ToolContext) -> None:
    """重算并更新项目总字数。"""
    project = ctx.db.query(Project).filter(Project.id == ctx.project_id).first()
    if project is None:
        return
    total = (
        ctx.db.query(ChapterContent.word_count)
        .filter(ChapterContent.project_id == ctx.project_id)
        .all()
    )
    project.current_word_count = sum(wc for (wc,) in total)


@tool(
    registry=registry,
    name="write_chapter",
    description=(
        "创建或覆盖指定章节的正文。如果该章节已存在，会用新内容替换旧内容。"
        "写入完成后会自动更新项目的总字数。写入前建议先用 read_chapter 确认章节当前内容。"
    ),
    permission="write",
    parameters={
        "type": "object",
        "properties": {
            "chapter_index": {"type": "integer", "description": "章节序号，从 1 开始"},
            "content": {"type": "string", "description": "章节正文"},
            "title": {"type": "string", "description": "章节标题（可选，不传则保留旧标题或使用默认标题）"},
        },
        "required": ["chapter_index", "content"],
    },
)
async def write_chapter(ctx: ToolContext, chapter_index: int, content: str, title: str = "") -> ToolResult:
    if chapter_index < 1:
        return ToolResult.fail("章节序号必须 >= 1。")

    existing = (
        ctx.db.query(ChapterContent)
        .filter(
            ChapterContent.project_id == ctx.project_id,
            ChapterContent.chapter_index == chapter_index,
        )
        .first()
    )

    word_count = len(content.replace(" ", "").replace("\n", ""))
    if existing:
        existing.content = content
        if title:
            existing.title = title
        existing.word_count = word_count
        existing.status = "generated"
    else:
        ch = ChapterContent(
            project_id=ctx.project_id,
            chapter_index=chapter_index,
            title=title or f"第{chapter_index}章",
            content=content,
            word_count=word_count,
            status="generated",
        )
        ctx.db.add(ch)

    ctx.db.flush()  # 确保新数据在查询前可见
    _capture_entities(ctx, content, chapter_index)
    _update_project_word_count(ctx)
    ctx.db.commit()
    return ToolResult.ok({"chapter_index": chapter_index, "word_count": word_count, "status": "written"})


@tool(
    registry=registry,
    name="revise_chapter",
    description=(
        "对已存在的章节应用修订：替换完整正文为新内容。"
        "使用前需要先用 read_chapter 读取当前内容。"
    ),
    permission="write",
    parameters={
        "type": "object",
        "properties": {
            "chapter_index": {"type": "integer", "description": "要修订的章节序号"},
            "new_content": {"type": "string", "description": "修订后的完整正文"},
            "new_title": {"type": "string", "description": "可选的新标题"},
        },
        "required": ["chapter_index", "new_content"],
    },
)
async def revise_chapter(ctx: ToolContext, chapter_index: int, new_content: str, new_title: str = "") -> ToolResult:
    chapter = (
        ctx.db.query(ChapterContent)
        .filter(
            ChapterContent.project_id == ctx.project_id,
            ChapterContent.chapter_index == chapter_index,
        )
        .first()
    )
    if chapter is None:
        return ToolResult.fail(f"第 {chapter_index} 章不存在。请先用 write_chapter 创建或 list_chapters 确认。")

    chapter.content = new_content
    chapter.word_count = len(new_content.replace(" ", "").replace("\n", ""))
    if new_title:
        chapter.title = new_title
    ctx.db.flush()
    _capture_entities(ctx, new_content, chapter_index)
    _update_project_word_count(ctx)
    ctx.db.commit()
    return ToolResult.ok({"chapter_index": chapter_index, "word_count": chapter.word_count, "status": "revised"})


@tool(
    registry=registry,
    name="check_chapter_quality",
    description=(
        "对指定章节做质量检查：字数范围、标题完整性、内容形式问题。"
        "如果返回的问题列表为空，说明章节质量基础过关。"
    ),
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "chapter_index": {"type": "integer", "description": "要检查的章节序号"},
        },
        "required": ["chapter_index"],
    },
)
async def check_chapter_quality(ctx: ToolContext, chapter_index: int) -> ToolResult:
    chapter = (
        ctx.db.query(ChapterContent)
        .filter(
            ChapterContent.project_id == ctx.project_id,
            ChapterContent.chapter_index == chapter_index,
        )
        .first()
    )
    if chapter is None:
        return ToolResult.fail(f"第 {chapter_index} 章不存在。")

    issues = []
    content = chapter.content or ""
    word_count = len(content.replace(" ", "").replace("\n", ""))

    # 字数检查
    if word_count < 50:
        issues.append({"severity": "warning", "type": "too_short", "detail": f"字数仅 {word_count}，建议至少 500 字"})
    elif word_count < 500:
        issues.append({"severity": "info", "type": "slightly_short", "detail": f"字数 {word_count}，偏短"})
    elif word_count > 50000:
        issues.append({"severity": "warning", "type": "too_long", "detail": f"字数 {word_count}，超过 50000 字建议拆分"})

    # 标题检查
    if not chapter.title or chapter.title.strip() == "":
        issues.append({"severity": "error", "type": "missing_title", "detail": "章节标题为空"})

    # 内容检查
    if not content.strip():
        issues.append({"severity": "error", "type": "empty_content", "detail": "章节正文为空"})
    elif len(content.strip()) < 10:
        issues.append({"severity": "error", "type": "placeholder_content", "detail": "章节正文过短，可能为占位内容"})

    return ToolResult.ok({
        "chapter_index": chapter_index,
        "title": chapter.title,
        "word_count": word_count,
        "status": chapter.status,
        "issues": issues,
        "quality": "pass" if not issues or all(i["severity"] == "info" for i in issues) else "needs_review",
    })


# ── M5.2: Quality Trend Analysis ──


@tool(
    registry=registry,
    name="check_quality_trend",
    description=(
        "分析最近 N 章的质量趋势：查看章节长度变化曲线，检测是否有持续下滑。"
        "【跨弧线对比】写作跨越多个弧线时，务必用本工具检查全局趋势（window≥20），"
        "确保新弧线的章节质量不低于已完成弧线。如果发现跨弧线衰减，"
        "请检查是否对新弧线投入了足够的情节构思和场景细节。"
    ),
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "window": {
                "type": "integer",
                "description": "检查最近几章，默认 10",
                "default": 10,
            },
        },
    },
)
async def check_quality_trend(ctx: ToolContext, window: int = 10) -> ToolResult:
    chapters = (
        ctx.db.query(ChapterContent)
        .filter(ChapterContent.project_id == ctx.project_id)
        .order_by(ChapterContent.chapter_index.asc())
        .all()
    )
    if not chapters:
        return ToolResult.ok({"trend": "no_data", "tip": "还没有章节数据。"})

    # Take last N chapters
    recent = chapters[-window:]
    if len(recent) < 3:
        return ToolResult.ok({"trend": "insufficient_data", "tip": f"只有 {len(recent)} 章，至少需要 3 章才能分析趋势。"})

    word_counts = []
    titles = []
    for c in recent:
        content = c.content if c.content else ""
        wc = len(content) if content else 0
        word_counts.append(wc)
        titles.append(c.title or f"Ch{c.chapter_index}")

    # Compute trend
    first_half_avg = sum(word_counts[:len(word_counts)//2]) / max(1, len(word_counts)//2)
    second_half_avg = sum(word_counts[len(word_counts)//2:]) / max(1, len(word_counts) - len(word_counts)//2)
    ratio = second_half_avg / max(1, first_half_avg)
    min_wc = min(word_counts)
    max_wc = max(word_counts)

    if ratio < 0.5:
        trend = "severe_decline"
        advice = (
            f"严重下滑：近 {window} 章的字数从平均 {int(first_half_avg)} 字降至 {int(second_half_avg)} 字"
            f"（降幅 {int((1-ratio)*100)}%）。请立即检查："
            f"1) 主线是否已完结？如果是，用 plan_arc define 规划新弧线；"
            f"2) 是否在写填充内容（番外/后记）？应聚焦主线情节；"
            f"3) 是否需要补充更多场景、对话、描写来充实内容。"
        )
    elif ratio < 0.75:
        trend = "declining"
        advice = (
            f"轻度下滑：近 {window} 章字数从平均 {int(first_half_avg)} 降至 {int(second_half_avg)}"
            f"（降幅 {int((1-ratio)*100)}%）。注意质量控制，检查是否在接近弧线尾声。"
        )
    elif ratio > 1.3:
        trend = "growing"
        advice = f"字数增长中：从 {int(first_half_avg)} → {int(second_half_avg)}（+{int((ratio-1)*100)}%），保持势头。"
    else:
        trend = "stable"
        advice = f"字数稳定：{int(first_half_avg)} → {int(second_half_avg)}，质量趋势正常。"

    return ToolResult.ok({
        "trend": trend,
        "window": len(recent),
        "word_counts": [
            {"chapter_index": recent[i].chapter_index, "title": titles[i], "word_count": word_counts[i]}
            for i in range(len(recent))
        ],
        "first_half_avg": int(first_half_avg),
        "second_half_avg": int(second_half_avg),
        "min": min_wc,
        "max": max_wc,
        "ratio": round(ratio, 2),
        "advice": advice,
    })

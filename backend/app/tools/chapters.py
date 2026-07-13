"""章节读取与写入工具。"""
from __future__ import annotations

from app.agent.tooling import ToolContext, ToolResult, tool
from app.models import ChapterContent, Project
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

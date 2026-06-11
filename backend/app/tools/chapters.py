"""章节读取工具。"""
from __future__ import annotations

from app.agent.tooling import ToolContext, ToolResult, tool
from app.models import ChapterContent
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

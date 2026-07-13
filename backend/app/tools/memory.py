"""长期记忆工具：情节线追踪和实体状态查询（M4）。"""
from __future__ import annotations

from datetime import UTC, datetime

from app.agent.tooling import ToolContext, ToolResult, tool
from app.models import LongformMemory
from app.tools.registry import registry


@tool(
    registry=registry,
    name="track_plotline",
    description=(
        "登记、查询或闭环一条情节线/伏笔。操作类型决定行为："
        "open=创建新情节线，close=闭环，query=查询。"
    ),
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["open", "close", "query"],
                "description": "操作类型",
            },
            "title": {"type": "string", "description": "情节线标题，如「林舟父亲失踪之谜」"},
            "summary": {"type": "string", "description": "情节线描述"},
            "chapter_index": {"type": "integer", "description": "当前章节序号"},
        },
        "required": ["action"],
    },
)
async def track_plotline(
    ctx: ToolContext,
    action: str,
    title: str = "",
    summary: str = "",
    chapter_index: int = 0,
) -> ToolResult:
    if action == "open":
        if not title:
            return ToolResult.fail("open 操作需要 title 参数。")
        existing = (
            ctx.db.query(LongformMemory)
            .filter(
                LongformMemory.project_id == ctx.project_id,
                LongformMemory.memory_type == "plotline",
                LongformMemory.scope_key == title,
                LongformMemory.status == "open",
            )
            .first()
        )
        if existing:
            return ToolResult.ok({
                "action": "already_exists",
                "id": existing.id,
                "title": title,
                "status": "open",
            })
        mem = LongformMemory(
            project_id=ctx.project_id,
            memory_type="plotline",
            scope_key=title,
            title=title,
            summary=summary,
            start_chapter_index=chapter_index or None,
            status="open",
        )
        ctx.db.add(mem)
        ctx.db.commit()
        return ToolResult.ok({
            "action": "opened",
            "id": mem.id,
            "title": title,
            "status": "open",
        })

    elif action == "close":
        if not title:
            return ToolResult.fail("close 操作需要 title 参数。")
        mem = (
            ctx.db.query(LongformMemory)
            .filter(
                LongformMemory.project_id == ctx.project_id,
                LongformMemory.memory_type == "plotline",
                LongformMemory.scope_key == title,
                LongformMemory.status == "open",
            )
            .first()
        )
        if not mem:
            return ToolResult.fail(f"未找到开放的情节线「{title}」。")
        mem.status = "closed"
        mem.end_chapter_index = chapter_index or None
        ctx.db.commit()
        return ToolResult.ok({
            "action": "closed",
            "id": mem.id,
            "title": title,
            "status": "closed",
        })

    elif action == "query":
        query = ctx.db.query(LongformMemory).filter(
            LongformMemory.project_id == ctx.project_id,
            LongformMemory.memory_type == "plotline",
        )
        if title:
            query = query.filter(LongformMemory.scope_key == title)
        memories = query.order_by(LongformMemory.created_at.desc()).all()
        return ToolResult.ok({
            "action": "query_result",
            "plotlines": [
                {
                    "id": m.id,
                    "title": m.title,
                    "summary": m.summary,
                    "status": m.status,
                    "start_chapter": m.start_chapter_index,
                    "end_chapter": m.end_chapter_index,
                }
                for m in memories
            ],
        })

    return ToolResult.fail(f"未知操作：{action}，支持 open/close/query。")


@tool(
    registry=registry,
    name="query_memory",
    description=(
        "查询跨章节的长期记忆：按类型和关键字检索。"
        "写作前调用本工具了解人物/地点的历史状态，避免前后矛盾。"
    ),
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "memory_type": {
                "type": "string",
                "enum": ["plotline", "entity_state", "all"],
                "description": "记忆类型",
            },
            "keyword": {"type": "string", "description": "搜索关键字（标题或内容）"},
            "limit": {"type": "integer", "description": "最多返回条数"},
        },
    },
)
async def query_memory(ctx: ToolContext, memory_type: str = "all", keyword: str = "", limit: int = 20) -> ToolResult:
    query = ctx.db.query(LongformMemory).filter(
        LongformMemory.project_id == ctx.project_id,
    )
    if memory_type != "all":
        query = query.filter(LongformMemory.memory_type == memory_type)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (LongformMemory.scope_key.like(like)) |
            (LongformMemory.title.like(like)) |
            (LongformMemory.summary.like(like))
        )
    memories = query.order_by(LongformMemory.updated_at.desc()).limit(limit).all()
    return ToolResult.ok({
        "memories": [
            {
                "id": m.id,
                "type": m.memory_type,
                "key": m.scope_key,
                "title": m.title,
                "summary": m.summary,
                "status": m.status,
                "chapter_range": {
                    "start": m.start_chapter_index,
                    "end": m.end_chapter_index,
                },
                "metadata": m.memory_metadata,
            }
            for m in memories
        ],
        "total": len(memories),
    })

"""全文语义检索工具（封装 athena_retrieval）。"""
from __future__ import annotations

from app.agent.tooling import ToolContext, ToolResult, tool
from app.core.athena_retrieval import search_retrieval
from app.tools.registry import registry


@tool(
    registry=registry,
    name="search_text",
    description=(
        "在项目全部已索引文本（章节、记忆、知识库）中做语义+关键词混合检索，"
        "返回相关片段及出处。回忆「之前写过什么」时使用。"
    ),
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "检索词或问题"},
            "limit": {"type": "integer", "description": "最多返回条数，默认 8"},
            "max_chapter_index": {
                "type": "integer",
                "description": "只检索该章节序号之前的内容（避免剧透未来章节）",
            },
        },
        "required": ["query"],
    },
)
async def search_text(
    ctx: ToolContext,
    query: str,
    limit: int = 8,
    max_chapter_index: int | None = None,
) -> ToolResult:
    payload = search_retrieval(
        ctx.db,
        ctx.project_id,
        query,
        limit=limit,
        max_chapter_index=max_chapter_index,
    )
    items = [
        {
            "source_type": item.get("source_type"),
            "title": item.get("title"),
            "chapter_index": item.get("chapter_index"),
            "excerpt": (item.get("snippet") or "")[:500],
            "score": item.get("score"),
        }
        for item in payload.get("items", [])
    ]
    return ToolResult.ok({"query": query, "total": payload.get("total", len(items)), "items": items})

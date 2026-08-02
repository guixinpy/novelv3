"""检索/实体工具（arch-refactor）：get_entities / retrieve。

- get_entities：实体挖掘候选 + rule 跨章转正查询（entity_miner，已迁 domain/retrieval）
- retrieve：语义/关键词检索（athena_retrieval，已迁 domain/retrieval）
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from core.tools.base import ToolContext, ToolRegistry, ToolResult, tool
from domain.retrieval.entity_miner import mine_entities_from_text, promoted_entity_names, register_entity_candidates


class GetEntitiesArgs(BaseModel):
    chapter_index: int = Field(..., ge=1, description="章节号")
    text: str = Field(default="", max_length=12000, description="章节文本（用于挖掘新候选）")
    promote: bool = Field(default=True, description="对跨≥2章候选执行 rule 转正")


class RetrieveArgs(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="检索查询")
    limit: int = Field(default=5, ge=1, le=10)


def register_retrieval_tools(registry: ToolRegistry) -> None:
    @tool(
        registry=registry,
        name="get_entities",
        description=(
            "获取项目的实体名单（角色/地点等）。提供当前章节文本时挖掘新候选并登记；"
            "候选跨≥2 章出现会自动转正为正式实体。返回转正实体与待确认候选。"
        ),
        args_model=GetEntitiesArgs,
        permission="write",  # 有登记副作用（code-review #15）
    )
    def get_entities(ctx: ToolContext, chapter_index: int, text: str = "", promote: bool = True) -> ToolResult:
        db = ctx.db
        if db is None or not ctx.project_id:
            return ToolResult.fail("工具上下文缺少 db/project_id", error_code="tool_context_missing")
        if text:
            candidates = mine_entities_from_text(text)
            for name in candidates:
                register_entity_candidates(db, ctx.project_id, chapter_index, [name])
        promoted = promoted_entity_names(db, ctx.project_id) if promote else []
        return ToolResult.ok({"entities": promoted})

    @tool(
        registry=registry,
        name="retrieve",
        description="检索项目内的相关文档/章节内容（用于写作前查证设定与人物状态）。",
        args_model=RetrieveArgs,
        permission="read",
    )
    def retrieve(ctx: ToolContext, query: str, limit: int = 5) -> ToolResult:
        from domain.retrieval.athena_retrieval import search_retrieval

        db = ctx.db
        if db is None or not ctx.project_id:
            return ToolResult.fail("工具上下文缺少 db/project_id", error_code="tool_context_missing")
        try:
            results = search_retrieval(db, ctx.project_id, query, limit=limit)
        except Exception as exc:  # noqa: BLE001 - 检索失败回填给模型
            return ToolResult.fail(f"检索失败：{exc}", error_code="retrieval_failed")
        return ToolResult.ok({"results": results})

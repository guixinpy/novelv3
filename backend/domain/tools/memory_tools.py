"""记忆工具（arch-refactor）：plan_arc / track_plotline / query_memory / memory_tree。

服务逻辑复用旧 app/tools/memory.py 的 handler（阶段 4 前过渡期，
旧业务逻辑随后续清理迁入 domain/memory/）；本层只做：
- pydantic args_model（新框架 schema 契约）
- 旧 ToolResult → 新 ToolResult 适配
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from core.tools.base import ToolContext, ToolRegistry, ToolResult, tool
import app.tools.memory as _old_memory  # 旧业务逻辑（过渡期）


class TrackPlotlineArgs(BaseModel):
    action: str = Field(..., pattern="^(open|close|query)$", description="open=创建/close=闭环/query=查询")
    title: str = Field(default="", max_length=100, description="情节线标题")
    summary: str = Field(default="", max_length=500, description="情节线描述")
    chapter_index: int = Field(default=0, ge=0, description="当前章节序号")


class QueryMemoryArgs(BaseModel):
    memory_type: str = Field(default="all", pattern="^(plotline|entity_state|arc_summary|all)$")
    keyword: str = Field(default="", max_length=100)
    limit: int = Field(default=5, ge=1, le=10)
    provenance: str = Field(default="all", pattern="^(author_explicit|agent_inferred|all)$")


class PlanArcArgs(BaseModel):
    action: str = Field(..., pattern="^(define|progress|list)$", description="define=定义弧线/progress=检查进度/list=列出")
    title: str = Field(default="", max_length=100, description="弧线标题")
    summary: str = Field(default="", max_length=500, description="弧线描述")
    start_chapter: int = Field(default=0, ge=0, description="起始章节")
    end_chapter: int = Field(default=0, ge=0, description="结束章节")
    must_resolve: list[str] = Field(default_factory=list, description="本弧线必须收束的元素")
    relation_to_previous: str = Field(default="", max_length=200, description="与上一弧线的关系")


def _adapt(old_result) -> ToolResult:
    """旧 ToolResult → 新 ToolResult。"""
    if old_result.is_error:
        return ToolResult.fail(str(old_result.error), error_code="memory_op_failed")
    return ToolResult.ok(old_result.data)


def register_memory_tools(registry: ToolRegistry) -> None:
    @tool(
        registry=registry,
        name="track_plotline",
        description=_old_memory.track_plotline.__doc__ or "登记、查询或闭环一条情节线/伏笔",
        args_model=TrackPlotlineArgs,
        permission="read",
    )
    def track_plotline(ctx: ToolContext, action: str, title: str = "", summary: str = "", chapter_index: int = 0) -> ToolResult:
        return _adapt(_old_memory.track_plotline(ctx, action, title=title, summary=summary, chapter_index=chapter_index))

    @tool(
        registry=registry,
        name="query_memory",
        description=_old_memory.query_memory.__doc__ or "查询跨章节的长期记忆",
        args_model=QueryMemoryArgs,
        permission="read",
    )
    def query_memory(ctx: ToolContext, memory_type: str = "all", keyword: str = "", limit: int = 5, provenance: str = "all") -> ToolResult:
        return _adapt(_old_memory.query_memory(ctx, memory_type, keyword=keyword, limit=limit, provenance=provenance))

    @tool(
        registry=registry,
        name="plan_arc",
        description=_old_memory.plan_arc.__doc__ or "规划/检查/列出弧线",
        args_model=PlanArcArgs,
        permission="read",
    )
    def plan_arc(
        ctx: ToolContext, action: str, title: str = "", summary: str = "",
        start_chapter: int = 0, end_chapter: int = 0,
        must_resolve: list[str] | None = None, relation_to_previous: str = "",
    ) -> ToolResult:
        return _adapt(
            _old_memory.plan_arc(
                ctx, action, title=title, summary=summary,
                start_chapter=start_chapter, end_chapter=end_chapter,
                must_resolve=must_resolve, relation_to_previous=relation_to_previous,
            )
        )

    @tool(
        registry=registry,
        name="memory_tree",
        description=_old_memory.memory_tree.__doc__ or "查看记忆树概览",
        args_model=None,
        permission="read",
    )
    def memory_tree(ctx: ToolContext) -> ToolResult:
        return _adapt(_old_memory.memory_tree(ctx))

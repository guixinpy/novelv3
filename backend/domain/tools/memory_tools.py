"""记忆工具（arch-refactor）：plan_arc / track_plotline / query_memory / memory_tree。

业务逻辑在 domain/memory/memory_service.py（工具描述与业务分离），
本层只做 pydantic args_model + 服务调用 + 错误转换。
"""
from __future__ import annotations

from pydantic import BaseModel, Field, StrictInt

from core.tools.base import ToolContext, ToolRegistry, ToolResult, tool
from domain.memory.memory_service import MemoryServiceError, memory_tree, plan_arc, query_memory, track_plotline


class TrackPlotlineArgs(BaseModel):
    action: str = Field(
        ...,
        pattern="^(open|close|postpone|query)$",
        description="open=创建/postpone=显式延期/close=闭环/query=查询",
    )
    title: str = Field(default="", max_length=100, description="情节线标题")
    summary: str = Field(default="", max_length=500, description="情节线描述")
    chapter_index: int = Field(default=0, ge=0, description="当前章节序号")
    # StrictInt：pydantic lax 模式会把 JSON 布尔 true 静默强转为 1（code-review 4 项 #5）——
    # 落库 expected=1 会自第 2 章起永久误报超期，无迁移路径
    expected_resolve_chapter: StrictInt = Field(
        default=0, ge=0, description="预计回收章（open/postpone 用；账本据此判定临期/超期）"
    )
    payoff: str = Field(default="", max_length=200, description="回收摘要（close 可选，如何回收的）")


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


class MemoryTreeArgs(BaseModel):
    detail_level: str = Field(default="overview", pattern="^(overview|arcs|chapters|full)$")


def _require_ctx(ctx: ToolContext) -> None:
    if ctx.db is None or not ctx.project_id:
        raise MemoryServiceError("工具上下文缺少 db/project_id")


def _call(ctx: ToolContext, fn, *args, **kwargs) -> ToolResult:
    _require_ctx(ctx)
    try:
        return ToolResult.ok(fn(ctx.db, ctx.project_id, *args, **kwargs))
    except MemoryServiceError as exc:
        return ToolResult.fail(str(exc), error_code="memory_op_failed")


def register_memory_tools(registry: ToolRegistry) -> None:
    @tool(
        registry=registry,
        name="track_plotline",
        description=(
            "登记、查询或闭环一条情节线/伏笔。操作类型决定行为："
            "open=创建新情节线（可带 expected_resolve_chapter 预计回收章），"
            "postpone=显式延期（必须带新的 expected_resolve_chapter），"
            "close=闭环（可带 payoff 回收摘要），query=查询（返回超期/临期两级标记）。"
            "伏笔账本：超过预计回收章会被标记超期；无预计回收章的伏笔 30 章未收"
            "也会被标记超期，届时应优先回收或显式延期。"
        ),
        args_model=TrackPlotlineArgs,
        permission="write",
    )
    def track_plotline_handler(
        ctx: ToolContext, action: str, title: str = "", summary: str = "",
        chapter_index: int = 0, expected_resolve_chapter: int = 0, payoff: str = "",
    ) -> ToolResult:
        return _call(
            ctx, track_plotline, action, title, summary=summary, chapter_index=chapter_index,
            expected_resolve_chapter=expected_resolve_chapter, payoff=payoff,
        )

    @tool(
        registry=registry,
        name="query_memory",
        description=(
            "查询跨章节的长期记忆：按类型和关键字检索。"
            "【上下文注入上限】每次 LLM 调用最多使用本工具 1 次，返回最多 5 条记忆。"
            "推荐用法：1) 写作前用 memory_type='arc_summary' 回顾已完成弧线摘要（上限 3 条）；"
            "2) 用 memory_type='plotline' 检查开放情节线（上限 5 条）；"
            "3) 用 keyword 搜索特定人物/地点（上限 3 条）。"
            "注意每条 memory 携带 provenance 字段：author_explicit=作者显式设定（可信度高），agent_inferred=Agent 推理（可信度低）。"
        ),
        args_model=QueryMemoryArgs,
        permission="read",
    )
    def query_memory_handler(ctx: ToolContext, memory_type: str = "all", keyword: str = "", limit: int = 5, provenance: str = "all") -> ToolResult:
        return _call(ctx, query_memory, memory_type, keyword, limit=limit, provenance=provenance)

    @tool(
        registry=registry,
        name="plan_arc",
        description=(
            "规划、检查或列出弧线（story arc）。操作类型决定行为："
            "define=定义新弧线（指定起始和结束章节），progress=检查弧线进度，list=列出全部弧线。"
            "每章写完后用 progress 检查；弧线还剩 3 章时提前规划下一弧线。"
        ),
        args_model=PlanArcArgs,
        permission="write",
    )
    def plan_arc_handler(
        ctx: ToolContext, action: str, title: str = "", summary: str = "",
        start_chapter: int = 0, end_chapter: int = 0,
        must_resolve: list[str] | None = None, relation_to_previous: str = "",
    ) -> ToolResult:
        return _call(
            ctx, plan_arc, action, title, summary=summary,
            start_chapter=start_chapter, end_chapter=end_chapter,
            must_resolve=must_resolve, relation_to_previous=relation_to_previous,
        )

    @tool(
        registry=registry,
        name="memory_tree",
        description=(
            "查看项目的层级记忆树结构（project → arc → chapter → plotline）。"
            "用于了解项目整体记忆组织、发现记忆空白区域。"
        ),
        args_model=MemoryTreeArgs,
        permission="read",
    )
    def memory_tree_handler(ctx: ToolContext, detail_level: str = "overview") -> ToolResult:
        return _call(ctx, memory_tree, detail_level)

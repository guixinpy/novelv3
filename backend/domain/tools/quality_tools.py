"""质量保障工具（P1①/② 恢复）：check_continuity / check_quality_trend。

业务逻辑在 domain/writing/（quality_trend / continuity），本层只做
pydantic args_model + 服务调用 + 错误转换（与记忆/检索工具同模式）。
error_code 契约：同一失败类只用一个码（tool_context_missing——
code-review 5 项 #5：此前自创 missing_context 造成护栏聚合漂移）。
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from core.tools.base import ToolContext, ToolRegistry, ToolResult, tool
from domain.writing.continuity import check_continuity as check_continuity_service
from domain.writing.quality_trend import quality_trend_stats


class CheckContinuityArgs(BaseModel):
    chapter_index: int = Field(default=0, ge=0, description="要检查的章节号（0=最近一章）")


class CheckQualityTrendArgs(BaseModel):
    window: int = Field(default=10, ge=3, le=50, description="趋势窗口（最近 N 章）")


def _require_ctx(ctx: ToolContext) -> None:
    if ctx.db is None or not ctx.project_id:
        raise ValueError("工具上下文缺少 db/project_id")


def register_quality_tools(registry: ToolRegistry) -> None:
    @tool(
        registry=registry,
        name="check_continuity",
        description=(
            "检查单章与设定的连续性（当前为角色状态维度：设定卡标记为死亡的角色"
            "在正文再次出场；默认检查最新一章，可指定章节号）。输出为报告形态："
            "问题 + 证据 + 建议参考，供你判断——回忆、梦境、同名等场景可能是"
            "合法创作，由你决定是否处理。建议在弧线转折、久隔重写、长章节后调用自查。"
        ),
        args_model=CheckContinuityArgs,
        permission="read",
    )
    def check_continuity_handler(ctx: ToolContext, chapter_index: int = 0) -> ToolResult:
        try:
            _require_ctx(ctx)
        except ValueError as exc:
            return ToolResult.fail(str(exc), error_code="tool_context_missing")
        result = check_continuity_service(ctx.db, ctx.project_id, chapter_index)
        # 章节不存在 → fail（code-review 5 项 #4：与 check_chapter_format 的
        # chapter_not_found 契约一致；ok + error 字段会被模型读成「检查通过」）
        if result.get("error"):
            return ToolResult.fail(str(result["error"]), error_code="chapter_not_found")
        return ToolResult.ok(result)

    @tool(
        registry=registry,
        name="check_quality_trend",
        description=(
            "查询近 N 章的字数趋势（信息形态：趋势标签 + 前后窗口均值 + 可能原因供参考）。"
            "数据不足 3 章时返回 insufficient_data 提示。可用于回答「最近写作质量趋势如何」"
            "或长程写作的自查。"
        ),
        args_model=CheckQualityTrendArgs,
        permission="read",
    )
    def check_quality_trend_handler(ctx: ToolContext, window: int = 10) -> ToolResult:
        try:
            _require_ctx(ctx)
        except ValueError as exc:
            return ToolResult.fail(str(exc), error_code="tool_context_missing")
        stats = quality_trend_stats(ctx.db, ctx.project_id, window=window)
        if stats is None:
            return ToolResult.ok(
                {"trend": "insufficient_data", "tip": "不足 3 个有效章节，无法分析趋势。"}
            )
        return ToolResult.ok(stats)

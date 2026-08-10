"""质量保障工具（P1①/② 恢复）：check_continuity。

业务逻辑在 domain/writing/（quality_trend / continuity），本层只做
pydantic args_model + 服务调用 + 错误转换（与记忆/检索工具同模式）。
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from core.tools.base import ToolContext, ToolRegistry, ToolResult, tool
from domain.writing.continuity import check_continuity as check_continuity_service


class CheckContinuityArgs(BaseModel):
    chapter_index: int = Field(default=0, ge=0, description="要检查的章节号（0=最近一章）")


def register_quality_tools(registry: ToolRegistry) -> None:
    @tool(
        registry=registry,
        name="check_continuity",
        description=(
            "检查章节与设定的连续性（当前为角色状态维度：设定卡标记为死亡的角色"
            "在正文再次出场）。输出为报告形态：问题 + 证据 + 建议参考，供你判断——"
            "回忆、梦境、同名等场景可能是合法创作，由你决定是否处理。"
            "建议在弧线转折、久隔重写、长章节后调用自查。"
        ),
        args_model=CheckContinuityArgs,
        permission="read",
    )
    def check_continuity_handler(ctx: ToolContext, chapter_index: int = 0) -> ToolResult:
        if ctx.db is None or not ctx.project_id:
            return ToolResult.fail("工具上下文缺少 db/project_id", error_code="missing_context")
        return ToolResult.ok(check_continuity_service(ctx.db, ctx.project_id, chapter_index))

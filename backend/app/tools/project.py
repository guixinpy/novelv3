"""项目状态工具。"""
from __future__ import annotations

from app.agent.tooling import ToolContext, ToolResult, tool
from app.models import ChapterContent, Outline, Project, Setup
from app.tools.registry import registry


@tool(
    registry=registry,
    name="get_project_state",
    description=(
        "获取项目整体状态：基本信息、设定/大纲完成情况、章节进度。"
        "回合开始时想了解项目当前处于什么阶段就用本工具。"
    ),
    permission="read",
    parameters={"type": "object", "properties": {}},
)
async def get_project_state(ctx: ToolContext) -> ToolResult:
    project = ctx.db.query(Project).filter(Project.id == ctx.project_id).first()
    if project is None:
        return ToolResult.fail(f"项目 {ctx.project_id} 不存在。请确认会话绑定的项目。")

    setup = ctx.db.query(Setup).filter(Setup.project_id == project.id).first()
    outline = ctx.db.query(Outline).filter(Outline.project_id == project.id).first()
    chapter_count = (
        ctx.db.query(ChapterContent).filter(ChapterContent.project_id == project.id).count()
    )
    return ToolResult.ok(
        {
            "project": {
                "name": project.name,
                "genre": project.genre,
                "description": project.description,
                "status": project.status,
                "current_phase": project.current_phase,
                "target_chapter_count": project.target_chapter_count,
                "target_word_count": project.target_word_count,
                "current_word_count": project.current_word_count,
                "style": project.style,
            },
            "setup_status": setup.status if setup else "missing",
            "outline_status": outline.status if outline else "missing",
            "outline_total_chapters": outline.total_chapters if outline else 0,
            "chapter_count": chapter_count,
        }
    )

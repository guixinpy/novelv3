"""项目状态工具与写入工具。"""
from __future__ import annotations

from datetime import UTC, datetime

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


@tool(
    registry=registry,
    name="update_outline",
    description=(
        "更新项目的大纲信息：总章节数、章节列表、情节线等。"
        "大纲不存在时会自动创建。只传需要更新的字段，不传的字段保持不变。"
    ),
    permission="write",
    parameters={
        "type": "object",
        "properties": {
            "total_chapters": {"type": "integer", "description": "计划总章节数"},
            "chapters": {
                "type": "array",
                "description": "章节列表，每项为 {\"index\": 1, \"title\": \"第1章\"}",
                "items": {"type": "object"},
            },
        },
    },
)
async def update_outline(ctx: ToolContext, total_chapters: int | None = None, chapters: list | None = None) -> ToolResult:
    outline = ctx.db.query(Outline).filter(Outline.project_id == ctx.project_id).first()
    if outline is None:
        outline = Outline(
            project_id=ctx.project_id,
            total_chapters=total_chapters or 0,
            chapters=chapters or [],
            status="generated",
        )
        ctx.db.add(outline)
    else:
        if total_chapters is not None:
            outline.total_chapters = total_chapters
        if chapters is not None:
            outline.chapters = chapters
        outline.status = "generated"
    ctx.db.commit()
    return ToolResult.ok({
        "total_chapters": outline.total_chapters,
        "status": outline.status,
    })


@tool(
    registry=registry,
    name="update_setup",
    description=(
        "更新项目的世界观设定（world_building）、角色列表（characters）、核心概念（core_concept）。"
        "传入的字段会合并到现有设定中，不会覆盖未传的字段。"
    ),
    permission="write",
    parameters={
        "type": "object",
        "properties": {
            "world_building": {"type": "object", "description": "世界观设定（背景、地理、社会、规则等）"},
            "characters": {"type": "array", "description": "角色列表", "items": {"type": "object"}},
            "core_concept": {"type": "object", "description": "核心概念（主题、钩子等）"},
        },
    },
)
async def update_setup(ctx: ToolContext, world_building: dict | None = None, characters: list | None = None, core_concept: dict | None = None) -> ToolResult:
    setup = ctx.db.query(Setup).filter(Setup.project_id == ctx.project_id).first()
    if setup is None:
        setup = Setup(
            project_id=ctx.project_id,
            world_building=world_building or {},
            characters=characters or [],
            core_concept=core_concept or {},
            status="generated",
        )
        ctx.db.add(setup)
    else:
        if world_building is not None:
            setup.world_building = world_building
        if characters is not None:
            setup.characters = characters
        if core_concept is not None:
            setup.core_concept = core_concept
        setup.status = "generated"
    ctx.db.commit()
    return ToolResult.ok({"status": setup.status})

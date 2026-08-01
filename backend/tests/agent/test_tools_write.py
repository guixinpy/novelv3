"""写入工具测试：write_chapter / revise_chapter / update_outline / update_setup。"""
from __future__ import annotations

import pytest

from app.agent.tooling import ToolContext
from app.models import ChapterContent, Outline, Project, Setup
from app.tools.chapters import write_chapter, revise_chapter, list_chapters, read_chapter
from app.tools.project import update_outline, update_setup, get_project_state


@pytest.fixture
def project(db_session):
    p = Project(name="测试项目", genre="悬疑", target_chapter_count=50)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def ctx(db_session, project):
    return ToolContext(project_id=project.id, session_id="s1", db=db_session)


@pytest.mark.asyncio
async def test_write_chapter_creates_new(ctx: ToolContext):
    """write_chapter 应创建新章节。"""
    result = await write_chapter(ctx, chapter_index=1, content="第一章正文内容", title="第一章 开始")
    assert not result.is_error
    data = result.data
    assert data["chapter_index"] == 1
    assert data["word_count"] == 7  # "第一章正文内容" = 7 chars
    assert data["status"] == "written"

    # 验证 DB 中有记录
    ch = ctx.db.query(ChapterContent).filter(
        ChapterContent.project_id == ctx.project_id,
        ChapterContent.chapter_index == 1,
    ).first()
    assert ch is not None
    assert ch.content == "第一章正文内容"
    assert ch.title == "第一章 开始"


@pytest.mark.asyncio
async def test_write_chapter_advances_project_status(ctx: ToolContext):
    """首章写入后项目应从 draft 进入 writing/content。"""
    project = ctx.db.query(Project).filter(Project.id == ctx.project_id).first()
    assert project.status in ("draft", "setup")

    result = await write_chapter(ctx, chapter_index=1, content="正文")
    assert not result.is_error

    project = ctx.db.query(Project).filter(Project.id == ctx.project_id).first()
    assert project.status == "writing"
    assert project.current_phase == "content"


@pytest.mark.asyncio
async def test_write_chapter_overwrites_existing(ctx: ToolContext):
    """write_chapter 应覆盖已存在的章节。"""
    ch = ChapterContent(
        project_id=ctx.project_id, chapter_index=1,
        title="旧标题", content="旧内容", word_count=3, status="generated",
    )
    ctx.db.add(ch)
    ctx.db.commit()

    result = await write_chapter(ctx, chapter_index=1, content="新正文", title="新标题")
    assert not result.is_error
    assert result.data["word_count"] == 3

    ch = ctx.db.query(ChapterContent).filter(
        ChapterContent.project_id == ctx.project_id,
        ChapterContent.chapter_index == 1,
    ).first()
    assert ch.content == "新正文"


@pytest.mark.asyncio
async def test_write_chapter_updates_project_word_count(ctx: ToolContext):
    """write_chapter 应更新项目的 current_word_count。"""
    await write_chapter(ctx, chapter_index=1, content="十二个字的内容在这里")
    project = ctx.db.query(Project).filter(Project.id == ctx.project_id).first()
    assert project.current_word_count == 10  # 10 Chinese chars


@pytest.mark.asyncio
async def test_write_chapter_invalid_index(ctx: ToolContext):
    """章节序号 < 1 应报错。"""
    result = await write_chapter(ctx, chapter_index=0, content="正文")
    assert result.is_error
    assert ">= 1" in result.error


@pytest.mark.asyncio
async def test_revise_chapter_updates_content(ctx: ToolContext):
    """revise_chapter 应修改已存在章节的内容。"""
    ch = ChapterContent(
        project_id=ctx.project_id, chapter_index=2,
        title="第二章", content="旧内容", word_count=3, status="generated",
    )
    ctx.db.add(ch)
    ctx.db.commit()

    result = await revise_chapter(ctx, chapter_index=2, new_content="修订后内容更长一些")
    assert not result.is_error
    assert result.data["word_count"] == 9

    ch = ctx.db.query(ChapterContent).filter(
        ChapterContent.project_id == ctx.project_id,
        ChapterContent.chapter_index == 2,
    ).first()
    assert ch.content == "修订后内容更长一些"


@pytest.mark.asyncio
async def test_revise_chapter_not_found(ctx: ToolContext):
    """不存在的章节应报错。"""
    result = await revise_chapter(ctx, chapter_index=99, new_content="正文")
    assert result.is_error
    assert "不存在" in result.error


@pytest.mark.asyncio
async def test_update_outline_creates(ctx: ToolContext):
    """update_outline 应创建新大纲。"""
    chapters = [{"index": i, "title": f"第{i}章"} for i in range(1, 11)]
    result = await update_outline(ctx, total_chapters=30, chapters=chapters)
    assert not result.is_error
    assert result.data["total_chapters"] == 30

    outline = ctx.db.query(Outline).filter(Outline.project_id == ctx.project_id).first()
    assert outline is not None
    assert outline.total_chapters == 30


@pytest.mark.asyncio
async def test_update_outline_updates_existing(ctx: ToolContext):
    """update_outline 应更新已有大纲。"""
    ol = Outline(project_id=ctx.project_id, total_chapters=10, status="generated")
    ctx.db.add(ol)
    ctx.db.commit()

    result = await update_outline(ctx, total_chapters=50)
    assert not result.is_error
    assert result.data["total_chapters"] == 50


@pytest.mark.asyncio
async def test_update_setup_creates(ctx: ToolContext):
    """update_setup 应创建新设定。"""
    wb = {"background": "测试世界"}
    result = await update_setup(ctx, world_building=wb, characters=[{"name": "测试角色"}])
    assert not result.is_error

    setup = ctx.db.query(Setup).filter(Setup.project_id == ctx.project_id).first()
    assert setup is not None
    assert setup.world_building["background"] == "测试世界"


@pytest.mark.asyncio
async def test_update_setup_merges(ctx: ToolContext):
    """update_setup 应与已有设定合并。"""
    setup = Setup(
        project_id=ctx.project_id,
        world_building={"background": "旧背景"},
        characters=[],
        status="generated",
    )
    ctx.db.add(setup)
    ctx.db.commit()

    result = await update_setup(ctx, world_building={"background": "新背景"})
    assert not result.is_error

    setup = ctx.db.query(Setup).filter(Setup.project_id == ctx.project_id).first()
    assert setup.world_building["background"] == "新背景"

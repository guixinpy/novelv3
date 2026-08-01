"""check_chapter_quality 工具测试。"""
from __future__ import annotations

import pytest

from app.agent.tooling import ToolContext
from app.models import ChapterContent, Project
from app.tools.chapters import check_chapter_quality


@pytest.fixture
def project(db_session):
    p = Project(name="测试", genre="悬疑")
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def ctx(db_session, project):
    return ToolContext(project_id=project.id, session_id="s1", db=db_session)


@pytest.mark.asyncio
async def test_quality_reports_no_issues(ctx: ToolContext):
    ch = ChapterContent(
        project_id=ctx.project_id, chapter_index=1,
        title="第一章",
        content="正常章节正文内容。" * 100,  # 800+ chars
        word_count=700, status="generated",
    )
    ctx.db.add(ch)
    ctx.db.commit()

    result = await check_chapter_quality(ctx, chapter_index=1)
    assert not result.is_error
    data = result.data
    assert len(data["issues"]) == 0
    assert data["quality"] == "pass"


@pytest.mark.asyncio
async def test_quality_reports_empty_title(ctx: ToolContext):
    ch = ChapterContent(
        project_id=ctx.project_id, chapter_index=1,
        title="", content="正文内容足够长。" * 100,
        word_count=700, status="generated",
    )
    ctx.db.add(ch)
    ctx.db.commit()

    result = await check_chapter_quality(ctx, chapter_index=1)
    assert not result.is_error
    issues = result.data["issues"]
    assert any(i["type"] == "missing_title" for i in issues)
    assert result.data["quality"] == "needs_review"


@pytest.mark.asyncio
async def test_quality_reports_nonexistent_chapter(ctx: ToolContext):
    result = await check_chapter_quality(ctx, chapter_index=99)
    assert result.is_error
    assert "不存在" in result.error


# ── T3 R3: check_quality_trend 终局核对 ──


@pytest.mark.asyncio
async def test_quality_trend_endgame_mode_near_arc_end(ctx: ToolContext):
    from app.models import LongformMemory
    from app.tools.chapters import check_quality_trend
    from app.tools.memory import plan_arc, track_plotline

    await plan_arc(
        ctx, action="define", title="第一卷",
        summary="雾城谜案", start_chapter=1, end_chapter=10,
        must_resolve=["旧牌"],
    )
    # 已写 8 章，最新章 = 8 → 剩余 2 章 ≤ 5
    for i in range(1, 9):
        ctx.db.add(ChapterContent(
            project_id=ctx.project_id, chapter_index=i,
            title=f"第{i}章", content="正文内容。" * 100,
            word_count=500, status="generated",
        ))
    await track_plotline(ctx, action="open", title="旧牌", chapter_index=1)

    result = await check_quality_trend(ctx, window=10)
    assert not result.is_error
    data = result.data
    assert data["endgame_mode"] is True
    assert "旧牌" in " ".join(data["must_resolve_open"])
    assert "回收" in data["endgame_advice"]


@pytest.mark.asyncio
async def test_quality_trend_no_endgame_far_from_end(ctx: ToolContext):
    from app.tools.chapters import check_quality_trend
    from app.tools.memory import plan_arc

    await plan_arc(
        ctx, action="define", title="第二卷",
        summary="南洋", start_chapter=1, end_chapter=10,
        must_resolve=["旧牌"],
    )
    # 最新章 = 3 → 剩余 7 章 > 5
    for i in range(1, 4):
        ctx.db.add(ChapterContent(
            project_id=ctx.project_id, chapter_index=i,
            title=f"第{i}章", content="正文内容。" * 100,
            word_count=500, status="generated",
        ))
    ctx.db.commit()

    result = await check_quality_trend(ctx, window=10)
    assert not result.is_error
    assert result.data["endgame_mode"] is False


# ── T4 R1/R2: check_chapter_format 工具 ──


@pytest.mark.asyncio
async def test_check_chapter_format_reports_bad_text(ctx: ToolContext):
    from app.tools.chapters import check_chapter_format

    ch = ChapterContent(
        project_id=ctx.project_id, chapter_index=1,
        title="第一章", content="他睡不着,又坐起来。\n同**道理**一般。",
        word_count=100, status="generated",
    )
    ctx.db.add(ch)
    ctx.db.commit()

    result = await check_chapter_format(ctx, chapter_index=1)
    assert not result.is_error
    data = result.data
    assert data["quality"] == "fail"
    types = {i["type"] for i in data["issues"]}
    assert "half_width_punct" in types
    assert "markdown_bold" in types


@pytest.mark.asyncio
async def test_check_chapter_format_passes_clean_text(ctx: ToolContext):
    from app.tools.chapters import check_chapter_format

    ch = ChapterContent(
        project_id=ctx.project_id, chapter_index=1,
        title="第一章", content="他睡不着，又坐起来。\n“明天就走。”她说。",
        word_count=100, status="generated",
    )
    ctx.db.add(ch)
    ctx.db.commit()

    result = await check_chapter_format(ctx, chapter_index=1)
    assert not result.is_error
    assert result.data["quality"] == "pass"
    assert result.data["issues"] == []


@pytest.mark.asyncio
async def test_check_chapter_format_missing_chapter(ctx: ToolContext):
    from app.tools.chapters import check_chapter_format

    result = await check_chapter_format(ctx, chapter_index=99)
    assert result.is_error
    assert "不存在" in result.error

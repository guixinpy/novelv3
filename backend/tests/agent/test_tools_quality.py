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

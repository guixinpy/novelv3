"""回合级项目状态快照测试（T6 R1）。"""
from __future__ import annotations

import pytest

from app.agent.tooling import ToolContext
from app.core.project_snapshot import build_project_snapshot
from app.models import ChapterContent, LongformMemory, Project, Setup


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
async def test_snapshot_contains_writing_context(ctx: ToolContext):
    from app.tools.memory import plan_arc, track_plotline

    # 3 章
    for i in range(1, 4):
        ctx.db.add(ChapterContent(
            project_id=ctx.project_id, chapter_index=i,
            title=f"第{i}章·{['面馆','仓库','码头'][i-1]}",
            content="正文内容。" * 100, word_count=500, status="generated",
        ))
    # 设定：角色与地点（事实表来源）
    ctx.db.add(Setup(
        project_id=ctx.project_id,
        characters=[{"name": "程砚秋"}, {"name": "苏晚晴"}],
        world_building={"locations": ["雾城", "静水庵"]},
        status="active",
    ))
    # 活跃弧线 + 终局
    await plan_arc(ctx, action="define", title="第一卷",
                   summary="雾城谜案", start_chapter=1, end_chapter=50,
                   must_resolve=["林舟案"])
    # 开放 plotline
    await track_plotline(ctx, action="open", title="林舟案", chapter_index=1)
    ctx.db.commit()

    snapshot = build_project_snapshot(ctx.db, ctx.project_id)
    assert snapshot is not None
    assert "3 章" in snapshot
    assert "面馆" in snapshot and "仓库" in snapshot and "码头" in snapshot
    assert "第一卷" in snapshot
    assert "1 条开放伏笔" in snapshot
    # 事实表：角色 + 地点 + 格式规范
    assert "程砚秋" in snapshot
    assert "苏晚晴" in snapshot
    assert "雾城" in snapshot
    assert "全角引号" in snapshot


def test_snapshot_none_without_project(db_session):
    assert build_project_snapshot(db_session, "no-such-project") is None

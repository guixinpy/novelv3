"""回合级项目状态快照测试（T6 R1）。"""
from __future__ import annotations

import pytest

from app.models import ChapterContent, Project, Setup
from core.tools.base import ToolContext
from domain.memory.project_snapshot import build_project_snapshot


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
    from domain.memory.memory_service import plan_arc, track_plotline

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
    plan_arc(ctx.db, ctx.project_id, action="define", title="第一卷",
                   summary="雾城谜案", start_chapter=1, end_chapter=50,
                   must_resolve=["林舟案"])
    # 开放 plotline
    track_plotline(ctx.db, ctx.project_id, action="open", title="林舟案", chapter_index=1)
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


def test_snapshot_includes_experience_section(db_session, project):
    """写作经验段（09 定稿）：最近 + 高信任，标记仅供参考。"""
    from domain.memory.writing_experience import apply_experiences

    apply_experiences(
        db_session, project.id, 1, "节奏",
        [{"key": "开篇节奏", "action": "new", "text": "开篇冲突前置有效。"}],
    )
    snapshot = build_project_snapshot(db_session, project.id)
    assert snapshot is not None
    assert "写作经验" in snapshot
    assert "仅供参考" in snapshot
    assert "开篇冲突前置" in snapshot  # 注入的是 text（summary），非 key


def test_snapshot_experience_disabled(db_session, project):
    """include_experience=False 关闭经验段（config 开关）。"""
    from app.models import ChapterContent
    from domain.memory.writing_experience import apply_experiences

    db_session.add(ChapterContent(
        project_id=project.id, chapter_index=1,
        title="第1章", content="正文。" * 50, word_count=150, status="generated",
    ))
    apply_experiences(
        db_session, project.id, 1, "节奏",
        [{"key": "开篇节奏", "action": "new", "text": "开篇冲突前置有效。"}],
    )
    snapshot = build_project_snapshot(db_session, project.id, include_experience=False)
    assert snapshot is not None
    assert "写作经验" not in snapshot
    assert "已写 1 章" in snapshot


# ── 伏笔账本快照钩子（09 定稿：注入优先超期清单）──


def test_snapshot_plotline_due_list(db_session, project):
    """快照注入超期/临期具体清单（≤3 条，超期优先）；未到期不虚报。"""
    from domain.memory.memory_service import track_plotline

    for i in range(1, 61):
        db_session.add(ChapterContent(
            project_id=project.id, chapter_index=i, title=f"Ch{i}",
            content="正文。" * 50, word_count=150, status="generated",
        ))
    # 超期（expected=50，当前 60）+ 临期（expected=62）+ 未到期（expected=100）
    track_plotline(db_session, project.id, "open", title="超期线", chapter_index=10, expected_resolve_chapter=50)
    track_plotline(db_session, project.id, "open", title="临期线", chapter_index=30, expected_resolve_chapter=62)
    track_plotline(db_session, project.id, "open", title="未到期线", chapter_index=40, expected_resolve_chapter=100)
    db_session.commit()

    snapshot = build_project_snapshot(db_session, project.id)
    assert snapshot is not None
    assert "3 条开放伏笔" in snapshot
    assert "到期伏笔" in snapshot
    assert "超期线" in snapshot and "已超预计 10 章" in snapshot
    assert "临期线" in snapshot and "预计 Ch62 收" in snapshot
    assert "未到期线" not in snapshot


def test_snapshot_plotline_no_false_due(db_session, project):
    """无超期/临期时快照保持计数，不虚报到期清单。"""
    from domain.memory.memory_service import track_plotline

    db_session.add(ChapterContent(
        project_id=project.id, chapter_index=1, title="Ch1",
        content="正文。" * 50, word_count=150, status="generated",
    ))
    track_plotline(db_session, project.id, "open", title="新线", chapter_index=1, expected_resolve_chapter=100)
    db_session.commit()

    snapshot = build_project_snapshot(db_session, project.id)
    assert snapshot is not None
    assert "1 条开放伏笔" in snapshot
    assert "到期伏笔" not in snapshot

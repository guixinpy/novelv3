"""长期记忆工具测试。"""
from __future__ import annotations

import pytest

from app.agent.tooling import ToolContext
from app.models import LongformMemory, Project
from app.tools.memory import query_memory, track_plotline


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
async def test_track_plotline_open(ctx: ToolContext):
    result = await track_plotline(ctx, action="open", title="林舟父亲之谜", summary="林舟父亲在灯塔火灾中失踪", chapter_index=1)
    assert not result.is_error
    assert result.data["action"] == "opened"
    assert result.data["status"] == "open"

    # Verify DB
    mem = ctx.db.query(LongformMemory).filter(
        LongformMemory.project_id == ctx.project_id,
        LongformMemory.scope_key == "林舟父亲之谜",
    ).first()
    assert mem is not None
    assert mem.status == "open"


@pytest.mark.asyncio
async def test_track_plotline_close(ctx: ToolContext):
    mem = LongformMemory(
        project_id=ctx.project_id, memory_type="plotline",
        scope_key="测试线", title="测试线", status="open",
    )
    ctx.db.add(mem)
    ctx.db.commit()

    result = await track_plotline(ctx, action="close", title="测试线", chapter_index=10)
    assert not result.is_error
    assert result.data["action"] == "closed"

    ctx.db.refresh(mem)
    assert mem.status == "closed"
    assert mem.end_chapter_index == 10


@pytest.mark.asyncio
async def test_track_plotline_query(ctx: ToolContext):
    mems = [
        LongformMemory(project_id=ctx.project_id, memory_type="plotline", scope_key="线A", title="线A", status="open"),
        LongformMemory(project_id=ctx.project_id, memory_type="plotline", scope_key="线B", title="线B", status="closed"),
    ]
    for m in mems:
        ctx.db.add(m)
    ctx.db.commit()

    result = await track_plotline(ctx, action="query")
    assert not result.is_error
    assert len(result.data["plotlines"]) == 2


@pytest.mark.asyncio
async def test_query_memory_by_type(ctx: ToolContext):
    mem = LongformMemory(
        project_id=ctx.project_id, memory_type="entity_state",
        scope_key="林舟", summary="林舟在第5章到达档案局",
        status="active",
    )
    ctx.db.add(mem)
    ctx.db.commit()

    result = await query_memory(ctx, memory_type="entity_state", keyword="林舟")
    assert not result.is_error
    assert len(result.data["memories"]) == 1
    assert result.data["memories"][0]["key"] == "林舟"

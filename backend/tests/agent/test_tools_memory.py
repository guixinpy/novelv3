"""长期记忆工具测试。"""
from __future__ import annotations

import pytest

from app.agent.tooling import ToolContext
from app.models import LongformMemory, Project
from app.tools.memory import plan_arc, query_memory, track_plotline


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
async def test_track_plotline_reopen_after_close_avoids_unique_conflict(ctx: ToolContext):
    """闭环后再次 open 同标题应复用记录，不触发唯一约束（200 章实验暴露）。"""
    opened = await track_plotline(ctx, action="open", title="线X", summary="旧摘要", chapter_index=1)
    assert not opened.is_error
    closed = await track_plotline(ctx, action="close", title="线X", chapter_index=5)
    assert not closed.is_error
    reopened = await track_plotline(ctx, action="open", title="线X", summary="新摘要", chapter_index=6)
    assert not reopened.is_error
    assert reopened.data["action"] == "reopened"

    rows = (
        ctx.db.query(LongformMemory)
        .filter(
            LongformMemory.memory_type == "plotline",
            LongformMemory.scope_key == "线X",
        )
        .all()
    )
    assert len(rows) == 1
    assert rows[0].status == "open"


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
async def test_plan_arc_define_upsert_same_title(ctx: ToolContext):
    """重复 define 同标题弧线应更新而非插入，避免唯一约束冲突。"""
    first = await plan_arc(
        ctx, action="define", title="第一弧",
        summary="原概要", start_chapter=1, end_chapter=10,
    )
    assert not first.is_error
    second = await plan_arc(
        ctx, action="define", title="第一弧",
        summary="新概要", start_chapter=1, end_chapter=12,
    )
    assert not second.is_error

    arcs = (
        ctx.db.query(LongformMemory)
        .filter(
            LongformMemory.memory_type == "story_arc",
            LongformMemory.scope_key == "第一弧",
        )
        .all()
    )
    assert len(arcs) == 1
    assert arcs[0].end_chapter_index == 12
    assert arcs[0].status == "active"


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


@pytest.mark.asyncio
async def test_query_memory_author_explicit_ranked_first(ctx: ToolContext):
    """T6 R3：人物卡优先级——author_explicit 排在 agent_inferred 前（即使更新更早）。"""
    old_explicit = LongformMemory(
        project_id=ctx.project_id, memory_type="entity_state",
        scope_key="程砚秋", title="程砚秋",
        summary="主角：雾城查案人，目标是查明林舟案",
        status="active",
        memory_metadata={"provenance": "author_explicit"},
    )
    ctx.db.add(old_explicit)
    new_inferred = LongformMemory(
        project_id=ctx.project_id, memory_type="entity_state",
        scope_key="苏晚晴", title="苏晚晴",
        summary="出现在第 5 章",
        status="active",
        memory_metadata={"provenance": "agent_inferred"},
    )
    ctx.db.add(new_inferred)
    ctx.db.commit()
    # 让 inferred 的 updated_at 更新（确保按时间排序时它在前，验证优先级排序生效）
    from datetime import UTC, datetime
    new_inferred.updated_at = datetime.now(UTC)
    ctx.db.commit()

    result = await query_memory(ctx, memory_type="entity_state")
    assert not result.is_error
    keys = [m["key"] for m in result.data["memories"]]
    assert keys.index("程砚秋") < keys.index("苏晚晴")


# ── T2 R3: 情节线登记与检索规范 ──


@pytest.mark.asyncio
async def test_track_plotline_rejects_overlong_title(ctx: ToolContext):
    long_title = "线" * 41
    result = await track_plotline(ctx, action="open", title=long_title, chapter_index=1)
    assert result.is_error
    assert "40" in result.error
    assert "弧名-目标" in result.error


@pytest.mark.asyncio
async def test_track_plotline_rejects_title_with_chapter_number(ctx: ToolContext):
    """200 章实验暴露：标题带「第139章线（第二部·第二卷…）」导致检索必然失败。"""
    bad_title = "程砚秋第139章线（第二部·第二卷·活水源头主线第十一章）"
    result = await track_plotline(ctx, action="open", title=bad_title, chapter_index=139)
    assert result.is_error
    assert "章节" in result.error


@pytest.mark.asyncio
async def test_track_plotline_query_prefix_match(ctx: ToolContext):
    mems = [
        LongformMemory(project_id=ctx.project_id, memory_type="plotline", scope_key="林舟父亲之谜", title="林舟父亲之谜", status="open"),
        LongformMemory(project_id=ctx.project_id, memory_type="plotline", scope_key="姚家旧账", title="姚家旧账", status="open"),
    ]
    for m in mems:
        ctx.db.add(m)
    ctx.db.commit()

    result = await track_plotline(ctx, action="query", title="林舟")
    assert not result.is_error
    assert len(result.data["plotlines"]) == 1
    assert result.data["plotlines"][0]["title"] == "林舟父亲之谜"


@pytest.mark.asyncio
async def test_track_plotline_query_contains_fallback(ctx: ToolContext):
    mems = [
        LongformMemory(project_id=ctx.project_id, memory_type="plotline", scope_key="码头来的沈默", title="码头来的沈默", status="open"),
    ]
    for m in mems:
        ctx.db.add(m)
    ctx.db.commit()

    result = await track_plotline(ctx, action="query", title="沈默")
    assert not result.is_error
    assert len(result.data["plotlines"]) == 1
    assert result.data["plotlines"][0]["title"] == "码头来的沈默"


@pytest.mark.asyncio
async def test_track_plotline_query_no_match_falls_back_to_recent(ctx: ToolContext):
    m = LongformMemory(project_id=ctx.project_id, memory_type="plotline", scope_key="最近开放线", title="最近开放线", status="open")
    ctx.db.add(m)
    ctx.db.commit()

    result = await track_plotline(ctx, action="query", title="完全不存在的东西")
    assert not result.is_error
    assert result.data.get("fallback") is True
    assert "fallback_note" in result.data
    assert result.data["plotlines"][0]["title"] == "最近开放线"


# ── T2 R2: get_or_create_longform_memory 统一 upsert 封装 ──


@pytest.mark.asyncio
async def test_get_or_create_creates_new(ctx: ToolContext):
    from domain.memory.longform_memory import get_or_create_longform_memory

    mem = get_or_create_longform_memory(
        ctx.db, ctx.project_id, "plotline", "新线",
        defaults={"title": "新线", "status": "open"},
    )
    ctx.db.commit()
    assert mem.id is not None
    assert mem.status == "open"

    rows = (
        ctx.db.query(LongformMemory)
        .filter(LongformMemory.scope_key == "新线")
        .all()
    )
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_get_or_create_updates_existing(ctx: ToolContext):
    from domain.memory.longform_memory import get_or_create_longform_memory

    mem = get_or_create_longform_memory(
        ctx.db, ctx.project_id, "plotline", "既有线",
        defaults={"title": "既有线", "status": "open"},
    )
    ctx.db.commit()

    same = get_or_create_longform_memory(
        ctx.db, ctx.project_id, "plotline", "既有线",
        updates={"status": "closed", "end_chapter_index": 9},
    )
    ctx.db.commit()
    assert same.id == mem.id
    assert same.status == "closed"
    assert same.end_chapter_index == 9

    rows = (
        ctx.db.query(LongformMemory)
        .filter(LongformMemory.scope_key == "既有线")
        .all()
    )
    assert len(rows) == 1


# ── T3 R1: plan_arc define 终局约束 ──


@pytest.mark.asyncio
async def test_plan_arc_define_endgame_metadata(ctx: ToolContext):
    result = await plan_arc(
        ctx, action="define", title="第一卷",
        summary="雾城谜案", start_chapter=1, end_chapter=50,
        must_resolve=["林舟案", "姚家旧账"],
    )
    assert not result.is_error

    arc = (
        ctx.db.query(LongformMemory)
        .filter(
            LongformMemory.memory_type == "story_arc",
            LongformMemory.scope_key == "第一卷",
        )
        .first()
    )
    metadata = arc.memory_metadata or {}
    assert metadata["endgame"] == {
        "resolve_before": 50,
        "must_resolve": ["林舟案", "姚家旧账"],
    }
    # 合并写入：provenance/source 必须保留
    assert metadata["provenance"] == "author_explicit"
    assert metadata["source"] == "plan_arc"


@pytest.mark.asyncio
async def test_plan_arc_define_no_endgame_without_must_resolve(ctx: ToolContext):
    result = await plan_arc(
        ctx, action="define", title="第二卷",
        summary="南洋", start_chapter=51, end_chapter=100,
    )
    assert not result.is_error

    arc = (
        ctx.db.query(LongformMemory)
        .filter(
            LongformMemory.memory_type == "story_arc",
            LongformMemory.scope_key == "第二卷",
        )
        .first()
    )
    assert "endgame" not in (arc.memory_metadata or {})


# ── T3 R2: plan_arc progress 终局状态 ──


@pytest.mark.asyncio
async def test_plan_arc_progress_endgame_warning_near_end(ctx: ToolContext):
    from app.models import ChapterContent

    await plan_arc(
        ctx, action="define", title="第一卷",
        summary="雾城谜案", start_chapter=1, end_chapter=5,
        must_resolve=["林舟案"],
    )
    # 已写 1 章，最新章 = 1 → 剩余 4 章 ≤ 5
    ctx.db.add(ChapterContent(
        project_id=ctx.project_id, chapter_index=1,
        title="第一章", content="正文" * 100, word_count=200, status="generated",
    ))
    # 开放 plotline 对应 must_resolve 项 → 未回收
    await track_plotline(ctx, action="open", title="林舟案", chapter_index=1)

    result = await plan_arc(ctx, action="progress")
    assert not result.is_error
    data = result.data
    assert data["endgame_remaining"] == 4
    assert "林舟案" in data["must_resolve_open"]
    assert "暂缓开新线" in data["endgame_warning"]


@pytest.mark.asyncio
async def test_plan_arc_progress_endgame_resolved(ctx: ToolContext):
    from app.models import ChapterContent

    await plan_arc(
        ctx, action="define", title="第一卷",
        summary="雾城谜案", start_chapter=1, end_chapter=5,
        must_resolve=["林舟案"],
    )
    ctx.db.add(ChapterContent(
        project_id=ctx.project_id, chapter_index=1,
        title="第一章", content="正文" * 100, word_count=200, status="generated",
    ))
    # 伏笔已闭环 → 视为已回收
    await track_plotline(ctx, action="open", title="林舟案", chapter_index=1)
    await track_plotline(ctx, action="close", title="林舟案", chapter_index=2)

    result = await plan_arc(ctx, action="progress")
    assert not result.is_error
    data = result.data
    assert data["must_resolve_open"] == []
    assert "endgame_warning" not in data


# ── T3 R4: 伏笔回收期限（stale） ──


@pytest.mark.asyncio
async def test_track_plotline_query_stale_warning(ctx: ToolContext):
    from app.models import ChapterContent

    # 最新章 = 40；老线起始于第 1 章 → 开放 39 章 > 30 → stale
    await track_plotline(ctx, action="open", title="老线", chapter_index=1)
    await track_plotline(ctx, action="open", title="新线", chapter_index=38)
    ctx.db.add(ChapterContent(
        project_id=ctx.project_id, chapter_index=40,
        title="第40章", content="正文" * 100, word_count=200, status="generated",
    ))
    ctx.db.commit()

    result = await track_plotline(ctx, action="query")
    assert not result.is_error
    data = result.data
    stale_titles = [
        p["title"] for p in data["plotlines"]
        if p.get("stale")
    ]
    assert stale_titles == ["老线"]
    assert "老线" in data["stale_warning"]
    assert "30" in data["stale_warning"]


# ── 弧线结构（内容无关）：relation_to_previous / 收束约束可见性 ──


@pytest.mark.asyncio
async def test_plan_arc_relation_recorded(ctx: ToolContext):
    result = await plan_arc(
        ctx, action="define", title="第二卷",
        summary="新舞台", start_chapter=11, end_chapter=20,
        relation_to_previous="承接第一卷的林舟案余波，程砚秋的关系网延续",
    )
    assert not result.is_error
    assert result.data["relation_to_previous"] == "承接第一卷的林舟案余波，程砚秋的关系网延续"

    arc = (
        ctx.db.query(LongformMemory)
        .filter(LongformMemory.memory_type == "story_arc", LongformMemory.scope_key == "第二卷")
        .first()
    )
    assert (arc.memory_metadata or {}).get("arc_relation") == "承接第一卷的林舟案余波，程砚秋的关系网延续"


@pytest.mark.asyncio
async def test_plan_arc_continuation_hint_without_relation(ctx: ToolContext):
    """接续上一弧线启动且未声明 relation → 提示（不拒绝，弧线照常创建）。"""
    first = await plan_arc(ctx, action="define", title="第一卷", summary="开篇", start_chapter=1, end_chapter=10)
    assert not first.is_error
    second = await plan_arc(ctx, action="define", title="第二卷", summary="续篇", start_chapter=11, end_chapter=20)
    assert not second.is_error
    assert "continuation_hint" in second.data
    assert "relation_to_previous" in second.data["continuation_hint"]


@pytest.mark.asyncio
async def test_plan_arc_no_continuation_hint_for_first_arc(ctx: ToolContext):
    result = await plan_arc(ctx, action="define", title="第一卷", summary="开篇", start_chapter=1, end_chapter=10)
    assert not result.is_error
    assert "continuation_hint" not in result.data


@pytest.mark.asyncio
async def test_plan_arc_progress_hints_missing_endgame(ctx: ToolContext):
    """活跃弧线未设收束约束（无 must_resolve）→ progress 提示（不阻塞）。"""
    await plan_arc(ctx, action="define", title="第一卷", summary="开篇", start_chapter=1, end_chapter=10)
    result = await plan_arc(ctx, action="progress")
    assert not result.is_error
    assert "endgame_hint" in result.data
    assert "must_resolve" in result.data["endgame_hint"]

"""记忆服务通道配额测试（openhuman 多通道召回配额，特化：混合查询按通道硬截断）。

guideline 原为提示语（模型自觉遵守），现为代码强制。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.models import ChapterContent, LongformMemory, Project
from domain.memory.memory_service import plotline_apply_updates, plotline_due_items, query_memory, track_plotline


def _seed(db, project_id: str, memory_type: str, count: int, title_prefix: str) -> None:
    for i in range(count):
        db.add(
            LongformMemory(
                project_id=project_id,
                memory_type=memory_type,
                scope_key=f"{title_prefix}-{i}",
                title=f"{title_prefix}{i}",
                summary=f"摘要 {title_prefix}{i}",
                status="current",
                updated_at=datetime.now(UTC) - timedelta(minutes=i),
            )
        )
    db.commit()


def test_mixed_query_caps_each_channel(db_session):
    """混合查询（all）：每通道硬上限（arc_summary≤3 / plotline≤5 / 其他≤3），总数≤limit。"""
    project = Project(name="测试项目")
    db_session.add(project)
    db_session.commit()
    _seed(db_session, project.id, "plotline", 4, "伏笔")
    _seed(db_session, project.id, "arc_summary", 4, "弧线")
    _seed(db_session, project.id, "chapter", 4, "章记忆")

    result = query_memory(db_session, project.id, memory_type="all", limit=10)
    memories = result["memories"]
    assert len(memories) <= 10
    by_type: dict[str, int] = {}
    for m in memories:
        by_type[m["type"]] = by_type.get(m["type"], 0) + 1
    assert by_type.get("plotline", 0) <= 5
    assert by_type.get("arc_summary", 0) <= 3
    assert by_type.get("chapter", 0) <= 3
    # 服务端强制配额在返回中可见
    assert result["injection_limit"]["channel_limits"] == {"arc_summary": 3, "plotline": 5}
    assert "已由服务端强制" in result["injection_limit"]["guideline"]


def test_mixed_query_respects_global_limit(db_session):
    """混合查询：总数仍受 limit 约束。"""
    project = Project(name="测试项目2")
    db_session.add(project)
    db_session.commit()
    _seed(db_session, project.id, "plotline", 6, "伏笔")
    _seed(db_session, project.id, "arc_summary", 6, "弧线")

    result = query_memory(db_session, project.id, memory_type="all", limit=4)
    assert len(result["memories"]) <= 4


def test_single_type_query_unaffected_by_channel_limit(db_session):
    """单类型查询：配额不适用（尊重 limit），行为与旧版一致。"""
    project = Project(name="测试项目3")
    db_session.add(project)
    db_session.commit()
    _seed(db_session, project.id, "plotline", 6, "伏笔")

    result = query_memory(db_session, project.id, memory_type="plotline", limit=6)
    assert len(result["memories"]) == 6
    assert result["injection_limit"]["channel_limits"] is None


def test_mixed_query_low_frequency_channel_has_quota(db_session):
    """code-review #7：每通道独立预取——高频通道 flood 时低频通道仍有配额代表。"""
    project = Project(name="测试项目5")
    db_session.add(project)
    db_session.commit()
    _seed(db_session, project.id, "plotline", 15, "伏笔")
    _seed(db_session, project.id, "arc_summary", 2, "弧线")

    result = query_memory(db_session, project.id, memory_type="all", limit=10)
    memories = result["memories"]
    by_type: dict[str, int] = {}
    for m in memories:
        by_type[m["type"]] = by_type.get(m["type"], 0) + 1
    # 低频通道（arc_summary）在 15 条 plotline flood 下仍有代表（≤3 配额内）
    assert by_type.get("arc_summary", 0) >= 1
    assert by_type.get("plotline", 0) <= 5


def test_mixed_query_round_robin_at_default_limit(db_session):
    """code-review 三轮 #5：默认 limit=5 时轮询分配——低频通道不被高频通道耗尽。"""
    project = Project(name="测试项目7")
    db_session.add(project)
    db_session.commit()
    _seed(db_session, project.id, "plotline", 15, "伏笔")
    _seed(db_session, project.id, "arc_summary", 2, "弧线")
    _seed(db_session, project.id, "chapter", 10, "章记忆")

    result = query_memory(db_session, project.id, memory_type="all", limit=5)
    memories = result["memories"]
    assert len(memories) == 5
    by_type: dict[str, int] = {}
    for m in memories:
        by_type[m["type"]] = by_type.get(m["type"], 0) + 1
    # 每通道都有代表（轮询保底），且不超过各自配额
    assert by_type.get("arc_summary", 0) >= 1
    assert by_type.get("chapter", 0) >= 1
    assert by_type.get("plotline", 0) <= 5


def test_archived_experience_filtered_from_query(db_session):
    """code-review #6：archived 经验不进记忆查询（与快照注入语义一致）。"""
    from app.models import LongformMemory

    project = Project(name="测试项目6")
    db_session.add(project)
    db_session.commit()
    db_session.add(LongformMemory(
        project_id=project.id,
        memory_type="writing_experience",
        scope_key="已归档经验",
        title="[节奏] 已归档经验",
        summary="旧指导文本。",
        status="archived",
        memory_metadata={"category": "节奏", "trust_score": 0},
    ))
    db_session.add(LongformMemory(
        project_id=project.id,
        memory_type="writing_experience",
        scope_key="活跃经验",
        title="[节奏] 活跃经验",
        summary="现行指导。",
        status="current",
        memory_metadata={"category": "节奏", "trust_score": 2},
    ))
    db_session.commit()
    result = query_memory(db_session, project.id, memory_type="all", limit=10)
    keys = [m["key"] for m in result["memories"]]
    assert "活跃经验" in keys
    assert "已归档经验" not in keys


async def test_aggregate_arc_summary_llm_cascade(db_session):
    """B4（openhuman 封箱聚合）：弧线完成后的 LLM 内容级联摘要。

    覆盖标题清单版 arc_summary；幂等（aggregated 标记跳过）；fail-open（无章节跳过）。
    """
    from app.models import ChapterContent, LongformMemory
    from domain.memory.memory_service import aggregate_arc_summary, aggregate_pending_arc_summaries, plan_arc
    from tests.core.conftest import ScriptedProvider

    project = Project(name="聚合测试")
    db_session.add(project)
    db_session.commit()
    # 弧线 + 章节
    plan_arc(db_session, project.id, action="define", title="第一卷", summary="雾城谜案",
             start_chapter=1, end_chapter=10)
    for i in range(1, 4):
        db_session.add(ChapterContent(
            project_id=project.id, chapter_index=i,
            title=f"第{i}章", content=f"林舟在雾城调查第{i}章内容。" * 30,
            word_count=300, status="generated",
        ))
    # 弧线完成（define 新弧线触发旧弧线 consolidation）
    plan_arc(db_session, project.id, action="define", title="第二卷", summary="码头风云",
             start_chapter=11, end_chapter=20)
    arc = (
        db_session.query(LongformMemory)
        .filter(LongformMemory.project_id == project.id, LongformMemory.memory_type == "story_arc")
        .first()
    )
    assert arc.status == "completed"

    # LLM 聚合
    script = ScriptedProvider([{"content": "第一卷内容级联摘要：林舟在雾城揭开谜案，苏晚晴身世浮现。"}])
    result = await aggregate_arc_summary(db_session, project.id, arc, provider=script)
    assert result["status"] == "aggregated"
    arc_summary = (
        db_session.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project.id,
            LongformMemory.memory_type == "arc_summary",
        )
        .first()
    )
    assert "内容级联摘要" in arc_summary.summary
    assert (arc_summary.memory_metadata or {}).get("aggregated") is True

    # 幂等：再次聚合 skipped（不重复 LLM 调用）
    script2 = ScriptedProvider([{"content": "不应被调用"}])
    result2 = await aggregate_arc_summary(db_session, project.id, arc, provider=script2)
    assert result2["status"] == "skipped"
    assert script2.script_remaining() == 1  # provider 未被消费

    # 批量聚合入口：已聚合 → 全部 skipped
    results = await aggregate_pending_arc_summaries(db_session, project.id, provider=script2)
    assert all(r["status"] == "skipped" for r in results)


async def test_aggregate_arc_summary_fail_open(db_session):
    """B4 fail-open：无章节的弧线跳过；provider 失败保持原标题清单版。"""
    from app.models import LongformMemory
    from domain.memory.memory_service import aggregate_arc_summary, plan_arc
    from tests.core.conftest import ScriptedProvider

    project = Project(name="聚合失败测试")
    db_session.add(project)
    db_session.commit()
    plan_arc(db_session, project.id, action="define", title="空卷", summary="无章节",
             start_chapter=1, end_chapter=10)
    plan_arc(db_session, project.id, action="define", title="下一卷", summary="x",
             start_chapter=11, end_chapter=20)
    arc = (
        db_session.query(LongformMemory)
        .filter(LongformMemory.project_id == project.id, LongformMemory.memory_type == "story_arc")
        .first()
    )
    # 无章节 → 跳过（不调用 LLM）
    script = ScriptedProvider([])
    result = await aggregate_arc_summary(db_session, project.id, arc, provider=script)
    assert result["status"] == "skipped"
    assert result["reason"] == "no_chapters"


def test_introspect_log_filtered_from_query(db_session):
    """code-review #4：introspect_log 内部标记行不进记忆查询（不挤占通道配额）。"""
    from app.models import LongformMemory

    project = Project(name="测试项目4")
    db_session.add(project)
    db_session.commit()
    _seed(db_session, project.id, "plotline", 2, "伏笔")
    # 自省标记行（title/summary 空）
    db_session.add(LongformMemory(
        project_id=project.id,
        memory_type="introspect_log",
        scope_key="chapter:1",
        title="",
        summary="",
        start_chapter_index=1,
        status="done",
    ))
    db_session.commit()
    result = query_memory(db_session, project.id, memory_type="all", limit=10)
    assert all(m["type"] != "introspect_log" for m in result["memories"])
    assert len(result["memories"]) == 2


# ── 伏笔账本（09 定稿独立后续项）──


def _make_project(db) -> Project:
    p = Project(name="伏笔账本")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _plotline(db, project_id, title):
    return (
        db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == "plotline",
            LongformMemory.scope_key == title,
        )
        .first()
    )


def test_plotline_apply_updates_open_close_postpone(db_session):
    """账本应用：open 新建（含 expected）、close 闭合（含 payoff + 结束章）、
    reopen（closed → open）+ postpone 更新 expected。"""
    project = _make_project(db_session)

    # open 新建
    applied = plotline_apply_updates(
        db_session, project.id, 1,
        [{"action": "open", "title": "黑市线", "summary": "黑市背后的势力", "expected_resolve_chapter": 80}],
    )
    assert applied["open"] == 1
    m = _plotline(db_session, project.id, "黑市线")
    assert m is not None and m.status == "open"
    assert m.start_chapter_index == 1
    assert (m.memory_metadata or {})["expected_resolve_chapter"] == 80
    assert (m.memory_metadata or {})["source"] == "introspect"

    # close 含 payoff
    applied = plotline_apply_updates(
        db_session, project.id, 76,
        [{"action": "close", "title": "黑市线", "payoff": "第 76 章揭晓幕后是程砚秋"}],
    )
    assert applied["close"] == 1
    m = _plotline(db_session, project.id, "黑市线")
    assert m.status == "closed"
    assert m.end_chapter_index == 76
    assert "程砚秋" in (m.memory_metadata or {})["payoff"]

    # reopen + postpone（同 batch）
    applied = plotline_apply_updates(
        db_session, project.id, 90,
        [
            {"action": "open", "title": "黑市线", "summary": "余党反扑"},
            {"action": "postpone", "title": "黑市线", "expected_resolve_chapter": 120},
        ],
    )
    assert applied["open"] == 1 and applied["postpone"] == 1
    m = _plotline(db_session, project.id, "黑市线")
    assert m.status == "open"
    assert (m.memory_metadata or {})["expected_resolve_chapter"] == 120


def test_plotline_apply_updates_skips_invalid(db_session):
    """fail-open：title 漂移/无开放伏笔/缺 expected/未知动作/超长 title/none → skipped 不炸。"""
    project = _make_project(db_session)
    applied = plotline_apply_updates(
        db_session, project.id, 1,
        [
            {"action": "close", "title": "不存在的线", "payoff": "x"},          # 无开放 → skipped
            {"action": "postpone", "title": "也不存在", "expected_resolve_chapter": 50},  # skipped
            {"action": "postpone", "title": "缺 expected"},                      # skipped
            {"action": "bogus", "title": "未知动作"},                            # skipped
            {"action": "open", "title": "超" * 80},                              # title 超长 → skipped
            {"action": "none", "title": "忽略"},                                 # none → skipped
        ],
    )
    assert applied == {"open": 0, "close": 0, "postpone": 0, "skipped": 6}
    assert db_session.query(LongformMemory).filter(
        LongformMemory.project_id == project.id,
        LongformMemory.memory_type == "plotline",
    ).count() == 0


def test_plotline_apply_updates_invalid_expected(db_session):
    """expected 非 int（字符串/bool/负数）→ 不落库但 open 仍成功。"""
    project = _make_project(db_session)
    applied = plotline_apply_updates(
        db_session, project.id, 2,
        [
            {"action": "open", "title": "字符串线", "expected_resolve_chapter": "80"},
            {"action": "open", "title": "负线", "expected_resolve_chapter": -5},
            {"action": "open", "title": "布尔线", "expected_resolve_chapter": True},
        ],
    )
    assert applied["open"] == 3
    for title in ("字符串线", "负线", "布尔线"):
        m = _plotline(db_session, project.id, title)
        assert (m.memory_metadata or {}).get("expected_resolve_chapter") is None


def test_plotline_query_due_marks(db_session):
    """query 两级标记：overdue（超 expected / 无 expected 超 30 章）、due_soon（距 expected ≤3 章）。"""
    project = _make_project(db_session)
    for i in range(1, 61):
        db_session.add(ChapterContent(
            project_id=project.id, chapter_index=i, title=f"Ch{i}",
            content="正文", status="generated",
        ))
    # 超期：expected=50，当前 60 → 超 10 章
    track_plotline(db_session, project.id, "open", title="超期线", chapter_index=10, expected_resolve_chapter=50)
    # 临期：expected=62，当前 60 → 2 章后回收
    track_plotline(db_session, project.id, "open", title="临期线", chapter_index=30, expected_resolve_chapter=62)
    # 未到期：expected=100
    track_plotline(db_session, project.id, "open", title="未到期线", chapter_index=40, expected_resolve_chapter=100)
    # 无 expected 且超 30 章（埋于 Ch1，当前 60）
    track_plotline(db_session, project.id, "open", title="无计划超期线", chapter_index=1)
    db_session.commit()

    result = track_plotline(db_session, project.id, "query")
    by_title = {p["title"]: p for p in result["plotlines"]}
    assert by_title["超期线"]["overdue"] is True
    assert by_title["超期线"]["overdue_by"] == 10
    assert by_title["临期线"]["due_soon"] is True
    assert by_title["临期线"]["resolves_in"] == 2
    assert by_title["无计划超期线"]["overdue"] is True
    assert by_title["无计划超期线"]["age_chapters"] == 59
    assert by_title["未到期线"].get("overdue") is None
    assert by_title["未到期线"].get("due_soon") is None
    assert "超期" in result["stale_warning"] and "临期" in result["stale_warning"]
    # 新字段回读（无 expected 的条目为 None）
    assert all("expected_resolve_chapter" in p and "payoff" in p for p in result["plotlines"])
    assert by_title["无计划超期线"]["expected_resolve_chapter"] is None
    assert by_title["超期线"]["expected_resolve_chapter"] == 50


# ── code-review 4 项修复回归 ──


def test_plotline_apply_updates_duplicate_open_same_batch(db_session):
    """#1 同批重复 open → 第二次 skipped（防双 INSERT 撞唯一约束回滚整笔事务）。"""
    project = _make_project(db_session)
    applied = plotline_apply_updates(
        db_session, project.id, 1,
        [
            {"action": "open", "title": "玉佩来历", "summary": "A"},
            {"action": "open", "title": "玉佩来历", "summary": "B"},
            {"action": "open", "title": "玉佩来历", "summary": "C"},
        ],
    )
    assert applied["open"] == 1 and applied["skipped"] == 2
    assert db_session.query(LongformMemory).filter(
        LongformMemory.project_id == project.id,
        LongformMemory.memory_type == "plotline",
    ).count() == 1
    # open 后同批 postpone 合法（reopen 后立即延期，不被去重误伤）
    applied2 = plotline_apply_updates(
        db_session, project.id, 2,
        [
            {"action": "postpone", "title": "玉佩来历", "expected_resolve_chapter": 50},
            {"action": "postpone", "title": "玉佩来历", "expected_resolve_chapter": 60},
        ],
    )
    assert applied2["postpone"] == 2  # postpone 不受 open 去重限制


def test_plotline_due_with_null_start_and_expected(db_session):
    """#2 start=NULL 的开放伏笔：expected 分支仍生效（超期判定不依赖埋设章）。"""
    project = _make_project(db_session)
    for i in range(1, 81):
        db_session.add(ChapterContent(
            project_id=project.id, chapter_index=i, title=f"Ch{i}",
            content="正文", status="generated",
        ))
    # 直接落库 start=NULL + expected=50（模拟 track_plotline open 未传 chapter_index）
    db_session.add(LongformMemory(
        project_id=project.id, memory_type="plotline", scope_key="无埋设章线",
        title="无埋设章线", summary="", start_chapter_index=None, status="open",
        memory_metadata={"expected_resolve_chapter": 50},
    ))
    db_session.commit()

    total, items = plotline_due_items(db_session, project.id)
    assert total == 1
    assert items and items[0]["title"] == "无埋设章线" and items[0]["overdue"] is True
    assert items[0]["overdue_by"] == 30  # 80 - 50


def test_plotline_reopen_clears_stale_meta(db_session):
    """#3/#12 reopen：清旧 expected/payoff、保留首次埋设章（不重新计时）。"""
    project = _make_project(db_session)
    # 埋设 Ch1 expected=50 → close Ch55（payoff）→ reopen Ch80
    track_plotline(db_session, project.id, "open", title="黑市线", chapter_index=1, expected_resolve_chapter=50)
    track_plotline(db_session, project.id, "close", title="黑市线", chapter_index=55, payoff="真凶落网")
    plotline_apply_updates(
        db_session, project.id, 80,
        [{"action": "open", "title": "黑市线", "summary": "余党反扑"}],
    )
    m = _plotline(db_session, project.id, "黑市线")
    assert m.status == "open"
    assert m.start_chapter_index == 1  # 保留首次埋设章
    meta = m.memory_metadata or {}
    assert "expected_resolve_chapter" not in meta  # 旧计划清除
    assert "payoff" not in meta  # 旧回收记录清除
    assert meta.get("source") == "track_plotline"  # 原来源保留


def test_plotline_postpone_action(db_session):
    """#9 track_plotline 支持 postpone 动作（stale_warning 文案可执行）。"""
    project = _make_project(db_session)
    track_plotline(db_session, project.id, "open", title="玉佩来历", chapter_index=1, expected_resolve_chapter=50)
    result = track_plotline(db_session, project.id, "postpone", title="玉佩来历", expected_resolve_chapter=120)
    assert result["action"] == "postponed"
    assert result["expected_resolve_chapter"] == 120
    m = _plotline(db_session, project.id, "玉佩来历")
    assert (m.memory_metadata or {})["expected_resolve_chapter"] == 120
    # 缺 expected → 报错
    from domain.memory.memory_service import MemoryServiceError

    with pytest.raises(MemoryServiceError) as exc_info:
        track_plotline(db_session, project.id, "postpone", title="玉佩来历")
    assert "expected_resolve_chapter" in str(exc_info.value)


def test_plotline_query_fallback_with_due_mark(db_session):
    """#10 标题漂移 fallback 分支：回退行带到期标记（不再呈现「干净」条目）。"""
    project = _make_project(db_session)
    for i in range(1, 61):
        db_session.add(ChapterContent(
            project_id=project.id, chapter_index=i, title=f"Ch{i}",
            content="正文", status="generated",
        ))
    track_plotline(db_session, project.id, "open", title="玉佩来历", chapter_index=1, expected_resolve_chapter=50)
    db_session.commit()

    result = track_plotline(db_session, project.id, "query", title="玉佩的来历")
    assert result["fallback"] is True
    assert result["plotlines"][0]["title"] == "玉佩来历"
    assert result["plotlines"][0]["overdue"] is True
    assert result["plotlines"][0]["overdue_by"] == 10


def test_plotline_expected_float_accepted(db_session):
    """#15 自省通道接受整值浮点 expected（80.0 → 80，与工具通道 lax 强转一致）。"""
    project = _make_project(db_session)
    applied = plotline_apply_updates(
        db_session, project.id, 1,
        [{"action": "open", "title": "浮点线", "expected_resolve_chapter": 80.0}],
    )
    assert applied["open"] == 1
    m = _plotline(db_session, project.id, "浮点线")
    assert (m.memory_metadata or {})["expected_resolve_chapter"] == 80


def test_plotline_open_chapter_ref_rejected(db_session):
    """#11 自省 open 拒绝含章节序号标题（与 track_plotline 校验一致）。"""
    project = _make_project(db_session)
    applied = plotline_apply_updates(
        db_session, project.id, 1,
        [{"action": "open", "title": "第50章黑市线", "summary": "x"}],
    )
    assert applied["open"] == 0 and applied["skipped"] == 1
    assert db_session.query(LongformMemory).filter(
        LongformMemory.project_id == project.id,
        LongformMemory.memory_type == "plotline",
    ).count() == 0


def test_plotline_tool_args_reject_bool_expected():
    """#5 pydantic lax 模式会把 JSON 布尔 true 强转为 1：StrictInt 拒绝，
    防落库 expected=1 自第 2 章起永久误报超期。"""
    from pydantic import ValidationError

    from domain.tools.memory_tools import TrackPlotlineArgs

    args = TrackPlotlineArgs(action="open", title="门主失踪之谜", expected_resolve_chapter=80)
    assert args.expected_resolve_chapter == 80
    with pytest.raises(ValidationError):
        TrackPlotlineArgs(action="open", title="门主失踪之谜", expected_resolve_chapter=True)


def test_open_plotline_rows_null_start_text(db_session):
    """#2 自省清单渲染：start=NULL 不出现「埋于 ChNone」。"""
    from domain.memory.memory_service import open_plotline_rows

    project = _make_project(db_session)
    db_session.add(LongformMemory(
        project_id=project.id, memory_type="plotline", scope_key="无埋设章线",
        title="无埋设章线", summary="", start_chapter_index=None, status="open",
        memory_metadata={"expected_resolve_chapter": 50},
    ))
    db_session.commit()
    rows = open_plotline_rows(db_session, project.id)
    assert len(rows) == 1
    assert rows[0]["start_chapter_text"] == "埋设章未知"
    assert "ChNone" not in rows[0]["start_chapter_text"]

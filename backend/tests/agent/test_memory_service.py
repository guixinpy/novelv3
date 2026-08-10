"""记忆服务通道配额测试（openhuman 多通道召回配额，特化：混合查询按通道硬截断）。

guideline 原为提示语（模型自觉遵守），现为代码强制。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models import LongformMemory, Project
from domain.memory.memory_service import query_memory


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

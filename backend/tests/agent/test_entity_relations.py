"""实体共现图测试（openhuman 共现图，特化适配：count + last_chapter 双字段）。

建边：同章提取实体两两成对 upsert 无向边；同章重复不累计，新章 count+1。
查询：related_entities 按共现次数降序，默认只返回转正实体关联（挡噪声边）。
"""
from __future__ import annotations

from app.models import EntityCandidate, EntityRelation, Project
from domain.retrieval.entity_miner import (
    record_entity_cooccurrences,
    related_entities,
    register_entity_candidates,
)


def _make_project(db) -> Project:
    project = Project(name="共现图项目")
    db.add(project)
    db.commit()
    return project


def test_cooccurrence_edges_created_and_counted(db_session):
    project = _make_project(db_session)
    names = ["林舟", "苏晚晴", "顾衍"]
    # 第 1 章共现：3 实体 → 3 条无向边
    record_entity_cooccurrences(db_session, project.id, 1, names)
    assert db_session.query(EntityRelation).count() == 3
    # 同章重复调用不累计
    record_entity_cooccurrences(db_session, project.id, 1, names)
    rows = db_session.query(EntityRelation).all()
    assert all(r.count == 1 for r in rows)
    # 第 2 章再次共现：count+1，last_chapter 更新
    record_entity_cooccurrences(db_session, project.id, 2, names)
    rows = db_session.query(EntityRelation).all()
    assert all(r.count == 2 for r in rows)
    assert all(r.last_chapter == 2 for r in rows)
    # 无向唯一：边对按字典序存储
    assert db_session.query(EntityRelation).filter(EntityRelation.entity_a == "苏晚晴").count() == 1


def test_related_entities_sorted_and_promoted_filtered(db_session):
    project = _make_project(db_session)
    register_entity_candidates(db_session, project.id, 1, ["林舟", "苏晚晴", "顾衍"])
    # 林舟-苏晚晴 共现 2 章，林舟-顾衍 共现 1 章
    record_entity_cooccurrences(db_session, project.id, 1, ["林舟", "苏晚晴", "顾衍"])
    record_entity_cooccurrences(db_session, project.id, 2, ["林舟", "苏晚晴"])
    # 未转正（chapter_count=1）：默认 only_promoted 过滤 → 无结果
    assert related_entities(db_session, project.id, "林舟") == []
    # 第 2 章登记 → chapter_count=2 转正 → 返回关联，按 count 降序
    register_entity_candidates(db_session, project.id, 2, ["林舟", "苏晚晴", "顾衍"])
    result = related_entities(db_session, project.id, "林舟")
    assert [r["entity"] for r in result] == ["苏晚晴", "顾衍"]
    assert result[0]["cooccurrence_count"] == 2
    assert result[0]["last_chapter"] == 2
    # only_promoted=False：返回全部（含未转正）
    assert len(related_entities(db_session, project.id, "林舟", only_promoted=False)) == 2


def test_related_entities_sql_filter_survives_truncation_line(db_session):
    """code-review #12：转正关联在截断线以下也能返回（SQL 层过滤而非先截断）。"""
    project = _make_project(db_session)
    # 林舟与 30 个未转正噪声实体共现（count 高、排位靠前）+ 1 个转正实体（count=1）
    noisy = [f"噪声{i}" for i in range(30)]
    register_entity_candidates(db_session, project.id, 1, ["林舟"] + noisy)
    record_entity_cooccurrences(db_session, project.id, 1, ["林舟"] + noisy)
    register_entity_candidates(db_session, project.id, 1, ["苏晚晴"])
    record_entity_cooccurrences(db_session, project.id, 1, ["林舟", "苏晚晴"])
    # 噪声实体转正（count≥2），苏晚晴 count=1 未转正
    register_entity_candidates(db_session, project.id, 2, noisy)
    record_entity_cooccurrences(db_session, project.id, 2, ["林舟"] + noisy)
    result = related_entities(db_session, project.id, "林舟", limit=8)
    # 返回的关联全部是转正实体（噪声已转正），无未转正的苏晚晴
    assert result
    assert all(r["entity"] != "苏晚晴" for r in result)
    assert len(result) <= 8


async def test_get_entities_tool_builds_edges(db_session):
    """get_entities 工具：提供文本时登记候选并同步建边。"""
    from core.tools.base import ToolContext, ToolRegistry
    from domain.tools.retrieval_tools import register_retrieval_tools

    project = _make_project(db_session)
    registry = ToolRegistry()
    register_retrieval_tools(registry)
    ctx = ToolContext(project_id=project.id, db=db_session)
    result = await registry.execute(
        "get_entities",
        {"chapter_index": 1, "text": "林舟看向苏晚晴，顾衍沉默不语。"},
        ctx,
    )
    assert not result.is_error
    # 提取出的候选已登记（姓氏白名单：林舟/苏晚晴/顾衍）
    candidates = db_session.query(EntityCandidate).count()
    assert candidates >= 3
    # 同章共现边已建
    assert db_session.query(EntityRelation).count() >= 3

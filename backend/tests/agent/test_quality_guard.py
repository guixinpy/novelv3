"""质量保障特化测试（P1①/② 恢复，2026-08-10）。

覆盖：质量趋势四级判定/不足 3 章/无数据；快照趋势段（非 stable 注入、
信息形态无指令）；连续性检测（死亡角色出场/正常角色/无设定卡/无数据）。
"""
from __future__ import annotations

from app.models import ChapterContent, Project, Setup
from domain.memory.project_snapshot import build_project_snapshot
from domain.writing.continuity import check_continuity
from domain.writing.quality_trend import quality_trend_stats


def _make_project(db) -> Project:
    p = Project(name="质量保障")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _add_chapter(db, project_id, index: int, word_count: int) -> None:
    db.add(ChapterContent(
        project_id=project_id, chapter_index=index,
        title=f"第{index}章", content="正文。" * max(1, word_count // 3),
        word_count=word_count, status="generated",
    ))
    db.commit()


def test_trend_severe_decline(db_session):
    """字数腰斩 → severe_decline + 可能原因（信息形态）。"""
    project = _make_project(db_session)
    for i in range(1, 11):
        _add_chapter(db_session, project.id, i, 3000 if i <= 5 else 1000)
    stats = quality_trend_stats(db_session, project.id)
    assert stats is not None
    assert stats["trend"] == "severe_decline"
    assert stats["first_avg"] == 3000 and stats["second_avg"] == 1000
    assert stats["possible_causes"]  # 信息形态：可能原因列表


def test_trend_stable_and_insufficient(db_session):
    """稳定 → stable；不足 3 章 → None（快照不注入）。"""
    project = _make_project(db_session)
    for i in range(1, 6):
        _add_chapter(db_session, project.id, i, 2000)
    stats = quality_trend_stats(db_session, project.id)
    assert stats["trend"] == "stable"
    # 不足 3 章
    project2 = _make_project(db_session)
    _add_chapter(db_session, project2.id, 1, 2000)
    _add_chapter(db_session, project2.id, 2, 2000)
    assert quality_trend_stats(db_session, project2.id) is None
    # 无数据
    project3 = _make_project(db_session)
    assert quality_trend_stats(db_session, project3.id) is None


def test_snapshot_trend_section(db_session):
    """快照趋势段：非 stable 注入、信息形态（无指令文案）、stable 不注入。"""
    project = _make_project(db_session)
    for i in range(1, 11):
        _add_chapter(db_session, project.id, i, 3000 if i <= 5 else 1000)
    snapshot = build_project_snapshot(db_session, project.id)
    assert snapshot is not None
    assert "质量趋势" in snapshot
    assert "降" in snapshot and "%" in snapshot
    # 信息形态：无「请立即」「必须」等指令
    assert "请立即" not in snapshot and "必须" not in snapshot
    # stable 不注入
    project2 = _make_project(db_session)
    for i in range(1, 6):
        _add_chapter(db_session, project2.id, i, 2000)
    snapshot2 = build_project_snapshot(db_session, project2.id)
    assert "质量趋势" not in snapshot2


def test_continuity_dead_character_appears(db_session):
    """死亡角色再次出场 → fatal issue（报告形态，含证据与建议参考）。"""
    project = _make_project(db_session)
    _add_chapter(db_session, project.id, 1, 900)
    db_session.add(Setup(
        project_id=project.id,
        characters=[{"name": "程砚秋", "character_status": "dead"}, {"name": "苏晚晴"}],
        status="active",
    ))
    db_session.commit()
    # 本章正文包含死亡角色名（entity_miner 提取）
    ch = db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id).first()
    ch.content = "程砚秋走进来，苏晚晴抬头看他。" * 10
    db_session.commit()

    result = check_continuity(db_session, project.id)
    assert result["checked_chapters"] == 1
    issues = result["issues"]
    assert len(issues) == 1
    issue = issues[0]
    assert issue["checker"] == "character_state"
    assert issue["subject"] == "程砚秋"
    assert issue["severity"] == "fatal"
    assert "死亡" in issue["evidence"] and "再次出场" in issue["evidence"]
    assert issue["suggestion"]  # 建议参考存在（非指令，供模型裁决）


def test_continuity_no_issue_and_no_setup(db_session):
    """正常角色/无设定卡 → 无 issue。"""
    project = _make_project(db_session)
    _add_chapter(db_session, project.id, 1, 900)
    db_session.add(Setup(
        project_id=project.id,
        characters=[{"name": "程砚秋", "character_status": "alive"}, {"name": "苏晚晴"}],
        status="active",
    ))
    db_session.commit()
    ch = db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id).first()
    ch.content = "程砚秋走进来，苏晚晴抬头看他。" * 10
    db_session.commit()
    assert check_continuity(db_session, project.id)["issues"] == []
    # 无设定卡
    project2 = _make_project(db_session)
    _add_chapter(db_session, project2.id, 1, 900)
    assert check_continuity(db_session, project2.id)["issues"] == []
    # 无章节
    project3 = _make_project(db_session)
    assert check_continuity(db_session, project3.id)["issues"] == []


def test_continuity_specific_chapter_and_missing(db_session):
    """指定章节检查；章节不存在 → error 信息。"""
    project = _make_project(db_session)
    _add_chapter(db_session, project.id, 5, 900)
    result = check_continuity(db_session, project.id, chapter_index=5)
    assert result["checked_chapter_index"] == 5
    result = check_continuity(db_session, project.id, chapter_index=99)
    assert result["issues"] == []
    assert "error" in result

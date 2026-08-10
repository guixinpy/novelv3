"""质量趋势纯函数测试（P1① 恢复，2026-08-10）。

覆盖：四级判定、零值过滤（#1）、奇数窗口中间章归前半（#9）、
不足 3 有效行、无数据。
"""
from __future__ import annotations

from app.models import ChapterContent, Project
from domain.writing.quality_trend import quality_trend_stats


def _make_project(db) -> Project:
    p = Project(name="质量趋势")
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
    """稳定 → stable；不足 3 有效行 → None。"""
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


def test_trend_zero_word_count_filtered(db_session):
    """#1 零值过滤：word_count=0/NULL 是缺失数据，不伪装成腰斩/暴涨。"""
    project = _make_project(db_session)
    # 5 章 3000 字 + 5 章 0 字（缺失）
    for i in range(1, 6):
        _add_chapter(db_session, project.id, i, 3000)
    for i in range(6, 11):
        _add_chapter(db_session, project.id, i, 0)
    stats = quality_trend_stats(db_session, project.id)
    assert stats is not None
    assert stats["trend"] == "stable"  # 有效行均为 3000，不是 severe_decline
    assert stats["window"] == 5  # 只统计有效行
    # 有效行不足 3 → None
    project2 = _make_project(db_session)
    for i in range(1, 4):
        _add_chapter(db_session, project2.id, i, 0)
    _add_chapter(db_session, project2.id, 4, 2000)
    _add_chapter(db_session, project2.id, 5, 2000)
    assert quality_trend_stats(db_session, project2.id) is None


def test_trend_odd_window_mid_in_first_half(db_session):
    """#9 奇数窗口：中间章归前半窗——「序章短章 + 两章正文」不误判为暴涨。"""
    project = _make_project(db_session)
    _add_chapter(db_session, project.id, 1, 300)  # 序章短章
    _add_chapter(db_session, project.id, 2, 3000)
    _add_chapter(db_session, project.id, 3, 3000)
    stats = quality_trend_stats(db_session, project.id)
    assert stats is not None
    # mid=2：前半 [300,3000] avg 1650、后半 [3000] → ratio≈1.82（growing 但非 900%）
    assert stats["trend"] == "growing"
    assert stats["ratio"] < 2.0

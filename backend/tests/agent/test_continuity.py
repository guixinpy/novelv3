"""连续性检测测试（P1② 恢复，2026-08-10）。

覆盖：死亡角色出场（含「已死亡」表述 #3、短名/停止词尾字角色 #2）、
正常角色/无设定卡/无章节无 issue、指定章节、章节不存在 error 标记。
"""
from __future__ import annotations

from app.models import ChapterContent, Project, Setup
from domain.writing.continuity import check_continuity


def _make_project(db) -> Project:
    p = Project(name="连续性")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _add_chapter(db, project_id, index: int, content: str) -> None:
    db.add(ChapterContent(
        project_id=project_id, chapter_index=index,
        title=f"第{index}章", content=content * 10,
        word_count=900, status="generated",
    ))
    db.commit()


def test_continuity_dead_character_appears(db_session):
    """死亡角色再次出场 → error issue（报告形态，含证据与建议参考）。"""
    project = _make_project(db_session)
    _add_chapter(db_session, project.id, 1, "程砚秋走进来，苏晚晴抬头看他。")
    db_session.add(Setup(
        project_id=project.id,
        characters=[{"name": "程砚秋", "character_status": "dead"}, {"name": "苏晚晴"}],
        status="active",
    ))
    db_session.commit()

    result = check_continuity(db_session, project.id)
    assert result["checked_chapters"] == 1
    issues = result["issues"]
    assert len(issues) == 1
    issue = issues[0]
    # 形态与 format_checker 一致（severity/type/detail，code-review 5 项 #8）
    assert issue["severity"] == "error"
    assert issue["type"] == "character_state"
    assert "死亡" in issue["detail"] and "再次出场" in issue["detail"]
    assert issue["evidence"]
    assert issue["suggestion"]  # 建议参考存在（非指令，供模型裁决）


def test_continuity_dead_status_variants(db_session):
    """#3 死亡表述包含匹配：「已死亡」「身亡」都命中。"""
    project = _make_project(db_session)
    _add_chapter(db_session, project.id, 1, "李海走进来，王虎跟在他身后。")
    db_session.add(Setup(
        project_id=project.id,
        characters=[
            {"name": "李海", "character_status": "已死亡"},
            {"name": "王虎", "character_status": "身亡"},
            {"name": "赵铁", "character_status": "alive"},
        ],
        status="active",
    ))
    db_session.commit()

    issues = check_continuity(db_session, project.id)["issues"]
    subjects = {i["subject"] if "subject" in i else i["detail"].split("「")[1].split("」")[0] for i in issues}
    assert "李海" in subjects and "王虎" in subjects
    assert len(issues) == 2  # 赵铁 alive 不报


def test_continuity_short_name_with_stop_tail(db_session):
    """#2 子串匹配：尾字停止词/短名角色不漏报（entity_miner 语法候选会漏）。"""
    project = _make_project(db_session)
    _add_chapter(db_session, project.id, 1, "李海走进来，苏梅在院子里。")
    db_session.add(Setup(
        project_id=project.id,
        characters=[{"name": "李海", "character_status": "dead"}, {"name": "苏梅", "character_status": "dead"}],
        status="active",
    ))
    db_session.commit()

    issues = check_continuity(db_session, project.id)["issues"]
    assert len(issues) == 2  # 李海（海是停止词尾）、苏梅 都检出


def test_continuity_no_issue_and_no_setup(db_session):
    """正常角色/无设定卡 → 无 issue。"""
    project = _make_project(db_session)
    _add_chapter(db_session, project.id, 1, "程砚秋走进来，苏晚晴抬头看他。")
    db_session.add(Setup(
        project_id=project.id,
        characters=[{"name": "程砚秋", "character_status": "alive"}, {"name": "苏晚晴"}],
        status="active",
    ))
    db_session.commit()
    assert check_continuity(db_session, project.id)["issues"] == []
    # 无设定卡
    project2 = _make_project(db_session)
    _add_chapter(db_session, project2.id, 1, "程砚秋走进来。")
    assert check_continuity(db_session, project2.id)["issues"] == []
    # 无章节
    project3 = _make_project(db_session)
    assert check_continuity(db_session, project3.id)["issues"] == []


def test_continuity_specific_chapter_and_missing(db_session):
    """指定章节检查；章节不存在 → error 标记（工具层转 fail）。"""
    project = _make_project(db_session)
    _add_chapter(db_session, project.id, 5, "程砚秋走进来。")
    result = check_continuity(db_session, project.id, chapter_index=5)
    assert result["checked_chapter_index"] == 5
    result = check_continuity(db_session, project.id, chapter_index=99)
    assert result["issues"] == []
    assert "error" in result

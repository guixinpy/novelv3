"""正文实体候选提取测试（实体登记来源扩展）。"""
from __future__ import annotations

from app.core.entity_miner import (
    mine_entities_from_text,
    promoted_entity_names,
    register_entity_candidates,
)
from app.models import EntityCandidate, Project


def test_mine_extracts_main_characters():
    text = (
        "程砚秋走进仓库时，苏晚晴已经等在雾里。"
        "顾沉舟从码头赶来，身后跟着姚先生。"
    )
    found = mine_entities_from_text(text)
    assert "程砚秋" in found
    assert "苏晚晴" in found
    assert "顾沉舟" in found
    # 姚先生（称谓式）尾字「生/先」为停止词 → 不提取（避免称谓截断误报）
    assert "姚先生" not in found
    assert "姚先" not in found


def test_mine_compound_surname():
    text = "欧阳雪站在灯塔下，司马懿笑了笑。"
    found = mine_entities_from_text(text)
    assert "欧阳雪" in found
    # 复姓不被单姓拆分
    assert "欧" not in found
    assert "司" not in found


def test_mine_filters_stop_words():
    text = "王顾左右而言他。我觉得今天的水很冷。"
    found = mine_entities_from_text(text)
    assert "王顾左" not in found
    assert "我觉得" not in found


def test_mine_deduplicates_preserving_order():
    text = "程砚秋来了。程砚秋又走了。苏晚晴在。"
    assert mine_entities_from_text(text) == ["程砚秋", "苏晚晴"]


def test_register_candidate_cross_chapter_counts(db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    register_entity_candidates(db_session, project.id, 1, ["程砚秋", "苏晚晴"], source="rule")
    # 同章重复：不增计数
    register_entity_candidates(db_session, project.id, 1, ["程砚秋"], source="rule")
    # 新章：计数 +1
    register_entity_candidates(db_session, project.id, 2, ["程砚秋"], source="rule")

    row = (
        db_session.query(EntityCandidate)
        .filter(EntityCandidate.project_id == project.id, EntityCandidate.name == "程砚秋")
        .one()
    )
    assert row.chapter_count == 2
    assert row.first_chapter == 1
    assert row.last_chapter == 2

    # rule 来源：程砚秋跨 2 章（ch1+ch2）转正；苏晚晴仅 ch1 未转正
    assert "程砚秋" in promoted_entity_names(db_session, project.id)
    assert "苏晚晴" not in promoted_entity_names(db_session, project.id)


def test_promoted_rule_after_two_chapters_and_l2_immediate(db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    register_entity_candidates(db_session, project.id, 1, ["程砚秋"], source="rule")
    register_entity_candidates(db_session, project.id, 2, ["程砚秋"], source="rule")
    register_entity_candidates(db_session, project.id, 1, ["婆婆"], source="l2")

    promoted = promoted_entity_names(db_session, project.id)
    assert "程砚秋" in promoted  # rule 跨 2 章转正
    assert "婆婆" in promoted    # l2 免转正

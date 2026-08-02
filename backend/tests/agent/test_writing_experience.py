"""per-book 自优化：写作经验服务测试（09 定稿）。

覆盖：信任度记账（new/reinforce/override）、30 章惰性衰减 + 归档、pinned 豁免、
预算淘汰、注入条目（最近 + 高信任轮转）、自省服务（解析/幂等/不可解析容错）、
作者否决入口（delete/pin）。
"""
from __future__ import annotations

from app.models import LongformMemory, Project
from domain.memory.writing_experience import (
    EXPERIENCE_TYPE,
    INTROSPECT_CATEGORIES,
    apply_experiences,
    delete_experience,
    experience_injection_items,
    introspect_and_record,
    pin_experience,
)
from tests.core.conftest import ScriptedProvider


def _make_project(db) -> Project:
    p = Project(name="自优化测试")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _entries(db, project_id):
    return (
        db.query(LongformMemory)
        .filter(LongformMemory.project_id == project_id, LongformMemory.memory_type == EXPERIENCE_TYPE)
        .all()
    )


def _by_key(db, project_id) -> dict:
    return {e.scope_key: e for e in _entries(db, project_id)}


# ── 信任度记账 ──


def test_new_reinforce_override_accounting(db_session):
    project = _make_project(db_session)
    # new
    applied = apply_experiences(
        db_session, project.id, 1, "节奏",
        [{"key": "战斗场景长度", "action": "new", "text": "战斗场景应控制在 800 字内。"}],
    )
    assert applied["new"] == 1
    entry = _by_key(db_session, project.id)["战斗场景长度"]
    assert (entry.memory_metadata or {})["trust_score"] == 1
    assert entry.status == "current"
    # reinforce：同 key 第 2 章出现 → +1
    apply_experiences(
        db_session, project.id, 2, "节奏",
        [{"key": "战斗场景长度", "action": "reinforce", "text": "战斗场景 800 字内，本章验证有效。"}],
    )
    entry = _by_key(db_session, project.id)["战斗场景长度"]
    assert (entry.memory_metadata or {})["trust_score"] == 2
    assert (entry.memory_metadata or {})["last_reinforce_chapter_index"] == 2
    # override：新文本覆盖 + 降权
    apply_experiences(
        db_session, project.id, 3, "节奏",
        [{"key": "战斗场景长度", "action": "override", "text": "800 字上限过于僵硬，改为 600-1000 字浮动。"}],
    )
    entry = _by_key(db_session, project.id)["战斗场景长度"]
    assert (entry.memory_metadata or {})["trust_score"] == 1
    assert "浮动" in entry.summary


def test_stale_decay_and_archive(db_session):
    """30 章未强化 → trust-1；≤0 → archived。"""
    project = _make_project(db_session)
    apply_experiences(
        db_session, project.id, 1, "文风",
        [{"key": "对话占比", "action": "new", "text": "对话应精简。"}],
    )
    # 第 31 章自省时，Ch1 条目已 30 章未强化 → 衰减至 0 → 归档
    apply_experiences(
        db_session, project.id, 31, "文风",
        [{"key": "动作描写", "action": "new", "text": "动作应具体。"}],
    )
    entries = _by_key(db_session, project.id)
    assert entries["对话占比"].status == "archived"
    assert (entries["对话占比"].memory_metadata or {})["trust_score"] == 0
    assert entries["动作描写"].status == "current"


def test_pinned_exempt_from_decay(db_session):
    """作者钉住：不衰减、不淘汰。"""
    project = _make_project(db_session)
    apply_experiences(
        db_session, project.id, 1, "教训",
        [{"key": "钩子收尾", "action": "new", "text": "章末必须留钩子。"}],
    )
    assert pin_experience(db_session, project.id, "钩子收尾", pinned=True)["pinned"]
    apply_experiences(
        db_session, project.id, 31, "教训",
        [{"key": "新教训", "action": "new", "text": "新教训。"}],
    )
    pinned = _by_key(db_session, project.id)["钩子收尾"]
    assert pinned.status == "current"
    assert (pinned.memory_metadata or {})["trust_score"] == 1  # 未衰减


def test_budget_evicts_lowest_trust(db_session):
    """每类 20 条上限：超限按信任度淘汰（archived 不删除）。"""
    project = _make_project(db_session)
    items = [{"key": f"经验{i}", "action": "new", "text": f"经验{i}内容。"} for i in range(21)]
    apply_experiences(db_session, project.id, 1, "节奏", items)
    active = [e for e in _entries(db_session, project.id) if e.status == "current"]
    assert len(active) == 20
    assert len(_entries(db_session, project.id)) == 21  # 淘汰只是归档


# ── 注入条目 ──


def test_injection_items_recent_plus_high_trust(db_session):
    project = _make_project(db_session)
    # 长期原则：Ch1-3 强化 3 次 → trust 3（高信任，但不在最近窗口内）
    for ch in (1, 2, 3):
        apply_experiences(
            db_session, project.id, ch, "节奏",
            [{"key": "长期原则", "action": "new" if ch == 1 else "reinforce", "text": f"长期原则 v{ch}。"}],
        )
    # 两条即时经验：Ch5、Ch6（最近窗口）
    apply_experiences(
        db_session, project.id, 5, "节奏",
        [{"key": "即时甲", "action": "new", "text": "即时甲内容。"}],
    )
    apply_experiences(
        db_session, project.id, 6, "节奏",
        [{"key": "即时乙", "action": "new", "text": "即时乙内容。"}],
    )
    items = experience_injection_items(db_session, project.id)
    assert len(items) == 3  # 最近 2 + 高信任 1
    texts = " | ".join(i["text"] for i in items)
    assert "即时甲" in texts and "即时乙" in texts
    assert "长期原则" in texts  # 高信任条目（trust 3）补齐
    # 锚点：强化章号
    assert any(i["anchor"] == "Ch6验证" for i in items)


def test_injection_items_respects_limit_and_empty(db_session):
    project = _make_project(db_session)
    assert experience_injection_items(db_session, project.id) == []
    apply_experiences(
        db_session, project.id, 1, "节奏",
        [{"key": "一条经验", "action": "new", "text": "内容。"}],
    )
    items = experience_injection_items(db_session, project.id)
    assert len(items) == 1


# ── 自省服务 ──


async def test_introspect_records_and_is_idempotent(db_session):
    project = _make_project(db_session)
    script = ScriptedProvider([
        {"content": '{"experiences": [{"key": "钩子收尾", "action": "new", "text": "章末留钩子有效。"}]}'},
    ])
    result = await introspect_and_record(
        db_session, project.id, 1, provider=script,
        plan_context="章纲", chapter_text="正文" * 50,
    )
    assert result["status"] == "recorded"
    assert result["category"] in INTROSPECT_CATEGORIES
    entries = _entries(db_session, project.id)
    assert len(entries) == 1
    assert entries[0].scope_key == "钩子收尾"
    # 幂等：同章再次自省跳过（会话重启安全）
    result2 = await introspect_and_record(db_session, project.id, 1, provider=script)
    assert result2["status"] == "skipped"
    assert len(_entries(db_session, project.id)) == 1


async def test_introspect_category_rotates_by_chapter(db_session):
    """分类轮转：Ch1→节奏，Ch2→文风，Ch3→设定运用，Ch4→教训。"""
    project = _make_project(db_session)
    for ch in range(1, 5):
        script = ScriptedProvider([{"content": '{"experiences": []}'}])
        result = await introspect_and_record(
            db_session, project.id, ch, provider=script, chapter_text="正文",
        )
        assert result["status"] == "recorded"
        assert result["category"] == INTROSPECT_CATEGORIES[(ch - 1) % 4]


async def test_introspect_unparseable_output_noop(db_session):
    """自省输出不可解析 → 空应用，不炸流程。"""
    project = _make_project(db_session)
    script = ScriptedProvider([{"content": "我总结一下本章的经验教训……"}])
    result = await introspect_and_record(db_session, project.id, 1, provider=script, chapter_text="x")
    assert result["status"] == "recorded"
    assert result["applied"]["new"] == 0
    assert len(_entries(db_session, project.id)) == 0


# ── 作者否决入口 ──


def test_delete_and_pin_experience(db_session):
    project = _make_project(db_session)
    apply_experiences(
        db_session, project.id, 1, "节奏",
        [{"key": "删除我", "action": "new", "text": "内容。"}],
    )
    assert delete_experience(db_session, project.id, "删除我")["deleted"]
    assert len(_entries(db_session, project.id)) == 0

    apply_experiences(
        db_session, project.id, 1, "节奏",
        [{"key": "钉住我", "action": "new", "text": "内容。"}],
    )
    assert pin_experience(db_session, project.id, "钉住我", pinned=True)["pinned"]
    entry = _by_key(db_session, project.id)["钉住我"]
    assert (entry.memory_metadata or {})["pinned"] is True

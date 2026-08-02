"""回合级项目状态快照（T6 R1）。

每回合临时拼进 system prompt，让模型自带「可行动的写作上下文」：
章节进度、活跃弧线、最近 3 章、开放伏笔、全书事实表（角色/地点/格式规范）。
减少模型用工具探索的无效往返（200 章实测：模型频繁 list_chapters/get_project_state）。
快照不持久化（由 harness 拼进 system 消息，system 本就不落盘）。
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import ChapterContent, LongformMemory, Project, Setup

_FACT_SHEET_FORMAT_RULES = "格式规范：对话用全角引号“”；正文不得含 markdown 标记（**）、备选词（X/Y）、章题重复行。"


def build_project_snapshot(
    db: Session,
    project_id: str,
    *,
    include_experience: bool = True,
) -> str | None:
    """构建项目状态快照文本（≤约 400 字）。项目不存在或无数据返回 None。

    include_experience=False 可关闭写作经验段（per-book 自优化 config 开关）。
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        return None

    parts: list[str] = []

    # 章节进度
    chapters = (
        db.query(ChapterContent)
        .filter(ChapterContent.project_id == project_id)
        .order_by(ChapterContent.chapter_index.asc())
        .all()
    )
    total = len(chapters)
    if total:
        parts.append(f"已写 {total} 章")
        recent = chapters[-3:]
        recent_desc = "，".join(
            f"Ch{c.chapter_index}《{c.title}》({c.word_count}字)" for c in recent
        )
        parts.append(f"最近章节: {recent_desc}")

    # 活跃弧线 + 终局
    active_arc = (
        db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == "story_arc",
            LongformMemory.status == "active",
        )
        .first()
    )
    if active_arc is not None:
        span = f"Ch{active_arc.start_chapter_index}→{active_arc.end_chapter_index}"
        arc_desc = f"活跃弧线「{active_arc.title}」({span})"
        endgame = (active_arc.memory_metadata or {}).get("endgame")
        if endgame:
            arc_desc += f"，收束于 Ch{endgame.get('resolve_before')}"
        parts.append(arc_desc)

    # 开放伏笔
    open_lines = (
        db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == "plotline",
            LongformMemory.status == "open",
        )
        .count()
    )
    if open_lines:
        parts.append(f"{open_lines} 条开放伏笔")

    # 全书事实表：角色 / 地点 / 格式规范
    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    if setup is not None:
        names: list[str] = []
        for ch in (setup.characters or []):
            if isinstance(ch, dict) and ch.get("name"):
                names.append(str(ch["name"]))
        wb = setup.world_building or {}
        for loc in (wb.get("locations") or []):
            if isinstance(loc, str):
                names.append(loc)
        if names:
            parts.append("事实表: " + "、".join(names))
        parts.append(_FACT_SHEET_FORMAT_RULES)

    # 写作经验段（per-book 自优化，09 定稿）：最近 2 + 高信任 1，标记仅供参考
    if include_experience:
        try:
            from domain.memory.writing_experience import experience_injection_items

            experience_items = experience_injection_items(db, project_id)
        except Exception:
            # 经验段是辅助信息，查询失败静默跳过（fail-open）
            experience_items = []
        if experience_items:
            desc = "；".join(f"{item['text']}({item['anchor']})" for item in experience_items)
            parts.append(f"写作经验(仅供参考): {desc}")

    if not parts:
        return None
    return "【项目状态快照】" + "；".join(parts) + "。"

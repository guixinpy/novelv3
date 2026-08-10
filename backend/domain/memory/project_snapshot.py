"""回合级项目状态快照（T6 R1）。

每回合临时拼进 system prompt，让模型自带「可行动的写作上下文」：
章节进度、活跃弧线、最近 3 章、开放伏笔、全书事实表（角色/地点/格式规范）。
减少模型用工具探索的无效往返（200 章实测：模型频繁 list_chapters/get_project_state）。
快照不持久化（由 harness 拼进 system 消息，system 本就不落盘）。
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import ChapterContent, LongformMemory, Project, Setup
from domain.memory.memory_service import plotline_due_items
from domain.memory.writing_experience import experience_injection_items
from domain.writing.quality_trend import quality_trend_stats

# 快照到期伏笔条目文案（超期/临期单行 ≤约 30 字，控制快照总预算——
# title 截断到 12 字 + 省略号，code-review 4 项 #6：此前完整 title 单条约 74 字，
# 3 条 230 字超快照「≤约 400 字」预算 40%）
_DUE_TITLE_MAX = 12


def _clip_title(title: str) -> str:
    return title[:_DUE_TITLE_MAX] + ("…" if len(title) > _DUE_TITLE_MAX else "")


def _due_item_text(item: dict) -> str:
    title = _clip_title(str(item["title"]))
    if item.get("overdue"):
        if "overdue_by" in item:
            return f"「{title}」(超{item['overdue_by']}章)"
        return f"「{title}」(开{item['age_chapters']}章未收)"
    return f"「{title}」(Ch{item['expected']}收)"


# 质量趋势快照文案（信息形态 ≤约 40 字：数字 + 可能原因首条供参考，无指令。
# code-review 5 项 #6：全量 causes 拼接曾达 60 字，超快照单段预算 50%）
def _trend_text(trend: dict) -> str:
    ratio = trend["ratio"]
    change = f"降{round((1 - ratio) * 100)}%" if ratio < 1 else f"增{round((ratio - 1) * 100)}%"
    cause = trend["possible_causes"][0] if trend["possible_causes"] else ""
    cause_suffix = f"，可能: {cause}" if cause else ""
    return f"质量趋势: 近{trend['window']}章字数 {trend['first_avg']}→{trend['second_avg']}（{change}{cause_suffix}）"

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

    # 章节进度（simplify：count + 末 3 章，此前全量加载全书正文入内存）
    total = (
        db.query(ChapterContent.chapter_index)
        .filter(ChapterContent.project_id == project_id)
        .count()
    )
    if total:
        parts.append(f"已写 {total} 章")
        recent = (
            db.query(ChapterContent)
            .filter(ChapterContent.project_id == project_id)
            .order_by(ChapterContent.chapter_index.desc())
            .limit(3)
            .all()
        )
        recent_desc = "，".join(
            f"Ch{c.chapter_index}《{c.title}》({c.word_count}字)" for c in reversed(recent)
        )
        parts.append(f"最近章节: {recent_desc}")

    # 质量趋势（P1① 恢复）：非 stable 才注入，≤约 40 字，信息形态（无指令文案）。
    # 守卫 total>=3（code-review 5 项 #15：0-2 章项目每回合白付一次必然为空的查询）
    if total >= 3:
        trend = quality_trend_stats(db, project_id)
        if trend is not None and trend["trend"] != "stable":
            parts.append(_trend_text(trend))

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

    # 伏笔账本（09 定稿钩子）：数量 + 超期/临期具体清单（≤3 条，超期优先）——
    # 计数无行动价值，清单驱动模型决策（收线或显式延期）。
    # 单次查询：count 与 due 判定共用（code-review 4 项 #13：此前两次查询）
    open_lines, due_items = plotline_due_items(db, project_id)
    if open_lines:
        parts.append(f"{open_lines} 条开放伏笔")
    if due_items:
        desc = "；".join(_due_item_text(item) for item in due_items)
        parts.append(f"到期伏笔: {desc}")

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
        experience_items = experience_injection_items(db, project_id)
        if experience_items:
            desc = "；".join(f"{item['text']}({item['anchor']})" for item in experience_items)
            parts.append(f"写作经验(仅供参考): {desc}")

    if not parts:
        return None
    return "【项目状态快照】" + "；".join(parts) + "。"

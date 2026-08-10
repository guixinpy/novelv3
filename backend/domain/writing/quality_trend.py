"""质量趋势纯函数（P1① 恢复，信息形态）。

近 N 章字数前后半窗口均值比 → 四级判定（severe_decline/declining/growing/stable）。
确定性纯函数（零 LLM 成本）——长程实验的观测尺子：先有量化，才能判定
「质量不下滑」是否成立。

口径说明（code-review 5 项 #7）：word_count 以当前写入路径（len(content)）为准；
迁移书若窗口跨 arch-refactor 边界（旧路径存去空格长度，低约 1-3%），比值有
系统性偏差——长程实验判定以新写章节为准，不迁移历史口径。

工具不越权原则（2026-08-10 用户约束）：本模块只产出「信息 + 可能原因（供参考）」，
无指令式文案、不自动修复、不阻塞。旧 check_quality_trend 的指令式 advice
（「请立即检查：1)…」）按此原则修正。
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import ChapterContent

_TREND_WINDOW = 10

# 可能原因（信息形态，供模型/用户参考，非命令）
_DECLINE_CAUSES = ("主线可能已近尾声", "可能在写填充内容", "场景或对话可能单薄")
_GROW_CAUSES = ("篇幅增长中", "场景铺开")  # 增长一般无需干预，仅提示


def quality_trend_stats(
    db: Session,
    project_id: str,
    window: int = _TREND_WINDOW,
) -> dict | None:
    """近 ≤window 章字数趋势统计。

    有效行过滤（code-review 5 项 #1）：word_count 为 0/NULL 的行是缺失数据
    （列可空且 default=0），不当真实零值计入——否则一次数据缺口会被伪装成
    「质量腰斩」每回合注入快照。
    不足 3 个有效行返回 None（快照不注入）。
    """
    rows = (
        db.query(ChapterContent.chapter_index, ChapterContent.word_count)
        .filter(ChapterContent.project_id == project_id)
        .order_by(ChapterContent.chapter_index.desc())
        .limit(window)
        .all()
    )
    # 过滤缺失数据行（0/NULL word_count）
    valid = [(idx, wc) for idx, wc in rows if wc]
    if len(valid) < 3:
        return None
    # 时间序（最近在尾部）
    recent = sorted(valid, key=lambda r: r[0])
    counts = [wc for _, wc in recent]
    # mid 划入前半窗（code-review 5 项 #9）：奇数窗口下中间章归前半——
    # 避免「序章短章 + 两章正文」把短章单独成窗误判为 900% 增长
    mid = len(counts) - len(counts) // 2
    first_avg = sum(counts[:mid]) / max(1, mid)
    second_avg = sum(counts[mid:]) / max(1, len(counts) - mid)
    ratio = second_avg / max(1, first_avg)

    if ratio < 0.5:
        trend = "severe_decline"
        causes = _DECLINE_CAUSES
    elif ratio < 0.75:
        trend = "declining"
        causes = _DECLINE_CAUSES
    elif ratio > 1.3:
        trend = "growing"
        causes = _GROW_CAUSES
    else:
        trend = "stable"
        causes = ()

    return {
        "trend": trend,
        "window": len(counts),
        "first_avg": int(first_avg),
        "second_avg": int(second_avg),
        "ratio": round(ratio, 2),
        # 信息形态：可能原因供参考，非指令
        "possible_causes": list(causes),
    }

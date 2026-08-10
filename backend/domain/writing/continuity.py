"""连续性检测（P1② 恢复：角色状态维度，checker registry 可扩展）。

第一版只做角色状态：设定卡标记为死亡的角色在正文再次出场 → issue。
复用 entity_miner 的正文角色提取（同一通道，不新造提取器）。

工具不越权原则（2026-08-10 用户约束）：输出为报告形态（问题 + 证据 +
建议参考），不自动修复、不阻塞流程、无指令式文案。issue 由模型/用户裁决——
回忆、梦境、同名等误报场景交给最终决策者判断。
"""
from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from app.models import ChapterContent, Setup
from domain.retrieval.entity_miner import mine_entities_from_text

# 设定卡角色状态字段（题材无关：状态词从设定卡读取，不硬编码网文术语）
_STATUS_FIELD = "character_status"
_DEAD_STATES = ("dead", "死亡", "已死")


class ContinuityChecker(Protocol):
    """checker 扩展点：后续维度（时间线/编号/关系锚点）实现同一接口。"""

    def check(self, db: Session, project_id: str, chapter: ChapterContent, setup: Setup | None) -> list[dict]:
        ...


def _character_state_issues(
    db: Session, project_id: str, chapter: ChapterContent, setup: Setup | None
) -> list[dict]:
    if setup is None or not setup.characters:
        return []
    dead_names: list[str] = []
    for ch in setup.characters:
        if not isinstance(ch, dict):
            continue
        status = str(ch.get(_STATUS_FIELD) or "alive").strip().lower()
        name = str(ch.get("name") or "").strip()
        if name and status in _DEAD_STATES:
            dead_names.append(name)
    if not dead_names:
        return []
    appeared = set(mine_entities_from_text(chapter.content or ""))
    issues: list[dict] = []
    for name in dead_names:
        if name in appeared:
            issues.append(
                {
                    "checker": "character_state",
                    "severity": "fatal",
                    "subject": name,
                    "chapter_index": chapter.chapter_index,
                    "evidence": f"角色「{name}」已标记为死亡，却在第 {chapter.chapter_index} 章再次出场",
                    # 建议参考（模型/用户裁决，非强制）
                    "suggestion": "确认该角色状态是否准确，或调整本章出场安排",
                }
            )
    return issues


def check_continuity(
    db: Session,
    project_id: str,
    chapter_index: int = 0,
) -> dict:
    """连续性检测入口。chapter_index=0 时检查最近一章。

    返回报告形态：issues 清单 + 检查范围；无问题返回空 issues。
    """
    query = db.query(ChapterContent).filter(ChapterContent.project_id == project_id)
    if chapter_index and chapter_index > 0:
        chapter = query.filter(ChapterContent.chapter_index == chapter_index).first()
        if chapter is None:
            return {"issues": [], "checked_chapters": 0, "error": f"章节 Ch{chapter_index} 不存在"}
    else:
        chapter = query.order_by(ChapterContent.chapter_index.desc()).first()
        if chapter is None:
            return {"issues": [], "checked_chapters": 0}
    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    issues = _character_state_issues(db, project_id, chapter, setup)
    return {
        "issues": issues,
        "checked_chapters": 1,
        "checked_chapter_index": chapter.chapter_index,
    }

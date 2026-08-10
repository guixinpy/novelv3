"""连续性检测（P1② 恢复：角色状态维度）。

检测设定卡标记为死亡的角色在正文再次出场 → issue。
出场判定用 text_mentions 子串匹配（code-review 5 项 #2/#10：entity_miner
的姓氏语法候选对尾字停止词/短名/非中文名静默漏检，子串匹配覆盖任意名）。

工具不越权原则（2026-08-10 用户约束）：输出为报告形态（问题 + 证据 +
建议参考），不自动修复、不阻塞流程、无指令式文案。issue 由模型/用户裁决——
回忆、梦境、同名等误报场景交给最终决策者判断。
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import ChapterContent, Setup
from domain.retrieval.text_mentions import count_non_overlapping_mentions

# 设定卡角色状态字段（题材无关：状态词从设定卡读取，不硬编码网文术语）
_STATUS_FIELD = "character_status"
# 死亡表述词根（code-review 5 项 #3：包含匹配——「已死亡」「身亡」「战死」
# 等自然表述都命中，精确成员判断会漏检）
_DEAD_KEYWORDS = ("dead", "死亡", "身亡", "已死")


def _is_dead(status: str) -> bool:
    lowered = status.strip().lower()
    return any(keyword in lowered for keyword in _DEAD_KEYWORDS)


def _dead_character_names(setup: Setup | None) -> list[str]:
    """设定卡中标记为死亡的角色名单。"""
    if setup is None or not setup.characters:
        return []
    names: list[str] = []
    for ch in setup.characters:
        if not isinstance(ch, dict):
            continue
        status = str(ch.get(_STATUS_FIELD) or "alive")
        name = str(ch.get("name") or "").strip()
        if name and _is_dead(status):
            names.append(name)
    return names


def _character_state_issues(chapter: ChapterContent, setup: Setup | None) -> list[dict]:
    dead_names = _dead_character_names(setup)
    if not dead_names:
        return []
    appeared = {
        name
        for name in dead_names
        if count_non_overlapping_mentions(text=chapter.content or "", names=[name]) > 0
    }
    issues: list[dict] = []
    for name in sorted(appeared):
        issues.append(
            {
                # 形态与 format_checker 一致（severity: error/warning + type + detail，
                # code-review 5 项 #8：此前自创 fatal/checker/subject/evidence 四字段）
                "severity": "error",
                "type": "character_state",
                "detail": f"角色「{name}」已标记为死亡，却在第 {chapter.chapter_index} 章再次出场",
                "evidence": f"第 {chapter.chapter_index} 章正文出现「{name}」",
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

    章节不存在返回 {"error": ...}（工具层转 ToolResult.fail——
    code-review 5 项 #4：此前返回 ok + error 字段，模型把「检查失败」
    读成「检查通过」，绕过工具错误统计与恢复提示）。
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
    issues = _character_state_issues(chapter, setup)
    return {
        "issues": issues,
        "checked_chapters": 1,
        "checked_chapter_index": chapter.chapter_index,
    }

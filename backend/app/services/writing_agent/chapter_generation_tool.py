from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import ChapterContent, Project
from app.services.actions.action_execution_service import ActionExecutionService

CONTINUITY_KEY_TERMS = ("空白信", "雾晶", "记忆雾晶", "钥匙", "下城", "黑市", "灯塔", "实验体", "叶知秋", "苏晚晴", "林深")
LENGTH_POLICY_RECENT_WINDOW = 5
LENGTH_POLICY_REPEATED_DRIFT_THRESHOLD = 3
POST_GENERATION_NEXT_TOOLS = [
    "review_chapter_quality",
    "review_chapter_continuity",
    "analyze_chapter_world_model",
]


async def execute_generate_chapter_tool(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    command_args: str | None = None,
    action_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    continuity = _chapter_continuity_feedback(db, project_id, chapter_index)
    feedback = _chapter_generation_feedback(db, project_id)
    result = await ActionExecutionService(db).execute(
        "generate_chapter",
        project_id,
        command_args=_effective_chapter_command_args(command_args, continuity, feedback),
        action_params={**(action_params or {}), "chapter_index": chapter_index},
    )
    if continuity and isinstance(result, dict):
        result["agent_continuity_feedback"] = continuity
    if feedback and isinstance(result, dict):
        result["agent_generation_feedback"] = feedback
    if isinstance(result, dict) and str(result.get("status") or "") == "success":
        result.setdefault("recommended_next_tools", list(POST_GENERATION_NEXT_TOOLS))
    return result


def _chapter_generation_feedback(db: Session, project_id: str) -> dict[str, Any] | None:
    check = _length_policy_check(db, project_id)
    if check.get("status") != "review_required":
        return None
    reason = str(check.get("reason") or "")
    project = db.query(Project).filter(Project.id == project_id).first()
    target_range = None
    if project is not None:
        from app.prompting.providers.chapter import project_chapter_word_range

        target_range = project_chapter_word_range(project)
    if not target_range:
        return None
    low, high = target_range
    if reason == "repeated_over_target":
        message = (
            f"【Writing Agent 长度校准】近期章节连续偏长；本章正文建议回到{low}-{high}字，"
            f"优先压缩说明性段落和重复心理描写；若为保证剧情完整可少量浮动，但避免继续明显超过{high}字。"
        )
    elif reason == "repeated_under_target":
        message = (
            f"【Writing Agent 长度校准】近期章节连续偏短；本章正文建议写到{low}-{high}字，"
            f"补足场景动作、关键对话、信息揭示和章末钩子；避免长期低于{low}字。"
        )
    else:
        return None
    return {
        "status": "active",
        "reason": reason,
        "target_min_word_count": low,
        "target_max_word_count": high,
        "repeated_drift_count": check.get("repeated_drift_count"),
        "message": message,
    }


def _length_policy_check(db: Session, project_id: str) -> dict[str, Any]:
    policy = _length_drift_policy(db, project_id, status=None)
    if policy["status"] != "blocked":
        return {
            "status": "ready",
            "reason": None,
            "repeated_drift_count": policy["repeated_drift_count"],
            "recent_window": policy["recent_window"],
            "recent_chapter_indexes": policy["recent_chapter_indexes"],
            "recent_under_target_count": policy["recent_under_target_count"],
            "recent_over_target_count": policy["recent_over_target_count"],
            "historical_under_target_count": policy["historical_under_target_count"],
            "historical_over_target_count": policy["historical_over_target_count"],
            "recommended_actions": [],
        }
    direction = "过长" if policy["reason"] == "repeated_over_target" else "过短"
    return {
        "status": "review_required",
        "reason": policy["reason"],
        "repeated_drift_count": policy["repeated_drift_count"],
        "recent_window": policy["recent_window"],
        "recent_chapter_indexes": policy["recent_chapter_indexes"],
        "recent_under_target_count": policy["recent_under_target_count"],
        "recent_over_target_count": policy["recent_over_target_count"],
        "historical_under_target_count": policy["historical_under_target_count"],
        "historical_over_target_count": policy["historical_over_target_count"],
        "recommended_actions": policy["recommended_actions"],
        "message": f"最近{policy['recent_window']}章中已有{policy['repeated_drift_count']}章{direction}，后续生成需复核章节长度策略。",
    }


def _length_drift_policy(db: Session, project_id: str, *, status: str | None) -> dict[str, Any]:
    snapshot = _length_drift_snapshot(db, project_id)
    over_count = int(snapshot["recent_over_target_count"])
    under_count = int(snapshot["recent_under_target_count"])
    if status == "over" and over_count >= LENGTH_POLICY_REPEATED_DRIFT_THRESHOLD:
        return _blocked_length_policy("repeated_over_target", over_count, snapshot)
    if status == "under" and under_count >= LENGTH_POLICY_REPEATED_DRIFT_THRESHOLD:
        return _blocked_length_policy("repeated_under_target", under_count, snapshot)
    if status is None:
        if over_count >= LENGTH_POLICY_REPEATED_DRIFT_THRESHOLD:
            return _blocked_length_policy("repeated_over_target", over_count, snapshot)
        if under_count >= LENGTH_POLICY_REPEATED_DRIFT_THRESHOLD:
            return _blocked_length_policy("repeated_under_target", under_count, snapshot)
    return {
        "status": "ready",
        "reason": None,
        "repeated_drift_count": over_count if status == "over" else under_count if status == "under" else 0,
        "recommended_actions": [],
        **snapshot,
    }


def _length_drift_snapshot(db: Session, project_id: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "recent_window": LENGTH_POLICY_RECENT_WINDOW,
        "recent_chapter_indexes": [],
        "recent_under_target_count": 0,
        "recent_over_target_count": 0,
        "historical_under_target_count": 0,
        "historical_over_target_count": 0,
    }
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        return base
    from app.prompting.providers.chapter import project_chapter_word_range

    target_range = project_chapter_word_range(project)
    if not target_range:
        return base
    low, high = target_range
    chapters = (
        db.query(ChapterContent.chapter_index, ChapterContent.word_count)
        .filter(ChapterContent.project_id == project_id, ChapterContent.content != "")
        .order_by(ChapterContent.chapter_index.asc())
        .all()
    )
    recent = chapters[-LENGTH_POLICY_RECENT_WINDOW:]

    def status_for(word_count: int) -> str:
        if word_count < low:
            return "under"
        if word_count > high:
            return "over"
        return "within"

    historical_statuses = [status_for(int(chapter.word_count or 0)) for chapter in chapters]
    recent_statuses = [status_for(int(chapter.word_count or 0)) for chapter in recent]
    return {
        **base,
        "recent_chapter_indexes": [int(chapter.chapter_index) for chapter in recent],
        "recent_under_target_count": recent_statuses.count("under"),
        "recent_over_target_count": recent_statuses.count("over"),
        "historical_under_target_count": historical_statuses.count("under"),
        "historical_over_target_count": historical_statuses.count("over"),
    }


def _blocked_length_policy(reason: str, count: int, snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "repeated_drift_count": count,
        "recommended_actions": ["revise_or_adjust_project_target"],
        **snapshot,
    }


def _chapter_continuity_feedback(db: Session, project_id: str, chapter_index: int) -> dict[str, Any] | None:
    card = _previous_chapter_state_card(db, project_id, chapter_index)
    if card.get("status") != "ready":
        return None
    message = f"【上一章状态卡】第{card['chapter_index']}章《{card.get('title') or ''}》结尾：{card.get('last_excerpt') or ''}"
    key_terms = card.get("key_terms") or []
    if key_terms:
        message += f"；延续关键词：{', '.join(str(term) for term in key_terms[:8])}"
    return {"status": "active", "card": card, "message": message}


def _previous_chapter_state_card(db: Session, project_id: str, chapter_index: int) -> dict[str, Any]:
    if chapter_index <= 1:
        return {"status": "not_required"}
    chapter = (
        db.query(ChapterContent)
        .filter(ChapterContent.project_id == project_id, ChapterContent.chapter_index == chapter_index - 1)
        .first()
    )
    if chapter is None:
        return {"status": "missing", "chapter_index": chapter_index - 1}
    content = str(chapter.content or "").strip()
    excerpt = content[-220:] if len(content) > 220 else content
    key_terms = [term for term in CONTINUITY_KEY_TERMS if term in content]
    return {
        "status": "ready",
        "chapter_index": chapter.chapter_index,
        "title": chapter.title,
        "last_excerpt": excerpt,
        "key_terms": key_terms,
    }


def _effective_chapter_command_args(command_args: str | None, *feedbacks: dict[str, Any] | None) -> str | None:
    parts = [str(command_args or "").strip()]
    parts.extend(str((feedback or {}).get("message") or "").strip() for feedback in feedbacks)
    joined = "\n\n".join(part for part in parts if part)
    return joined or None

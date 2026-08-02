from typing import Any

from sqlalchemy.orm import Session

from app.models import Project, PromptRule


def _clamp(value: int, minimum: int = 1, maximum: int = 5) -> int:
    return max(minimum, min(maximum, value))


def _add_rule_once(db: Session, project_id: str, condition: str, action: str, priority: int = 50) -> bool:
    existing = db.query(PromptRule).filter(
        PromptRule.project_id == project_id,
        PromptRule.rule_type == "learned",
        PromptRule.condition == condition,
        PromptRule.action == action,
    ).first()
    if existing:
        existing.hit_count = (existing.hit_count or 0) + 1
        return False
    db.add(PromptRule(project_id=project_id, rule_type="learned", condition=condition, action=action, priority=priority))
    return True


def apply_revision_optimization(
    db: Session,
    project: Project,
    annotations: list[dict[str, Any]],
    corrections: list[dict[str, Any]],
) -> dict[str, int]:
    feedback_text = "\n".join(str(item.get("comment", "")) for item in annotations)
    correction_text = "\n".join(
        f"{item.get('original_text', '')}->{item.get('corrected_text', '')}" for item in corrections
    )
    combined = f"{feedback_text}\n{correction_text}"
    config = dict(project.style_config or {})

    created_rules = 0
    if "节奏太慢" in combined:
        if _add_rule_once(db, project.id, "用户反馈节奏太慢", "减少铺垫，加快场景推进", priority=80):
            created_rules += 1

    if "描写太多" in combined:
        if _add_rule_once(db, project.id, "用户反馈描写太多", "压缩环境和心理描写，保留推动剧情的信息", priority=75):
            created_rules += 1

    if "节奏太慢" in combined or "描写太多" in combined:
        config["description_density"] = _clamp(int(config.get("description_density", 3)) - 1)

    if "套话" in combined or any("寒风凛冽" in str(item.get("original_text", "")) for item in corrections):
        if _add_rule_once(db, project.id, "用户替换或批评套话", "避免陈词滥调，使用更具体的新鲜表达", priority=70):
            created_rules += 1

    if "对话不足" in combined:
        if _add_rule_once(db, project.id, "用户反馈对话不足", "提高关键场景中的角色对话占比", priority=65):
            created_rules += 1
        config["dialogue_ratio"] = _clamp(int(config.get("dialogue_ratio", 3)) + 1)

    project.style_config = config
    db.add(project)
    db.commit()
    return {"created_rules": created_rules}

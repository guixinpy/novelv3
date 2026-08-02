from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.athena_shared import require_project
from app.db import get_db
from app.models import PromptRule

router = APIRouter()
DEFAULT_OPTIMIZATION_RULE_LIMIT = 100


@router.get("/optimization")
def get_optimization(
    project_id: str,
    rules_offset: int = Query(0, ge=0),
    rules_limit: int = Query(DEFAULT_OPTIMIZATION_RULE_LIMIT, ge=1, le=500),
    db: Session = Depends(get_db),
):
    project = require_project(db, project_id)
    query = db.query(PromptRule).filter(
        PromptRule.project_id == project_id,
        PromptRule.rule_type == "learned",
    )
    rules_total = query.with_entities(func.count(PromptRule.id)).order_by(None).scalar() or 0
    rules = (
        query
        .order_by(PromptRule.created_at.desc(), PromptRule.id.desc())
        .offset(rules_offset)
        .limit(rules_limit)
        .all()
    )

    rule_items = [
        {
            "id": rule.id,
            "rule_type": rule.rule_type,
            "condition": rule.condition,
            "action": rule.action,
            "priority": rule.priority,
            "hit_count": rule.hit_count,
            "created_at": rule.created_at,
        }
        for rule in rules
    ]
    return {
        "rules": rule_items,
        "style_config": project.style_config or {},
        "learning_logs": [
            {
                "rule_id": rule["id"],
                "event_type": "rule_learned",
                "summary": f"学到规则：{rule['condition']} → {rule['action']}",
                "created_at": rule["created_at"],
            }
            for rule in rule_items
        ],
        "rules_total": rules_total,
        "rules_offset": rules_offset,
        "rules_limit": rules_limit,
        "rules_has_more": rules_offset + len(rule_items) < rules_total,
    }

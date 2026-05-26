from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.few_shot_library import FewShotExampleLibrary
from app.models import Project, PromptRule
from app.services.writing_agent.agent_knowledge_base_candidates import KNOWLEDGE_CANDIDATES_KEY
from app.services.writing_agent.memory_provenance_contract import build_memory_provenance, no_recovery

AGENT_KNOWLEDGE_BASE_ROUTE_VERSION = "phase76.agent_knowledge_base_route.v1"
MEMORY_PROVENANCE_VERSION = "phase222.agent_memory_provenance.v1"
DEFAULT_RULE_LIMIT = 20
MAX_RULE_LIMIT = 100
PREVIEW_LIMIT = 120


def inspect_agent_knowledge_base_route(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
    query: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    project = _require_project(db, project_id)
    clamped_limit = _clamp_limit(limit)
    learned_rules = _learned_rules(db, project_id, limit=clamped_limit)
    author_preferences = _author_preferences(project)
    project_strategy = _project_strategy(project)
    knowledge_candidates = _knowledge_candidates(project, limit=clamped_limit)
    reference_patterns = _reference_patterns(project, query=query)
    diagnostics = _diagnostics(
        author_preferences=author_preferences,
        learned_rules=learned_rules,
        knowledge_candidates=knowledge_candidates,
    )
    route = _route_decision(
        chapter_index=chapter_index,
        author_preferences=author_preferences,
        learned_rules=learned_rules,
        knowledge_candidates=knowledge_candidates,
    )
    memory_provenance = _memory_provenance(
        route=route,
        author_preferences=author_preferences,
        project_strategy=project_strategy,
        learned_rules=learned_rules,
        knowledge_candidates=knowledge_candidates,
        reference_patterns=reference_patterns,
    )
    return _json_safe_output(
        {
            "status": "completed",
            "project_id": project_id,
            "chapter_index": chapter_index,
            "query": _clean_query(query),
            "route": route,
            "author_preferences": author_preferences,
            "project_strategy": project_strategy,
            "learned_rules": learned_rules,
            "knowledge_candidates": knowledge_candidates,
            "reference_patterns": reference_patterns,
            "memory_provenance": memory_provenance,
            "diagnostics": diagnostics,
            "trace": {
                "source": "inspect_agent_knowledge_base_route",
                "version": AGENT_KNOWLEDGE_BASE_ROUTE_VERSION,
                "mutability": "read",
            },
        }
    )


def _require_project(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _author_preferences(project: Project) -> dict[str, Any]:
    style_config = project.style_config if isinstance(project.style_config, dict) else {}
    configured_items = {
        key: value
        for key, value in style_config.items()
        if key != KNOWLEDGE_CANDIDATES_KEY and value not in (None, "", [], {})
    }
    return {
        "status": "configured" if configured_items else "empty",
        "style_config": style_config,
        "facets": [
            {
                "key": key,
                "value": value,
                "source": "Project.style_config",
                "state": "active",
            }
            for key, value in sorted(configured_items.items())
        ],
        "source_ref": "Project.style_config",
    }


def _project_strategy(project: Project) -> dict[str, Any]:
    return {
        "name": project.name,
        "description": project.description or "",
        "genre": project.genre or "",
        "style": project.style or "",
        "complexity": project.complexity,
        "target_chapter_count": int(project.target_chapter_count or 0),
        "target_word_count": int(project.target_word_count or 0),
        "current_word_count": int(project.current_word_count or 0),
        "status": project.status,
        "current_phase": project.current_phase,
        "source_ref": "Project",
    }


def _learned_rules(db: Session, project_id: str, *, limit: int) -> dict[str, Any]:
    query = db.query(PromptRule).filter(
        PromptRule.project_id == project_id,
        PromptRule.rule_type == "learned",
    )
    total = query.with_entities(func.count(PromptRule.id)).order_by(None).scalar() or 0
    rows = (
        query.order_by(PromptRule.created_at.desc(), PromptRule.id.desc())
        .limit(limit)
        .all()
    )
    items = [
        {
            "id": rule.id,
            "condition": rule.condition,
            "action": rule.action,
            "priority": rule.priority,
            "hit_count": rule.hit_count,
            "source_ref": f"PromptRule:{rule.id}",
            "created_at": rule.created_at,
        }
        for rule in rows
    ]
    return {
        "total": int(total),
        "returned": len(items),
        "limit": limit,
        "has_more": len(items) < int(total),
        "items": items,
        "source_ref": "PromptRule(rule_type=learned)",
    }


def _knowledge_candidates(project: Project, *, limit: int) -> dict[str, Any]:
    style_config = project.style_config if isinstance(project.style_config, dict) else {}
    candidates = [item for item in style_config.get(KNOWLEDGE_CANDIDATES_KEY, []) if isinstance(item, dict)]
    visible = [item for item in candidates if str(item.get("status") or "candidate") not in {"rejected", "muted"}]
    sorted_items = sorted(
        visible,
        key=lambda item: (
            str(item.get("updated_at") or ""),
            str(item.get("created_at") or ""),
            str(item.get("id") or ""),
        ),
        reverse=True,
    )
    items = [
        {
            "id": item.get("id"),
            "memory_type": item.get("memory_type"),
            "title": item.get("title"),
            "summary": item.get("summary"),
            "source_refs": list(item.get("source_refs") or []),
            "confidence": item.get("confidence"),
            "status": item.get("status") or "candidate",
            "tags": list(item.get("tags") or []),
            "observed_count": int(item.get("observed_count") or 1),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }
        for item in sorted_items[:limit]
    ]
    return {
        "total": len(visible),
        "returned": len(items),
        "limit": limit,
        "has_more": len(items) < len(visible),
        "items": items,
        "source_ref": f"Project.style_config.{KNOWLEDGE_CANDIDATES_KEY}",
    }


def _reference_patterns(project: Project, *, query: str | None) -> dict[str, Any]:
    genre = project.genre or _clean_query(query) or ""
    examples = FewShotExampleLibrary().select_examples("chapter", genre, limit=2)
    return {
        "available": bool(examples),
        "task_type": "chapter",
        "genre": genre,
        "returned": len(examples),
        "items": [
            {
                "input_preview": _preview(example.get("input")),
                "output_preview": _preview(example.get("output")),
                "source_ref": "FewShotExampleLibrary",
            }
            for example in examples
        ],
        "source_ref": "FewShotExampleLibrary",
    }


def _diagnostics(
    *,
    author_preferences: dict[str, Any],
    learned_rules: dict[str, Any],
    knowledge_candidates: dict[str, Any],
) -> list[dict[str, Any]]:
    diagnostics = [
        {
            "code": "world_truth_boundary",
            "severity": "info",
            "message": "知识库是作者偏好、项目策略和写法经验，不是 Athena 世界真相；内部事实仍需走世界模型和提案机制。",
        }
    ]
    if (
        author_preferences["status"] == "empty"
        and int(learned_rules["total"]) == 0
        and int(knowledge_candidates["total"]) == 0
    ):
        diagnostics.append(
            {
                "code": "knowledge_base_sparse",
                "severity": "info",
                "message": "项目尚缺少明确作者偏好和学习规则，Agent 应通过生成、审稿和用户反馈逐步沉淀。",
            }
        )
    if learned_rules["has_more"]:
        diagnostics.append(
            {
                "code": "learned_rules_truncated",
                "severity": "info",
                "message": "学习规则已按窗口限制截断，Agent 应只使用最高优先级和最新的规则。",
                "total": learned_rules["total"],
                "returned": learned_rules["returned"],
            }
        )
    if knowledge_candidates["has_more"]:
        diagnostics.append(
            {
                "code": "knowledge_candidates_truncated",
                "severity": "info",
                "message": "知识库候选已按窗口限制截断，Agent 应只使用当前返回的候选项。",
                "total": knowledge_candidates["total"],
                "returned": knowledge_candidates["returned"],
            }
        )
    return diagnostics


def _route_decision(
    *,
    chapter_index: int | None,
    author_preferences: dict[str, Any],
    learned_rules: dict[str, Any],
    knowledge_candidates: dict[str, Any],
) -> dict[str, Any]:
    sparse = (
        author_preferences["status"] == "empty"
        and int(learned_rules["total"]) == 0
        and int(knowledge_candidates["total"]) == 0
    )
    recommended_tools = ["summarize_longform_context"]
    if chapter_index:
        recommended_tools.append("preflight_writing")
    recommended_tools.append("review_chapter_quality")
    return {
        "status": "sparse" if sparse else "ready",
        "reason": "knowledge_base_sparse" if sparse else "knowledge_base_available",
        "can_inform_generation": True,
        "recommended_tools": recommended_tools,
    }


def _memory_provenance(
    *,
    route: dict[str, Any],
    author_preferences: dict[str, Any],
    project_strategy: dict[str, Any],
    learned_rules: dict[str, Any],
    knowledge_candidates: dict[str, Any],
    reference_patterns: dict[str, Any],
) -> dict[str, Any]:
    sources = [
        {
            "source_ref": "Project",
            "source_type": "project_strategy",
            "item_count": 1,
            "mutability": "read",
        }
    ]
    if author_preferences["status"] != "empty":
        sources.append(
            {
                "source_ref": author_preferences["source_ref"],
                "source_type": "author_preferences",
                "item_count": len(author_preferences["facets"]),
                "mutability": "read",
            }
        )
    if int(learned_rules["returned"]) > 0:
        sources.append(
            {
                "source_ref": learned_rules["source_ref"],
                "source_type": "learned_rules",
                "item_count": int(learned_rules["returned"]),
                "total_count": int(learned_rules["total"]),
                "mutability": "read",
            }
        )
    if int(knowledge_candidates["returned"]) > 0:
        sources.append(
            {
                "source_ref": knowledge_candidates["source_ref"],
                "source_type": "knowledge_candidates",
                "item_count": int(knowledge_candidates["returned"]),
                "total_count": int(knowledge_candidates["total"]),
                "mutability": "read",
            }
        )
    if int(reference_patterns["returned"]) > 0:
        sources.append(
            {
                "source_ref": reference_patterns["source_ref"],
                "source_type": "reference_patterns",
                "item_count": int(reference_patterns["returned"]),
                "mutability": "read",
            }
    )
    return build_memory_provenance(
        version=MEMORY_PROVENANCE_VERSION,
        status="sparse" if route["status"] == "sparse" else "available",
        sources=sources,
        windows={
            "learned_rules": _window_provenance(learned_rules),
            "knowledge_candidates": _window_provenance(knowledge_candidates),
        },
        recovery=no_recovery(reason=route.get("reason")),
        trace={
            "source": "inspect_agent_knowledge_base_route",
            "version": MEMORY_PROVENANCE_VERSION,
            "mutability": "read",
        },
        extras={
            "boundaries": {
                "world_truth": {
                    "status": "separated",
                    "canonical_source": "Athena/world_model",
                    "knowledge_base_role": "author_preferences_project_strategy_reference_patterns_and_lessons",
                }
            },
        },
    )


def _window_provenance(section: dict[str, Any]) -> dict[str, Any]:
    return {
        "total": int(section["total"]),
        "returned": int(section["returned"]),
        "limit": int(section["limit"]),
        "has_more": bool(section["has_more"]),
    }


def _clean_query(query: str | None) -> str | None:
    cleaned = str(query or "").strip()
    return cleaned or None


def _preview(value: Any) -> str:
    return str(value or "")[:PREVIEW_LIMIT]


def _clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_RULE_LIMIT
    return min(max(int(limit), 1), MAX_RULE_LIMIT)


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

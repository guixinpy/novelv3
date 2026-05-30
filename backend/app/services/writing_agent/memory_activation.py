from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.longform_memory import get_longform_maintenance_diagnostics
from app.models import LongformMemory, Project, Storyline, WorldProposalItem
from app.services.writing_agent.memory_provenance_contract import build_memory_provenance, count_window

MEMORY_ACTIVATION_VERSION = "phase241.memory_activation.v1"
MEMORY_ACTIVATION_PROVENANCE_VERSION = "phase241.memory_activation_provenance.v1"
MAINTENANCE_REPAIR_PREPARE_TOOL = "prepare_repair_longform_maintenance"
LONGFORM_ITEM_LIMIT = 8
FORESHADOWING_ITEM_LIMIT = 5
WORLD_MODEL_ITEM_LIMIT = 5
SUMMARY_LIMIT = 220
PROMPT_BLOCK_LIMIT = 1800


def build_memory_activation_plan(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    query: str | None = None,
) -> dict[str, Any]:
    project = _require_project(db, project_id)
    target_chapter = max(1, int(chapter_index or 1))
    longform_items = _longform_items(db, project_id, target_chapter)
    foreshadowing = _foreshadowing_items(db, project_id, target_chapter)
    world_model = _world_model_items(db, project_id, target_chapter)
    style = _style_items(project)
    coverage_debt = _memory_coverage_debt(db, project_id)
    risks = _risks(coverage_debt)
    status = _status(risks)
    recommended_next_tools = _recommended_next_tools(status)
    activation = {
        "longform": longform_items,
        "foreshadowing": foreshadowing,
        "world_model": world_model,
        "style": style,
    }
    prompt_block = _prompt_block(
        chapter_index=target_chapter,
        query=query,
        activation=activation,
        risks=risks,
    )
    output = {
        "status": status,
        "version": MEMORY_ACTIVATION_VERSION,
        "project_id": project_id,
        "chapter_index": target_chapter,
        "query": str(query or "").strip() or None,
        "activation": activation,
        "coverage": {
            "memory_coverage_debt": coverage_debt,
            "activated_counts": {key: len(value) for key, value in activation.items()},
        },
        "risks": risks,
        "recommended_next_tools": recommended_next_tools,
        "prompt_block": prompt_block,
        "memory_provenance": _memory_provenance(
            status=status,
            activation=activation,
            coverage_debt=coverage_debt,
            recommended_next_tools=recommended_next_tools,
        ),
        "trace": {
            "source": "build_memory_activation_plan",
            "version": MEMORY_ACTIVATION_VERSION,
            "mutability": "read",
            "runtime_behavior_changed": False,
            "future_leak_guard": "end_chapter_index_before_target",
        },
    }
    return _json_safe_output(output)


def _require_project(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _longform_items(db: Session, project_id: str, chapter_index: int) -> list[dict[str, Any]]:
    rows = (
        db.query(LongformMemory)
        .filter(LongformMemory.project_id == project_id)
        .filter(LongformMemory.memory_type.in_(("global", "volume", "arc", "chapter", "scene", "beat")))
        .filter(or_(LongformMemory.end_chapter_index.is_(None), LongformMemory.end_chapter_index < chapter_index))
        .order_by(
            LongformMemory.memory_type.asc(),
            LongformMemory.start_chapter_index.desc().nullslast(),
            LongformMemory.scope_key.asc(),
        )
        .all()
    )
    ordered = sorted(rows, key=_memory_sort_key)
    return [_memory_item(memory) for memory in ordered[:LONGFORM_ITEM_LIMIT]]


def _memory_sort_key(memory: LongformMemory) -> tuple[int, int, str]:
    type_rank = {
        "global": 0,
        "volume": 1,
        "arc": 2,
        "chapter": 3,
        "scene": 4,
        "beat": 5,
    }.get(str(memory.memory_type or ""), 9)
    chapter_rank = -(memory.end_chapter_index or memory.start_chapter_index or 0)
    return (type_rank, chapter_rank, str(memory.scope_key or ""))


def _memory_item(memory: LongformMemory) -> dict[str, Any]:
    return {
        "kind": "longform_memory",
        "memory_id": memory.id,
        "memory_type": memory.memory_type,
        "scope_key": memory.scope_key,
        "title": memory.title or memory.scope_key,
        "summary": _limit_text(memory.summary, SUMMARY_LIMIT),
        "chapter_range": {
            "start": memory.start_chapter_index,
            "end": memory.end_chapter_index,
        },
        "source_ref": f"longform_memory:{memory.id}",
    }


def _foreshadowing_items(db: Session, project_id: str, chapter_index: int) -> list[dict[str, Any]]:
    storyline = (
        db.query(Storyline)
        .filter(Storyline.project_id == project_id)
        .order_by(Storyline.updated_at.desc(), Storyline.id.desc())
        .first()
    )
    if storyline is None or not isinstance(storyline.foreshadowing, list):
        return []
    items: list[dict[str, Any]] = []
    for raw in storyline.foreshadowing:
        if not isinstance(raw, dict):
            continue
        status = str(raw.get("status") or "open").strip()
        introduced = _optional_int(raw.get("introduced_chapter") or raw.get("planted_chapter"))
        if status not in {"open", "planted"}:
            continue
        if introduced is not None and introduced >= chapter_index:
            continue
        title = str(raw.get("title") or raw.get("name") or raw.get("hint") or "").strip()
        summary = str(raw.get("summary") or raw.get("description") or "").strip()
        if not title and not summary:
            continue
        items.append(
            {
                "kind": "foreshadowing",
                "title": title or summary[:40],
                "summary": _limit_text(summary or title, SUMMARY_LIMIT),
                "introduced_chapter": introduced,
                "expected_resolution_chapter": _optional_int(
                    raw.get("expected_resolution_chapter") or raw.get("resolved_chapter")
                ),
                "status": status,
                "source_ref": f"storyline:{storyline.id}:foreshadowing:{len(items)}",
            }
        )
    return sorted(items, key=lambda item: (item.get("introduced_chapter") or 0, item["title"]))[:FORESHADOWING_ITEM_LIMIT]


def _world_model_items(db: Session, project_id: str, chapter_index: int) -> list[dict[str, Any]]:
    rows = (
        db.query(WorldProposalItem)
        .filter(WorldProposalItem.project_id == project_id)
        .filter(WorldProposalItem.item_status.in_(("pending", "uncertain", "approved", "approved_with_edits")))
        .filter(or_(WorldProposalItem.chapter_index.is_(None), WorldProposalItem.chapter_index < chapter_index))
        .order_by(WorldProposalItem.chapter_index.desc().nullslast(), WorldProposalItem.updated_at.desc())
        .limit(WORLD_MODEL_ITEM_LIMIT)
        .all()
    )
    items: list[dict[str, Any]] = []
    for row in rows:
        items.append(
            {
                "kind": "world_model",
                "proposal_item_id": row.id,
                "chapter_index": row.chapter_index,
                "subject_ref": row.subject_ref,
                "predicate": row.predicate,
                "status": row.item_status,
                "summary": _limit_text(_world_model_summary(row), SUMMARY_LIMIT),
                "source_ref": f"world_proposal_item:{row.id}",
            }
        )
    return items


def _world_model_summary(item: WorldProposalItem) -> str:
    value = item.object_ref_or_value
    if isinstance(value, dict):
        summary = value.get("summary") or value.get("value") or value.get("name")
    else:
        summary = value
    text = str(summary or item.notes or item.predicate or "").strip()
    return text


def _style_items(project: Project) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if project.style:
        items.append(
            {
                "kind": "style_anchor",
                "title": "项目文风",
                "summary": _limit_text(project.style, SUMMARY_LIMIT),
                "source_ref": f"project:{project.id}:style",
            }
        )
    config = project.style_config if isinstance(project.style_config, dict) else {}
    for key in ("tone", "pov", "description_density", "dialogue_style"):
        value = config.get(key)
        if value in (None, "", []):
            continue
        items.append(
            {
                "kind": "style_anchor",
                "title": f"style_config.{key}",
                "summary": _limit_text(str(value), SUMMARY_LIMIT),
                "source_ref": f"project:{project.id}:style_config:{key}",
            }
        )
    return items[:4]


def _memory_coverage_debt(db: Session, project_id: str) -> dict[str, Any]:
    diagnostics = get_longform_maintenance_diagnostics(db, project_id, limit=10)
    issue_count = _non_negative_int(diagnostics.get("issue_count"))
    return {
        "status": "ready" if issue_count == 0 else "degraded",
        "issue_count": issue_count,
        "missing_memory_count": _non_negative_int(diagnostics.get("missing_memory_count")),
        "stale_memory_count": _non_negative_int(diagnostics.get("stale_memory_count")),
        "missing_retrieval_count": _non_negative_int(diagnostics.get("missing_retrieval_count")),
        "stale_retrieval_count": _non_negative_int(diagnostics.get("stale_retrieval_count")),
        "latest_synced_chapter_index": diagnostics.get("latest_synced_chapter_index"),
    }


def _risks(coverage_debt: dict[str, Any]) -> list[dict[str, Any]]:
    if coverage_debt.get("status") == "ready":
        return []
    return [
        {
            "code": "memory_coverage_debt",
            "severity": "warning",
            "message": "长篇记忆或检索索引存在缺口，生成前应修复或明确降级使用。",
            "issue_count": coverage_debt.get("issue_count", 0),
        }
    ]


def _status(risks: list[dict[str, Any]]) -> str:
    severities = {str(risk.get("severity") or "") for risk in risks}
    if "blocker" in severities or "error" in severities:
        return "blocked"
    if risks:
        return "degraded"
    return "ready"


def _recommended_next_tools(status: str) -> list[str]:
    if status == "ready":
        return ["preflight_writing", "generate_chapter"]
    return [MAINTENANCE_REPAIR_PREPARE_TOOL, "inspect_agent_memory_route"]


def _prompt_block(
    *,
    chapter_index: int,
    query: str | None,
    activation: dict[str, list[dict[str, Any]]],
    risks: list[dict[str, Any]],
) -> str:
    lines = [f"【Writing Agent 长记忆激活】目标：第{chapter_index}章"]
    if query:
        lines.append(f"写作意图：{query}")
    for title, key in [
        ("既往长篇记忆", "longform"),
        ("未闭合伏笔", "foreshadowing"),
        ("世界模型状态", "world_model"),
        ("风格锚点", "style"),
    ]:
        items = activation.get(key) or []
        if not items:
            continue
        lines.append(f"【{title}】")
        for item in items:
            lines.append(f"- {item.get('title') or item.get('subject_ref') or item.get('predicate')}：{item.get('summary') or ''}")
    if risks:
        lines.append("【记忆风险】")
        lines.extend(f"- {risk['code']}：{risk['message']}" for risk in risks)
    return _limit_text("\n".join(lines), PROMPT_BLOCK_LIMIT)


def _memory_provenance(
    *,
    status: str,
    activation: dict[str, list[dict[str, Any]]],
    coverage_debt: dict[str, Any],
    recommended_next_tools: list[str],
) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    windows: dict[str, Any] = {}
    for key, items in activation.items():
        windows[key] = count_window(len(items), returned=len(items), limit=_limit_for_key(key), has_more=False)
        for item in items:
            source_ref = str(item.get("source_ref") or "").strip()
            if not source_ref:
                continue
            sources.append(
                {
                    "source_type": str(item.get("kind") or key),
                    "source_ref": source_ref,
                    "title": item.get("title") or item.get("subject_ref"),
                }
            )
    recovery_status = "none" if status == "ready" else "recommended"
    return build_memory_provenance(
        version=MEMORY_ACTIVATION_PROVENANCE_VERSION,
        status="available" if sources else "empty",
        sources=sources,
        windows=windows,
        recovery={
            "status": recovery_status,
            "reason": "memory_activation_ready" if status == "ready" else "memory_coverage_debt",
            "next_tools": [] if status == "ready" else recommended_next_tools,
            "tools": [
                {"tool_name": tool_name, "params": {}}
                for tool_name in ([] if status == "ready" else recommended_next_tools)
            ],
        },
        trace={
            "source": "build_memory_activation_plan",
            "version": MEMORY_ACTIVATION_PROVENANCE_VERSION,
            "mutability": "read",
        },
        extras={"coverage_debt": coverage_debt},
    )


def _limit_for_key(key: str) -> int:
    if key == "longform":
        return LONGFORM_ITEM_LIMIT
    if key == "foreshadowing":
        return FORESHADOWING_ITEM_LIMIT
    if key == "world_model":
        return WORLD_MODEL_ITEM_LIMIT
    return 4


def _limit_text(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _non_negative_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

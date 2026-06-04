from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.ai_service import AIService
from app.core.deepseek_adapter import parse_json_safely
from app.core.model_call_trace import (
    build_context_block,
    create_trace,
    mark_trace_failed,
    mark_trace_success,
    now_ms,
)
from app.models import AIModelCallTrace, ChapterContent, LongformMemory, Outline, Project, Storyline

MEMORY_TREE_VERSION = "phase238.memory_tree_browsing.v1"
MEMORY_TREE_SUMMARY_MATERIALIZATION_VERSION = "phase237.memory_tree_summary_materialization.v1"
MEMORY_TREE_QUALITY_VERSION = "phase245.memory_tree_quality.v1"
MEMORY_TREE_LLM_SUMMARY_PLAN_VERSION = "phase247.memory_tree_llm_summary_plan.v1"
MEMORY_TREE_LLM_SUMMARY_CANDIDATE_VERSION = "phase248.memory_tree_llm_summary_candidate.v1"
MEMORY_TREE_LLM_CANDIDATE_INSPECTION_VERSION = "phase249.memory_tree_llm_candidate_inspection.v1"
MEMORY_TREE_LLM_CANDIDATE_MATERIALIZATION_VERSION = "phase250.memory_tree_llm_candidate_materialization.v1"
MEMORY_TREE_LEVELS = ["volume", "chapter", "scene", "beat"]
MEMORY_TREE_VOLUME_SUMMARY_TYPE = "memory_tree_volume_summary"
MEMORY_TREE_CHAPTER_SUMMARY_TYPE = "memory_tree_chapter_summary"
MEMORY_TREE_SUMMARY_TYPES = (MEMORY_TREE_VOLUME_SUMMARY_TYPE, MEMORY_TREE_CHAPTER_SUMMARY_TYPE)
MIN_SEMANTIC_RELEVANCE_SCORE = 0.5
DEFAULT_LLM_SUMMARY_SOURCE_CHARS = 2400
MIN_LLM_SUMMARY_SOURCE_CHARS = 120
MAX_LLM_SUMMARY_SOURCE_CHARS = 8000


def inspect_agent_memory_tree(
    db: Session,
    project_id: str,
    *,
    level: str | None = None,
    node_id: str | None = None,
    expand_node_id: str | None = None,
    chapter_index: int | None = None,
    query: str | None = None,
    include_ancestors: bool = False,
    max_depth: int | None = None,
) -> dict[str, Any]:
    chapters = _chapters(db, project_id)
    outline = _outline(db, project_id)
    storyline = _storyline(db, project_id)
    memories = _memories(db, project_id)
    all_nodes = _build_nodes(
        chapters=chapters,
        outline=outline,
        storyline=storyline,
        memories=memories,
    )
    nodes, navigation = _select_nodes(
        all_nodes,
        level=level,
        node_id=node_id,
        expand_node_id=expand_node_id,
        chapter_index=chapter_index,
        query=query,
        include_ancestors=include_ancestors,
        max_depth=max_depth,
    )
    return {
        "version": MEMORY_TREE_VERSION,
        "status": "ready",
        "project_id": project_id,
        "levels": list(MEMORY_TREE_LEVELS),
        "filters": {
            "level": level,
            "node_id": node_id,
            "expand_node_id": expand_node_id,
            "chapter_index": chapter_index,
            "query": query,
            "include_ancestors": include_ancestors,
            "max_depth": max_depth,
        },
        "navigation": navigation,
        "summary": _summary(all_nodes),
        "roots": [node["id"] for node in all_nodes if node["level"] == "volume"],
        "nodes": nodes,
        "trace": {
            "source_tables": ["chapter_contents", "outlines", "storylines", "longform_memories"],
            "projection": "in_memory",
        },
    }


def inspect_agent_memory_tree_quality(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    tree = inspect_agent_memory_tree(db, project_id)
    nodes = tree.get("nodes") if isinstance(tree.get("nodes"), list) else []
    coverage = _memory_tree_quality_coverage(nodes)
    semantic_probe = _memory_tree_semantic_probe(
        db,
        project_id,
        chapter_index=chapter_index,
        query=query,
    )
    diagnostics = _memory_tree_quality_diagnostics(coverage, semantic_probe)
    status = "ready" if not diagnostics else "degraded"
    return {
        "version": MEMORY_TREE_QUALITY_VERSION,
        "status": status,
        "project_id": project_id,
        "filters": {
            "chapter_index": chapter_index,
            "query": str(query or "").strip() or None,
        },
        "coverage": coverage,
        "semantic_probe": semantic_probe,
        "diagnostics": diagnostics,
        "recommended_next_tools": _memory_tree_quality_recommendations(diagnostics),
        "trace": {
            "source": "inspect_agent_memory_tree_quality",
            "version": MEMORY_TREE_QUALITY_VERSION,
            "mutability": "read",
            "runtime_behavior_changed": False,
        },
    }


def build_agent_memory_tree_llm_summary_plan(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
    query: str | None = None,
    max_source_chars: int | None = None,
) -> dict[str, Any]:
    target_chapter_index = _target_summary_chapter_index(db, project_id, chapter_index)
    source_budget = _clamp_source_chars(max_source_chars)
    query_text = str(query or "").strip() or None
    chapters = _chapters(db, project_id)
    chapter = next(
        (item for item in chapters if int(item.chapter_index) == int(target_chapter_index)),
        None,
    )
    outline = _outline(db, project_id)
    storyline = _storyline(db, project_id)
    memories = _memories(db, project_id)
    outline_item = _outline_by_chapter(outline).get(target_chapter_index)
    quality_precheck = inspect_agent_memory_tree_quality(
        db,
        project_id,
        chapter_index=target_chapter_index,
        query=query_text,
    )
    evidence_sources = _llm_summary_evidence_sources(
        chapter=chapter,
        outline=outline,
        outline_item=outline_item,
        storyline=storyline,
        memories=memories,
        chapter_index=target_chapter_index,
        max_source_chars=source_budget,
    )
    summary_target = {
        "level": "chapter",
        "chapter_index": target_chapter_index,
        "scope_key": f"chapter:{target_chapter_index}",
        "memory_type": MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
    }
    prompt_contract = _llm_summary_prompt_contract(
        summary_target=summary_target,
        query=query_text,
        evidence_sources=evidence_sources,
    )
    expected_postcheck = {
        "tool_name": "inspect_agent_memory_tree_quality",
        "params": {"chapter_index": target_chapter_index, "query": query_text},
    }
    return {
        "version": MEMORY_TREE_LLM_SUMMARY_PLAN_VERSION,
        "status": "ready" if evidence_sources else "blocked",
        "project_id": project_id,
        "summary_target": summary_target,
        "evidence_window": {
            "source_count": len(evidence_sources),
            "source_chars": sum(len(str(source.get("excerpt") or "")) for source in evidence_sources),
            "max_source_chars": source_budget,
            "sources": evidence_sources,
        },
        "llm_prompt_contract": prompt_contract,
        "quality_gate": {
            "precheck": quality_precheck,
            "expected_postcheck": expected_postcheck,
            "acceptance": {
                "summary_backed_chapter_ratio": 1.0,
                "semantic_probe_status": "matched" if query_text else "not_requested",
                "diagnostics": [],
            },
        },
        "side_effects": {"executed": [], "skipped": ["record_agent_memory_tree_summaries"]},
        "recommended_next_tools": [
            "summarize_agent_memory_tree_llm_candidate",
            "inspect_agent_memory_tree_llm_candidates",
            "inspect_agent_memory_tree_quality",
        ],
        "trace": {
            "source": "build_agent_memory_tree_llm_summary_plan",
            "version": MEMORY_TREE_LLM_SUMMARY_PLAN_VERSION,
            "mutability": "read",
            "runtime_behavior_changed": False,
            "llm_call_executed": False,
        },
    }


def inspect_agent_memory_tree_llm_candidates(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    normalized_limit = _clamp_candidate_limit(limit)
    query = db.query(AIModelCallTrace).filter(
        AIModelCallTrace.project_id == project_id,
        AIModelCallTrace.trace_type == "memory_tree_summary_generation",
    )
    if chapter_index is not None:
        query = query.filter(AIModelCallTrace.chapter_index == int(chapter_index))
    traces = (
        query.order_by(AIModelCallTrace.created_at.desc(), AIModelCallTrace.id.desc())
        .limit(normalized_limit)
        .all()
    )
    candidates = [_llm_candidate_trace_summary(trace) for trace in traces]
    ready_count = sum(1 for item in candidates if item.get("candidate", {}).get("summary"))
    return {
        "version": MEMORY_TREE_LLM_CANDIDATE_INSPECTION_VERSION,
        "status": "ready" if candidates else "empty",
        "project_id": project_id,
        "filters": {"chapter_index": chapter_index, "limit": normalized_limit},
        "summary": {
            "candidate_traces": len(candidates),
            "ready_candidates": ready_count,
        },
        "candidates": candidates,
        "recommended_next_tools": _llm_candidate_inspection_recommendations(candidates),
        "recommended_next_tool_calls": _llm_candidate_inspection_recommended_tool_calls(candidates),
        "trace": {
            "source": "inspect_agent_memory_tree_llm_candidates",
            "version": MEMORY_TREE_LLM_CANDIDATE_INSPECTION_VERSION,
            "mutability": "read",
            "runtime_behavior_changed": False,
        },
    }


async def summarize_agent_memory_tree_llm_candidate(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
    query: str | None = None,
    max_source_chars: int | None = None,
    ai_service: Any | None = None,
) -> dict[str, Any]:
    plan = build_agent_memory_tree_llm_summary_plan(
        db,
        project_id,
        chapter_index=chapter_index,
        query=query,
        max_source_chars=max_source_chars,
    )
    if plan["status"] != "ready":
        return {
            "version": MEMORY_TREE_LLM_SUMMARY_CANDIDATE_VERSION,
            "status": "blocked",
            "reason": "missing_evidence_sources",
            "project_id": project_id,
            "summary_target": plan["summary_target"],
            "evidence_window": plan["evidence_window"],
            "candidate": None,
            "quality_gate": plan["quality_gate"],
            "side_effects": {"executed": [], "skipped": ["memory_tree_summary_generation_trace"]},
            "recommended_next_tools": [
                "build_agent_memory_tree_llm_summary_plan",
                "inspect_agent_memory_tree_quality",
            ],
            "trace": {
                "source": "summarize_agent_memory_tree_llm_candidate",
                "version": MEMORY_TREE_LLM_SUMMARY_CANDIDATE_VERSION,
                "mutability": "read",
                "llm_call_executed": False,
            },
        }

    prompt_contract = plan["llm_prompt_contract"]
    messages = [
        {"role": "system", "content": str(prompt_contract.get("system_prompt") or "")},
        {"role": "user", "content": str(prompt_contract.get("user_prompt") or "")},
    ]
    summary_target = plan["summary_target"]
    evidence_window = plan["evidence_window"]
    evidence_sources = evidence_window.get("sources") if isinstance(evidence_window.get("sources"), list) else []
    project = db.query(Project).filter(Project.id == project_id).first()
    model = getattr(project, "ai_model", None) or "deepseek-chat"
    temperature = 0.2
    max_tokens = 800
    target_chapter_index = _optional_int(summary_target.get("chapter_index"))
    chapter = (
        db.query(ChapterContent)
        .filter(ChapterContent.project_id == project_id, ChapterContent.chapter_index == target_chapter_index)
        .first()
        if target_chapter_index is not None
        else None
    )
    trace = create_trace(
        db,
        project_id=project_id,
        trace_type=str(prompt_contract.get("trace_type") or "memory_tree_summary_generation"),
        messages=messages,
        context_blocks=_llm_summary_context_blocks(evidence_sources),
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        chapter_id=chapter.id if chapter is not None else None,
        chapter_index=target_chapter_index,
        trace_metadata={
            "memory_tree_llm_summary_candidate": {
                "version": MEMORY_TREE_LLM_SUMMARY_CANDIDATE_VERSION,
                "plan_version": plan.get("version"),
                "summary_target": summary_target,
                "source_count": evidence_window.get("source_count"),
                "source_chars": evidence_window.get("source_chars"),
                "quality_precheck_status": plan["quality_gate"]["precheck"].get("status"),
            }
        },
    )
    db.commit()
    started_at = now_ms()
    service = ai_service or AIService()
    should_close_service = ai_service is None

    try:
        result = await service.complete(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
            response_format={"type": "json_object"},
        )
        candidate = _parse_llm_summary_candidate(getattr(result, "content", "") or "")
        trace.trace_metadata = {
            **(trace.trace_metadata or {}),
            "memory_tree_llm_summary_candidate": {
                **((trace.trace_metadata or {}).get("memory_tree_llm_summary_candidate") or {}),
                "candidate_status": "ready" if candidate["summary"] else "empty",
                "candidate": candidate,
            },
        }
        mark_trace_success(
            db,
            trace,
            prompt_tokens=getattr(result, "prompt_tokens", 0),
            completion_tokens=getattr(result, "completion_tokens", 0),
            latency_ms=now_ms() - started_at,
        )
        db.commit()
    except Exception as exc:
        mark_trace_failed(db, trace, error_message=str(exc), latency_ms=now_ms() - started_at)
        db.commit()
        return {
            "version": MEMORY_TREE_LLM_SUMMARY_CANDIDATE_VERSION,
            "status": "failed",
            "reason": "model_call_failed",
            "error": str(exc),
            "project_id": project_id,
            "summary_target": summary_target,
            "evidence_window": evidence_window,
            "candidate": None,
            "quality_gate": plan["quality_gate"],
            "side_effects": {
                "executed": ["memory_tree_summary_generation_trace"],
                "skipped": ["record_agent_memory_tree_summaries"],
            },
            "recommended_next_tools": [
                "build_agent_memory_tree_llm_summary_plan",
                "inspect_agent_memory_tree_quality",
            ],
            "trace": {
                "source": "summarize_agent_memory_tree_llm_candidate",
                "version": MEMORY_TREE_LLM_SUMMARY_CANDIDATE_VERSION,
                "mutability": "read",
                "trace_id": trace.id,
                "trace_type": trace.trace_type,
                "llm_call_executed": True,
                "status": "failed",
            },
        }
    finally:
        if should_close_service:
            close = getattr(service, "close", None)
            if callable(close):
                await close()

    return {
        "version": MEMORY_TREE_LLM_SUMMARY_CANDIDATE_VERSION,
        "status": "ready" if candidate["summary"] else "blocked",
        "project_id": project_id,
        "summary_target": summary_target,
        "evidence_window": evidence_window,
        "candidate": candidate,
        "quality_gate": plan["quality_gate"],
        "candidate_write_policy": {
            "materialization_requires_approval": True,
            "approval_tools": [
                "prepare_record_agent_memory_tree_llm_candidate_summary",
                "execute_record_agent_memory_tree_llm_candidate_summary_with_approval",
            ],
        },
        "side_effects": {
            "executed": ["memory_tree_summary_generation_trace"],
            "skipped": ["record_agent_memory_tree_summaries"],
        },
        "recommended_next_tools": [
            "prepare_record_agent_memory_tree_llm_candidate_summary",
            "execute_record_agent_memory_tree_llm_candidate_summary_with_approval",
            "inspect_agent_memory_tree_quality",
        ],
        "trace": {
            "source": "summarize_agent_memory_tree_llm_candidate",
            "version": MEMORY_TREE_LLM_SUMMARY_CANDIDATE_VERSION,
            "mutability": "read",
            "trace_id": trace.id,
            "trace_type": trace.trace_type,
            "llm_call_executed": True,
            "status": trace.status,
        },
    }


def inspect_agent_memory_tree_llm_candidate_trace(
    db: Session,
    project_id: str,
    *,
    candidate_trace_id: str | None,
) -> dict[str, Any]:
    trace_id = str(candidate_trace_id or "").strip()
    if not trace_id:
        return _llm_candidate_trace_blocked(project_id, reason="candidate_trace_id_required")
    trace = (
        db.query(AIModelCallTrace)
        .filter(
            AIModelCallTrace.id == trace_id,
            AIModelCallTrace.project_id == project_id,
            AIModelCallTrace.trace_type == "memory_tree_summary_generation",
        )
        .first()
    )
    if trace is None:
        return _llm_candidate_trace_blocked(project_id, reason="candidate_trace_not_found")

    candidate_trace = _llm_candidate_trace_summary(trace)
    if candidate_trace["trace_status"] != "success":
        return _llm_candidate_trace_blocked(
            project_id,
            reason="candidate_trace_not_successful",
            candidate_trace=candidate_trace,
        )
    candidate = candidate_trace["candidate"]
    if not candidate.get("summary"):
        return _llm_candidate_trace_blocked(
            project_id,
            reason="candidate_summary_required",
            candidate_trace=candidate_trace,
        )
    summary_target = candidate_trace["summary_target"]
    if not _valid_llm_candidate_summary_target(summary_target):
        return _llm_candidate_trace_blocked(
            project_id,
            reason="candidate_summary_target_invalid",
            candidate_trace=candidate_trace,
        )
    return {
        "version": MEMORY_TREE_LLM_CANDIDATE_INSPECTION_VERSION,
        "status": "ready",
        "project_id": project_id,
        "candidate_trace_id": trace.id,
        "candidate_trace": candidate_trace,
        "summary_target": summary_target,
        "candidate": candidate,
        "candidate_summary_hash": _candidate_summary_hash(candidate),
        "trace": {
            "source": "inspect_agent_memory_tree_llm_candidate_trace",
            "mutability": "read",
            "runtime_behavior_changed": False,
        },
    }


def materialize_agent_memory_tree_llm_candidate_summary(
    db: Session,
    project_id: str,
    *,
    candidate_trace_id: str | None,
) -> dict[str, Any]:
    candidate_summary = inspect_agent_memory_tree_llm_candidate_trace(
        db,
        project_id,
        candidate_trace_id=candidate_trace_id,
    )
    if candidate_summary.get("status") != "ready":
        return {
            "version": MEMORY_TREE_LLM_CANDIDATE_MATERIALIZATION_VERSION,
            "status": "blocked",
            "project_id": project_id,
            "reason": candidate_summary.get("reason"),
            "candidate_summary": candidate_summary,
            "side_effects": {"executed": [], "skipped": ["longform_memories"]},
        }

    summary_target = candidate_summary["summary_target"]
    chapter_index = _optional_int(summary_target.get("chapter_index"))
    if chapter_index is None:
        return {
            "version": MEMORY_TREE_LLM_CANDIDATE_MATERIALIZATION_VERSION,
            "status": "blocked",
            "project_id": project_id,
            "reason": "candidate_chapter_index_required",
            "candidate_summary": candidate_summary,
            "side_effects": {"executed": [], "skipped": ["longform_memories"]},
        }
    chapter = (
        db.query(ChapterContent)
        .filter(ChapterContent.project_id == project_id, ChapterContent.chapter_index == chapter_index)
        .first()
    )
    candidate = candidate_summary["candidate"]
    candidate_trace = candidate_summary["candidate_trace"]
    record, was_created = _upsert_summary_memory(
        db,
        project_id=project_id,
        memory_type=MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
        scope_key=str(summary_target.get("scope_key") or f"chapter:{chapter_index}"),
        start_chapter_index=chapter_index,
        end_chapter_index=chapter_index,
        title=(chapter.title if chapter is not None and chapter.title else f"Chapter {chapter_index}"),
        summary=str(candidate.get("summary") or "").strip(),
        metadata={
            "level": "chapter",
            "chapter_index": chapter_index,
            "source": "memory_tree_llm_candidate_trace",
            "candidate_trace_id": candidate_summary["candidate_trace_id"],
            "candidate_summary_hash": candidate_summary["candidate_summary_hash"],
            "model": candidate_trace.get("model"),
            "prompt_tokens": candidate_trace.get("prompt_tokens"),
            "completion_tokens": candidate_trace.get("completion_tokens"),
            "candidate": candidate,
        },
    )
    db.commit()
    return {
        "version": MEMORY_TREE_LLM_CANDIDATE_MATERIALIZATION_VERSION,
        "status": "completed",
        "project_id": project_id,
        "candidate_summary": candidate_summary,
        "summary": {
            "candidate_summary_nodes": 1,
            "created_nodes": 1 if was_created else 0,
            "updated_nodes": 0 if was_created else 1,
        },
        "nodes": [_summary_record_projection(record)],
        "side_effects": {"executed": ["longform_memories"], "skipped": []},
        "trace": {
            "source": "materialize_agent_memory_tree_llm_candidate_summary",
            "storage": "longform_memories",
            "memory_type": MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
        },
    }


def _select_nodes(
    nodes: list[dict[str, Any]],
    *,
    level: str | None,
    node_id: str | None,
    expand_node_id: str | None,
    chapter_index: int | None,
    query: str | None,
    include_ancestors: bool,
    max_depth: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    nodes_by_id = {node["id"]: node for node in nodes}
    normalised_max_depth = _normalise_max_depth(max_depth)
    ancestor_node_ids: list[str] = []
    descendant_node_ids: list[str] = []
    relevance_by_id: dict[str, dict[str, Any]] = {}
    recommended_drilldowns: list[dict[str, Any]] = []
    semantic_search = False

    if expand_node_id:
        matched_node_ids = [expand_node_id] if expand_node_id in nodes_by_id else []
        descendant_node_ids = _descendant_node_ids(
            nodes_by_id,
            expand_node_id,
            max_depth=normalised_max_depth,
        )
        selected_node_ids = set(matched_node_ids) | set(descendant_node_ids)
        if include_ancestors:
            ancestor_node_ids = _ancestor_node_ids(nodes_by_id, matched_node_ids)
            selected_node_ids.update(ancestor_node_ids)
        mode = "expanded_subtree"
    else:
        matched_nodes, relevance_by_id, semantic_search = _filter_nodes(
            nodes,
            level=level,
            node_id=node_id,
            chapter_index=chapter_index,
            query=query,
        )
        matched_node_ids = [node["id"] for node in matched_nodes]
        selected_node_ids = set(matched_node_ids)
        if include_ancestors:
            ancestor_node_ids = _ancestor_node_ids(nodes_by_id, matched_node_ids)
            selected_node_ids.update(ancestor_node_ids)
        mode = _navigation_mode(query=query, include_ancestors=include_ancestors, semantic_search=semantic_search)
        recommended_drilldowns = _recommended_drilldowns(matched_nodes, relevance_by_id)

    return [_navigation_node(node, relevance_by_id) for node in nodes if node["id"] in selected_node_ids], {
        "mode": mode,
        "matched_node_ids": matched_node_ids,
        "expanded_node_id": expand_node_id,
        "include_ancestors": include_ancestors,
        "max_depth": normalised_max_depth,
        "ancestor_node_ids": ancestor_node_ids,
        "descendant_node_ids": descendant_node_ids,
        "recommended_drilldowns": recommended_drilldowns,
    }


def _memory_tree_quality_coverage(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    volume_nodes = [node for node in nodes if node.get("level") == "volume"]
    chapter_nodes = [node for node in nodes if node.get("level") == "chapter"]
    scene_nodes = [node for node in nodes if node.get("level") == "scene"]
    beat_nodes = [node for node in nodes if node.get("level") == "beat"]
    summary_backed_volume_nodes = [node for node in volume_nodes if _node_has_source_type(node, "longform_memory")]
    summary_backed_chapter_nodes = [node for node in chapter_nodes if _node_has_source_type(node, "longform_memory")]
    chapter_nodes_with_children = [node for node in chapter_nodes if node.get("children")]
    return {
        "volume_nodes": len(volume_nodes),
        "chapter_nodes": len(chapter_nodes),
        "scene_nodes": len(scene_nodes),
        "beat_nodes": len(beat_nodes),
        "summary_backed_volume_nodes": len(summary_backed_volume_nodes),
        "summary_backed_chapter_nodes": len(summary_backed_chapter_nodes),
        "chapter_nodes_with_children": len(chapter_nodes_with_children),
        "chapter_node_coverage_ratio": _ratio(len(chapter_nodes), len(chapter_nodes)),
        "summary_backed_chapter_ratio": _ratio(len(summary_backed_chapter_nodes), len(chapter_nodes)),
    }


def _memory_tree_semantic_probe(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None,
    query: str | None,
) -> dict[str, Any]:
    query_text = str(query or "").strip()
    if not query_text:
        return {
            "status": "not_requested",
            "query": None,
            "chapter_index": chapter_index,
            "matched_node_count": 0,
            "matched_levels": [],
            "recommended_drilldown_count": 0,
            "top_match": None,
        }
    probe_tree = inspect_agent_memory_tree(
        db,
        project_id,
        level="chapter",
        chapter_index=chapter_index,
        query=query_text,
    )
    nodes = probe_tree.get("nodes") if isinstance(probe_tree.get("nodes"), list) else []
    navigation = probe_tree.get("navigation") if isinstance(probe_tree.get("navigation"), dict) else {}
    return {
        "status": "matched" if nodes else "missing_match",
        "query": query_text,
        "chapter_index": chapter_index,
        "matched_node_count": len(nodes),
        "matched_levels": _dedupe([str(node.get("level") or "") for node in nodes]),
        "recommended_drilldown_count": len(navigation.get("recommended_drilldowns") or []),
        "top_match": _memory_tree_quality_top_match(nodes[0]) if nodes else None,
    }


def _memory_tree_quality_top_match(node: dict[str, Any]) -> dict[str, Any]:
    relevance = node.get("relevance") if isinstance(node.get("relevance"), dict) else {}
    return {
        "level": str(node.get("level") or ""),
        "chapter_index": node.get("chapter_index"),
        "title": str(node.get("title") or ""),
        "score": float(relevance.get("score") or 0),
        "matched_fields": _dedupe([str(field) for field in relevance.get("matched_fields") or []]),
        "match_reasons": _dedupe([str(reason) for reason in relevance.get("match_reasons") or []]),
        "matched_descendant_count": len(relevance.get("matched_descendant_ids") or []),
    }


def _memory_tree_quality_diagnostics(
    coverage: dict[str, Any],
    semantic_probe: dict[str, Any],
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    if int(coverage.get("chapter_nodes") or 0) <= 0:
        diagnostics.append(
            {
                "code": "memory_tree_no_chapter_nodes",
                "severity": "warning",
                "message": "Memory Tree has no chapter nodes to validate.",
            }
        )
    if float(coverage.get("summary_backed_chapter_ratio") or 0) < 1:
        diagnostics.append(
            {
                "code": "memory_tree_summary_gap",
                "severity": "warning",
                "message": "Some chapter nodes are not backed by materialized summary memory.",
            }
        )
    if semantic_probe.get("status") == "missing_match":
        diagnostics.append(
            {
                "code": "memory_tree_semantic_probe_miss",
                "severity": "info",
                "message": "The requested semantic probe did not match a Memory Tree node.",
            }
        )
    return diagnostics


def _memory_tree_quality_recommendations(diagnostics: list[dict[str, Any]]) -> list[str]:
    tools = ["inspect_agent_memory_tree", "inspect_agent_dogfood_evidence"]
    if any(item.get("code") == "memory_tree_summary_gap" for item in diagnostics):
        tools.insert(0, "record_agent_memory_tree_summaries")
    return _dedupe(tools)


def _node_has_source_type(node: dict[str, Any], source_type: str) -> bool:
    source_refs = node.get("source_refs") if isinstance(node.get("source_refs"), list) else []
    return any(isinstance(ref, dict) and ref.get("source_type") == source_type for ref in source_refs)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def materialize_agent_memory_tree_summaries(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
) -> dict[str, Any]:
    chapters = _chapters(db, project_id)
    if chapter_index is not None:
        chapters = [chapter for chapter in chapters if int(chapter.chapter_index) == int(chapter_index)]
    outline = _outline(db, project_id)
    storyline = _storyline(db, project_id)
    outline_by_chapter = _outline_by_chapter(outline)
    created = 0
    updated = 0
    volume_records: list[LongformMemory] = []
    chapter_records: list[LongformMemory] = []

    chapters_by_volume: dict[int, list[ChapterContent]] = {}
    for chapter in chapters:
        chapters_by_volume.setdefault(_volume_index(chapter.chapter_index), []).append(chapter)

    for volume_index, volume_chapters in sorted(chapters_by_volume.items()):
        record, was_created = _upsert_summary_memory(
            db,
            project_id=project_id,
            memory_type=MEMORY_TREE_VOLUME_SUMMARY_TYPE,
            scope_key=f"volume:{volume_index}",
            start_chapter_index=min(int(chapter.chapter_index) for chapter in volume_chapters),
            end_chapter_index=max(int(chapter.chapter_index) for chapter in volume_chapters),
            title=f"Volume {volume_index}",
            summary=_volume_summary(volume_index, chapters=volume_chapters, outline=outline, storyline=storyline),
            metadata={"level": "volume", "volume_index": volume_index},
        )
        volume_records.append(record)
        if was_created:
            created += 1
        else:
            updated += 1

    for chapter in chapters:
        chapter_index_value = int(chapter.chapter_index)
        record, was_created = _upsert_summary_memory(
            db,
            project_id=project_id,
            memory_type=MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
            scope_key=f"chapter:{chapter_index_value}",
            start_chapter_index=chapter_index_value,
            end_chapter_index=chapter_index_value,
            title=chapter.title or f"Chapter {chapter_index_value}",
            summary=_chapter_summary(chapter, outline_by_chapter.get(chapter_index_value)),
            metadata={"level": "chapter", "chapter_index": chapter_index_value},
        )
        chapter_records.append(record)
        if was_created:
            created += 1
        else:
            updated += 1

    db.commit()
    return {
        "version": MEMORY_TREE_SUMMARY_MATERIALIZATION_VERSION,
        "status": "completed",
        "project_id": project_id,
        "summary": {
            "volume_summary_nodes": len(volume_records),
            "chapter_summary_nodes": len(chapter_records),
            "created_nodes": created,
            "updated_nodes": updated,
        },
        "nodes": [
            _summary_record_projection(record)
            for record in sorted(
                [*volume_records, *chapter_records],
                key=lambda item: (item.start_chapter_index or 0, item.memory_type, item.scope_key),
            )
        ],
        "trace": {
            "source": "materialize_agent_memory_tree_summaries",
            "storage": "longform_memories",
            "memory_types": list(MEMORY_TREE_SUMMARY_TYPES),
        },
    }


def _build_nodes(
    *,
    chapters: list[ChapterContent],
    outline: Outline | None,
    storyline: Storyline | None,
    memories: list[LongformMemory],
) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    nodes_by_id: dict[str, dict[str, Any]] = {}
    outline_by_chapter = _outline_by_chapter(outline)
    chapter_by_index = {int(chapter.chapter_index): chapter for chapter in chapters}
    summary_by_scope = _summary_memories_by_scope(memories)

    for volume_index in sorted({_volume_index(chapter.chapter_index) for chapter in chapters} or {1}):
        volume_node = _volume_node(
            volume_index,
            outline=outline,
            storyline=storyline,
            summary_memory=summary_by_scope.get((MEMORY_TREE_VOLUME_SUMMARY_TYPE, f"volume:{volume_index}")),
        )
        nodes.append(volume_node)
        nodes_by_id[volume_node["id"]] = volume_node

    for chapter in chapters:
        volume_id = f"volume:{_volume_index(chapter.chapter_index)}"
        chapter_index = int(chapter.chapter_index)
        chapter_node = _chapter_node(
            chapter,
            outline=outline,
            outline_item=outline_by_chapter.get(chapter_index),
            summary_memory=summary_by_scope.get((MEMORY_TREE_CHAPTER_SUMMARY_TYPE, f"chapter:{chapter_index}")),
        )
        nodes.append(chapter_node)
        nodes_by_id[chapter_node["id"]] = chapter_node
        _append_child(nodes_by_id, volume_id, chapter_node["id"])

    scene_memories = [memory for memory in memories if memory.memory_type == "scene"]
    beat_memories = [memory for memory in memories if memory.memory_type == "beat"]
    scenes_by_scope = {memory.scope_key: memory for memory in scene_memories}

    for memory in scene_memories:
        scene_node = _memory_node("scene", memory, chapter_by_index)
        nodes.append(scene_node)
        nodes_by_id[scene_node["id"]] = scene_node
        _append_child(nodes_by_id, scene_node["parent_id"], scene_node["id"])

    for memory in beat_memories:
        beat_node = _memory_node("beat", memory, chapter_by_index, scenes_by_scope=scenes_by_scope)
        nodes.append(beat_node)
        nodes_by_id[beat_node["id"]] = beat_node
        _append_child(nodes_by_id, beat_node["parent_id"], beat_node["id"])

    return nodes


def _volume_node(
    volume_index: int,
    *,
    outline: Outline | None,
    storyline: Storyline | None,
    summary_memory: LongformMemory | None,
) -> dict[str, Any]:
    source_refs: list[dict[str, str]] = []
    if outline is not None:
        source_refs.append({"source_type": "outline", "source_id": outline.id})
    if storyline is not None:
        source_refs.append({"source_type": "storyline", "source_id": storyline.id})
    if summary_memory is not None:
        source_refs.append({"source_type": "longform_memory", "source_id": summary_memory.id})
    return {
        "id": f"volume:{volume_index}",
        "level": "volume",
        "parent_id": None,
        "chapter_index": None,
        "title": f"Volume {volume_index}",
        "summary": summary_memory.summary if summary_memory is not None else "",
        "source_refs": source_refs,
        "children": [],
    }


def _chapter_node(
    chapter: ChapterContent,
    *,
    outline: Outline | None,
    outline_item: dict[str, Any] | None,
    summary_memory: LongformMemory | None,
) -> dict[str, Any]:
    chapter_index = int(chapter.chapter_index)
    source_refs = [{"source_type": "chapter_content", "source_id": chapter.id}]
    if outline is not None and outline_item is not None:
        source_refs.append({"source_type": "outline", "source_id": outline.id})
    if summary_memory is not None:
        source_refs.append({"source_type": "longform_memory", "source_id": summary_memory.id})
    return {
        "id": f"chapter:{chapter_index}",
        "level": "chapter",
        "parent_id": f"volume:{_volume_index(chapter_index)}",
        "chapter_index": chapter_index,
        "title": chapter.title or str((outline_item or {}).get("title") or f"Chapter {chapter_index}"),
        "summary": (
            summary_memory.summary
            if summary_memory is not None
            else str((outline_item or {}).get("summary") or "")
        ),
        "source_refs": source_refs,
        "children": [],
    }


def _memory_node(
    level: str,
    memory: LongformMemory,
    chapter_by_index: dict[int, ChapterContent],
    *,
    scenes_by_scope: dict[str, LongformMemory] | None = None,
) -> dict[str, Any]:
    chapter_index = _memory_chapter_index(memory)
    parent_id = f"chapter:{chapter_index}" if chapter_index is not None else "volume:1"
    if level == "beat" and scenes_by_scope:
        scene_scope = _metadata_value(memory, "scene_scope_key")
        scene_memory = scenes_by_scope.get(scene_scope)
        if scene_memory is not None:
            parent_id = f"scene:{scene_memory.id}"
    source_refs = [{"source_type": "longform_memory", "source_id": memory.id}]
    chapter = chapter_by_index.get(chapter_index) if chapter_index is not None else None
    if chapter is not None:
        source_refs.append({"source_type": "chapter_content", "source_id": chapter.id})
    return {
        "id": f"{level}:{memory.id}",
        "level": level,
        "parent_id": parent_id,
        "chapter_index": chapter_index,
        "title": memory.title or memory.scope_key,
        "summary": memory.summary or "",
        "scope_key": memory.scope_key,
        "source_refs": source_refs,
        "children": [],
    }


def _filter_nodes(
    nodes: list[dict[str, Any]],
    *,
    level: str | None,
    node_id: str | None,
    chapter_index: int | None,
    query: str | None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], bool]:
    query_text = str(query or "").strip().lower()
    filtered = _candidate_nodes(nodes, level=level, node_id=node_id, chapter_index=chapter_index)
    if not query_text:
        return filtered, {}, False
    exact_matches = [node for node in filtered if _exact_query_match(node, query_text)]
    if exact_matches:
        return exact_matches, {}, False
    semantic_matches = _semantic_node_matches(
        filtered,
        query_text,
        all_nodes=nodes,
        rollup_descendants=bool(level or node_id or chapter_index is not None),
    )
    return [item["node"] for item in semantic_matches], {
        str(item["node"]["id"]): item["relevance"] for item in semantic_matches
    }, bool(semantic_matches)


def _candidate_nodes(
    nodes: list[dict[str, Any]],
    *,
    level: str | None,
    node_id: str | None,
    chapter_index: int | None,
) -> list[dict[str, Any]]:
    filtered = nodes
    if level:
        filtered = [node for node in filtered if node["level"] == level]
    if node_id:
        filtered = [node for node in filtered if node["id"] == node_id]
    if chapter_index is not None:
        filtered = [node for node in filtered if node["chapter_index"] == chapter_index]
    return filtered


def _exact_query_match(node: dict[str, Any], query_text: str) -> bool:
    return query_text in str(node.get("title") or "").lower() or query_text in str(node.get("summary") or "").lower()


def _semantic_node_matches(
    nodes: list[dict[str, Any]],
    query_text: str,
    *,
    all_nodes: list[dict[str, Any]],
    rollup_descendants: bool,
) -> list[dict[str, Any]]:
    query_terms = _query_terms(query_text)
    if not query_terms:
        return []
    nodes_by_id = {str(node.get("id") or ""): node for node in all_nodes}
    matches: list[dict[str, Any]] = []
    for node in nodes:
        relevance = _node_relevance(node, query_terms=query_terms, query_text=query_text)
        descendant_relevance = (
            _descendant_relevance(
                node,
                nodes_by_id=nodes_by_id,
                query_terms=query_terms,
                query_text=query_text,
            )
            if rollup_descendants
            else _empty_relevance(query_text)
        )
        relevance = _merge_relevance(relevance, descendant_relevance, query_text=query_text)
        if float(relevance["score"]) < MIN_SEMANTIC_RELEVANCE_SCORE:
            continue
        matches.append({"node": node, "relevance": relevance})
    return sorted(
        matches,
        key=lambda item: (
            -float(item["relevance"]["score"]),
            _level_rank(str(item["node"].get("level") or "")),
            str(item["node"].get("id") or ""),
        ),
    )


def _node_relevance(
    node: dict[str, Any],
    *,
    query_terms: list[str],
    query_text: str,
) -> dict[str, Any]:
    field_values = {
        "title": str(node.get("title") or "").lower(),
        "summary": str(node.get("summary") or "").lower(),
        "scope_key": str(node.get("scope_key") or "").lower(),
    }
    matched_terms: list[str] = []
    matched_fields: list[str] = []
    for field_name, value in field_values.items():
        field_matched = [term for term in query_terms if term and term in value]
        if not field_matched:
            continue
        matched_fields.append(field_name)
        for term in field_matched:
            if term not in matched_terms:
                matched_terms.append(term)
    if not matched_terms:
        return {
            "score": 0,
            "query": query_text,
            "matched_terms": [],
            "matched_fields": [],
            "match_reasons": [],
        }
    field_bonus = 0.1 * len(matched_fields)
    title_bonus = 0.1 if "title" in matched_fields else 0
    score = round((len(matched_terms) / len(query_terms)) + field_bonus + title_bonus, 4)
    return {
        "score": score,
        "query": query_text,
        "matched_terms": matched_terms,
        "matched_fields": matched_fields,
        "match_reasons": ["semantic_token_overlap"],
    }


def _descendant_relevance(
    node: dict[str, Any],
    *,
    nodes_by_id: dict[str, dict[str, Any]],
    query_terms: list[str],
    query_text: str,
) -> dict[str, Any]:
    node_id = str(node.get("id") or "")
    descendant_matches: list[dict[str, Any]] = []
    for descendant_id in _descendant_node_ids(nodes_by_id, node_id, max_depth=None):
        descendant = nodes_by_id.get(descendant_id)
        if descendant is None:
            continue
        relevance = _node_relevance(descendant, query_terms=query_terms, query_text=query_text)
        if float(relevance["score"]) < MIN_SEMANTIC_RELEVANCE_SCORE:
            continue
        descendant_matches.append({"node_id": descendant_id, "relevance": relevance})
    if not descendant_matches:
        return _empty_relevance(query_text)
    descendant_matches = sorted(
        descendant_matches,
        key=lambda item: (
            -float(item["relevance"]["score"]),
            str(item["node_id"]),
        ),
    )
    matched_terms: list[str] = []
    matched_fields: list[str] = []
    matched_descendant_ids: list[str] = []
    for match in descendant_matches:
        relevance = match["relevance"]
        matched_descendant_ids.append(str(match["node_id"]))
        for term in relevance.get("matched_terms") or []:
            if term not in matched_terms:
                matched_terms.append(str(term))
        for field in relevance.get("matched_fields") or []:
            descendant_field = f"descendant.{field}"
            if descendant_field not in matched_fields:
                matched_fields.append(descendant_field)
    top_score = float(descendant_matches[0]["relevance"]["score"])
    return {
        "score": round(top_score * 0.95, 4),
        "query": query_text,
        "matched_terms": matched_terms,
        "matched_fields": matched_fields,
        "match_reasons": ["descendant_semantic_match"],
        "matched_descendant_ids": matched_descendant_ids,
    }


def _merge_relevance(
    direct: dict[str, Any],
    descendant: dict[str, Any],
    *,
    query_text: str,
) -> dict[str, Any]:
    if float(direct.get("score") or 0) <= 0 and float(descendant.get("score") or 0) <= 0:
        return _empty_relevance(query_text)
    if float(descendant.get("score") or 0) > float(direct.get("score") or 0):
        base = dict(descendant)
    else:
        base = dict(direct)
    return {
        "score": base.get("score") or 0,
        "query": query_text,
        "matched_terms": _dedupe([str(term) for term in base.get("matched_terms") or []]),
        "matched_fields": _dedupe([str(field) for field in base.get("matched_fields") or []]),
        "match_reasons": _dedupe([str(reason) for reason in base.get("match_reasons") or []]),
        **(
            {"matched_descendant_ids": _dedupe([str(node_id) for node_id in base.get("matched_descendant_ids") or []])}
            if base.get("matched_descendant_ids")
            else {}
        ),
    }


def _empty_relevance(query_text: str) -> dict[str, Any]:
    return {
        "score": 0,
        "query": query_text,
        "matched_terms": [],
        "matched_fields": [],
        "match_reasons": [],
    }


def _query_terms(query_text: str) -> list[str]:
    terms: list[str] = []
    word = ""
    for char in query_text:
        if _is_cjk(char):
            if word:
                terms.append(word)
                word = ""
            terms.append(char)
        elif char.isalnum():
            word += char
        elif word:
            terms.append(word)
            word = ""
    if word:
        terms.append(word)
    return _dedupe([term.lower() for term in terms if term.strip()])


def _is_cjk(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff"


def _navigation_mode(*, query: str | None, include_ancestors: bool, semantic_search: bool) -> str:
    if not query:
        return "filtered"
    if semantic_search and include_ancestors:
        return "semantic_search_with_ancestors"
    if semantic_search:
        return "semantic_search"
    return "search_with_ancestors" if include_ancestors else "filtered"


def _navigation_node(node: dict[str, Any], relevance_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    relevance = relevance_by_id.get(str(node.get("id") or ""))
    if not relevance:
        return node
    output = dict(node)
    output["relevance"] = relevance
    return output


def _recommended_drilldowns(
    matched_nodes: list[dict[str, Any]],
    relevance_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not relevance_by_id or not matched_nodes:
        return []
    top_node = matched_nodes[0]
    relevance = relevance_by_id.get(str(top_node.get("id") or ""))
    if not relevance:
        return []
    if relevance.get("matched_descendant_ids"):
        return [
            {
                "node_id": top_node["id"],
                "expand_node_id": top_node["id"],
                "reason": "descendant_relevance",
                "score": relevance["score"],
                "matched_descendant_ids": [str(node_id) for node_id in relevance.get("matched_descendant_ids") or []],
            }
        ]
    return [
        {
            "node_id": top_node["id"],
            "expand_node_id": top_node["id"],
            "reason": "highest_relevance",
            "score": relevance["score"],
        }
    ]


def _level_rank(level: str) -> int:
    try:
        return MEMORY_TREE_LEVELS.index(level)
    except ValueError:
        return len(MEMORY_TREE_LEVELS)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _ancestor_node_ids(nodes_by_id: dict[str, dict[str, Any]], node_ids: list[str]) -> list[str]:
    ancestor_ids: list[str] = []
    seen: set[str] = set()
    for node_id in node_ids:
        node = nodes_by_id.get(node_id)
        if node is None:
            continue
        path: list[str] = []
        parent_id = node.get("parent_id")
        while parent_id and parent_id in nodes_by_id:
            path.append(parent_id)
            parent_id = nodes_by_id[parent_id].get("parent_id")
        for ancestor_id in reversed(path):
            if ancestor_id not in seen:
                ancestor_ids.append(ancestor_id)
                seen.add(ancestor_id)
    return ancestor_ids


def _descendant_node_ids(
    nodes_by_id: dict[str, dict[str, Any]],
    node_id: str,
    *,
    max_depth: int | None,
) -> list[str]:
    if node_id not in nodes_by_id:
        return []
    descendant_ids: list[str] = []
    queue = [(child_id, 1) for child_id in nodes_by_id[node_id].get("children", [])]
    while queue:
        current_id, depth = queue.pop(0)
        if current_id not in nodes_by_id:
            continue
        if max_depth is not None and depth > max_depth:
            continue
        descendant_ids.append(current_id)
        if max_depth is None or depth < max_depth:
            queue.extend((child_id, depth + 1) for child_id in nodes_by_id[current_id].get("children", []))
    return descendant_ids


def _summary(nodes: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "volume_nodes": sum(1 for node in nodes if node["level"] == "volume"),
        "chapter_nodes": sum(1 for node in nodes if node["level"] == "chapter"),
        "scene_nodes": sum(1 for node in nodes if node["level"] == "scene"),
        "beat_nodes": sum(1 for node in nodes if node["level"] == "beat"),
    }


def _target_summary_chapter_index(db: Session, project_id: str, chapter_index: int | None) -> int:
    if chapter_index and int(chapter_index) > 0:
        return int(chapter_index)
    latest = (
        db.query(ChapterContent)
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.content.isnot(None),
            ChapterContent.content != "",
        )
        .order_by(ChapterContent.chapter_index.desc(), ChapterContent.id.desc())
        .first()
    )
    return int(latest.chapter_index) if latest is not None else 1


def _clamp_source_chars(value: int | None) -> int:
    if value is None:
        return DEFAULT_LLM_SUMMARY_SOURCE_CHARS
    return max(MIN_LLM_SUMMARY_SOURCE_CHARS, min(MAX_LLM_SUMMARY_SOURCE_CHARS, int(value)))


def _clamp_candidate_limit(value: int | None) -> int:
    if value is None:
        return 5
    return max(1, min(20, int(value)))


def _llm_candidate_trace_summary(trace: AIModelCallTrace) -> dict[str, Any]:
    metadata = trace.trace_metadata if isinstance(trace.trace_metadata, dict) else {}
    candidate_metadata = metadata.get("memory_tree_llm_summary_candidate")
    if not isinstance(candidate_metadata, dict):
        candidate_metadata = {}
    candidate = candidate_metadata.get("candidate")
    if not isinstance(candidate, dict):
        candidate = {}
    return {
        "trace_id": trace.id,
        "trace_status": trace.status,
        "chapter_index": trace.chapter_index,
        "model": trace.model,
        "prompt_tokens": trace.prompt_tokens,
        "completion_tokens": trace.completion_tokens,
        "summary_target": candidate_metadata.get("summary_target") if isinstance(candidate_metadata.get("summary_target"), dict) else {},
        "candidate": _normalise_candidate_payload(candidate),
        "source_count": _optional_int(candidate_metadata.get("source_count")) or 0,
        "source_chars": _optional_int(candidate_metadata.get("source_chars")) or 0,
        "quality_precheck_status": str(candidate_metadata.get("quality_precheck_status") or ""),
    }


def _normalise_candidate_payload(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": str(candidate.get("summary") or "").strip(),
        "salient_terms": _string_list(candidate.get("salient_terms")),
        "open_questions": _string_list(candidate.get("open_questions")),
        "source_coverage": _string_list(candidate.get("source_coverage")),
    }


def _llm_candidate_inspection_recommendations(candidates: list[dict[str, Any]]) -> list[str]:
    if not candidates:
        return ["summarize_agent_memory_tree_llm_candidate", "build_agent_memory_tree_llm_summary_plan"]
    return [
        "prepare_record_agent_memory_tree_llm_candidate_summary",
        "execute_record_agent_memory_tree_llm_candidate_summary_with_approval",
        "inspect_agent_memory_tree_quality",
    ]


def _llm_candidate_inspection_recommended_tool_calls(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidate_trace = next(
        (item for item in candidates if str((item.get("candidate") or {}).get("summary") or "").strip()),
        None,
    )
    if candidate_trace is None:
        return []
    params: dict[str, Any] = {"candidate_trace_id": candidate_trace.get("trace_id")}
    summary_target = candidate_trace.get("summary_target")
    if not isinstance(summary_target, dict):
        summary_target = {}
    chapter_index = _optional_int(summary_target.get("chapter_index") or candidate_trace.get("chapter_index"))
    if chapter_index is not None:
        params["quality_chapter_index"] = chapter_index
    quality_query = _first_llm_candidate_quality_query(candidate_trace.get("candidate"))
    if quality_query:
        params["quality_query"] = quality_query
    return [
        {
            "tool_name": "prepare_record_agent_memory_tree_llm_candidate_summary",
            "params": params,
            "requires_confirmation": False,
        }
    ]


def _first_llm_candidate_quality_query(candidate: Any) -> str | None:
    if not isinstance(candidate, dict):
        return None
    for term in _string_list(candidate.get("salient_terms")):
        if term:
            return term
    return None


def _llm_candidate_trace_blocked(
    project_id: str,
    *,
    reason: str,
    candidate_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "version": MEMORY_TREE_LLM_CANDIDATE_INSPECTION_VERSION,
        "status": "blocked",
        "project_id": project_id,
        "reason": reason,
        "candidate_trace": candidate_trace,
        "recommended_next_tools": [
            "inspect_agent_memory_tree_llm_candidates",
            "summarize_agent_memory_tree_llm_candidate",
        ],
        "trace": {
            "source": "inspect_agent_memory_tree_llm_candidate_trace",
            "mutability": "read",
            "runtime_behavior_changed": False,
        },
    }


def _valid_llm_candidate_summary_target(summary_target: dict[str, Any]) -> bool:
    return (
        isinstance(summary_target, dict)
        and summary_target.get("level") == "chapter"
        and summary_target.get("memory_type") == MEMORY_TREE_CHAPTER_SUMMARY_TYPE
        and _optional_int(summary_target.get("chapter_index")) is not None
        and bool(str(summary_target.get("scope_key") or "").strip())
    )


def _candidate_summary_hash(candidate: dict[str, Any]) -> str:
    normalized = _normalise_candidate_payload(candidate)
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _llm_summary_evidence_sources(
    *,
    chapter: ChapterContent | None,
    outline: Outline | None,
    outline_item: dict[str, Any] | None,
    storyline: Storyline | None,
    memories: list[LongformMemory],
    chapter_index: int,
    max_source_chars: int,
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    used_chars = 0
    used_chars = _append_limited_source(
        sources,
        used_chars=used_chars,
        max_source_chars=max_source_chars,
        source_type="chapter_content",
        source_id=chapter.id if chapter is not None else None,
        title=chapter.title if chapter is not None else f"Chapter {chapter_index}",
        text=str(chapter.content or "") if chapter is not None else "",
        chapter_index=chapter_index,
    )
    used_chars = _append_limited_source(
        sources,
        used_chars=used_chars,
        max_source_chars=max_source_chars,
        source_type="outline",
        source_id=outline.id if outline is not None else None,
        title=str((outline_item or {}).get("title") or f"Outline chapter {chapter_index}"),
        text=str((outline_item or {}).get("summary") or ""),
        chapter_index=chapter_index,
    )
    used_chars = _append_limited_source(
        sources,
        used_chars=used_chars,
        max_source_chars=max_source_chars,
        source_type="storyline",
        source_id=storyline.id if storyline is not None else None,
        title="Storyline",
        text=_storyline_evidence_text(storyline, chapter_index=chapter_index),
        chapter_index=chapter_index,
    )
    for memory in memories:
        if memory.memory_type not in {"scene", "beat"}:
            continue
        if _memory_chapter_index(memory) != chapter_index:
            continue
        used_chars = _append_limited_source(
            sources,
            used_chars=used_chars,
            max_source_chars=max_source_chars,
            source_type=f"longform_memory:{memory.memory_type}",
            source_id=memory.id,
            title=memory.title or memory.scope_key,
            text=memory.summary or "",
            chapter_index=chapter_index,
        )
        if used_chars >= max_source_chars:
            break
    return sources


def _append_limited_source(
    sources: list[dict[str, Any]],
    *,
    used_chars: int,
    max_source_chars: int,
    source_type: str,
    source_id: str | None,
    title: str,
    text: str,
    chapter_index: int,
) -> int:
    clean_text = " ".join(str(text or "").split())
    if not clean_text or used_chars >= max_source_chars:
        return used_chars
    remaining = max_source_chars - used_chars
    excerpt = clean_text[:remaining]
    if not excerpt:
        return used_chars
    sources.append(
        {
            "source_type": source_type,
            "source_id": source_id,
            "chapter_index": chapter_index,
            "title": str(title or source_type),
            "excerpt": excerpt,
            "chars": len(excerpt),
            "truncated": len(clean_text) > len(excerpt),
        }
    )
    return used_chars + len(excerpt)


def _storyline_evidence_text(storyline: Storyline | None, *, chapter_index: int) -> str:
    if storyline is None:
        return ""
    plotlines = storyline.plotlines if isinstance(storyline.plotlines, list) else []
    foreshadowing = storyline.foreshadowing if isinstance(storyline.foreshadowing, list) else []
    parts: list[str] = []
    for item in plotlines:
        if not isinstance(item, dict):
            continue
        chapters = item.get("chapters") if isinstance(item.get("chapters"), list) else []
        if chapters and chapter_index not in [_optional_int(value) for value in chapters]:
            continue
        title = str(item.get("title") or item.get("name") or "").strip()
        summary = str(item.get("summary") or item.get("description") or "").strip()
        parts.append(": ".join(part for part in [title, summary] if part))
    for item in foreshadowing:
        if not isinstance(item, dict):
            continue
        introduced = _optional_int(item.get("introduced_chapter") or item.get("chapter_index"))
        if introduced is not None and introduced > chapter_index:
            continue
        title = str(item.get("title") or item.get("name") or "").strip()
        status = str(item.get("status") or "").strip()
        parts.append(" ".join(part for part in [title, status] if part))
    return "；".join(part for part in parts if part)


def _llm_summary_prompt_contract(
    *,
    summary_target: dict[str, Any],
    query: str | None,
    evidence_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    evidence_lines = [
        f"- [{source.get('source_type')}] {source.get('title')}: {source.get('excerpt')}"
        for source in evidence_sources
    ]
    query_line = f"语义探针/关注点：{query}" if query else "语义探针/关注点：未指定"
    return {
        "trace_required": True,
        "trace_type": "memory_tree_summary_generation",
        "model_task": "summarize_memory_tree_chapter",
        "system_prompt": (
            "你是 novelv3 的长期记忆摘要器。只根据给定证据生成可持久化的 Memory Tree 章级摘要，"
            "不得添加证据之外的新事实。"
        ),
        "user_prompt": "\n".join(
            [
                f"目标：为 {summary_target.get('scope_key')} 生成章级 Memory Tree 摘要。",
                query_line,
                "输出要求：保留人物、地点、因果、伏笔和未解决问题；100-180 字；中文。",
                "证据：",
                *evidence_lines,
            ]
        ),
        "expected_output_schema": {
            "summary": "string",
            "salient_terms": "array[string]",
            "open_questions": "array[string]",
            "source_coverage": "array[string]",
        },
    }


def _llm_summary_context_blocks(evidence_sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for index, source in enumerate(evidence_sources, start=1):
        blocks.append(
            build_context_block(
                key=f"memory_tree_summary_source_{index}",
                kind=str(source.get("source_type") or "memory_tree_source"),
                title=str(source.get("title") or f"Memory Tree source {index}"),
                content=str(source.get("excerpt") or ""),
                sources=[
                    {
                        "source_type": source.get("source_type"),
                        "source_id": source.get("source_id"),
                        "chapter_index": source.get("chapter_index"),
                    }
                ],
            )
        )
    return blocks


def _parse_llm_summary_candidate(content: str) -> dict[str, Any]:
    text = str(content or "").strip()
    try:
        payload = parse_json_safely(text)
    except Exception:
        payload = {"summary": text}
    if not isinstance(payload, dict):
        payload = {"summary": text}
    return {
        "summary": str(payload.get("summary") or payload.get("content") or text).strip(),
        "salient_terms": _string_list(payload.get("salient_terms")),
        "open_questions": _string_list(payload.get("open_questions")),
        "source_coverage": _string_list(payload.get("source_coverage")),
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _outline_by_chapter(outline: Outline | None) -> dict[int, dict[str, Any]]:
    if outline is None or not isinstance(outline.chapters, list):
        return {}
    items: dict[int, dict[str, Any]] = {}
    for item in outline.chapters:
        if not isinstance(item, dict):
            continue
        chapter_index = _optional_int(item.get("chapter_index") or item.get("index"))
        if chapter_index is not None:
            items[chapter_index] = item
    return items


def _chapters(db: Session, project_id: str) -> list[ChapterContent]:
    return (
        db.query(ChapterContent)
        .filter(ChapterContent.project_id == project_id)
        .order_by(ChapterContent.chapter_index.asc(), ChapterContent.id.asc())
        .all()
    )


def _outline(db: Session, project_id: str) -> Outline | None:
    return db.query(Outline).filter(Outline.project_id == project_id).order_by(Outline.created_at.desc()).first()


def _storyline(db: Session, project_id: str) -> Storyline | None:
    return db.query(Storyline).filter(Storyline.project_id == project_id).order_by(Storyline.created_at.desc()).first()


def _memories(db: Session, project_id: str) -> list[LongformMemory]:
    return (
        db.query(LongformMemory)
        .filter(LongformMemory.project_id == project_id)
        .filter(LongformMemory.memory_type.in_(("scene", "beat", *MEMORY_TREE_SUMMARY_TYPES)))
        .order_by(
            LongformMemory.start_chapter_index.asc(),
            LongformMemory.memory_type.desc(),
            LongformMemory.scope_key.asc(),
        )
        .all()
    )


def _summary_memories_by_scope(memories: list[LongformMemory]) -> dict[tuple[str, str], LongformMemory]:
    return {
        (memory.memory_type, memory.scope_key): memory
        for memory in memories
        if memory.memory_type in MEMORY_TREE_SUMMARY_TYPES
    }


def _memory_chapter_index(memory: LongformMemory) -> int | None:
    return memory.start_chapter_index or memory.end_chapter_index


def _volume_index(chapter_index: int) -> int:
    return ((int(chapter_index) - 1) // 100) + 1


def _append_child(nodes_by_id: dict[str, dict[str, Any]], parent_id: str | None, child_id: str) -> None:
    if parent_id and parent_id in nodes_by_id:
        nodes_by_id[parent_id]["children"].append(child_id)


def _metadata_value(memory: LongformMemory, key: str) -> str:
    metadata = memory.memory_metadata if isinstance(memory.memory_metadata, dict) else {}
    return str(metadata.get(key) or "").strip()


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalise_max_depth(value: int | None) -> int | None:
    if value is None:
        return None
    return max(0, int(value))


def _volume_summary(
    volume_index: int,
    *,
    chapters: list[ChapterContent],
    outline: Outline | None,
    storyline: Storyline | None,
) -> str:
    chapter_indexes = [int(chapter.chapter_index) for chapter in chapters]
    parts = [f"Volume {volume_index} covers chapters {min(chapter_indexes)}-{max(chapter_indexes)}."]
    plotlines = storyline.plotlines if storyline is not None and isinstance(storyline.plotlines, list) else []
    plot_titles = [
        str(item.get("title") or item.get("name") or "").strip()
        for item in plotlines
        if isinstance(item, dict)
    ]
    plot_titles = [title for title in plot_titles if title]
    if plot_titles:
        parts.append("Main plotlines: " + "; ".join(plot_titles[:3]) + ".")
    outline_items = _outline_by_chapter(outline)
    chapter_summaries = [
        str((outline_items.get(index) or {}).get("summary") or "").strip()
        for index in chapter_indexes
    ]
    chapter_summaries = [summary for summary in chapter_summaries if summary]
    if chapter_summaries:
        parts.append("Chapter summaries: " + "; ".join(chapter_summaries[:5]) + ".")
    return " ".join(parts)


def _chapter_summary(chapter: ChapterContent, outline_item: dict[str, Any] | None) -> str:
    outline_summary = str((outline_item or {}).get("summary") or "").strip()
    title = chapter.title or str((outline_item or {}).get("title") or f"Chapter {chapter.chapter_index}")
    content = str(chapter.content or "").strip().replace("\n", " ")
    content_preview = content[:160]
    if outline_summary and content_preview:
        return f"{title}: {outline_summary} Content points: {content_preview}"
    if outline_summary:
        return f"{title}: {outline_summary}"
    return f"{title}: {content_preview}" if content_preview else str(title)


def _upsert_summary_memory(
    db: Session,
    *,
    project_id: str,
    memory_type: str,
    scope_key: str,
    start_chapter_index: int,
    end_chapter_index: int,
    title: str,
    summary: str,
    metadata: dict[str, Any],
) -> tuple[LongformMemory, bool]:
    record = (
        db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == memory_type,
            LongformMemory.scope_key == scope_key,
        )
        .first()
    )
    created = record is None
    if record is None:
        record = LongformMemory(project_id=project_id, memory_type=memory_type, scope_key=scope_key)
        db.add(record)
    record.start_chapter_index = start_chapter_index
    record.end_chapter_index = end_chapter_index
    record.title = title
    record.summary = summary
    record.status = "current"
    record.memory_metadata = metadata
    db.flush()
    return record, created


def _summary_record_projection(record: LongformMemory) -> dict[str, Any]:
    return {
        "id": record.id,
        "memory_type": record.memory_type,
        "scope_key": record.scope_key,
        "start_chapter_index": record.start_chapter_index,
        "end_chapter_index": record.end_chapter_index,
        "title": record.title,
        "summary": record.summary,
    }

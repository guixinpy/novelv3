from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import ChapterContent, Project, WritingAgentStep
from app.services.writing_agent.memory_provenance_contract import build_memory_provenance, count_window

POST_CHAPTER_MEMORY_CAPTURE_VERSION = "phase242.post_chapter_memory_capture.v1"
POST_CHAPTER_MEMORY_TARGET_TYPE = "agent_post_chapter_memory_capture_plan"
POST_CHAPTER_REVIEW_TOOLS = ("review_chapter_quality", "review_chapter_continuity")
PREPARE_KNOWLEDGE_CANDIDATE_TOOL = "prepare_record_agent_knowledge_base_candidate"


def plan_post_chapter_memory_capture(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
) -> dict[str, Any]:
    _require_project(db, project_id)
    normalized_index = max(1, int(chapter_index or 1))
    chapter = _chapter_for_capture(db, project_id, normalized_index)
    if chapter is None:
        return _json_safe(
            _output(
                project_id=project_id,
                chapter_index=normalized_index,
                capture_status="missing_chapter",
                candidates=[],
                review_steps=[],
                recommended_next_tools=["generate_chapter"],
                memory_status="missing_chapter",
                recovery_reason="chapter_not_generated",
            )
        )

    review_steps = _review_steps_for_capture(db, project_id, normalized_index)
    if not review_steps:
        return _json_safe(
            _output(
                project_id=project_id,
                chapter_index=normalized_index,
                capture_status="needs_review",
                candidates=[],
                review_steps=[],
                recommended_next_tools=list(POST_CHAPTER_REVIEW_TOOLS),
                memory_status="needs_review",
                recovery_reason="review_evidence_missing",
                chapter=chapter,
            )
        )

    candidates = [_chapter_pattern_candidate(chapter)]
    findings = _review_findings(review_steps)
    if findings:
        candidates.append(_review_lesson_candidate(chapter, review_steps, findings))
    recommended_next_tools = [PREPARE_KNOWLEDGE_CANDIDATE_TOOL] if candidates else []
    return _json_safe(
        _output(
            project_id=project_id,
            chapter_index=normalized_index,
            capture_status="ready",
            candidates=candidates,
            review_steps=review_steps,
            recommended_next_tools=recommended_next_tools,
            memory_status="available",
            recovery_reason="approval_required_before_memory_write",
            chapter=chapter,
        )
    )


def _chapter_for_capture(db: Session, project_id: str, chapter_index: int) -> ChapterContent | None:
    return (
        db.query(ChapterContent)
        .filter(ChapterContent.project_id == project_id, ChapterContent.chapter_index == chapter_index)
        .first()
    )


def _require_project(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _review_steps_for_capture(db: Session, project_id: str, chapter_index: int) -> list[WritingAgentStep]:
    return list(
        db.query(WritingAgentStep)
        .filter(
            WritingAgentStep.project_id == project_id,
            WritingAgentStep.chapter_index == chapter_index,
            WritingAgentStep.tool_name.in_(POST_CHAPTER_REVIEW_TOOLS),
            WritingAgentStep.status == "success",
        )
        .order_by(WritingAgentStep.created_at.asc(), WritingAgentStep.step_index.asc(), WritingAgentStep.id.asc())
        .all()
    )


def _chapter_pattern_candidate(chapter: ChapterContent) -> dict[str, Any]:
    title = str(chapter.title or "").strip() or "未命名"
    content = str(chapter.content or "").strip()
    summary = f"第{chapter.chapter_index}章《{title}》已生成，后续章节应延续本章核心线索、场景推进和章末钩子。"
    if content:
        summary += f" 结尾证据：{_tail_excerpt(content)}"
    params = {
        "memory_type": "writing_pattern",
        "title": f"第{chapter.chapter_index}章写作沉淀：{title}",
        "summary": summary,
        "source_refs": [f"chapter_content:{chapter.id}"],
        "confidence": 0.72,
        "status": "candidate",
        "tags": ["post-chapter-capture", f"chapter:{chapter.chapter_index}"],
    }
    return {
        **params,
        "evidence": {
            "chapter_content_id": chapter.id,
            "chapter_index": chapter.chapter_index,
            "title": title,
            "word_count": _chapter_word_count(chapter),
        },
        "next_tool_call": {"tool_name": PREPARE_KNOWLEDGE_CANDIDATE_TOOL, "params": params},
    }


def _review_lesson_candidate(
    chapter: ChapterContent,
    review_steps: list[WritingAgentStep],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    title = str(chapter.title or "").strip() or "未命名"
    finding_summaries = [_finding_summary(finding) for finding in findings[:5]]
    source_refs = [f"chapter_content:{chapter.id}"] + [f"writing_agent_step:{step.id}" for step in review_steps]
    params = {
        "memory_type": "self_optimization_lesson",
        "title": f"第{chapter.chapter_index}章审稿经验：{title}",
        "summary": "；".join(finding_summaries) + "。后续生成应优先避免这些重复问题。",
        "source_refs": source_refs,
        "confidence": 0.78,
        "status": "candidate",
        "tags": ["post-review", "self-optimization", f"chapter:{chapter.chapter_index}"],
    }
    return {
        **params,
        "evidence": {
            "chapter_content_id": chapter.id,
            "chapter_index": chapter.chapter_index,
            "review_step_ids": [step.id for step in review_steps],
            "finding_count": len(findings),
        },
        "next_tool_call": {"tool_name": PREPARE_KNOWLEDGE_CANDIDATE_TOOL, "params": params},
    }


def _output(
    *,
    project_id: str,
    chapter_index: int,
    capture_status: str,
    candidates: list[dict[str, Any]],
    review_steps: list[WritingAgentStep],
    recommended_next_tools: list[str],
    memory_status: str,
    recovery_reason: str,
    chapter: ChapterContent | None = None,
) -> dict[str, Any]:
    return {
        "status": "completed",
        "version": POST_CHAPTER_MEMORY_CAPTURE_VERSION,
        "project_id": project_id,
        "chapter_index": chapter_index,
        "target_type": POST_CHAPTER_MEMORY_TARGET_TYPE,
        "capture_status": capture_status,
        "summary": {
            "chapter_available": chapter is not None,
            "review_step_count": len(review_steps),
            "candidate_count": len(candidates),
        },
        "candidates": candidates,
        "recommended_next_tools": recommended_next_tools,
        "memory_provenance": _memory_provenance(
            chapter=chapter,
            review_steps=review_steps,
            status=memory_status,
            recovery_reason=recovery_reason,
            next_tools=recommended_next_tools,
            recovery_tools=_candidate_recovery_tools(candidates),
        ),
        "trace": {
            "source": "plan_post_chapter_memory_capture",
            "version": POST_CHAPTER_MEMORY_CAPTURE_VERSION,
            "mutability": "read",
            "write_performed": False,
        },
    }


def _memory_provenance(
    *,
    chapter: ChapterContent | None,
    review_steps: list[WritingAgentStep],
    status: str,
    recovery_reason: str,
    next_tools: list[str],
    recovery_tools: list[dict[str, Any]],
) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    if chapter is not None:
        sources.append(
            {
                "source_type": "chapter_content",
                "source_ref": f"chapter_content:{chapter.id}",
                "chapter_index": chapter.chapter_index,
            }
        )
    sources.extend(
        {
            "source_type": "writing_agent_step",
            "source_ref": f"writing_agent_step:{step.id}",
            "tool_name": step.tool_name,
            "chapter_index": step.chapter_index,
        }
        for step in review_steps
    )
    return build_memory_provenance(
        version=POST_CHAPTER_MEMORY_CAPTURE_VERSION,
        status=status,
        sources=sources,
        windows={
            "chapter": count_window(1 if chapter is not None else 0),
            "review_steps": count_window(len(review_steps)),
        },
        recovery={
            "status": "action_required" if next_tools else "none",
            "reason": recovery_reason,
            "next_tools": next_tools,
            "tools": recovery_tools,
        },
        trace={
            "source": "plan_post_chapter_memory_capture",
            "version": POST_CHAPTER_MEMORY_CAPTURE_VERSION,
        },
    )


def _candidate_recovery_tools(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for candidate in candidates:
        next_tool_call = candidate.get("next_tool_call") if isinstance(candidate, dict) else None
        if not isinstance(next_tool_call, dict):
            continue
        tool_name = str(next_tool_call.get("tool_name") or "").strip()
        if tool_name != PREPARE_KNOWLEDGE_CANDIDATE_TOOL:
            continue
        params = next_tool_call.get("params")
        tools.append({"tool_name": tool_name, "params": dict(params) if isinstance(params, dict) else {}})
    return tools


def _review_findings(review_steps: list[WritingAgentStep]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for step in review_steps:
        output = step.output if isinstance(step.output, dict) else {}
        raw_findings = output.get("findings") if isinstance(output.get("findings"), list) else []
        for finding in raw_findings:
            if isinstance(finding, dict):
                findings.append(dict(finding))
    return findings


def _finding_summary(finding: dict[str, Any]) -> str:
    code = str(finding.get("code") or "review_finding").strip()
    message = str(finding.get("message") or "").strip()
    severity = str(finding.get("severity") or "").strip()
    prefix = f"{severity} " if severity else ""
    return f"{prefix}{code}: {message}".strip()


def _tail_excerpt(content: str) -> str:
    return content[-140:] if len(content) > 140 else content


def _chapter_word_count(chapter: ChapterContent) -> int:
    try:
        return int(chapter.word_count or 0)
    except (TypeError, ValueError):
        return 0


def _json_safe(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

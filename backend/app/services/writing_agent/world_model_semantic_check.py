from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.ai_service import AIService
from app.core.deepseek_adapter import parse_json_safely
from app.core.model_call_trace import build_context_block, create_trace, mark_trace_failed, mark_trace_success, now_ms
from app.models import ChapterContent, Project, ProjectProfileVersion, WorldFactClaim
from app.prompting.assembler import PromptAssembler

WORLD_MODEL_SEMANTIC_CHECK_VERSION = "phase254.world_model_semantic_check.v1"
WORLD_MODEL_SEMANTIC_CHECK_TRACE_TYPE = "world_model_semantic_check"
WORLD_MODEL_SEMANTIC_CHECKER_NAME = "semantic_consistency_llm"
DEFAULT_WORLD_MODEL_SEMANTIC_FACT_LIMIT = 20
MAX_WORLD_MODEL_SEMANTIC_FACT_LIMIT = 80


async def inspect_agent_world_model_semantic_check(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
    subject_ref: str | None = None,
    max_facts: int | None = None,
    ai_service: Any | None = None,
) -> dict[str, Any]:
    project = _require_project(db, project_id)
    normalized_chapter_index = _optional_int(chapter_index) or 1
    normalized_subject_ref = _clean_subject(subject_ref)
    fact_limit = _clamp_fact_limit(max_facts)
    profile = _current_profile(db, project_id)
    if profile is None:
        return _blocked(
            project_id,
            chapter_index=normalized_chapter_index,
            subject_ref=normalized_subject_ref,
            reason="missing_world_model_profile",
            recommended_next_tools=["import_setup_world_model"],
        )

    chapter = _chapter(db, project_id, normalized_chapter_index)
    if chapter is None:
        return _blocked(
            project_id,
            chapter_index=normalized_chapter_index,
            subject_ref=normalized_subject_ref,
            reason="missing_generated_chapter",
            profile=_profile_payload(profile),
            recommended_next_tools=["preflight_writing"],
        )

    facts, total_facts = _confirmed_fact_window(
        db,
        project_id,
        profile=profile,
        chapter_index=normalized_chapter_index,
        subject_ref=normalized_subject_ref,
        limit=fact_limit,
    )
    if not facts:
        return _blocked(
            project_id,
            chapter_index=normalized_chapter_index,
            subject_ref=normalized_subject_ref,
            reason="missing_confirmed_world_facts",
            profile=_profile_payload(profile),
            chapter_window=_chapter_window(chapter),
            fact_window=_fact_window_payload(facts, total_facts=total_facts, limit=fact_limit),
            recommended_next_tools=["inspect_agent_world_model_route"],
        )

    prompt_contract = _llm_prompt_contract(
        chapter=chapter,
        facts=facts,
        subject_ref=normalized_subject_ref,
        fact_limit=fact_limit,
    )
    messages = [
        {"role": "system", "content": prompt_contract["system_prompt"]},
        {"role": "user", "content": prompt_contract["user_prompt"]},
    ]
    model = project.ai_model or "deepseek-chat"
    temperature = 0.1
    max_tokens = 900
    trace = create_trace(
        db,
        project_id=project_id,
        trace_type=WORLD_MODEL_SEMANTIC_CHECK_TRACE_TYPE,
        messages=messages,
        context_blocks=_context_blocks(chapter=chapter, facts=facts),
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        chapter_id=chapter.id,
        chapter_index=chapter.chapter_index,
        trace_metadata={
            "world_model_semantic_check": {
                "version": WORLD_MODEL_SEMANTIC_CHECK_VERSION,
                "checker_name": WORLD_MODEL_SEMANTIC_CHECKER_NAME,
                "layer": "L5 Semantic Checks",
                "profile_version": profile.version,
                "fact_count": len(facts),
                "subject_ref": normalized_subject_ref,
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
        parsed = _parse_semantic_check(parse_json(getattr(result, "content", "") or ""))
        trace.trace_metadata = {
            **(trace.trace_metadata or {}),
            "world_model_semantic_check": {
                **((trace.trace_metadata or {}).get("world_model_semantic_check") or {}),
                "overall_status": parsed["overall_status"],
                "issue_count": len(parsed["issues"]),
                "summary": parsed["summary"],
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
        return _json_safe(
            {
                "version": WORLD_MODEL_SEMANTIC_CHECK_VERSION,
                "status": "failed",
                "reason": "model_call_failed",
                "error": str(exc),
                "project_id": project_id,
                "chapter_index": normalized_chapter_index,
                "subject_ref": normalized_subject_ref,
                "profile": _profile_payload(profile),
                "chapter_window": _chapter_window(chapter),
                "fact_window": _fact_window_payload(facts, total_facts=total_facts, limit=fact_limit),
                "semantic_check": _semantic_check_payload("failed", 0, "模型调用失败。"),
                "issues": [],
                "llm_prompt_contract": prompt_contract,
                "side_effects": {
                    "executed": ["world_model_semantic_check_trace"],
                    "skipped": ["world_fact_write", "world_model_proposal_write"],
                },
                "recommended_next_tools": ["inspect_agent_trace_audit", "inspect_agent_world_model_route"],
                "trace": _trace_payload(trace, llm_call_executed=True),
            }
        )
    finally:
        if should_close_service:
            close = getattr(service, "close", None)
            if callable(close):
                await close()

    issues = parsed["issues"]
    overall_status = parsed["overall_status"]
    return _json_safe(
        {
            "version": WORLD_MODEL_SEMANTIC_CHECK_VERSION,
            "status": "completed",
            "project_id": project_id,
            "chapter_index": normalized_chapter_index,
            "subject_ref": normalized_subject_ref,
            "profile": _profile_payload(profile),
            "chapter_window": _chapter_window(chapter),
            "fact_window": _fact_window_payload(facts, total_facts=total_facts, limit=fact_limit),
            "semantic_check": _semantic_check_payload(overall_status, len(issues), parsed["summary"]),
            "issues": issues,
            "llm_prompt_contract": prompt_contract,
            "side_effects": {
                "executed": ["world_model_semantic_check_trace"],
                "skipped": ["world_fact_write", "world_model_proposal_write"],
            },
            "recommended_next_tools": _recommended_next_tools(issues),
            "trace": _trace_payload(trace, llm_call_executed=True),
        }
    )


def _blocked(
    project_id: str,
    *,
    chapter_index: int,
    subject_ref: str | None,
    reason: str,
    profile: dict[str, Any] | None = None,
    chapter_window: dict[str, Any] | None = None,
    fact_window: dict[str, Any] | None = None,
    recommended_next_tools: list[str] | None = None,
) -> dict[str, Any]:
    return _json_safe(
        {
            "version": WORLD_MODEL_SEMANTIC_CHECK_VERSION,
            "status": "blocked",
            "reason": reason,
            "project_id": project_id,
            "chapter_index": chapter_index,
            "subject_ref": subject_ref,
            "profile": profile,
            "chapter_window": chapter_window,
            "fact_window": fact_window or _fact_window_payload([], total_facts=0, limit=0),
            "semantic_check": _semantic_check_payload("blocked", 0, ""),
            "issues": [],
            "llm_prompt_contract": None,
            "side_effects": {"executed": [], "skipped": ["world_model_semantic_check_trace"]},
            "recommended_next_tools": recommended_next_tools or ["inspect_agent_world_model_route"],
            "trace": {
                "source": "inspect_agent_world_model_semantic_check",
                "version": WORLD_MODEL_SEMANTIC_CHECK_VERSION,
                "mutability": "read",
                "llm_call_executed": False,
            },
        }
    )


def _require_project(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _current_profile(db: Session, project_id: str) -> ProjectProfileVersion | None:
    return (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(
            ProjectProfileVersion.version.desc(),
            ProjectProfileVersion.created_at.desc(),
            ProjectProfileVersion.id.desc(),
        )
        .first()
    )


def _chapter(db: Session, project_id: str, chapter_index: int) -> ChapterContent | None:
    return (
        db.query(ChapterContent)
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.chapter_index == chapter_index,
            ChapterContent.status == "generated",
        )
        .first()
    )


def _confirmed_fact_window(
    db: Session,
    project_id: str,
    *,
    profile: ProjectProfileVersion,
    chapter_index: int,
    subject_ref: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    filters = [
        WorldFactClaim.project_id == project_id,
        WorldFactClaim.project_profile_version_id == profile.id,
        WorldFactClaim.profile_version == profile.version,
        WorldFactClaim.claim_status == "confirmed",
        WorldFactClaim.claim_layer == "truth",
        or_(WorldFactClaim.chapter_index.is_(None), WorldFactClaim.chapter_index <= chapter_index),
    ]
    if subject_ref:
        filters.append(WorldFactClaim.subject_ref == subject_ref)
    total = db.query(func.count(WorldFactClaim.id)).filter(*filters).scalar() or 0
    rows = (
        db.query(WorldFactClaim)
        .filter(*filters)
        .order_by(
            WorldFactClaim.chapter_index.asc().nullsfirst(),
            WorldFactClaim.intra_chapter_seq.asc(),
            WorldFactClaim.claim_id.asc(),
        )
        .limit(limit)
        .all()
    )
    return [_fact_payload(row) for row in rows], int(total)


def _fact_payload(fact: WorldFactClaim) -> dict[str, Any]:
    return {
        "claim_id": fact.claim_id,
        "chapter_index": fact.chapter_index,
        "subject_ref": fact.subject_ref,
        "predicate": fact.predicate,
        "object_ref_or_value": fact.object_ref_or_value,
        "confidence": fact.confidence,
        "evidence_refs": fact.evidence_refs or [],
    }


def _profile_payload(profile: ProjectProfileVersion) -> dict[str, Any]:
    return {
        "id": profile.id,
        "version": profile.version,
        "contract_version": profile.contract_version,
    }


def _chapter_window(chapter: ChapterContent) -> dict[str, Any]:
    excerpt = _truncate(chapter.content or "", 1600)
    return {
        "chapter_id": chapter.id,
        "chapter_index": chapter.chapter_index,
        "title": chapter.title or "",
        "content_chars": len(chapter.content or ""),
        "excerpt": excerpt,
    }


def _fact_window_payload(facts: list[dict[str, Any]], *, total_facts: int, limit: int) -> dict[str, Any]:
    return {
        "total_confirmed_facts": total_facts,
        "returned_facts": len(facts),
        "limit": limit,
        "facts": facts,
    }


def _llm_prompt_contract(
    *,
    chapter: ChapterContent,
    facts: list[dict[str, Any]],
    subject_ref: str | None,
    fact_limit: int,
) -> dict[str, Any]:
    response_schema = {
        "overall_status": "passed | issues_found",
        "summary": "one sentence",
        "issues": [
            {
                "code": "fact_semantic_conflict | missing_explanation | uncertain",
                "severity": "info | warning | error",
                "message": "reader-facing issue summary",
                "subject_ref": "optional world subject",
                "predicate": "optional predicate",
                "claim_id": "optional claim id",
                "evidence_excerpt": "short chapter excerpt",
            }
        ],
    }
    rendered = PromptAssembler().build(
        "athena.world_model_semantic_check",
        {
            "chapter_index": chapter.chapter_index,
            "chapter_title": chapter.title or "",
            "subject_ref": subject_ref or "<all>",
            "max_facts": fact_limit,
            "chapter_excerpt": _truncate(chapter.content or "", 1800),
            "facts_json": json.dumps(facts, ensure_ascii=False, sort_keys=True),
        },
    )
    return {
        "trace_required": True,
        "trace_type": WORLD_MODEL_SEMANTIC_CHECK_TRACE_TYPE,
        "checker_layer": "L5 Semantic Checks",
        "checker_name": WORLD_MODEL_SEMANTIC_CHECKER_NAME,
        "prompt_id": rendered.prompt_id,
        "prompt_version": rendered.version,
        "template_name": rendered.template_name,
        "template_hash": rendered.template_hash,
        "system_prompt": "你是长篇小说世界模型的 L5 语义一致性审查器。",
        "user_prompt": rendered.content,
        "response_schema": response_schema,
    }


def _context_blocks(*, chapter: ChapterContent, facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        build_context_block(
            key=f"chapter:{chapter.chapter_index}",
            kind="chapter_content",
            title=f"第{chapter.chapter_index}章正文",
            content=chapter.content or "",
            sources=[{"source_type": "chapter_content", "chapter_index": chapter.chapter_index}],
            max_chars=1800,
        ),
        build_context_block(
            key=f"world_model_facts:{chapter.chapter_index}",
            kind="world_model_fact_window",
            title="确认世界事实窗口",
            content=json.dumps(facts, ensure_ascii=False, sort_keys=True),
            sources=[{"source_type": "world_model_fact_claim", "claim_id": fact["claim_id"]} for fact in facts],
            max_chars=4000,
        ),
    ]


def parse_json(content: str) -> dict[str, Any]:
    parsed = parse_json_safely(content)
    return parsed if isinstance(parsed, dict) else {}


def _parse_semantic_check(parsed: dict[str, Any]) -> dict[str, Any]:
    raw_issues = parsed.get("issues") if isinstance(parsed.get("issues"), list) else []
    issues = [_semantic_issue(item) for item in raw_issues if isinstance(item, dict)]
    overall_status = _clean_status(parsed.get("overall_status"), issues)
    summary = str(parsed.get("summary") or "").strip()
    if not summary:
        summary = "发现语义一致性问题。" if issues else "未发现语义一致性问题。"
    return {"overall_status": overall_status, "summary": summary, "issues": issues}


def _semantic_issue(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": str(item.get("code") or "semantic_consistency_issue").strip() or "semantic_consistency_issue",
        "severity": _severity(item.get("severity")),
        "message": str(item.get("message") or "").strip(),
        "subject_ref": str(item.get("subject_ref") or "").strip(),
        "predicate": str(item.get("predicate") or "").strip(),
        "claim_id": str(item.get("claim_id") or "").strip(),
        "evidence_excerpt": _truncate(str(item.get("evidence_excerpt") or "").strip(), 180),
    }


def _clean_status(value: Any, issues: list[dict[str, Any]]) -> str:
    status = str(value or "").strip()
    if status in {"passed", "issues_found", "blocked", "failed"}:
        return status
    return "issues_found" if issues else "passed"


def _severity(value: Any) -> str:
    severity = str(value or "").strip()
    return severity if severity in {"info", "warning", "error"} else "warning"


def _semantic_check_payload(status: str, issue_count: int, summary: str) -> dict[str, Any]:
    return {
        "layer": "L5 Semantic Checks",
        "checker_name": WORLD_MODEL_SEMANTIC_CHECKER_NAME,
        "status": status,
        "issue_count": issue_count,
        "summary": summary,
    }


def _recommended_next_tools(issues: list[dict[str, Any]]) -> list[str]:
    if issues:
        return [
            "prepare_analyze_chapter_world_model_execution",
            "review_world_model_proposals",
            "inspect_agent_world_model_route",
        ]
    return ["preflight_writing", "inspect_agent_world_model_route"]


def _trace_payload(trace: Any, *, llm_call_executed: bool) -> dict[str, Any]:
    return {
        "source": "inspect_agent_world_model_semantic_check",
        "version": WORLD_MODEL_SEMANTIC_CHECK_VERSION,
        "mutability": "read",
        "trace_id": trace.id,
        "trace_type": trace.trace_type,
        "llm_call_executed": llm_call_executed,
        "status": trace.status,
    }


def _clean_subject(subject_ref: str | None) -> str | None:
    cleaned = str(subject_ref or "").strip()
    return cleaned or None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clamp_fact_limit(value: int | None) -> int:
    if value is None:
        return DEFAULT_WORLD_MODEL_SEMANTIC_FACT_LIMIT
    return min(max(int(value), 1), MAX_WORLD_MODEL_SEMANTIC_FACT_LIMIT)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 1)] + "…"


def _json_safe(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

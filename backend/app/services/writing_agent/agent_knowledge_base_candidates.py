from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Project

AGENT_KNOWLEDGE_BASE_CANDIDATE_VERSION = "phase78.agent_knowledge_base_candidate.v1"
KNOWLEDGE_CANDIDATES_KEY = "knowledge_base_candidates"
SUPPORTED_MEMORY_TYPES = {
    "author_preference",
    "project_strategy",
    "writing_pattern",
    "self_optimization_lesson",
    "decomposition_pattern",
}
SUPPORTED_STATUSES = {"candidate", "active", "muted", "rejected"}
logger = logging.getLogger(__name__)


def record_agent_knowledge_base_candidate(
    db: Session,
    project_id: str,
    *,
    memory_type: str,
    title: str,
    summary: str,
    source_refs: list[str],
    confidence: float | None = None,
    status: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    project = _require_project(db, project_id)
    normalized = _normalize_candidate_input(
        memory_type=memory_type,
        title=title,
        summary=summary,
        source_refs=source_refs,
        confidence=confidence,
        status=status,
        tags=tags or [],
    )
    if normalized.get("error"):
        return _json_safe_output(
            {
                "status": "failed",
                "project_id": project_id,
                "error": normalized["error"],
                "trace": _trace_metadata(),
            }
        )

    config = dict(project.style_config or {})
    candidates = [dict(item) for item in config.get(KNOWLEDGE_CANDIDATES_KEY, []) if isinstance(item, dict)]
    fingerprint = _fingerprint(normalized)
    now = _now_iso()
    existing = next((item for item in candidates if item.get("fingerprint") == fingerprint), None)
    if existing is None:
        candidate = {
            "id": str(uuid.uuid4()),
            "fingerprint": fingerprint,
            "memory_type": normalized["memory_type"],
            "title": normalized["title"],
            "summary": normalized["summary"],
            "source_refs": normalized["source_refs"],
            "confidence": normalized["confidence"],
            "status": normalized["status"],
            "tags": normalized["tags"],
            "created_at": now,
            "updated_at": now,
            "observed_count": 1,
        }
        candidates.append(candidate)
        action = "created"
    else:
        candidate = existing
        candidate["confidence"] = max(float(candidate.get("confidence") or 0), float(normalized["confidence"]))
        candidate["status"] = normalized["status"]
        candidate["tags"] = sorted(set(list(candidate.get("tags") or []) + list(normalized["tags"])))
        candidate["source_refs"] = sorted(set(list(candidate.get("source_refs") or []) + list(normalized["source_refs"])))
        candidate["updated_at"] = now
        candidate["observed_count"] = int(candidate.get("observed_count") or 1) + 1
        action = "updated"

    config[KNOWLEDGE_CANDIDATES_KEY] = candidates
    project.style_config = config
    db.add(project)
    db.commit()
    retrieval_sync = _sync_retrieval_document(db, project_id=project_id, candidate=candidate)
    return _json_safe_output(
        {
            "status": "completed",
            "project_id": project_id,
            "action": action,
            "candidate": candidate,
            "candidate_count": len(candidates),
            "retrieval_sync": retrieval_sync,
            "trace": _trace_metadata(),
        }
    )


def _require_project(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _normalize_candidate_input(
    *,
    memory_type: str,
    title: str,
    summary: str,
    source_refs: list[str],
    confidence: float | None,
    status: str | None,
    tags: list[str],
) -> dict[str, Any]:
    normalized_type = str(memory_type or "").strip()
    normalized_title = str(title or "").strip()
    normalized_summary = str(summary or "").strip()
    normalized_refs = [str(item).strip() for item in source_refs if str(item).strip()]
    normalized_status = str(status or "candidate").strip()
    if normalized_type not in SUPPORTED_MEMORY_TYPES:
        return {"error": {"code": "unsupported_memory_type", "message": f"Unsupported memory_type: {normalized_type}"}}
    if not normalized_title:
        return {"error": {"code": "missing_title", "message": "title is required"}}
    if not normalized_summary:
        return {"error": {"code": "missing_summary", "message": "summary is required"}}
    if not normalized_refs:
        return {"error": {"code": "missing_source_refs", "message": "source_refs is required"}}
    if normalized_status not in SUPPORTED_STATUSES:
        return {"error": {"code": "unsupported_status", "message": f"Unsupported status: {normalized_status}"}}
    return {
        "memory_type": normalized_type,
        "title": normalized_title,
        "summary": normalized_summary,
        "source_refs": normalized_refs,
        "confidence": _clamp_confidence(confidence),
        "status": normalized_status,
        "tags": sorted(set(str(tag).strip() for tag in tags if str(tag).strip())),
    }


def _fingerprint(candidate: dict[str, Any]) -> str:
    payload = {
        "memory_type": candidate["memory_type"],
        "title": candidate["title"],
        "summary": candidate["summary"],
        "source_refs": sorted(candidate["source_refs"]),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _clamp_confidence(confidence: float | None) -> float:
    if confidence is None:
        return 0.5
    return min(max(float(confidence), 0.0), 1.0)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _trace_metadata() -> dict[str, Any]:
    return {
        "source": "record_agent_knowledge_base_candidate",
        "version": AGENT_KNOWLEDGE_BASE_CANDIDATE_VERSION,
        "mutability": "write",
    }


def _sync_retrieval_document(db: Session, *, project_id: str, candidate: dict[str, Any]) -> dict[str, Any]:
    try:
        from app.core.athena_retrieval import sync_knowledge_base_candidate_retrieval_document

        return sync_knowledge_base_candidate_retrieval_document(db, project_id, candidate)
    except Exception as exc:
        db.rollback()
        candidate_id = str(candidate.get("id") or "").strip() or None
        logger.exception("Failed to sync retrieval document for knowledge base candidate %s", candidate_id)
        return {"status": "failed", "candidate_id": candidate_id, "error": str(exc)}


def _json_safe_output(output: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(output, ensure_ascii=False, default=str))

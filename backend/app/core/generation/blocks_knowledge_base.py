from __future__ import annotations

from typing import Any

from app.core.model_call_trace import build_context_block
from app.models import Project

KNOWLEDGE_CANDIDATES_KEY = "knowledge_base_candidates"
PROMPT_SAFE_MEMORY_TYPES = {
    "author_preference",
    "project_strategy",
    "writing_pattern",
    "decomposition_pattern",
}
PROMPT_SAFE_STATUSES = {"active", "candidate"}
MIN_CANDIDATE_CONFIDENCE = 0.7
DEFAULT_CANDIDATE_LIMIT = 4


def build_knowledge_base_candidate_block(project: Project, *, limit: int = DEFAULT_CANDIDATE_LIMIT) -> dict | None:
    candidates = _eligible_candidates(project)
    if not candidates:
        return None
    selected = candidates[: max(1, limit)]
    lines = ["【知识库创作记忆】"]
    for item in selected:
        memory_type = str(item.get("memory_type") or "")
        title = str(item.get("title") or "").strip()
        summary = str(item.get("summary") or "").strip()
        confidence = float(item.get("confidence") or 0)
        lines.append(f"- {title}：{summary}（类型：{memory_type}；置信度：{confidence:.2f}）")
    return build_context_block(
        key="knowledge_base_candidates",
        kind="knowledge_base",
        title="知识库创作记忆",
        content="\n".join(lines),
        sources=[
            {
                "source_type": "KnowledgeBaseCandidate",
                "source_id": str(item.get("id") or ""),
                "label": str(item.get("title") or ""),
                "source_ref": f"Project.style_config.{KNOWLEDGE_CANDIDATES_KEY}:{item.get('id')}",
                "metadata": {
                    "memory_type": item.get("memory_type"),
                    "status": item.get("status") or "candidate",
                    "confidence": item.get("confidence"),
                    "source_refs": list(item.get("source_refs") or []),
                },
            }
            for item in selected
        ],
        max_chars=2000,
    )


def _eligible_candidates(project: Project) -> list[dict[str, Any]]:
    style_config = project.style_config if isinstance(project.style_config, dict) else {}
    candidates = style_config.get(KNOWLEDGE_CANDIDATES_KEY)
    if not isinstance(candidates, list):
        return []
    eligible = [item for item in candidates if isinstance(item, dict) and _is_prompt_safe(item)]
    return sorted(
        eligible,
        key=lambda item: (
            str(item.get("status") or "") == "active",
            float(item.get("confidence") or 0),
            str(item.get("updated_at") or ""),
            str(item.get("created_at") or ""),
        ),
        reverse=True,
    )


def _is_prompt_safe(item: dict[str, Any]) -> bool:
    memory_type = str(item.get("memory_type") or "")
    status = str(item.get("status") or "candidate")
    confidence = float(item.get("confidence") or 0)
    if memory_type not in PROMPT_SAFE_MEMORY_TYPES:
        return False
    if status not in PROMPT_SAFE_STATUSES:
        return False
    if status == "candidate" and confidence < MIN_CANDIDATE_CONFIDENCE:
        return False
    return bool(str(item.get("title") or "").strip() and str(item.get("summary") or "").strip())

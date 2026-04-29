from typing import Any

from sqlalchemy.orm import Session

from app.core.athena_retrieval import build_chapter_retrieval_context
from app.core.model_call_trace import build_context_block
from app.prompting.providers.errors import build_provider_error_block


def build_chapter_retrieval_block(
    db: Session,
    *,
    project_id: str,
    chapter_index: int,
) -> tuple[dict | None, dict[str, Any] | None, dict | None]:
    try:
        retrieval_context = build_chapter_retrieval_context(
            db=db,
            project_id=project_id,
            chapter_index=chapter_index,
        )
    except Exception as exc:
        return None, None, build_provider_error_block(
            key="retrieval_context_error",
            provider="retrieval",
            exc=exc,
        )
    if not retrieval_context:
        return None, None, None

    section = retrieval_context.get("section") or {}
    items = section.get("items") or []
    prompt_lines = [str(line) for line in retrieval_context.get("prompt_lines", [])]
    if prompt_lines and prompt_lines[0] == "【检索证据】":
        prompt_lines = prompt_lines[1:]
    block = build_context_block(
        key="retrieval_evidence",
        kind="retrieval",
        title="检索证据",
        content="\n".join(prompt_lines),
        sources=[
            {
                "source_type": item.get("source_type") or "retrieval",
                "source_id": str(item.get("chunk_id") or item.get("title") or index),
                "label": item.get("title") or "检索证据",
                "source_ref": item.get("source_ref") or item.get("title") or "",
                "metadata": item,
            }
            for index, item in enumerate(items)
            if isinstance(item, dict)
        ],
    )
    block["metadata"] = {"result_count": len(items)}
    return block, retrieval_context, None

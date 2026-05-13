from typing import Any

from sqlalchemy.orm import Session

from app.core.longform_memory import build_longform_context_package
from app.core.model_call_trace import build_context_block
from app.prompting.providers.errors import build_provider_error_block


def build_longform_context_block(
    db: Session,
    *,
    project_id: str,
    chapter_index: int,
    user_query: str | None = None,
) -> tuple[dict | None, dict[str, Any] | None, dict | None]:
    try:
        package = build_longform_context_package(
            db=db,
            project_id=project_id,
            chapter_index=chapter_index,
            user_query=user_query,
        )
    except Exception as exc:
        return None, None, build_provider_error_block(
            key="longform_context_error",
            provider="longform",
            exc=exc,
        )

    prompt_context = package.get("prompt_context")
    if not prompt_context:
        return None, package, None

    section_keys = [
        section.get("key")
        for section in package.get("sections", [])
        if isinstance(section, dict)
    ]
    block = build_context_block(
        key="longform_memory_context",
        kind="longform_context",
        title="长篇记忆上下文",
        content=prompt_context,
        sources=[
            {
                "source_type": "LongformMemory",
                "source_id": project_id,
                "label": f"第{chapter_index}章长篇上下文",
                "source_ref": f"chapter:{chapter_index}:longform_context",
                "metadata": {
                    "chapter_index": chapter_index,
                    "section_keys": section_keys,
                },
            }
        ],
    )
    block["metadata"] = {
        "chapter_index": chapter_index,
        "section_keys": section_keys,
    }
    return block, package, None

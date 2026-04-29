from typing import Any

from sqlalchemy.orm import Session

from app.core.athena_longform import build_chapter_context_package
from app.core.model_call_trace import build_context_block
from app.prompting.providers.errors import build_provider_error_block


def build_athena_chapter_context_block(
    db: Session,
    *,
    project_id: str,
    chapter_index: int,
) -> tuple[dict | None, dict[str, Any] | None, dict | None]:
    try:
        package = build_chapter_context_package(db=db, project_id=project_id, chapter_index=chapter_index)
    except Exception as exc:
        return None, None, build_provider_error_block(
            key="athena_context_error",
            provider="Athena",
            exc=exc,
        )

    prompt_context = package.get("prompt_context")
    if not prompt_context:
        return None, package, None

    profile_version = package.get("profile_version")
    block = build_context_block(
        key="athena_world_context",
        kind="athena_context",
        title="Athena 世界上下文",
        content=prompt_context,
        sources=[
            {
                "source_type": "Athena",
                "source_id": str(package.get("project_profile_version_id") or project_id),
                "label": "Athena chapter context package",
                "source_ref": f"profile_version:{profile_version}",
                "metadata": {
                    "profile_version": profile_version,
                    "project_profile_version_id": package.get("project_profile_version_id"),
                    "section_keys": [
                        section.get("key")
                        for section in package.get("sections", [])
                        if isinstance(section, dict)
                    ],
                },
            }
        ],
    )
    block["metadata"] = {
        "profile_version": profile_version,
        "project_profile_version_id": package.get("project_profile_version_id"),
    }
    return block, package, None


def athena_context_has_retrieval(package: dict[str, Any] | None) -> bool:
    if not package:
        return False
    if "【检索证据】" in str(package.get("prompt_context") or ""):
        return True
    return any(
        isinstance(section, dict) and section.get("key") == "retrieval"
        for section in package.get("sections", [])
    )

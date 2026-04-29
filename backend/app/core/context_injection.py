"""Compatibility wrappers for world model context summaries."""

from sqlalchemy.orm import Session

from app.core.world_context_assembler import build_dialog_context_blocks, build_dialog_context_text


def build_athena_world_context_blocks(db: Session, project_id: str) -> list[dict]:
    """Structured world knowledge blocks for Athena model-call tracing."""
    return build_dialog_context_blocks(db, project_id, "athena")


def build_hermes_world_context_blocks(
    db: Session,
    project_id: str,
    chapter_index: int | None = None,
) -> list[dict]:
    """Structured compact world context blocks for Hermes model-call tracing."""
    return build_dialog_context_blocks(db, project_id, "hermes", chapter_index=chapter_index)


def build_athena_world_context(db: Session, project_id: str) -> str:
    """Full world knowledge for Athena dialog."""
    return build_dialog_context_text(db, project_id, "athena")


def build_hermes_world_context(db: Session, project_id: str, chapter_index: int | None = None) -> str:
    """Compact world summary for Hermes dialog."""
    return build_dialog_context_text(db, project_id, "hermes", chapter_index=chapter_index)

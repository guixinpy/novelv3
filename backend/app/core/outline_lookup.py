import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def find_outline_chapter(db: Session, project_id: str, chapter_index: int) -> tuple[str, dict[str, Any]] | None:
    row = (
        db.execute(
            text(
                """
                SELECT outlines.id AS outline_id, chapter.value AS chapter_outline
                FROM outlines, json_each(outlines.chapters) AS chapter
                WHERE outlines.project_id = :project_id
                  AND CAST(json_extract(chapter.value, '$.chapter_index') AS INTEGER) = :chapter_index
                ORDER BY outlines.updated_at DESC
                LIMIT 1
                """
            ),
            {"project_id": project_id, "chapter_index": chapter_index},
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    chapter_outline = _decode_json_value(row["chapter_outline"])
    if not isinstance(chapter_outline, dict):
        return None
    return str(row["outline_id"]), chapter_outline


def _decode_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value

import json

from sqlalchemy import text
from sqlalchemy.orm import Session


def parse_json_list(value: object) -> list:
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except ValueError:
        return []
    return parsed if isinstance(parsed, list) else []


def get_setup_character_projection(db: Session, project_id: str) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT
                json_extract(item.value, '$.name') AS name,
                json_extract(item.value, '$.character_status') AS character_status,
                json_extract(item.value, '$.ref') AS ref,
                json_extract(item.value, '$.aliases') AS aliases,
                json_extract(item.value, '$.names') AS names
            FROM setups, json_each(setups.characters) AS item
            WHERE setups.project_id = :project_id
            ORDER BY CAST(item.key AS INTEGER)
            """
        ),
        {"project_id": project_id},
    ).mappings()
    characters = []
    for row in rows:
        name = str(row["name"] or "").strip()
        if not name:
            continue
        characters.append(
            {
                "name": name,
                "character_status": row["character_status"] or "alive",
                "ref": row["ref"],
                "aliases": parse_json_list(row["aliases"]),
                "names": parse_json_list(row["names"]),
            }
        )
    return characters

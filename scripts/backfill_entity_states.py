"""为已写章节回填 entity_state 记忆（M4 修复后的数据补齐）。

背景：`_capture_entities` 修复前只认 world_characters 表，update_setup 写入的角色
从未生成 entity_state；本脚本对现有章节按 Setups.characters 重新捕获。
用法：python scripts/backfill_entity_states.py <project_id>
"""
from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from datetime import UTC, datetime


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/backfill_entity_states.py <project_id>")
        return 2
    pid = sys.argv[1]
    conn = sqlite3.connect("data/mozhou.db")
    cur = conn.cursor()

    row = cur.execute(
        "SELECT characters FROM setups WHERE project_id=?", (pid,)
    ).fetchone()
    if not row or not row[0]:
        print("no setup characters found")
        conn.close()
        return 1
    chars = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    names = [
        str(c["name"]) for c in chars
        if isinstance(c, dict) and c.get("name")
    ]

    now = datetime.now(UTC)
    created = 0
    updated = 0
    for idx, content in cur.execute(
        "SELECT chapter_index, content FROM chapter_contents WHERE project_id=?",
        (pid,),
    ):
        for name in names:
            if name not in content:
                continue
            existing = cur.execute(
                "SELECT id FROM longform_memories"
                " WHERE project_id=? AND memory_type='entity_state'"
                " AND scope_key=? AND status='active'",
                (pid, name),
            ).fetchone()
            if existing:
                cur.execute(
                    "UPDATE longform_memories SET end_chapter_index=?, updated_at=?"
                    " WHERE id=?",
                    (idx, now, existing[0]),
                )
                updated += 1
            else:
                cur.execute(
                    "INSERT INTO longform_memories"
                    " (id, project_id, memory_type, scope_key, title, summary,"
                    " start_chapter_index, end_chapter_index, status,"
                    " memory_metadata, created_at, updated_at)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        str(uuid.uuid4()), pid, "entity_state", name, name,
                        f"「{name}」出现在第 {idx} 章", idx, idx, "active",
                        json.dumps({"provenance": "agent_inferred", "source": "backfill"}),
                        now, now,
                    ),
                )
                created += 1

    conn.commit()
    print(f"created={created} updated={updated} entities={len(names)}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""把项目的章节正文导出为 Markdown，便于阅读与评审。

用法：python scripts/export_novel.py --project-id <id> [--out data/exports]
"""
from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import datetime


def export(project_id: str, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    conn = sqlite3.connect("data/mozhou.db")
    cur = conn.cursor()

    cur.execute("SELECT name, genre, current_word_count FROM projects WHERE id=?", (project_id,))
    project = cur.fetchone()
    name = project[0] if project else project_id

    cur.execute(
        "SELECT chapter_index, title, content, word_count FROM chapter_contents"
        " WHERE project_id=? ORDER BY chapter_index",
        (project_id,),
    )
    chapters = cur.fetchall()
    conn.close()

    safe_name = "".join(c for c in name if c not in '\\/:*?"<>|').strip() or project_id[:8]
    path = os.path.join(out_dir, f"{safe_name}-{len(chapters)}章.md")

    lines = [
        f"# {name}",
        "",
        f"- 项目 ID：`{project_id}`",
        f"- 题材：{project[1] if project else '?'}",
        f"- 章节数：{len(chapters)}",
        f"- 总字数：{sum(c[3] for c in chapters)}",
        f"- 导出时间：{datetime.now().isoformat(timespec='seconds')}",
        "",
        "---",
        "",
    ]
    for idx, title, content, wc in chapters:
        lines.append(f"## 第 {idx} 章 · {title or '(无标题)'}")
        lines.append("")
        lines.append(f"> 字数：{wc}")
        lines.append("")
        lines.append((content or "").strip())
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def main() -> int:
    p = argparse.ArgumentParser(description="导出小说正文为 Markdown")
    p.add_argument("--project-id", required=True)
    p.add_argument("--out", default=r"data\exports")
    args = p.parse_args()
    path = export(args.project_id, args.out)
    print(f"exported: {os.path.abspath(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

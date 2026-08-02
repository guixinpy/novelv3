"""Dogfood 实验分析：把 DB + 会话日志汇总为结构化报告，供后续优化决策。

用法：python scripts/analyze_dogfood.py --project-id <id> [--out <dir>]

输出：
  <out>/<project_id>_chapters.csv   —— 每章字数/状态
  <out>/<project_id>_sessions.json —— 每会话 turns/compaction/错误
  <out>/<project_id>_report.md     —— 汇总报告（质量趋势、护栏、压缩、错误）
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import sqlite3
from collections import Counter
from datetime import datetime

# T7 R1：幻觉工具名解析（「工具 X 不存在」）
_HALLUCINATED_TOOL_RE = re.compile(r"工具\s*([A-Za-z_][A-Za-z0-9_]*)\s*不存在")
# T7 R4：压缩摘要是否保留可行动的写作信息
_WRITING_CONTEXT_MARKERS = ("最近写入章节", "质量自检", "最近写作上下文")


def analyze(project_id: str, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    conn = sqlite3.connect("data/mozhou.db")
    cur = conn.cursor()

    cur.execute(
        "SELECT name, status, current_phase, current_word_count FROM projects WHERE id=?",
        (project_id,),
    )
    project = cur.fetchone()
    cur.execute(
        "SELECT chapter_index, title, word_count, status, created_at"
        " FROM chapter_contents WHERE project_id=? ORDER BY chapter_index",
        (project_id,),
    )
    chapters = cur.fetchall()
    cur.execute(
        "SELECT COUNT(*) FROM longform_memories WHERE project_id=?", (project_id,)
    )
    memories = cur.fetchone()[0]
    cur.execute(
        "SELECT memory_type, status, COUNT(*) FROM longform_memories"
        " WHERE project_id=? GROUP BY memory_type, status",
        (project_id,),
    )
    memory_stats = cur.fetchall()
    conn.close()

    # 会话日志
    sessions: list[dict] = []
    for meta_path in glob.glob("data/agent_sessions/*.meta.json"):
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        if meta.get("project_id") != project_id:
            continue
        sid = meta["session_id"]
        log_path = f"data/agent_sessions/{sid}.jsonl"
        if not os.path.exists(log_path):
            continue
        session = {
            "session_id": sid, "entries": 0, "turns": [], "compactions": [], "errors": [],
            "tool_messages": 0, "hallucinated_tools": [], "chapter_quality": [],
        }
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                session["entries"] += 1
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                d = e.get("data", {})
                if e.get("type") == "turn_ended":
                    session["turns"].append({
                        "stop_reason": d.get("stop_reason"),
                        "iterations": d.get("iterations"),
                        "prompt_tokens": d.get("prompt_tokens"),
                        "completion_tokens": d.get("completion_tokens"),
                    })
                elif e.get("type") == "compaction":
                    summary = d.get("summary") or ""
                    before = d.get("before_count") or 0
                    after = d.get("after_count") or 0
                    session["compactions"].append({
                        "before_count": before,
                        "after_count": after,
                        "usage_pct": d.get("usage_pct"),
                        "saving_ratio": round(1 - after / before, 3) if before else 0.0,
                        "has_writing_context": any(m in summary for m in _WRITING_CONTEXT_MARKERS),
                        "summary": summary[:300],
                    })
                elif e.get("type") == "message" and d.get("role") == "tool":
                    session["tool_messages"] += 1
                    content = str(d.get("content", ""))
                    # T7 R1：幻觉工具名
                    m = _HALLUCINATED_TOOL_RE.search(content)
                    if m:
                        session["hallucinated_tools"].append(m.group(1))
                    # T7 R3：每章质量自检（check_chapter_quality / check_chapter_format 返回）
                    try:
                        payload = json.loads(content)
                    except (json.JSONDecodeError, TypeError):
                        payload = None
                    if isinstance(payload, dict) and "quality" in payload:
                        session["chapter_quality"].append({
                            "chapter_index": payload.get("chapter_index"),
                            "quality": payload["quality"],
                            "issue_types": sorted({i.get("type") for i in payload.get("issues") or []}),
                        })
                    if any(k in content for k in ("error", "失败", "不存在", "rolled back")):
                        session["errors"].append(content[:400])
        sessions.append(session)
    sessions.sort(key=lambda s: s["session_id"])

    # 汇总
    word_counts = [c[2] for c in chapters]
    all_hallucinated = [t for s in sessions for t in s["hallucinated_tools"]]
    hallucinated_tools = [
        {"name": name, "count": count}
        for name, count in Counter(all_hallucinated).most_common()
    ]
    tool_message_total = sum(s["tool_messages"] for s in sessions)
    unknown_tool_rate = (
        round(len(all_hallucinated) / tool_message_total * 100, 2) if tool_message_total else 0.0
    )
    # 每章质量自检：一 章多检取最新
    quality_by_chapter: dict[int, dict] = {}
    for s in sessions:
        for q in s["chapter_quality"]:
            quality_by_chapter[q["chapter_index"]] = q
    # 压缩摘要质量
    all_compactions = [c for s in sessions for c in s["compactions"]]
    compactions_with_context = sum(1 for c in all_compactions if c["has_writing_context"])
    report = {
        "project_id": project_id,
        "project_name": project[0] if project else None,
        "project_status": project[1] if project else None,
        "phase": project[2] if project else None,
        "total_chapters": len(chapters),
        "max_chapter": max((c[0] for c in chapters), default=0),
        "total_words": project[3] if project else sum(word_counts),
        "avg_words_per_chapter": round(sum(word_counts) / len(word_counts), 1) if word_counts else 0,
        "min_words": min(word_counts) if word_counts else 0,
        "max_words": max(word_counts) if word_counts else 0,
        "memories": memories,
        "memory_stats": [list(r) for r in memory_stats],
        "guard_trips": sum(
            1 for s in sessions for t in s["turns"] if t["stop_reason"] == "guard_tripped"
        ),
        "compaction_count": len(all_compactions),
        "compaction_quality": {
            "count": len(all_compactions),
            "with_writing_context": compactions_with_context,
            "avg_saving_ratio": round(
                sum(c["saving_ratio"] for c in all_compactions) / len(all_compactions), 3
            ) if all_compactions else 0.0,
        },
        "hallucinated_tools": hallucinated_tools,
        "unknown_tool_count": len(all_hallucinated),
        "unknown_tool_rate": unknown_tool_rate,
        "chapter_quality": [
            {"chapter_index": idx, "quality": q["quality"], "issue_types": q["issue_types"]}
            for idx, q in sorted(quality_by_chapter.items())
        ],
        "total_prompt_tokens": sum(
            t["prompt_tokens"] or 0 for s in sessions for t in s["turns"]
        ),
        "total_completion_tokens": sum(
            t["completion_tokens"] or 0 for s in sessions for t in s["turns"]
        ),
        "tool_errors": [e for s in sessions for e in s["errors"]],
        "chapters": [
            {"index": c[0], "title": c[1], "word_count": c[2], "status": c[3], "created_at": str(c[4])}
            for c in chapters
        ],
        "sessions": sessions,
        "analyzed_at": datetime.now().isoformat(),
    }

    # chapters.csv
    csv_path = os.path.join(out_dir, f"{project_id}_chapters.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["chapter_index", "title", "word_count", "status", "created_at"])
        w.writerows(chapters)

    # sessions.json
    with open(os.path.join(out_dir, f"{project_id}_sessions.json"), "w", encoding="utf-8") as f:
        json.dump({"sessions": sessions}, f, ensure_ascii=False, indent=2)

    # report.md
    md_lines = [
        f"# Dogfood 分析报告 · {report['project_name'] or project_id}",
        "",
        f"- 分析时间：{report['analyzed_at']}",
        f"- 项目状态：{report['project_status']} / {report['phase']}",
        f"- 章节：{report['total_chapters']}（最大 {report['max_chapter']}）",
        f"- 总字数：{report['total_words']}，平均 {report['avg_words_per_chapter']}/章，"
        f"范围 {report['min_words']}-{report['max_words']}",
        f"- 记忆条数：{report['memories']}",
        f"- 护栏触发：{report['guard_trips']}",
        f"- 压缩次数：{report['compaction_count']}",
        f"- tokens：输入 {report['total_prompt_tokens']} / 输出 {report['total_completion_tokens']}",
        f"- 工具错误：{len(report['tool_errors'])}",
        f"- 幻觉工具调用：{report['unknown_tool_count']} 次（工具消息中占 {report['unknown_tool_rate']}%）",
        f"- 质量自检覆盖：{len(report['chapter_quality'])} 章",
        f"- 压缩摘要含写作上下文：{report['compaction_quality']['with_writing_context']}/"
        f"{report['compaction_quality']['count']}",
        "",
        "## 幻觉工具调用",
        "",
    ]
    if report["hallucinated_tools"]:
        md_lines += ["| 工具名 | 次数 |", "|---|---|"]
        md_lines += [f"| {t['name']} | {t['count']} |" for t in report["hallucinated_tools"]]
    else:
        md_lines += ["无。"]
    md_lines += [
        "",
        "## 每章质量自检",
        "",
        "| 章节 | 质量 | 问题类型 |",
        "|---|---|---|",
    ]
    if report["chapter_quality"]:
        md_lines += [
            f"| Ch{q['chapter_index']} | {q['quality']} | {'、'.join(q['issue_types']) or '-'} |"
            for q in report["chapter_quality"]
        ]
    else:
        md_lines += ["（无质量自检记录）"]
    md_lines += [
        "",
        "## 压缩摘要质量",
        "",
        f"- 压缩 {report['compaction_quality']['count']} 次，其中 "
        f"{report['compaction_quality']['with_writing_context']} 次摘要保留了写作上下文"
        f"（最近写入章节/质量自检/最近写作上下文）。",
        f"- 平均节省比例：{report['compaction_quality']['avg_saving_ratio']:.1%}",
        "",
        "## 字数趋势（每 10 章窗口）",
        "",
        "| 窗口 | 平均字数 | 最小 | 最大 |",
        "|---|---|---|---|",
    ]
    for i in range(0, len(word_counts), 10):
        window = word_counts[i:i + 10]
        md_lines.append(
            f"| Ch{i + 1}-{i + len(window)} | {sum(window) // len(window)} | {min(window)} | {max(window)} |"
        )
    if report["tool_errors"]:
        md_lines += ["", "## 工具错误", ""]
        md_lines += [f"- {e}" for e in report["tool_errors"][:20]]
    for s in sessions:
        if s["compactions"]:
            md_lines += ["", f"## 会话 {s['session_id'][:8]} 压缩记录", ""]
            for c in s["compactions"]:
                md_lines.append(
                    f"- {c['usage_pct']:.1%} 触发：{c['before_count']} → {c['after_count']} 条；{c['summary'][:120]}"
                )
    md_lines.append("")
    md_path = os.path.join(out_dir, f"{project_id}_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--project-id", required=True)
    p.add_argument("--out", default=r"C:\tmp\dogfood_reports")
    args = p.parse_args()
    report = analyze(args.project_id, args.out)
    print(
        f"project={report['project_name']} chapters={report['total_chapters']} "
        f"words={report['total_words']} guards={report['guard_trips']} "
        f"compactions={report['compaction_count']} tool_errors={len(report['tool_errors'])} "
        f"hallucinated={report['unknown_tool_count']}({report['unknown_tool_rate']}%) "
        f"quality_checked={len(report['chapter_quality'])}"
    )
    print(f"report written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

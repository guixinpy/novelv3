"""验证前置：创建项目并生成设定 + N 章大纲 + 弧线规划（L4=50 章，M5=200 章）。"""
from __future__ import annotations

import asyncio
import argparse
import json
import sys

import httpx


BASE = "http://127.0.0.1:8000"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="创建项目并生成设定/大纲/弧线")
    p.add_argument("--name", default="M4-50章", help="项目名")
    p.add_argument("--genre", default="悬疑", help="题材")
    p.add_argument("--total-chapters", type=int, default=50, help="目标章节数")
    p.add_argument("--arcs", type=int, default=5, help="弧线数量")
    return p.parse_args()


async def send(client: httpx.AsyncClient, sid: str, content: str) -> list[dict]:
    events: list[dict] = []
    evt = "unknown"
    async with client.stream(
        "POST", f"{BASE}/api/v2/sessions/{sid}/messages", json={"content": content}
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("event: "):
                evt = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
                events.append({"type": evt, "data": data})
                if evt == "approval_pending":
                    print(f"  [approval] {data.get('tool_name', '?')}")
                    await client.post(
                        f"{BASE}/api/v2/sessions/{sid}/approve", json={"reason": "auto"}
                    )
                elif evt == "tool_call_started":
                    print(f"  [tool] {data.get('tool_name', '?')}")
                elif evt == "turn_ended":
                    print(
                        f"  [turn] {data.get('stop_reason', '?')}, "
                        f"{data.get('iterations', 0)} iters"
                    )
    return events


async def main() -> int:
    args = parse_args()
    total = args.total_chapters
    arcs_n = args.arcs
    per = max(1, total // arcs_n)
    arc_spans = []
    for i in range(arcs_n):
        s = i * per + 1
        e = (i + 1) * per if i < arcs_n - 1 else total
        arc_spans.append(f"「第{i + 1}弧」(Ch{s}-{e})")
    arc_text = "、".join(arc_spans)

    async with httpx.AsyncClient(timeout=httpx.Timeout(1200.0, connect=60.0, read=300.0, write=60.0)) as client:
        r = await client.post(
            f"{BASE}/api/v1/projects",
            json={"name": args.name, "genre": args.genre, "language": "zh-CN"},
        )
        r.raise_for_status()
        pid = r.json().get("id")
        print(f"Project: {pid}")

        r2 = await client.post(f"{BASE}/api/v2/projects/{pid}/sessions")
        r2.raise_for_status()
        sid = r2.json()["session_id"]
        print(f"Session: {sid}")

        print(f"Phase 0: {arcs_n}-arc plan + setup + {total}-ch outline")
        await send(
            client,
            sid,
            f"请为这个{args.genre}小说项目做开工准备，目标是一部完整的超长篇（{total} 章）："
            f"1) 用 plan_arc define 创建 {arcs_n} 条弧线：{arc_text}，每条弧线写清概要；"
            "2) 用 update_setup 生成完整世界观设定（含主角与关键人物）；"
            f"3) 用 update_outline 生成 {total} 章大纲，确保第 {total} 章才是故事结局，中间章节不得提前完结。",
        )
        print("Phase 0 done.")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

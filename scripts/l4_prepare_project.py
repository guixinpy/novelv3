"""L4 50 章验证前置：创建项目并生成设定 + 50 章大纲 + 5 弧线规划。"""
from __future__ import annotations

import asyncio
import json
import sys

import httpx


BASE = "http://127.0.0.1:8000"


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
    async with httpx.AsyncClient(timeout=httpx.Timeout(1200.0, connect=60.0, read=300.0, write=60.0)) as client:
        r = await client.post(
            f"{BASE}/api/v1/projects",
            json={"name": "M4-50章", "genre": "悬疑", "language": "zh-CN"},
        )
        r.raise_for_status()
        pid = r.json().get("id")
        print(f"Project: {pid}")

        r2 = await client.post(f"{BASE}/api/v2/projects/{pid}/sessions")
        r2.raise_for_status()
        sid = r2.json()["session_id"]
        print(f"Session: {sid}")

        print("Phase 0: 5-arc plan + setup + 50-ch outline")
        await send(
            client,
            sid,
            "请为这个悬疑小说项目做开工准备，目标是一部完整的中长篇（50 章）："
            "1) 用 plan_arc define 创建五条弧线：「第一弧·起源」(Ch1-10)、「第二弧·暗流」(Ch11-20)、"
            "「第三弧·迷雾」(Ch21-30)、「第四弧·裂痕」(Ch31-40)、「第五弧·终局」(Ch41-50)，每条弧线写清概要；"
            "2) 用 update_setup 生成完整世界观设定（含主角与关键人物）；"
            "3) 用 update_outline 生成 50 章大纲，确保第 50 章才是故事结局，中间章节不得提前完结。",
        )
        print("Phase 0 done.")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

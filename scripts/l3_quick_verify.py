"""L3 快速验证：一次调用完成设定→大纲→10章"""
from __future__ import annotations
import asyncio, json, sys
import httpx

BASE = "http://127.0.0.1:8765"
PROJECT_ID = "0bcd0198-a99c-4f9c-a4f9-9f258fb01e86"


async def send_and_wait(client, session_id, content):
    """发送消息，自动审批，等待回合完成。返回事件列表。"""
    events = []
    event_type = "unknown"
    async with client.stream(
        "POST", f"{BASE}/api/v2/sessions/{session_id}/messages",
        json={"content": content},
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            line = line.strip()
            if not line: continue
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
                events.append({"type": event_type, "data": data})
                if event_type == "approval_pending":
                    await client.post(f"{BASE}/api/v2/sessions/{session_id}/approve", json={"reason": "auto"})
                    print(f"  [APPROVED] {data.get('tool_name', '?')}")
                elif event_type == "tool_call_started":
                    print(f"  [TOOL] {data.get('name', '?')}")
                elif event_type == "tool_call_finished":
                    flag = "ERR" if data.get("is_error") else "OK"
                    print(f"  [{flag}] {data.get('name', '?')}")
                elif event_type == "turn_ended":
                    print(f"  [DONE] {data.get('stop_reason')} ({data.get('iterations')} iters)")
    return events


async def main():
    async with httpx.AsyncClient(timeout=httpx.Timeout(1200.0, connect=60.0, read=300.0, write=60.0, pool=60.0)) as client:
        # Step 0: Create session
        r = await client.post(f"{BASE}/api/v2/projects/{PROJECT_ID}/sessions")
        sid = r.json()["session_id"]
        print(f"会话: {sid}\n")

        # Step 1: Generate setup + outline
        print("=" * 50)
        print("Step 1: 生成设定 + 大纲")
        print("=" * 50)
        await send_and_wait(client, sid,
            "请为悬疑小说项目完成以下工作："
            "1. 用 generate_setup 生成世界观设定；"
            "2. 用 generate_outline 生成 10 章大纲，主角林舟。"
        )

        # Step 2: Generate 10 chapters one by one
        for ch in range(1, 11):
            print(f"\n{'=' * 50}")
            print(f"Step 2.{ch}: 第 {ch} 章")
            print("=" * 50)
            msg = (
                f"请写第 {ch} 章。完成后用 check_chapter_quality 自检。"
                if ch == 1 else
                f"请继续写第 {ch} 章。写之前用 query_world 确认人物位置关系。完成后用 check_chapter_quality 自检。"
            )
            events = await send_and_wait(client, sid, msg)

            # Check for guard trips
            for e in events:
                if e["type"] == "turn_ended" and e["data"].get("stop_reason") == "guard_tripped":
                    print(f"\n  *** 护栏触发！{e['data']}")
                    return 1

            # Verify chapter was written
            writes = sum(1 for e in events if e["type"] == "tool_call_started" and "write_chapter" in str(e["data"].get("name", "")))
            if writes == 0:
                print(f"  *** 第 {ch} 章: write_chapter 未被调用")
                return 1
            print(f"  [OK] 第 {ch} 章完成")

        print("\n" + "=" * 50)
        print("*** L3 验证通过！10 章无人值守生成完成")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

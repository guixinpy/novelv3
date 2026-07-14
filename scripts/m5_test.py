"""M5 综合测试：弧线规划 + 质量趋势 + 10章生成"""
from __future__ import annotations
import asyncio, json, sys
import httpx

BASE = "http://127.0.0.1:8765"

async def send_and_wait(client, session_id, content):
    events, evt = [], "unknown"
    async with client.stream("POST", f"{BASE}/api/v2/sessions/{session_id}/messages", json={"content": content}) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            line = line.strip()
            if not line: continue
            if line.startswith("event: "): evt = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
                events.append({"type": evt, "data": data})
                if evt == "approval_pending":
                    await client.post(f"{BASE}/api/v2/sessions/{session_id}/approve", json={"reason": "auto"})
                elif evt == "tool_call_started":
                    print(f"  [T] {data.get('name', '?')}")
                elif evt == "tool_call_finished":
                    f = "ERR" if data.get("is_error") else "OK"
                    print(f"  [{f}] {data.get('name', '?')}")
                elif evt == "turn_ended":
                    print(f"  [DONE] {data.get('stop_reason')} ({data.get('iterations')} iters)")
    return events

async def main():
    async with httpx.AsyncClient(timeout=httpx.Timeout(1200.0, connect=60.0, read=300.0, write=60.0)) as client:
        # Create project
        r = await client.post(f"{BASE}/api/v1/projects", json={"name": "M5-Test", "genre": "科幻", "language": "zh-CN"})
        pid = r.json()["id"] if "id" in r.json() else print(f"Create resp: {r.json()}")
        if not pid:
            # Use existing project
            pid = "0bcd0198-a99c-4f9c-a4f9-9f258fb01e86"
        r2 = await client.post(f"{BASE}/api/v2/projects/{pid}/sessions")
        sid = r2.json()["session_id"]
        print(f"Project: {pid[:8]}...")
        print(f"Session: {sid[:8]}...")

        # Step 1: Plan arc + generate setup + outline
        print("\n=== Step 1: Arc + Setup + Outline ===")
        await send_and_wait(client, sid,
            "请为科幻小说项目完成以下工作："
            "1. 用 plan_arc define 创建一个 10 章的故事弧线「第一弧·觉醒」，包含弧线概要；"
            "2. 用 update_setup 生成世界观设定；"
            "3. 用 update_outline 生成 10 章大纲（每章一个节点）。"
        )

        # Step 2: Generate 10 chapters with arc progress + quality trend checks
        for ch in range(1, 11):
            print(f"\n=== Ch{ch}/10 ===")
            if ch == 1:
                msg = "请写第 1 章。写完后用 check_chapter_quality 自检，用 plan_arc progress 查看弧线进度。"
            elif ch == 6:
                msg = (f"请写第 {ch} 章（弧线中点）。写前用 plan_arc progress 查看进度。"
                       f"写后用 check_quality_trend 检查质量趋势。")
            elif ch >= 8:
                msg = (f"请写第 {ch} 章（接近弧线尾声）。写前用 plan_arc progress 确认进度。"
                       f"如果弧线将结束，提前规划下一弧线。写后用 check_quality_trend 检查趋势。")
            else:
                msg = (f"请写第 {ch} 章。写后用 check_chapter_quality + plan_arc progress。")

            events = await send_and_wait(client, sid, msg)
            writes = sum(1 for e in events if e["type"] == "tool_call_started" and "write_chapter" in str(e["data"].get("name", "")))
            if writes == 0:
                print(f"  [FAIL] write_chapter missing at Ch{ch}")
                return 1
            arc_calls = sum(1 for e in events if e["type"] == "tool_call_started" and "plan_arc" in str(e["data"].get("name", "")))
            trend_calls = sum(1 for e in events if e["type"] == "tool_call_started" and "check_quality_trend" in str(e["data"].get("name", "")))
            print(f"  [OK] Ch{ch} done, arc_calls={arc_calls}, trend_calls={trend_calls}")

        # Verify chapters
        chk = await client.get(f"{BASE}/api/v1/projects/{pid}/chapters")
        chs = chk.json()
        items = chs if isinstance(chs, list) else chs.get('chapters', [])
        print(f"\n=== RESULT: {len(items)} chapters ===")
        for c in items:
            wc = c.get('word_count', 0) or 0
            print(f"  Ch{c.get('chapter_index', '?')}: {str(c.get('title', '?'))[:45]} ({wc}字)")
        print("PASS" if len(items) >= 10 else "FAIL")
        return 0 if len(items) >= 10 else 1

asyncio.run(main())

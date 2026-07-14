"""M5 全功能综合测试：16工具 + 15章 + 所有M5组件"""
from __future__ import annotations
import asyncio, json, sys
import httpx

BASE = "http://127.0.0.1:8765"

async def send(client, sid, content):
    events, evt = [], "unknown"
    async with client.stream("POST", f"{BASE}/api/v2/sessions/{sid}/messages", json={"content": content}) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            line = line.strip()
            if not line: continue
            if line.startswith("event: "): evt = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
                events.append({"type": evt, "data": data})
                if evt == "approval_pending":
                    await client.post(f"{BASE}/api/v2/sessions/{sid}/approve", json={"reason": "auto"})
    return events

def count_tool(events, name):
    return sum(1 for e in events if e["type"] == "tool_call_started" and name in str(e["data"].get("name", "")))

async def main():
    async with httpx.AsyncClient(timeout=httpx.Timeout(1200.0, connect=60.0, read=300.0, write=60.0)) as client:
        # Create project
        r = await client.post(f"{BASE}/api/v1/projects", json={"name": "M5-Full-Test", "genre": "奇幻", "language": "zh-CN"})
        pid = r.json().get("id") or (await client.get(f"{BASE}/api/v1/projects")).json()[-1]["id"]
        r2 = await client.post(f"{BASE}/api/v2/projects/{pid}/sessions")
        sid = r2.json()["session_id"]
        print(f"Project: {pid[:8]}  Session: {sid[:8]}\n")

        # Phase 1: Arc + Setup + Outline
        print("=" * 50 + "\nPhase 1: Arc + Setup + Outline\n" + "=" * 50)
        await send(client, sid,
            "1) 用 plan_arc define 创建 15 章弧线「第一弧·龙醒」，概要：少年在废墟中发现龙蛋，踏上驭龙之路。"
            "2) 用 update_setup 生成奇幻世界观设定。"
            "3) 用 update_outline 生成 15 章大纲。"
        )
        print("Phase 1 complete.\n")

        # Phase 2: Generate 15 chapters
        stats = {"chapters": 0, "plan_arc": 0, "quality_trend": 0, "entity_rel": 0,
                 "query_mem": 0, "track_plot": 0, "check_qual": 0}
        wcs = []

        for ch in range(1, 16):
            print(f"Ch{ch:>2}/15 ", end="", flush=True)

            if ch == 1:
                msg = ("请写第 1 章。写前用 query_world 检查世界设定。"
                       "写后用 check_chapter_quality 自检 + plan_arc progress 查进度 + track_plotline 登记情节线。")
            elif ch == 8:
                msg = (f"请写第 {ch} 章（弧线中点）。写前用 plan_arc progress + check_quality_trend。"
                       f"写后用 derive_entity_relations 检查关键角色共现关系。")
            elif ch >= 12:
                msg = (f"请写第 {ch} 章（弧线尾声）。写前用 plan_arc progress 确认进度——"
                       f"如果弧线即将结束，提前用 plan_arc define 规划「第二弧」。"
                       f"写后用 check_quality_trend + derive_entity_relations。")
            else:
                msg = (f"请写第 {ch} 章。写后用 check_chapter_quality + plan_arc progress + track_plotline。")

            events = await send(client, sid, msg)

            # Collect stats
            stats["plan_arc"] += count_tool(events, "plan_arc")
            stats["quality_trend"] += count_tool(events, "check_quality_trend")
            stats["entity_rel"] += count_tool(events, "derive_entity_relations")
            stats["query_mem"] += count_tool(events, "query_memory")
            stats["track_plot"] += count_tool(events, "track_plotline")
            stats["check_qual"] += count_tool(events, "check_chapter_quality")
            writes = count_tool(events, "write_chapter")
            if writes: stats["chapters"] += 1

            # Get chapter word count
            chs = (await client.get(f"{BASE}/api/v1/projects/{pid}/chapters")).json()
            items = chs if isinstance(chs, list) else chs.get("chapters", [])
            wc = items[-1].get("word_count", 0) if items else 0
            wcs.append(wc)
            trend = "stable" if len(wcs) < 3 else (
                "growing" if wcs[-1] > wcs[0]*1.1 else ("declining" if wcs[-1] < wcs[0]*0.7 else "stable"))
            print(f"{wc:>5}字 [{trend}]")

            if not writes:
                print(f"  FAIL: write_chapter missing!")
                break

        # Report
        print(f"\n{'=' * 50}\nM5 Full Test Results\n{'=' * 50}")
        print(f"Chapters: {stats['chapters']}/15")
        print(f"Tool usage:")
        for k in ["plan_arc", "quality_trend", "entity_rel", "query_mem", "track_plot", "check_qual"]:
            print(f"  {k}: {stats[k]} calls")
        if len(wcs) >= 2:
            first3 = sum(wcs[:3])/3 if len(wcs)>=3 else wcs[0]
            last3 = sum(wcs[-3:])/3 if len(wcs)>=3 else wcs[-1]
            ratio = last3/max(1,first3)
            print(f"Word trend: {int(first3)} -> {int(last3)} (ratio={ratio:.2f}, {'STABLE' if 0.7<=ratio<=1.3 else 'DECLINING' if ratio<0.7 else 'GROWING'})")
        print(f"Result: {'PASS' if stats['chapters']>=15 and (len(wcs)<3 or 0.7<=last3/max(1,first3)<=1.3) else 'NEEDS REVIEW'}")

        return 0 if stats['chapters'] >= 15 else 1

asyncio.run(main())

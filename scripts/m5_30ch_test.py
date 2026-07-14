"""M5 30章大规模多弧线过渡测试"""
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
        r = await client.post(f"{BASE}/api/v1/projects", json={"name": "M5-30章", "genre": "奇幻", "language": "zh-CN"})
        pid = r.json().get("id") or (await client.get(f"{BASE}/api/v1/projects")).json()[-1]["id"]
        r2 = await client.post(f"{BASE}/api/v2/projects/{pid}/sessions")
        sid = r2.json()["session_id"]
        print(f"Project: {pid[:8]}  Session: {sid[:8]}\n")

        # Phase 1: 3-arc plan + setup + outline
        print("=" * 50 + "\nPhase 1: 3-Arc Plan + Setup + 30-Ch Outline\n" + "=" * 50)
        await send(client, sid,
            "请为奇幻小说项目做以下工作："
            "1) 用 plan_arc define 创建三条弧线：「第一弧·觉醒」(Ch1-10)、「第二弧·远征」(Ch11-20)、「第三弧·终焉」(Ch21-30)，每条弧线写清概要；"
            "2) 用 update_setup 生成世界观设定；"
            "3) 用 update_outline 生成 30 章大纲。"
        )
        print("Phase 1 done.\n")

        # Phase 2: 30 chapters
        stats = {"chapters": 0, "plan_arc": 0, "quality_trend": 0, "entity_rel": 0, "mem_tree": 0}
        wcs = []

        for ch in range(1, 31):
            if ch == 1:
                msg = "请写第 1 章。写后用 check_chapter_quality + plan_arc progress + track_plotline。"
            elif ch == 10:
                msg = ("第 10 章（第一弧终点）。写前用 plan_arc progress。弧线应已完成——用 memory_tree 查看记忆树，"
                       "确认弧线摘要已自动生成。完成后准备进入第二弧。")
            elif ch == 11:
                msg = ("第 11 章（第二弧起点）。先激活第二弧（plan_arc progress 应自动切换），"
                       "写前用 query_memory type=arc_summary 回顾第一弧摘要。写后 check_quality_trend。")
            elif ch == 20:
                msg = ("第 20 章（第二弧终点）。用 memory_tree overview 查看记忆覆盖。"
                       "确保第二弧摘要生成后进入第三弧。")
            elif ch == 21:
                msg = ("第 21 章（第三弧起点）。先回顾前两弧摘要(query_memory)，"
                       "再用 derive_entity_relations 检查关键角色关系网。")
            else:
                msg = (f"第 {ch} 章。写后用 check_chapter_quality + plan_arc progress。(弧线中点/终点时额外用 check_quality_trend)")
                if ch in (5, 15, 25):
                    msg = f"第 {ch} 章（弧线中点）。写前用 plan_arc progress。写后用 check_quality_trend + track_plotline。"

            print(f"Ch{ch:>2}/30 ", end="", flush=True)
            events = await send(client, sid, msg)
            stats["plan_arc"] += count_tool(events, "plan_arc")
            stats["quality_trend"] += count_tool(events, "check_quality_trend")
            stats["entity_rel"] += count_tool(events, "derive_entity_relations")
            stats["mem_tree"] += count_tool(events, "memory_tree")
            writes = count_tool(events, "write_chapter")
            if writes: stats["chapters"] += 1

            chs = (await client.get(f"{BASE}/api/v1/projects/{pid}/chapters")).json()
            items = chs if isinstance(chs, list) else chs.get("chapters", [])
            wc = items[-1].get("word_count", 0) if items else 0
            wcs.append(wc)
            print(f"{wc:>5}字" + (" [trend]" if ch in (10, 20, 30) else ""))

            if not writes:
                print(f"  FAIL at Ch{ch}!")
                break

        # Report
        print(f"\n{'=' * 50}\nM5 30-Chapter Results\n{'=' * 50}")
        print(f"Chapters: {stats['chapters']}/30")
        for k, v in stats.items():
            if k != "chapters": print(f"  {k}: {v} calls")
        if len(wcs) >= 6:
            seg_size = max(1, len(wcs)//3)
            s1 = sum(wcs[:seg_size])/seg_size
            s2 = sum(wcs[seg_size:2*seg_size])/(2*seg_size-seg_size)
            s3 = sum(wcs[2*seg_size:])/max(1,len(wcs)-2*seg_size)
            print(f"Word trend: {int(s1)} -> {int(s2)} -> {int(s3)}")
            stable = 0.7 <= s3/max(1,s1) <= 1.3
            print(f"Result: {'PASS - STABLE across 3 arcs' if stable else 'REVIEW - trend needs attention'}")
        else:
            print("Result: INCOMPLETE")
        return 0 if stats["chapters"] >= 30 else 1

asyncio.run(main())

"""L4 记忆狗食快速验证：从已有项目继续生成 40 章（总计 50 章）"""
from __future__ import annotations
import asyncio, json, sys
import httpx

BASE = "http://127.0.0.1:8765"
PROJECT_ID = "0bcd0198-a99c-4f9c-a4f9-9f258fb01e86"
START_CHAPTER = 11  # Already have 10 chapters from L3
TOTAL_TARGET = 50


async def send_and_wait(client, session_id, content):
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
                    print(f"  [A] {data.get('tool_name', '?')}")
                elif event_type == "tool_call_started":
                    print(f"  [T] {data.get('name', '?')}")
                elif event_type == "tool_call_finished":
                    flag = "ERR" if data.get("is_error") else "OK"
                    print(f"  [{flag}] {data.get('name', '?')}")
                elif event_type == "context_warning":
                    print(f"  [CTX] {data.get('usage_pct', 0):.1%} of context")
                elif event_type == "turn_ended":
                    print(f"  [DONE] {data.get('stop_reason')} ({data.get('iterations')} iters)")
    return events


async def main():
    async with httpx.AsyncClient(timeout=httpx.Timeout(1200.0, connect=60.0, read=300.0, write=60.0, pool=60.0)) as client:
        r = await client.post(f"{BASE}/api/v2/projects/{PROJECT_ID}/sessions")
        sid = r.json()["session_id"]
        print(f"Session: {sid[:8]}...")
        print(f"Resuming from Ch{START_CHAPTER}, target Ch{TOTAL_TARGET}\n")

        stats = {"chapters": 0, "mem_queries": 0, "plotlines": 0, "guard_trips": 0, "errors": 0}

        for ch in range(START_CHAPTER, TOTAL_TARGET + 1):
            print(f"\n{'=' * 50}")
            print(f"Chapter {ch}/{TOTAL_TARGET}")
            print("=" * 50)

            if ch == START_CHAPTER:
                msg = (
                    f"请继续写第 {ch} 章。写之前务必：\n"
                    f"1. 用 query_memory 回顾当前人物位置和关系（不要读早期章节正文）\n"
                    f"2. 用 track_plotline query 确认开放的情节线状态\n"
                    f"写完后：\n"
                    f"3. 用 check_chapter_quality 自检\n"
                    f"4. 用 track_plotline 推进或闭环相关情节线"
                )
            else:
                msg = (
                    f"请继续写第 {ch} 章。写之前用 query_memory 回顾人物关系，"
                    f"用 track_plotline query 看开放情节线。"
                    f"完成后用 check_chapter_quality + track_plotline 维护记忆。"
                )

            try:
                events = await send_and_wait(client, sid, msg)
            except Exception as exc:
                print(f"  [FAIL] Ch{ch}: {exc}")
                stats["errors"] += 1
                break

            for e in events:
                if e["type"] == "turn_ended" and e["data"].get("stop_reason") == "guard_tripped":
                    stats["guard_trips"] += 1
                    print(f"  [GUARD] TRIPPED at Ch{ch}!")
                    break

            writes = sum(1 for e in events if e["type"] == "tool_call_started" and "write_chapter" in str(e["data"].get("name", "")))
            mems = sum(1 for e in events if e["type"] == "tool_call_started" and e["data"].get("name") == "query_memory")
            tracks = sum(1 for e in events if e["type"] == "tool_call_started" and "track_plotline" in str(e["data"].get("name", "")))
            reads = sum(1 for e in events if e["type"] == "tool_call_started" and "read_chapter" in str(e["data"].get("name", "")))

            if writes > 0:
                stats["chapters"] += 1
                stats["mem_queries"] += mems
                stats["plotlines"] += tracks
                print(f"  [STATS] ch={stats['chapters']}, mem_q={mems}, plot={tracks}, reads={reads}")
            else:
                print(f"  [MISS] write_chapter not called at Ch{ch}")
                stats["errors"] += 1
                break

        print(f"\n{'=' * 50}")
        print(f"L4 DOGFOOD COMPLETE")
        print(f"  Chapters: {stats['chapters']}/{-START_CHAPTER + TOTAL_TARGET}")
        print(f"  Memory queries: {stats['mem_queries']}")
        print(f"  Plotline operations: {stats['plotlines']}")
        print(f"  Guard trips: {stats['guard_trips']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Result: {'PASS' if stats['chapters'] >= -START_CHAPTER + TOTAL_TARGET and stats['errors'] == 0 else 'FAIL'}")
        return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

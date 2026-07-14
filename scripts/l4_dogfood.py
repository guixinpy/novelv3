#!/usr/bin/env python
"""L4 记忆狗食验证：50 章一致性验证。

前置条件：
1. 后端服务运行中
2. DeepSeek API key 已配置
3. 已创建测试项目（设定 + 大纲就绪）

用法：
    python l4_dogfood.py --project-id <PROJECT_ID> [--chapters 50]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx


@dataclass
class DogfoodResult:
    chapters_written: int = 0
    plotlines_tracked: int = 0
    plotlines_closed: int = 0
    memory_queries: int = 0
    consistency_issues: list[str] = field(default_factory=list)
    guard_trips: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""

    @property
    def success(self) -> bool:
        return self.chapters_written >= 50 and len(self.errors) == 0

    def report(self) -> str:
        lines = [
            "=" * 60,
            "L4 Memory Dogfood Report",
            "=" * 60,
            f"  Start: {self.start_time}",
            f"  End:   {self.end_time}",
            f"  Chapters: {self.chapters_written}/50",
            f"  Plotlines tracked: {self.plotlines_tracked}",
            f"  Plotlines closed:  {self.plotlines_closed}",
            f"  Memory queries:    {self.memory_queries}",
            f"  Guard trips: {len(self.guard_trips)}",
            f"  Consistency issues: {len(self.consistency_issues)}",
            f"  Errors: {len(self.errors)}",
            f"  Status: {'PASS' if self.success else 'FAIL'}",
        ]
        if self.consistency_issues:
            lines.append("\nConsistency Issues:")
            for ci in self.consistency_issues[:20]:
                lines.append(f"  - {ci}")
            if len(self.consistency_issues) > 20:
                lines.append(f"  ... and {len(self.consistency_issues) - 20} more")
        if self.errors:
            lines.append("\nErrors:")
            for e in self.errors:
                lines.append(f"  - {e}")
        return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="L4 Memory Dogfood")
    p.add_argument("--project-id", required=True, help="Project ID")
    p.add_argument("--base-url", default="http://localhost:8000", help="API URL")
    p.add_argument("--chapters", type=int, default=50, help="Target chapters")
    p.add_argument("--timeout", type=int, default=600, help="Timeout per chapter (s)")
    p.add_argument("--start-chapter", type=int, default=1, help="Starting chapter index")
    return p.parse_args()


class L4DogfoodRunner:
    def __init__(self, base_url: str, project_id: str, chapter_count: int, timeout: int, start_chapter: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.project_id = project_id
        self.chapter_count = chapter_count
        self.timeout = timeout
        self.start_chapter = start_chapter
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))
        self.session_id: str = ""

    async def create_session(self) -> str:
        r = await self.client.post(f"{self.base_url}/api/v2/projects/{self.project_id}/sessions")
        r.raise_for_status()
        data: dict[str, str] = r.json()
        self.session_id = data["session_id"]
        print(f"Session: {self.session_id}")
        return self.session_id

    async def send_message(self, content: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        event_type: str = "unknown"

        async with self.client.stream(
            "POST",
            f"{self.base_url}/api/v2/sessions/{self.session_id}/messages",
            json={"content": content},
        ) as response:
            response.raise_for_status()
            async for raw_line in response.aiter_lines():
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("event: "):
                    event_type = line[7:]
                elif line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    events.append({"type": event_type, "data": data})

                    if event_type == "approval_pending":
                        print(f"  [approval] {data.get('tool_name', '?')}")
                        await self.approve()

                    elif event_type == "tool_call_started":
                        tool = data.get("tool_name", "?")
                        print(f"  [tool] {tool}")

                    elif event_type == "tool_call_finished":
                        ok = "ERR" if data.get("is_error") else "OK"
                        print(f"  [tool] {ok}: {data.get('tool_name', '?')}")

                    elif event_type == "turn_ended":
                        print(
                            f"  [turn] {data.get('stop_reason', '?')}, "
                            f"{data.get('iterations', 0)} iters"
                        )
        return events

    async def approve(self) -> None:
        try:
            await self.client.post(
                f"{self.base_url}/api/v2/sessions/{self.session_id}/approve",
                json={"reason": "auto"},
            )
            print("  [approval] auto-approved")
        except Exception:
            pass

    def _count_tool_calls(self, events: list[dict[str, Any]], tool_name: str) -> int:
        return sum(
            1 for e in events
            if e["type"] == "tool_call_started" and e["data"].get("tool_name") == tool_name
        )

    async def run(self) -> DogfoodResult:
        result = DogfoodResult(start_time=datetime.now(UTC).isoformat())

        for ch in range(self.start_chapter, self.start_chapter + self.chapter_count):
            if ch == 1:
                await self.create_session()
                msg = (
                    "请写第 1 章。完成后："
                    "1) 用 track_plotline 登记新出现的情节线和伏笔；"
                    "2) 用 check_chapter_quality 自检；"
                    "3) 用 query_memory 确认人物状态一致。"
                )
            else:
                msg = (
                    f"请继续写第 {ch} 章。写之前："
                    f"1) 用 query_memory 回顾当前人物位置和关系；"
                    f"2) 用 track_plotline query 确认开放的情节线状态；"
                    f"写完后："
                    f"3) 用 check_chapter_quality 自检；"
                    f"4) 用 track_plotline 推进或闭环相关情节线。"
                )

            print(f"\n{'=' * 40}")
            print(f"Chapter {ch}/{self.start_chapter + self.chapter_count - 1}")
            print(f"{'=' * 40}")

            try:
                events = await self.send_message(msg)
            except Exception as exc:
                result.errors.append(f"Ch {ch}: {exc}")
                break

            # Check for guard trips
            for e in events:
                if e["type"] == "turn_ended" and e["data"].get("stop_reason") == "guard_tripped":
                    result.guard_trips.append(e["data"])
                    result.errors.append(f"Ch {ch}: Guard tripped: {e['data'].get('stop_reason')}")
                    break

            if result.errors:
                break

            # Count tool usage
            write_count = self._count_tool_calls(events, "write_chapter")
            track_count = self._count_tool_calls(events, "track_plotline")
            mem_query_count = self._count_tool_calls(events, "query_memory")

            if write_count > 0:
                result.chapters_written += 1
                result.plotlines_tracked += track_count
                result.memory_queries += mem_query_count

                print(f"  [stats] written={result.chapters_written}, "
                      f"plotline_calls={track_count}, mem_queries={mem_query_count}")
            else:
                result.errors.append(f"Ch {ch}: write_chapter not called")
                break

        result.end_time = datetime.now(UTC).isoformat()
        return result

    async def verify_memory_recall(self) -> bool:
        """记忆召回质量验证：Agent 能否通过记忆工具（不用全文重读）回答问题。"""
        print("\n=== Memory Recall Quality Test ===")
        await self.create_session()

        questions = [
            "主角现在在哪里？和谁在一起？请通过 query_memory 回答，不要读章节正文。",
            "当前开放的情节线有哪些？请通过 track_plotline query 回答。",
            "最近 5 章新增了哪些重要人物？请通过 query_memory 回答。",
        ]
        all_ok = True
        for q in questions:
            print(f"\n[recall] {q}")
            try:
                events = await self.send_message(q)
                query_calls = self._count_tool_calls(events, "query_memory")
                track_calls = self._count_tool_calls(events, "track_plotline")
                read_calls = self._count_tool_calls(events, "read_chapter")

                if read_calls > 0:
                    print(f"  WARNING: Agent used read_chapter ({read_calls}x) instead of memory")
                    all_ok = False
                if query_calls + track_calls > 0:
                    print(f"  OK: Agent used memory tools ({query_calls + track_calls}x)")
            except Exception as exc:
                print(f"  ERROR: {exc}")
                all_ok = False

        return all_ok

    async def close(self) -> None:
        await self.client.aclose()


async def main() -> None:
    args = parse_args()
    runner = L4DogfoodRunner(
        base_url=args.base_url,
        project_id=args.project_id,
        chapter_count=args.chapters,
        timeout=args.timeout,
        start_chapter=args.start_chapter,
    )

    try:
        # Main dogfood run
        print("=" * 60)
        print("L4 Memory Dogfood: 50-Chapter Generation")
        print("=" * 60)
        result = await runner.run()

        # Memory recall test
        recall_ok = await runner.verify_memory_recall()

        if not recall_ok:
            result.errors.append("Memory recall test FAILED")

        print(f"\n{result.report()}")
        sys.exit(0 if result.success and recall_ok else 1)

    except httpx.ConnectError:
        print(f"\nCANNOT CONNECT to {args.base_url}")
        sys.exit(2)
    finally:
        await runner.close()


if __name__ == "__main__":
    asyncio.run(main())

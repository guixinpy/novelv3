#!/usr/bin/env python
"""L3 自治验证脚本：无人值守连续生成 10 章。

前置条件：
1. 后端服务运行中（默认 http://localhost:8000）
2. DeepSeek API key 已配置
3. 已创建测试项目（设定 + 大纲就绪）

用法：
    python l3_verify.py --project-id <PROJECT_ID> [--base-url http://localhost:8000]

验证项：
- 10 章逐章生成（每章一个 turn）
- 审批自动处理
- 护栏熔断检测
- 异常诊断报告
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
class TestResult:
    chapters_written: int = 0
    total_turns: int = 0
    guard_trips: list[dict[str, Any]] = field(default_factory=list)
    context_warnings: list[dict[str, Any]] = field(default_factory=list)
    approval_events: int = 0
    errors: list[str] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""

    @property
    def success(self) -> bool:
        return self.chapters_written >= 10 and len(self.errors) == 0

    def report(self) -> str:
        lines = [
            "=" * 60,
            "L3 自治验证报告",
            "=" * 60,
            f"  开始: {self.start_time}",
            f"  结束: {self.end_time}",
            f"  章节数: {self.chapters_written}/10",
            f"  总轮次: {self.total_turns}",
            f"  审批事件: {self.approval_events}",
            f"  护栏触发: {len(self.guard_trips)}",
            f"  上下文警告: {len(self.context_warnings)}",
            f"  错误数: {len(self.errors)}",
            f"  状态: {'PASS' if self.success else 'FAIL'}",
        ]
        if self.guard_trips:
            lines.append("\n护栏事件:")
            for g in self.guard_trips:
                lines.append(f"  - {g.get('level', '?')}: {g.get('reason', '?')}")
        if self.context_warnings:
            lines.append("\n上下文警告:")
            for w in self.context_warnings:
                lines.append(f"  - {w.get('usage_pct', 0):.1%} ({w.get('total_tokens', 0)} tokens)")
        if self.errors:
            lines.append("\n错误:")
            for e in self.errors:
                lines.append(f"  - {e}")
        return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="L3 自治验证")
    p.add_argument("--project-id", required=True, help="测试项目 ID")
    p.add_argument("--base-url", default="http://localhost:8000", help="API 地址")
    p.add_argument("--chapters", type=int, default=10, help="目标章节数")
    p.add_argument("--timeout", type=int, default=600, help="每章超时（秒）")
    return p.parse_args()


class L3Verifier:
    def __init__(self, base_url: str, project_id: str, chapter_count: int, timeout: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.project_id = project_id
        self.chapter_count = chapter_count
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))
        self.session_id: str = ""

    async def create_session(self) -> str:
        r = await self.client.post(
            f"{self.base_url}/api/v2/projects/{self.project_id}/sessions",
        )
        r.raise_for_status()
        data: dict[str, str] = r.json()
        self.session_id = data["session_id"]
        print(f"Session created: {self.session_id}")
        return self.session_id

    async def send_message(self, content: str) -> list[dict[str, Any]]:
        """发送消息并收集所有 SSE 事件。自动处理审批。"""
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
                        print(f"  [approval] pending: {data.get('tool_name', '?')}")
                        await self.approve()

                    elif event_type == "tool_call_started":
                        print(f"  [tool] start: {data.get('tool_name', '?')}")

                    elif event_type == "tool_call_finished":
                        ok = "OK" if not data.get("is_error") else "ERR"
                        print(f"  [tool] {ok}: {data.get('tool_name', '?')}")

                    elif event_type == "assistant_delta":
                        pass

                    elif event_type == "assistant_message":
                        preview = (data.get("content", "") or "")[:100]
                        if preview.strip():
                            print(f"  [msg] {preview}...")

                    elif event_type == "turn_ended":
                        stop = data.get("stop_reason", "?")
                        iters = data.get("iterations", 0)
                        usage = data.get("usage", {})
                        print(
                            f"  [turn] end: {stop}, {iters} iters, "
                            f"{usage.get('prompt_tokens', 0)}p/{usage.get('completion_tokens', 0)}c"
                        )
        return events

    async def approve(self) -> None:
        try:
            r = await self.client.post(
                f"{self.base_url}/api/v2/sessions/{self.session_id}/approve",
                json={"reason": "auto"},
            )
            if r.is_success:
                print("  [approval] auto-approved")
        except Exception as exc:
            print(f"  [approval] error: {exc}")

    async def verify_unattended_generation(self) -> TestResult:
        """逐章生成验证。每章一个 API 调用。"""
        result = TestResult(start_time=datetime.now(UTC).isoformat())

        for ch in range(1, self.chapter_count + 1):
            if ch == 1:
                await self.create_session()
                msg = (
                    f"请写第 1 章。完成后用 check_chapter_quality 自检。"
                    f"注意保持人物和设定一致。"
                )
            else:
                msg = (
                    f"请继续写第 {ch} 章。完成后用 check_chapter_quality 自检。"
                    f"注意保持与前面章节的连贯性。"
                )

            print(f"\n--- Chapter {ch}/{self.chapter_count} ---")
            print(f"[send] {msg}")

            try:
                events = await self.send_message(msg)
            except Exception as exc:
                result.errors.append(f"第 {ch} 章: API 错误: {exc}")
                break

            # 分析本轮事件
            turn_ended = [e for e in events if e["type"] == "turn_ended"]
            guard_trips = [
                e["data"] for e in events
                if e["type"] == "turn_ended" and e["data"].get("stop_reason") == "guard_tripped"
            ]
            context_warns = [
                e["data"] for e in events if e["type"] == "context_warning"
            ]
            approval_count = sum(1 for e in events if e["type"] == "approval_pending")

            result.total_turns += len(turn_ended)
            result.approval_events += approval_count
            result.guard_trips.extend(guard_trips)
            result.context_warnings.extend(context_warns)

            if guard_trips:
                guard_info = guard_trips[0]
                result.errors.append(
                    f"第 {ch} 章: 护栏触发 ({guard_info.get('level', '?')}): "
                    f"{guard_info.get('reason', '?')}"
                )
                print(f"  [guard] TRIPPED: {guard_info.get('level')} - {guard_info.get('reason')}")
                break  # 护栏触发，停止生成

            # 检查章节是否实际写入
            write_calls = sum(
                1 for e in events
                if e["type"] == "tool_call_started" and e["data"].get("tool_name") == "write_chapter"
            )
            if write_calls > 0:
                result.chapters_written += 1
                print(f"  [progress] {result.chapters_written}/{self.chapter_count} chapters written")
            else:
                result.errors.append(f"第 {ch} 章: write_chapter 未被调用")
                break

            # 检查是否有异常停止
            if turn_ended:
                stop_reason = turn_ended[-1]["data"].get("stop_reason", "")
                if stop_reason not in ("completed", "iteration_budget_exhausted"):
                    result.errors.append(f"第 {ch} 章: 异常停止: {stop_reason}")
                    break

        result.end_time = datetime.now(UTC).isoformat()
        return result

    async def verify_guard_ping_pong(self) -> bool:
        """构造乒乓场景：连续发送互相矛盾的世界观修改请求。"""
        print("\n=== Ping-Pong Guard Test ===")

        await self.create_session()

        for i in range(6):
            if i % 2 == 0:
                msg = "请将世界观设定为：主角林思是魔法师，来自北方冰原。"
            else:
                msg = "请推翻之前的设定。世界观应该是：主角林思是剑客，来自南方沙漠。"

            print(f"\n[ping-pong {i + 1}/6] {msg[:60]}...")

            try:
                events = await self.send_message(msg)
            except Exception as exc:
                print(f"  [error] {exc}")
                return False

            for e in events:
                if e["type"] == "turn_ended":
                    stop = e["data"].get("stop_reason", "")
                    if stop == "guard_tripped":
                        print(f"\n  PING-PONG GUARD: Tripped at round {i + 1}!")
                        return True

        print("\n  PING-PONG GUARD: Not tripped within 6 rounds (FAIL)")
        return False

    async def close(self) -> None:
        await self.client.aclose()


async def main() -> None:
    args = parse_args()
    verifier = L3Verifier(
        base_url=args.base_url,
        project_id=args.project_id,
        chapter_count=args.chapters,
        timeout=args.timeout,
    )

    try:
        # Test 1: Unattended 10-chapter generation
        print("=" * 60)
        print("TEST 1: Unattended 10-Chapter Generation")
        print("=" * 60)
        result = await verifier.verify_unattended_generation()

        # Test 2: Ping-pong guard
        print("\n" + "=" * 60)
        print("TEST 2: Ping-Pong Guard")
        print("=" * 60)
        ping_pong_ok = await verifier.verify_guard_ping_pong()

        if not ping_pong_ok:
            result.errors.append("Ping-pong guard test FAILED")

        # Report
        print(f"\n{result.report()}")

        exit_code = 0 if result.success and ping_pong_ok else 1
        sys.exit(exit_code)

    except httpx.ConnectError:
        print(f"\nCANNOT CONNECT to {args.base_url} — is the backend running?")
        sys.exit(2)
    finally:
        await verifier.close()


if __name__ == "__main__":
    asyncio.run(main())

"""core 内核测试设施：scripted mock LLM 上游（openhuman/openclaw 黄金模式）。

不用真模型、全确定性、能测重试/错误路径/工具调用序列/请求形状。
"""
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from core.providers.base import Provider, ProviderError, ProviderResponse, TextDelta, ToolCall, Usage


class ScriptedProvider(Provider):
    """按脚本化响应序列回答；记录每次请求形状供断言。

    script 每项：
      {"content": "文本", "tool_calls": [{"name": ..., "arguments": {...}}, ...]}
      {"content": ..., "error": "msg", "retryable": bool}   # 第 N 次调用抛错
      {"content": ..., "usage": Usage(...)}
    """

    def __init__(self, script: list[dict]) -> None:
        self._script = list(script)
        self.requests: list[list[dict]] = []   # 每次请求的 messages 形状
        self.tools_seen: list[list] = []
        self.error_after: int = 0              # 产出 N 个字符后抛 ProviderError（部分流中断）
        self.error_retryable: bool = True      # 部分流中断的 retryable 标志

    def script_remaining(self) -> int:
        return len(self._script)

    def next_step(self) -> dict:
        if not self._script:
            raise AssertionError(f"script exhausted; requests so far={len(self.requests)}")
        return self._script.pop(0)

    async def stream(
        self,
        messages: list[dict],
        tools: list | None = None,
        **kwargs,
    ) -> AsyncIterator[TextDelta | ProviderResponse]:
        # 深拷贝快照：调用方后续会 append 新消息（别名污染断言）
        self.requests.append([dict(m) for m in messages])
        self.tools_seen.append(tools or [])
        step = self.next_step()
        if "error" in step:
            raise ProviderError(step["error"], retryable=step.get("retryable", False))
        content = step.get("content", "")
        if content:
            if self.error_after and len(content) > self.error_after:
                # 部分流中断：先产出前 N 个字符，再抛错误
                # （provider 层部分流不可重试——防重复输出）
                yield TextDelta(text=content[: self.error_after])
                raise ProviderError("partial stream failure", retryable=self.error_retryable)
            yield TextDelta(text=content)
        usage = step.get("usage", Usage())
        if "tool_calls" in step and step["tool_calls"]:
            calls = [
                ToolCall(
                    id=call.get("id", f"call-{i}"),
                    name=call["name"],
                    arguments_raw=call.get("arguments_raw", ""),
                    arguments=call.get("arguments"),
                )
                for i, call in enumerate(step["tool_calls"])
            ]
            yield ProviderResponse(content=content, tool_calls=calls, usage=usage)
        else:
            yield ProviderResponse(content=content, finish_reason="stop", usage=usage)


@pytest.fixture
def scripted_provider_factory():
    def make(script: list[dict]) -> ScriptedProvider:
        return ScriptedProvider(script)

    return make

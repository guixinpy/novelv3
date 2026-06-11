"""Provider 抽象：子类只做格式转换与流解析，重试/用量归一化只写一遍(CADR-006)。"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments_raw: str
    arguments: dict | None

    @staticmethod
    def from_raw(id: str, name: str, arguments_raw: str) -> "ToolCall":
        try:
            parsed = json.loads(arguments_raw) if arguments_raw.strip() else {}
            if not isinstance(parsed, dict):
                parsed = None
        except json.JSONDecodeError:
            parsed = None
        return ToolCall(id=id, name=name, arguments_raw=arguments_raw, arguments=parsed)


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class ProviderResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    usage: Usage = field(default_factory=Usage)
    model: str = ""


class ProviderError(Exception):
    def __init__(self, message: str, status_code: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


StreamEvent = TextDelta | ProviderResponse


class Provider(ABC):
    """流式优先：complete() 一律由 stream() 排空实现。"""

    @abstractmethod
    def stream(
        self,
        messages: list[dict],
        tools: list[ToolSpec] | None = None,
        **kwargs,
    ) -> AsyncIterator[StreamEvent]:
        """逐事件产出 TextDelta，最后一个事件必须是 ProviderResponse。"""

    async def complete(
        self,
        messages: list[dict],
        tools: list[ToolSpec] | None = None,
        **kwargs,
    ) -> ProviderResponse:
        final: ProviderResponse | None = None
        async for event in self.stream(messages, tools=tools, **kwargs):
            if isinstance(event, ProviderResponse):
                final = event
        if final is None:
            raise ProviderError("provider stream ended without a final response", retryable=True)
        return final

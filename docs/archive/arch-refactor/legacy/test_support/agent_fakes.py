"""新内核测试用 Fake Provider 与响应构造助手。"""
from __future__ import annotations

from app.agent.providers.base import Provider, ProviderResponse, TextDelta, ToolCall, Usage


class FakeProvider(Provider):
    """按脚本顺序返回预设响应，记录每次收到的消息。

    content 中的 ``|`` 是流式分片标记：``"你好|，作者"`` 产出两个 TextDelta。
    """

    def __init__(self, responses: list[ProviderResponse]):
        self.responses = list(responses)
        self.calls: list[list[dict]] = []

    async def stream(self, messages, tools=None, **kwargs):
        self.calls.append([dict(m) for m in messages])
        response = self.responses.pop(0)
        for piece in response.content.split("|"):
            if piece:
                yield TextDelta(text=piece)
        yield ProviderResponse(
            content=response.content.replace("|", ""),
            tool_calls=response.tool_calls,
            finish_reason=response.finish_reason,
            usage=response.usage,
            model=response.model,
        )


def text_response(content: str, prompt: int = 10, completion: int = 5) -> ProviderResponse:
    return ProviderResponse(
        content=content, finish_reason="stop", usage=Usage(prompt, completion)
    )


def tool_response(*calls: ToolCall, prompt: int = 10, completion: int = 5) -> ProviderResponse:
    return ProviderResponse(
        content="", tool_calls=list(calls), finish_reason="tool_calls",
        usage=Usage(prompt, completion),
    )


def call(name: str, args: str = "{}", id: str = "call_1") -> ToolCall:
    return ToolCall.from_raw(id=id, name=name, arguments_raw=args)

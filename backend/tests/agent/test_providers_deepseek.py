import json

import httpx
import pytest

from app.agent.providers.base import (
    ProviderError,
    ProviderResponse,
    TextDelta,
    ToolSpec,
)
from app.agent.providers.deepseek import DeepSeekProvider


def sse_body(chunks: list[dict]) -> bytes:
    parts = [f"data: {json.dumps(c)}\n\n" for c in chunks]
    parts.append("data: [DONE]\n\n")
    return "".join(parts).encode()


def chunk(delta: dict | None = None, finish: str | None = None, usage: dict | None = None) -> dict:
    payload: dict = {"id": "c1", "model": "deepseek-chat", "choices": []}
    if delta is not None or finish is not None:
        payload["choices"] = [{"index": 0, "delta": delta or {}, "finish_reason": finish}]
    if usage is not None:
        payload["usage"] = usage
    return payload


def make_provider(handler) -> DeepSeekProvider:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.deepseek.com",
    )
    return DeepSeekProvider(api_key="test-key", client=client, base_delay=0.0)


def text_stream_handler(request: httpx.Request) -> httpx.Response:
    body = sse_body(
        [
            chunk(delta={"role": "assistant", "content": "你好"}),
            chunk(delta={"content": "，作者"}),
            chunk(delta={}, finish="stop"),
            chunk(usage={"prompt_tokens": 12, "completion_tokens": 5}),
        ]
    )
    return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})


@pytest.mark.asyncio
async def test_stream_yields_text_deltas_then_response():
    provider = make_provider(text_stream_handler)
    events = [event async for event in provider.stream([{"role": "user", "content": "hi"}])]

    deltas = [e for e in events if isinstance(e, TextDelta)]
    assert [d.text for d in deltas] == ["你好", "，作者"]

    final = events[-1]
    assert isinstance(final, ProviderResponse)
    assert final.content == "你好，作者"
    assert final.finish_reason == "stop"
    assert final.tool_calls == []
    assert final.usage.prompt_tokens == 12
    assert final.usage.completion_tokens == 5


@pytest.mark.asyncio
async def test_complete_drains_stream():
    provider = make_provider(text_stream_handler)
    result = await provider.complete([{"role": "user", "content": "hi"}])
    assert isinstance(result, ProviderResponse)
    assert result.content == "你好，作者"
    assert result.usage.completion_tokens == 5


@pytest.mark.asyncio
async def test_tool_call_fragments_reassembled_across_chunks():
    def handler(request: httpx.Request) -> httpx.Response:
        body = sse_body(
            [
                chunk(
                    delta={
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "read_chapter", "arguments": '{"chap'},
                            }
                        ]
                    }
                ),
                chunk(
                    delta={
                        "tool_calls": [
                            {"index": 0, "function": {"arguments": 'ter_index": 3}'}}
                        ]
                    }
                ),
                chunk(delta={}, finish="tool_calls"),
                chunk(usage={"prompt_tokens": 30, "completion_tokens": 9}),
            ]
        )
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    provider = make_provider(handler)
    result = await provider.complete([{"role": "user", "content": "hi"}])
    assert result.finish_reason == "tool_calls"
    assert len(result.tool_calls) == 1
    call = result.tool_calls[0]
    assert call.id == "call_1"
    assert call.name == "read_chapter"
    assert call.arguments == {"chapter_index": 3}
    assert call.arguments_raw == '{"chapter_index": 3}'


@pytest.mark.asyncio
async def test_parallel_tool_calls_tracked_by_index():
    def handler(request: httpx.Request) -> httpx.Response:
        body = sse_body(
            [
                chunk(
                    delta={
                        "tool_calls": [
                            {"index": 0, "id": "call_a", "function": {"name": "tool_a", "arguments": "{}"}},
                            {"index": 1, "id": "call_b", "function": {"name": "tool_b", "arguments": '{"x":'}},
                        ]
                    }
                ),
                chunk(delta={"tool_calls": [{"index": 1, "function": {"arguments": " 1}"}}]}),
                chunk(delta={}, finish="tool_calls"),
            ]
        )
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    provider = make_provider(handler)
    result = await provider.complete([{"role": "user", "content": "hi"}])
    assert [c.id for c in result.tool_calls] == ["call_a", "call_b"]
    assert result.tool_calls[1].arguments == {"x": 1}


@pytest.mark.asyncio
async def test_invalid_tool_arguments_kept_raw():
    def handler(request: httpx.Request) -> httpx.Response:
        body = sse_body(
            [
                chunk(
                    delta={
                        "tool_calls": [
                            {"index": 0, "id": "call_1", "function": {"name": "t", "arguments": "{not json"}}
                        ]
                    }
                ),
                chunk(delta={}, finish="tool_calls"),
            ]
        )
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    provider = make_provider(handler)
    result = await provider.complete([{"role": "user", "content": "hi"}])
    call = result.tool_calls[0]
    assert call.arguments is None
    assert call.arguments_raw == "{not json"


@pytest.mark.asyncio
async def test_tools_converted_to_openai_format_in_payload():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return text_stream_handler(request)

    provider = make_provider(handler)
    tool = ToolSpec(
        name="read_chapter",
        description="读取章节",
        parameters={"type": "object", "properties": {"chapter_index": {"type": "integer"}}},
    )
    await provider.complete([{"role": "user", "content": "hi"}], tools=[tool])

    assert seen["stream"] is True
    assert seen["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "read_chapter",
                "description": "读取章节",
                "parameters": {"type": "object", "properties": {"chapter_index": {"type": "integer"}}},
            },
        }
    ]


@pytest.mark.asyncio
async def test_retries_on_server_error_then_succeeds():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, json={"error": "boom"})
        return text_stream_handler(request)

    provider = make_provider(handler)
    result = await provider.complete([{"role": "user", "content": "hi"}])
    assert calls["n"] == 2
    assert result.content == "你好，作者"


@pytest.mark.asyncio
async def test_no_retry_on_client_error():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, json={"error": {"message": "bad request"}})

    provider = make_provider(handler)
    with pytest.raises(ProviderError) as exc_info:
        await provider.complete([{"role": "user", "content": "hi"}])
    assert calls["n"] == 1
    assert exc_info.value.status_code == 400
    assert not exc_info.value.retryable


@pytest.mark.asyncio
async def test_gives_up_after_max_attempts():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, json={"error": "overloaded"})

    provider = make_provider(handler)
    with pytest.raises(ProviderError) as exc_info:
        await provider.complete([{"role": "user", "content": "hi"}])
    assert calls["n"] == 3
    assert exc_info.value.retryable


@pytest.mark.asyncio
async def test_mid_stream_failure_not_retried():
    calls = {"n": 0}

    class BrokenStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'data: {"id": "c1", "model": "m", "choices": [{"index": 0, "delta": {"content": "abc"}, "finish_reason": null}]}\n\n'
            raise httpx.ReadError("connection dropped")

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            200, stream=BrokenStream(), headers={"content-type": "text/event-stream"}
        )

    provider = make_provider(handler)
    events = []
    with pytest.raises(ProviderError):
        async for event in provider.stream([{"role": "user", "content": "hi"}]):
            events.append(event)
    assert calls["n"] == 1
    assert [e.text for e in events if isinstance(e, TextDelta)] == ["abc"]

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import httpx

from core.providers.base import (
    Provider,
    ProviderError,
    ProviderResponse,
    StreamEvent,
    TextDelta,
    ToolCall,
    ToolSpec,
    Usage,
)

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


class _ToolCallAccumulator:
    """按 index 重组跨 chunk 的 tool_call 分片。"""

    def __init__(self) -> None:
        self._calls: dict[int, dict] = {}

    def feed(self, fragments: list[dict]) -> None:
        for frag in fragments:
            index = frag.get("index", 0)
            slot = self._calls.setdefault(index, {"id": "", "name": "", "arguments": ""})
            if frag.get("id"):
                slot["id"] = frag["id"]
            fn = frag.get("function") or {}
            if fn.get("name"):
                slot["name"] = fn["name"]
            if fn.get("arguments"):
                slot["arguments"] += fn["arguments"]

    def finalize(self) -> list[ToolCall]:
        return [
            ToolCall.from_raw(id=slot["id"], name=slot["name"], arguments_raw=slot["arguments"])
            for _, slot in sorted(self._calls.items())
        ]


class DeepSeekProvider(Provider):
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        client: httpx.AsyncClient | None = None,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        timeout: float = 300.0,
    ) -> None:
        self.model = model
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self._client = client or httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )
        if client is not None:
            self._client.headers.setdefault("Authorization", f"Bearer {api_key}")

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _convert_tools(tools: list[ToolSpec]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

    def _build_payload(
        self,
        messages: list[dict],
        tools: list[ToolSpec] | None,
        **kwargs,
    ) -> dict:
        payload: dict = {
            "model": kwargs.pop("model", self.model),
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
            **kwargs,
        }
        if tools:
            payload["tools"] = self._convert_tools(tools)
        return payload

    async def stream(
        self,
        messages: list[dict],
        tools: list[ToolSpec] | None = None,
        **kwargs,
    ) -> AsyncIterator[StreamEvent]:
        payload = self._build_payload(messages, tools, **kwargs)
        for attempt in range(1, self.max_attempts + 1):
            yielded = False
            try:
                async for event in self._stream_once(payload):
                    yielded = True
                    yield event
                return
            except ProviderError as exc:
                # 已产出部分流后不可重试，否则会重复输出
                if yielded or not exc.retryable or attempt == self.max_attempts:
                    raise
                await asyncio.sleep(self.base_delay * (2 ** (attempt - 1)))

    async def _stream_once(self, payload: dict) -> AsyncIterator[StreamEvent]:
        try:
            async with self._client.stream("POST", "/v1/chat/completions", json=payload) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    raise self._http_error(resp.status_code, body)
                async for event in self._parse_sse(resp):
                    yield event
        except httpx.RequestError as exc:
            raise ProviderError(f"network error: {exc}", retryable=True) from exc

    @staticmethod
    def _http_error(status_code: int, body: bytes) -> ProviderError:
        try:
            detail = json.loads(body).get("error")
            message = detail.get("message") if isinstance(detail, dict) else str(detail)
        except (json.JSONDecodeError, AttributeError):
            message = body.decode(errors="replace")[:500]
        retryable = status_code == 429 or status_code >= 500
        return ProviderError(
            f"deepseek http {status_code}: {message}", status_code=status_code, retryable=retryable
        )

    async def _parse_sse(self, resp: httpx.Response) -> AsyncIterator[StreamEvent]:
        content_parts: list[str] = []
        accumulator = _ToolCallAccumulator()
        finish_reason: str | None = None
        usage = Usage()
        model = ""

        async for line in resp.aiter_lines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                break
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                continue
            model = payload.get("model") or model
            if payload.get("usage"):
                usage = Usage(
                    prompt_tokens=payload["usage"].get("prompt_tokens", 0),
                    completion_tokens=payload["usage"].get("completion_tokens", 0),
                )
            for choice in payload.get("choices") or []:
                if choice.get("finish_reason"):
                    finish_reason = choice["finish_reason"]
                delta = choice.get("delta") or {}
                if delta.get("content"):
                    content_parts.append(delta["content"])
                    yield TextDelta(text=delta["content"])
                if delta.get("tool_calls"):
                    accumulator.feed(delta["tool_calls"])

        yield ProviderResponse(
            content="".join(content_parts),
            tool_calls=accumulator.finalize(),
            finish_reason=finish_reason,
            usage=usage,
            model=model,
        )

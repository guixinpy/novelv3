import json
import re
import httpx
from pydantic import BaseModel
from app.core.error_handler import AppError


class CompletionResult(BaseModel):
    content: str
    prompt_tokens: int
    completion_tokens: int
    model: str


class DeepSeekAdapter:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120.0,
        )

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def complete(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        model: str = "deepseek-chat",
        response_format: dict | None = None,
    ) -> CompletionResult:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format
        resp = await self.client.post(
            "/v1/chat/completions",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        result = CompletionResult(
            content=choice["message"]["content"],
            prompt_tokens=data["usage"]["prompt_tokens"],
            completion_tokens=data["usage"]["completion_tokens"],
            model=data["model"],
        )
        return result


def parse_json_safely(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if match:
        candidate = match.group(1).replace("'", '"')
        candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise AppError("PARSE_ERROR", "无法解析模型返回的 JSON")

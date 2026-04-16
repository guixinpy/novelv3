from app.config import load_api_key
from app.core.deepseek_adapter import DeepSeekAdapter, parse_json_safely
from app.core.error_handler import with_retry


class AIService:
    def __init__(self):
        self._adapter = None

    def _get_adapter(self) -> DeepSeekAdapter:
        if self._adapter is None:
            key = load_api_key()
            if not key:
                raise ValueError("API key not configured")
            self._adapter = DeepSeekAdapter(api_key=key)
        return self._adapter

    async def complete(self, messages: list[dict], **kwargs):
        adapter = self._get_adapter()
        return await with_retry(lambda: adapter.complete(messages, **kwargs))

    def parse_json(self, text: str) -> dict:
        return parse_json_safely(text)

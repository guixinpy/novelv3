from app.config import load_api_key
from app.core.json_utils import parse_json_safely

# v1 绞杀：提示词从 prompting 装配器内联至此，LLM 调用统一走 v2 provider
_L2_PROMPT_TEMPLATE = (
    "你是故事一致性检查助手。从给定章节正文中提取「事实断言」列表，"
    "每个断言为 {{subject, predicate, object, chapter_index}} 结构，"
    "subject/object 为人物或地点名，predicate 为简短动作或状态描述。"
    "只提取明确陈述的事实，不推断。以 JSON 数组返回。\n\n正文：\n{content}"
)


class L2LLMExtractor:
    def __init__(self) -> None:
        self._provider = None

    def _get_provider(self):
        if self._provider is None:
            from app.agent.providers import build_provider
            self._provider = build_provider()
        return self._provider

    async def extract(self, chapter_content: str) -> list[dict]:
        if not load_api_key():
            return []
        try:
            prompt = _L2_PROMPT_TEMPLATE.format(content=chapter_content[:3000])
            result = await self._get_provider().complete(
                [{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )
            data = parse_json_safely(result.content)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "facts" in data:
                return data["facts"]
            return [data] if isinstance(data, dict) else []
        except Exception:
            return []

    async def close(self) -> None:
        if self._provider is not None:
            await self._provider.close()
            self._provider = None

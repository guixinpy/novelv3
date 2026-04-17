import json
from app.core.ai_service import AIService
from app.config import load_api_key

EXTRACTION_PROMPT = """分析以下章节内容，提取所有事实变化。以 JSON 数组格式返回，每个元素包含：
- type: character_state_change / location_presence / time_reference / relationship_change
- subject: 涉及的角色或实体名
- attribute: 变化的属性
- new_value: 新状态值
- evidence: 原文证据（引用原文）
- confidence: 置信度 0-1

章节内容：
{content}

只返回 JSON 数组，不要其他文字。"""


class L2LLMExtractor:
    def __init__(self):
        self.ai_service = AIService()

    async def extract(self, chapter_content: str) -> list[dict]:
        if not load_api_key():
            return []
        prompt = EXTRACTION_PROMPT.format(content=chapter_content[:3000])
        try:
            result = await self.ai_service.complete(
                [{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )
            data = self.ai_service.parse_json(result.content)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "facts" in data:
                return data["facts"]
            return [data] if isinstance(data, dict) else []
        except Exception:
            return []

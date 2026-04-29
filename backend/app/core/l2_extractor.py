from app.config import load_api_key
from app.core.ai_service import AIService
from app.prompting.assembler import PromptAssembler


class L2LLMExtractor:
    def __init__(self):
        self.ai_service = AIService()

    async def extract(self, chapter_content: str) -> list[dict]:
        if not load_api_key():
            return []
        prompt = PromptAssembler().build(
            "athena.extract_l2",
            {"content": chapter_content[:3000]},
        ).content
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

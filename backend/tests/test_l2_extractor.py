from types import SimpleNamespace

import pytest

from app.core import l2_extractor as l2_module
from app.core.l2_extractor import L2LLMExtractor


@pytest.mark.asyncio
async def test_l2_extractor_uses_registered_prompt_and_parses_facts(monkeypatch):
    chapter_content = ("林深在灯塔发现记忆潮汐将在午夜回卷。" + "x" * 3200)[:3100] + "TAIL_SHOULD_BE_TRUNCATED"
    parsed_facts = [
        {
            "type": "time_reference",
            "subject": "记忆潮汐",
            "attribute": "回卷时间",
            "new_value": "午夜",
            "evidence": "记忆潮汐将在午夜回卷",
            "confidence": 0.9,
        }
    ]
    build_calls = []

    class FakeAssembler:
        def build(self, prompt_id, variables):
            build_calls.append((prompt_id, variables))
            return SimpleNamespace(content=f"FROM_REGISTERED_TEMPLATE::{variables['content']}")

    class FakeAIService:
        def __init__(self):
            self.messages = None
            self.kwargs = None

        async def complete(self, messages, **kwargs):
            self.messages = messages
            self.kwargs = kwargs
            return SimpleNamespace(content='{"facts": []}')

        def parse_json(self, text):
            return {"facts": parsed_facts}

    monkeypatch.setattr(l2_module, "load_api_key", lambda: "sk-test")
    monkeypatch.setattr(l2_module, "PromptAssembler", FakeAssembler)

    extractor = L2LLMExtractor()
    fake_ai = FakeAIService()
    extractor.ai_service = fake_ai

    facts = await extractor.extract(chapter_content)

    assert build_calls == [
        ("athena.extract_l2", {"content": chapter_content[:3000]}),
    ]
    assert fake_ai.messages == [
        {"role": "user", "content": f"FROM_REGISTERED_TEMPLATE::{chapter_content[:3000]}"}
    ]
    assert "TAIL_SHOULD_BE_TRUNCATED" not in fake_ai.messages[0]["content"]
    assert fake_ai.kwargs["response_format"] == {"type": "json_object"}
    assert facts == parsed_facts

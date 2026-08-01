import json
from types import SimpleNamespace

import pytest

from app.core import l2_extractor as l2_module
from app.core.l2_extractor import L2LLMExtractor


@pytest.mark.asyncio
async def test_l2_extractor_builds_prompt_and_parses_facts(monkeypatch):
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

    class FakeProvider:
        def __init__(self):
            self.messages = None
            self.kwargs = None

        async def complete(self, messages, **kwargs):
            self.messages = messages
            self.kwargs = kwargs
            return SimpleNamespace(
                content=json.dumps({"facts": parsed_facts}, ensure_ascii=False),
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
            )

        async def close(self):
            pass

    monkeypatch.setattr(l2_module, "load_api_key", lambda: "sk-test")
    fake_provider = FakeProvider()
    monkeypatch.setattr("app.agent.providers.build_provider", lambda: fake_provider)

    extractor = L2LLMExtractor()
    facts = await extractor.extract(chapter_content)

    # 提示词内联且正文截断到 3000
    assert fake_provider.messages[0]["role"] == "user"
    assert fake_provider.messages[0]["content"].startswith("你是故事一致性检查助手")
    assert "TAIL_SHOULD_BE_TRUNCATED" not in fake_provider.messages[0]["content"]
    assert fake_provider.kwargs["response_format"] == {"type": "json_object"}
    assert facts == parsed_facts


@pytest.mark.asyncio
async def test_l2_extractor_returns_empty_on_provider_failure(monkeypatch):
    class BrokenProvider:
        async def complete(self, messages, **kwargs):
            raise RuntimeError("provider exploded")

        async def close(self):
            pass

    monkeypatch.setattr(l2_module, "load_api_key", lambda: "sk-test")
    monkeypatch.setattr("app.agent.providers.build_provider", lambda: BrokenProvider())

    extractor = L2LLMExtractor()
    assert await extractor.extract("任意章节内容") == []

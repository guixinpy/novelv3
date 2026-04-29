from app.core.prompt_manager import PromptManager


def test_storyline_prompt_substitutes_project_context():
    prompt = PromptManager().load(
        "generate_storyline",
        {
            "name": "潮汐门",
            "genre": "科幻悬疑",
            "world_building": "记忆潮汐每72小时发生。",
            "characters": '[{"name":"林深"}]',
            "core_concept": '{"hook":"潮汐门"}',
        },
    )

    assert "{{" not in prompt
    assert "潮汐门" in prompt
    assert "记忆潮汐每72小时发生。" in prompt
    assert "林深" in prompt


def test_outline_prompt_substitutes_story_context():
    prompt = PromptManager().load(
        "generate_outline",
        {
            "name": "潮汐门",
            "world_building": "静默空间保存被交换的记忆。",
            "characters": '[{"name":"林深"},{"name":"苏晚晴"}]',
            "core_concept": '{"theme":"记忆与自我"}',
            "storyline": '{"plotlines":[{"name":"记忆潮汐危机"}]}',
            "total_chapters": 10,
        },
    )

    assert "{{" not in prompt
    assert "静默空间保存被交换的记忆。" in prompt
    assert "林深" in prompt
    assert "苏晚晴" in prompt
    assert "总章节数：10" in prompt

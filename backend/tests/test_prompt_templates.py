from app.core.prompt_manager import PromptManager
from app.prompting.registry import PROMPT_REGISTRY
from app.prompting.renderer import PromptRenderer


SAMPLE_PROMPT_VARS = {
    "chapter_index": 1,
    "characters": '[{"name":"林深"}]',
    "completed_items": "设定",
    "complexity": "中等",
    "content": "林深在灯塔发现记忆潮汐将在午夜回卷。",
    "core_concept": '{"hook":"潮汐门"}',
    "current_phase": "setup",
    "current_words": "0",
    "description": "记忆潮汐每72小时发生。",
    "dialog_lines": "用户：继续推进\n助手：建议生成故事线。",
    "genre": "科幻悬疑",
    "has_chapters": "false",
    "has_outline": "false",
    "has_setup": "true",
    "has_storyline": "false",
    "missing_items": "故事线、大纲、正文",
    "name": "潮汐门",
    "profile_version": "1",
    "project_description": "记忆潮汐每72小时发生。",
    "project_genre": "科幻悬疑",
    "project_name": "潮汐门",
    "project_phase": "设定阶段",
    "project_status": "进行中",
    "storyline": '{"plotlines":[{"name":"记忆潮汐危机"}]}',
    "style": "冷峻",
    "suggested_next_step": "preview_storyline",
    "target_chapters": "10",
    "target_words": "30000",
    "total_chapters": 10,
    "world_building": "静默空间保存被交换的记忆。",
    "world_context": "当前世界模型为空。",
}


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


def test_prompt_manager_supports_custom_prompts_dir(tmp_path):
    (tmp_path / "custom.txt").write_text("项目：${name}", encoding="utf-8")

    prompt = PromptManager(prompts_dir=tmp_path).load("custom", {"name": "潮汐门"})

    assert prompt == "项目：潮汐门"


def test_registered_prompt_templates_exist():
    renderer = PromptRenderer()

    for spec in PROMPT_REGISTRY.values():
        assert renderer.template_path(spec.template_name).exists()


def test_registered_prompt_templates_render_with_sample_vars():
    renderer = PromptRenderer()

    for spec in PROMPT_REGISTRY.values():
        variables = {
            name: SAMPLE_PROMPT_VARS[name]
            for name in spec.required_vars
        }
        rendered = renderer.render(spec.template_name, variables)

        assert "${" not in rendered.content
        assert "{{" not in rendered.content

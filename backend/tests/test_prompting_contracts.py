import pytest
from pathlib import Path

from app.prompting.assembler import PromptAssembler, build_generation_payload
from app.prompting.budget import PromptBudgeter
from app.prompting.registry import PROMPT_REGISTRY
from app.prompting.renderer import PromptRenderer, default_prompts_dir
from app.prompting.tracing import build_prompt_trace_metadata


def test_default_prompts_dir_points_to_backend_prompts():
    prompts_dir = default_prompts_dir()

    assert prompts_dir.name == "prompts"
    assert (prompts_dir / "generate_setup.txt").exists()


def test_registry_contains_expected_production_prompts():
    assert set(PROMPT_REGISTRY) == {
        "setup.generate",
        "storyline.generate",
        "outline.generate",
        "chapter.generate",
        "dialog.hermes",
        "dialog.athena",
        "dialog.compact",
        "project.diagnose",
        "athena.extract_l2",
    }
    assert PROMPT_REGISTRY["setup.generate"].template_name == "generate_setup"
    assert PROMPT_REGISTRY["chapter.generate"].output_type == "plain_text"
    assert PROMPT_REGISTRY["athena.extract_l2"].template_name == "athena_extract_l2"
    assert PROMPT_REGISTRY["athena.extract_l2"].output_type == "json"


def test_renderer_returns_stable_template_hash():
    renderer = PromptRenderer()

    template_hash = renderer.template_hash("generate_setup")

    assert template_hash.startswith("sha256:")
    assert len(template_hash) == len("sha256:") + 64
    assert template_hash == renderer.template_hash("generate_setup")


def test_renderer_missing_template_raises_prompt_not_found():
    renderer = PromptRenderer()

    with pytest.raises(FileNotFoundError, match="Prompt not found"):
        renderer.render("missing_template")


@pytest.mark.parametrize("template_name", ["../generate_setup", "nested/name", r"nested\name"])
def test_renderer_rejects_template_path_escape(template_name):
    renderer = PromptRenderer()

    with pytest.raises(ValueError):
        renderer.render(template_name)


def test_renderer_does_not_substitute_when_variables_are_none_or_empty():
    renderer = PromptRenderer()

    assert "${name}" in renderer.render("generate_setup").content
    assert "${name}" in renderer.render("generate_setup", {}).content


def test_renderer_missing_variable_names_variable():
    renderer = PromptRenderer()

    with pytest.raises(KeyError, match="Missing prompt variable 'name'"):
        renderer.render("generate_setup", {"genre": "科幻"})


def test_budgeter_keeps_priority_but_returns_original_order_and_truncates():
    blocks = [
        {"key": "low", "content": "LLLL", "priority": 50},
        {"key": "high", "content": "HHHHHH", "priority": 1},
        {"key": "mid", "content": "MMMM", "priority": 10},
    ]

    kept_blocks, report = PromptBudgeter().apply(blocks, max_chars=8)

    assert [block["key"] for block in kept_blocks] == ["high", "mid"]
    assert kept_blocks[0]["content"] == "HHHHHH"
    assert kept_blocks[1]["content"] == "MM"
    assert report.max_context_chars == 8
    assert report.included_blocks == 2
    assert report.omitted_blocks == 1
    assert report.omitted_block_keys == ["low"]
    assert report.truncated_blocks == ["mid"]


def test_budgeter_treats_missing_priority_as_100():
    blocks = [
        {"key": "default", "content": "BBBB"},
        {"key": "preferred", "content": "AAAA", "priority": 50},
    ]

    kept_blocks, report = PromptBudgeter().apply(blocks, max_chars=4)

    assert [block["key"] for block in kept_blocks] == ["preferred"]
    assert report.omitted_block_keys == ["default"]


def test_budgeter_normalizes_non_string_content():
    kept_blocks, report = PromptBudgeter().apply(
        [{"key": "number", "content": 123, "priority": 1}],
        max_chars=10,
    )

    assert kept_blocks == [{"key": "number", "content": "123", "priority": 1}]
    assert report.included_blocks == 1


def test_budgeter_omits_empty_blocks_when_max_chars_is_zero():
    kept_blocks, report = PromptBudgeter().apply(
        [
            {"key": "empty", "content": "", "priority": 1},
            {"key": "missing", "priority": 2},
        ],
        max_chars=0,
    )

    assert kept_blocks == []
    assert report.included_blocks == 0
    assert report.omitted_blocks == 2
    assert report.omitted_block_keys == ["empty", "missing"]


def test_assembler_builds_prompt_result_with_budgeted_context():
    result = PromptAssembler().build(
        "chapter.generate",
        variables={
            "chapter_index": 3,
            "world_building": "潮汐每七十二小时重置。",
            "characters": '[{"name":"林深"}]',
            "core_concept": '{"hook":"潮汐门"}',
        },
        context_blocks=[
            {"key": "later", "content": "later", "priority": 20},
            {"key": "first", "content": "first", "priority": 1},
        ],
        max_context_chars=5,
    )

    assert result.prompt_id == "chapter.generate"
    assert result.template_name == "generate_chapter"
    assert result.output_type == "plain_text"
    assert result.messages[0]["role"] == "user"
    assert result.content in result.messages[0]["content"]
    assert "【上下文】" in result.messages[0]["content"]
    assert "【first】\nfirst" in result.messages[0]["content"]
    assert "later" not in result.messages[0]["content"]
    assert [block["key"] for block in result.context_blocks] == ["first"]
    assert result.budget_report.omitted_block_keys == ["later"]
    assert "第 3 章正文" in result.content


def test_assembler_appends_kept_context_blocks_to_default_message_content():
    result = PromptAssembler().build(
        "project.diagnose",
        variables={
            "current_phase": "setup",
            "has_setup": "false",
            "has_storyline": "false",
            "has_outline": "false",
            "has_chapters": "false",
        },
        context_blocks=[
            {"key": "omitted", "title": "不应出现", "content": "DROP", "priority": 50},
            {"key": "kept", "title": "保留块", "content": "KEEP", "priority": 1},
        ],
        max_context_chars=4,
    )

    message_content = result.messages[0]["content"]

    assert "【上下文】" in message_content
    assert "【保留块】\nKEEP" in message_content
    assert "DROP" not in message_content
    assert "不应出现" not in message_content


def test_assembler_uses_provided_messages():
    messages = [{"role": "system", "content": "自定义"}]

    result = PromptAssembler().build(
        "dialog.compact",
        variables={"project_name": "潮汐门", "dialog_lines": "用户：继续"},
        context_blocks=[{"key": "ctx", "content": "不注入"}],
        max_context_chars=10,
        messages=messages,
    )

    assert result.messages is messages


def test_build_generation_payload_keeps_trace_blocks_out_of_message_content():
    trace_context_blocks = [
        {
            "key": "audit_only",
            "kind": "audit",
            "title": "审计块",
            "content": "TRACE_ONLY_SECRET",
            "sources": [],
            "char_count": 17,
            "token_estimate": 9,
            "original_char_count": 17,
            "truncated": False,
        }
    ]

    payload = build_generation_payload(
        "setup.generate",
        {
            "name": "潮汐门",
            "genre": "科幻悬疑",
            "description": "记忆潮汐每72小时发生。",
            "style": "冷峻",
            "complexity": "中等",
        },
        trace_context_blocks=trace_context_blocks,
        command_args="主角是植物学家",
    )

    message_content = payload["messages"][0]["content"]

    assert "附加要求：主角是植物学家" in message_content
    assert payload["context_blocks"] == trace_context_blocks
    assert "TRACE_ONLY_SECRET" not in message_content
    assert payload["trace_metadata"]["prompt_id"] == "setup.generate"
    assert payload["trace_metadata"]["template_hash"].startswith("sha256:")
    assert payload["rendered_prompt"] in message_content


def test_build_generation_payload_can_build_trace_blocks_from_rendered_prompt():
    payload = build_generation_payload(
        "setup.generate",
        {
            "name": "潮汐门",
            "genre": "科幻悬疑",
            "description": "记忆潮汐每72小时发生。",
            "style": "冷峻",
            "complexity": "中等",
        },
        trace_context_blocks=lambda rendered_prompt: [{"key": "prompt_snapshot", "content": rendered_prompt}],
    )

    assert payload["context_blocks"] == [{"key": "prompt_snapshot", "content": payload["rendered_prompt"]}]


def test_assembler_unknown_prompt_id_raises_key_error():
    with pytest.raises(KeyError):
        PromptAssembler().build("unknown.prompt")


def test_assembler_missing_required_vars_raises_value_error():
    with pytest.raises(ValueError) as exc_info:
        PromptAssembler().build("setup.generate", {"name": "x"})

    message = str(exc_info.value)
    assert "Missing prompt variables" in message
    assert "genre" in message
    assert "description" in message
    assert "style" in message
    assert "complexity" in message


def test_assembler_model_defaults_are_copied_from_registry():
    result = PromptAssembler().build(
        "setup.generate",
        {
            "name": "潮汐门",
            "genre": "科幻悬疑",
            "description": "记忆潮汐每72小时发生。",
            "style": "冷峻",
            "complexity": "中等",
        },
    )

    result.model_defaults["temperature"] = 0.7

    assert "temperature" not in PROMPT_REGISTRY["setup.generate"].model_defaults


def test_trace_metadata_contains_prompt_and_budget_data():
    result = PromptAssembler().build(
        "project.diagnose",
        variables={
            "current_phase": "setup",
            "has_setup": "false",
            "has_storyline": "false",
            "has_outline": "false",
            "has_chapters": "false",
        },
        context_blocks=[{"key": "diagnosis", "content": "abc", "priority": 1}],
        max_context_chars=2,
    )

    metadata = build_prompt_trace_metadata(result)

    assert metadata["prompt_id"] == "project.diagnose"
    assert metadata["prompt_version"] == result.version
    assert metadata["template_name"] == "diagnose_project"
    assert metadata["template_hash"] == result.template_hash
    assert metadata["budget"]["truncated_blocks"] == ["diagnosis"]


def test_athena_extract_l2_prompt_renders_without_unresolved_placeholders():
    result = PromptAssembler().build(
        "athena.extract_l2",
        {"content": "林深在灯塔发现记忆潮汐将在午夜回卷。"},
    )

    assert result.prompt_id == "athena.extract_l2"
    assert result.template_name == "athena_extract_l2"
    assert result.output_type == "json"
    assert "林深在灯塔发现记忆潮汐将在午夜回卷。" in result.content
    assert "${" not in result.content
    assert "{{" not in result.content


def test_project_diagnose_prompt_stays_registry_renderable():
    result = PromptAssembler().build(
        "project.diagnose",
        {
            "current_phase": "setup",
            "has_setup": "true",
            "has_storyline": "false",
            "has_outline": "false",
            "has_chapters": "false",
        },
    )

    assert result.prompt_id == "project.diagnose"
    assert result.template_name == "diagnose_project"
    assert "${" not in result.content


def test_chat_project_assistant_is_unregistered_legacy_template_without_backend_call_site():
    assert "chat_project_assistant" not in {
        spec.template_name for spec in PROMPT_REGISTRY.values()
    }

    app_dir = Path(__file__).resolve().parents[1] / "app"
    references = []
    for path in app_dir.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "chat_project_assistant" in text:
            references.append(path.relative_to(app_dir.parent).as_posix())

    assert references == []

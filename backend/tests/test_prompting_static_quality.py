import ast
import re
from pathlib import Path
from string import Template

from app.prompting.registry import PROMPT_REGISTRY
from app.prompting.renderer import PromptRenderer, default_prompts_dir


BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"

ALLOWED_INLINE_PROMPT_FILES = {
    "backend/app/prompting/registry.py",
    "backend/app/prompting/providers/style.py",
    "backend/app/prompting/providers/few_shot.py",
}

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
    "dialog_lines": "1. [user] 继续推进\n2. [assistant] 建议生成故事线。",
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

JSON_PROMPT_CALL_SITE_FILES = {
    "setup.generate": {"backend/app/api/setups.py"},
    "storyline.generate": {"backend/app/api/storylines.py"},
    "outline.generate": {"backend/app/api/outlines.py"},
    "athena.extract_l2": {"backend/app/core/l2_extractor.py"},
}

REGISTRY_ONLY_JSON_PROMPTS = {"project.diagnose"}

INLINE_PROMPT_KEYWORDS = (
    "你是",
    "请",
    "返回格式",
    "JSON",
    "章节内容",
    "回答要求",
    "输出要求",
    "分析以下",
)


def test_registered_prompt_templates_exist():
    prompts_dir = default_prompts_dir()

    missing = [
        f"{prompt_id}: {spec.template_name}.txt"
        for prompt_id, spec in PROMPT_REGISTRY.items()
        if not (prompts_dir / f"{spec.template_name}.txt").exists()
    ]

    assert missing == []


def test_registered_prompt_templates_render_with_sample_variables():
    renderer = PromptRenderer()
    failures = []

    for prompt_id, spec in PROMPT_REGISTRY.items():
        variables = {name: SAMPLE_PROMPT_VARS[name] for name in spec.required_vars}
        rendered = renderer.render(spec.template_name, variables)
        unresolved_template_vars, unresolved_braces = _unresolved_placeholders(rendered.content)
        if unresolved_template_vars or unresolved_braces:
            failures.append(
                {
                    "prompt_id": prompt_id,
                    "template": spec.template_name,
                    "dollar_vars": unresolved_template_vars,
                    "brace_vars": unresolved_braces,
                }
            )

    assert failures == []


def test_all_prompt_templates_render_with_sample_variables():
    renderer = PromptRenderer()
    failures = []
    rendered_template_names = set()

    for path in sorted(default_prompts_dir().glob("*.txt")):
        template_name = path.stem
        source = path.read_text(encoding="utf-8")
        required_vars = Template(source).get_identifiers()
        missing_sample_vars = sorted(set(required_vars) - set(SAMPLE_PROMPT_VARS))
        if missing_sample_vars:
            failures.append(
                {
                    "template": template_name,
                    "missing_sample_vars": missing_sample_vars,
                }
            )
            continue

        variables = {name: SAMPLE_PROMPT_VARS[name] for name in required_vars}
        rendered = renderer.render(template_name, variables)
        rendered_template_names.add(template_name)
        unresolved_template_vars, unresolved_braces = _unresolved_placeholders(rendered.content)
        if unresolved_template_vars or unresolved_braces:
            failures.append(
                {
                    "template": template_name,
                    "dollar_vars": unresolved_template_vars,
                    "brace_vars": unresolved_braces,
                }
            )

    assert "chat_project_assistant" in rendered_template_names
    assert failures == []


def test_registered_prompts_have_static_metadata():
    assert PROMPT_REGISTRY

    for prompt_id, spec in PROMPT_REGISTRY.items():
        assert spec.prompt_id == prompt_id
        assert spec.version.strip()
        assert spec.output_type in {"json", "plain_text", "chat"}


def test_json_prompts_have_parser_or_response_format_expectation():
    json_prompt_ids = {
        prompt_id
        for prompt_id, spec in PROMPT_REGISTRY.items()
        if spec.output_type == "json"
    }

    assert json_prompt_ids == set(JSON_PROMPT_CALL_SITE_FILES) | REGISTRY_ONLY_JSON_PROMPTS

    for prompt_id, expected_files in JSON_PROMPT_CALL_SITE_FILES.items():
        actual_files = _production_call_site_files(prompt_id)
        assert actual_files == expected_files
        for relative_file in actual_files:
            source = _backend_file(relative_file).read_text(encoding="utf-8")
            assert (
                'response_format={"type": "json_object"}' in source
                or "parse_json(" in source
            )

    for prompt_id in REGISTRY_ONLY_JSON_PROMPTS:
        assert _production_call_site_files(prompt_id) == set()


def test_active_production_prompts_do_not_contain_todo_tbd_or_unresolved_braces():
    renderer = PromptRenderer()
    failures = []

    for prompt_id, spec in PROMPT_REGISTRY.items():
        variables = {name: SAMPLE_PROMPT_VARS[name] for name in spec.required_vars}
        rendered = renderer.render(spec.template_name, variables)
        if re.search(r"\b(TODO|TBD)\b", rendered.content, re.IGNORECASE):
            failures.append(f"{prompt_id}: contains TODO/TBD")
        unresolved_braces = re.findall(r"{{[^{}]+}}", rendered.content)
        if unresolved_braces:
            failures.append(f"{prompt_id}: unresolved {unresolved_braces}")

    assert failures == []


def test_no_prompt_template_contains_todo_or_tbd():
    failures = []

    for path in sorted(default_prompts_dir().glob("*.txt")):
        content = path.read_text(encoding="utf-8")
        if re.search(r"\b(TODO|TBD)\b", content, re.IGNORECASE):
            failures.append(path.name)

    assert failures == []


def test_backend_app_has_no_large_inline_prompt_constants():
    suspicious = []

    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = _relative_backend_path(path)
        if relative_path in ALLOWED_INLINE_PROMPT_FILES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        docstring_node_ids = _docstring_constant_node_ids(tree)
        for value, lineno, node_id in _string_literals(tree):
            if node_id in docstring_node_ids:
                continue
            if _looks_like_inline_prompt(value):
                suspicious.append(f"{relative_path}:{lineno}")

    assert suspicious == []


def _production_call_site_files(prompt_id: str) -> set[str]:
    files = set()
    for path in APP_ROOT.rglob("*.py"):
        relative_path = _relative_backend_path(path)
        if relative_path == "backend/app/prompting/registry.py":
            continue
        if prompt_id in path.read_text(encoding="utf-8"):
            files.add(relative_path)
    return files


def _unresolved_placeholders(content: str) -> tuple[list[str], list[str]]:
    return (
        Template(content).get_identifiers(),
        re.findall(r"{{[^{}]+}}", content),
    )


def _backend_file(relative_path: str) -> Path:
    return BACKEND_ROOT.parent / relative_path


def _relative_backend_path(path: Path) -> str:
    return path.relative_to(BACKEND_ROOT.parent).as_posix()


def _docstring_constant_node_ids(tree: ast.AST) -> set[int]:
    node_ids = set()
    nodes = [tree]
    nodes.extend(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef, ast.FunctionDef))
    )
    for node in nodes:
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                node_ids.add(id(first.value))
    return node_ids


def _string_literals(tree: ast.AST) -> list[tuple[str, int, int]]:
    literals = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.append((node.value, node.lineno, id(node)))
        elif isinstance(node, ast.JoinedStr):
            literal_parts = [
                part.value
                for part in node.values
                if isinstance(part, ast.Constant) and isinstance(part.value, str)
            ]
            if literal_parts:
                literals.append(("".join(literal_parts), node.lineno, id(node)))
    return literals


def _looks_like_inline_prompt(value: str) -> bool:
    normalized = value.strip()
    if not normalized:
        return False
    is_large = len(normalized) >= 500 or normalized.count("\n") >= 4
    if not is_large:
        return False
    return any(keyword in normalized for keyword in INLINE_PROMPT_KEYWORDS)

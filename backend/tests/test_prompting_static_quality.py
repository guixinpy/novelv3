import ast
import inspect
import re
from pathlib import Path
from string import Template

from app.core.prompt_manager import PromptManager
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
    "language": "zh-CN",
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

JSON_PROMPT_CALL_SITE_CONTRACTS = {
    "setup.generate": {("backend/app/api/setups.py", "_build_setup_call_payload", "generate_setup")},
    "storyline.generate": {("backend/app/api/storylines.py", "_build_storyline_call_payload", "generate_storyline")},
    "outline.generate": {("backend/app/api/outlines.py", "_build_outline_call_payload", "generate_outline")},
    "athena.extract_l2": {("backend/app/core/l2_extractor.py", "extract", "extract")},
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


def test_allowed_inline_prompt_files_matches_phase_7_plan():
    assert ALLOWED_INLINE_PROMPT_FILES == {
        "backend/app/prompting/registry.py",
        "backend/app/prompting/providers/style.py",
        "backend/app/prompting/providers/few_shot.py",
    }


def test_inline_prompt_scanner_does_not_skip_allowed_files(tmp_path):
    app_root = tmp_path / "backend" / "app"
    allowed_file = app_root / "prompting" / "providers" / "style.py"
    allowed_file.parent.mkdir(parents=True)
    allowed_file.write_text(
        'INLINE_PROMPT = """你是一个写作助手。\n'
        "请严格分析以下章节内容，并按 JSON 返回。\n"
        "输出要求：列出人物、事件、冲突、伏笔、世界规则。\n"
        "回答要求：不要闲聊，不要解释过程。\n"
        "章节内容：" + ("这是一段测试文本。" * 80) + '"""\n',
        encoding="utf-8",
    )

    suspicious = _scan_large_inline_prompt_constants(
        app_root=app_root,
        backend_parent=tmp_path,
    )

    assert suspicious == ["backend/app/prompting/providers/style.py:1"]


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
        unresolved_template_vars, unresolved_braces = _unresolved_placeholders(rendered.content)
        if unresolved_template_vars or unresolved_braces:
            failures.append(
                {
                    "template": template_name,
                    "dollar_vars": unresolved_template_vars,
                    "brace_vars": unresolved_braces,
                }
            )

    assert failures == []


def test_all_active_prompt_templates_are_registered():
    prompt_templates = {path.stem for path in default_prompts_dir().glob("*.txt")}
    registered_templates = {spec.template_name for spec in PROMPT_REGISTRY.values()}

    assert prompt_templates == registered_templates


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
        actual_contracts = _production_json_prompt_call_contracts(prompt_id)
        assert actual_contracts == JSON_PROMPT_CALL_SITE_CONTRACTS[prompt_id]
        for relative_file, _builder_name, consumer_name in actual_contracts:
            consumer = _function_node(_backend_file(relative_file), consumer_name)
            assert consumer is not None
            assert _has_json_response_format(consumer)
            assert _has_parse_json_call(consumer)

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
    suspicious = _scan_large_inline_prompt_constants(
        app_root=APP_ROOT,
        backend_parent=BACKEND_ROOT.parent,
    )
    assert suspicious == []


def test_prompt_manager_is_legacy_and_not_used_by_production_code():
    doc = (inspect.getdoc(PromptManager) or "").lower()
    assert "legacy compatibility wrapper" in doc
    assert "promptassembler" in doc

    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = _relative_backend_path(path)
        if relative_path == "backend/app/core/prompt_manager.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if _uses_prompt_manager(tree):
            offenders.append(relative_path)

    assert offenders == []


def test_static_prompt_guards_ignore_comments_and_docstrings():
    tree = ast.parse(
        '"""PromptManager setup.generate parse_json( response_format={\\"type\\": \\"json_object\\"}"""\n'
        "# from app.core.prompt_manager import PromptManager\n"
        "# build_generation_payload('setup.generate', {})\n"
    )

    assert _uses_prompt_manager(tree) is False
    assert _calls_prompt_id(tree, "setup.generate") is False
    assert _has_json_response_or_parser(tree) is False


def test_static_prompt_guards_detect_real_imports_calls_and_json_handling():
    assert _uses_prompt_manager(ast.parse("from app.core import prompt_manager\n")) is True
    assert _uses_prompt_manager(ast.parse("from app.core.prompt_manager import PromptManager\n")) is True
    assert _uses_prompt_manager(ast.parse("from app.core.prompt_manager import *\n")) is True
    assert _uses_prompt_manager(ast.parse("PromptManager().load('generate_setup')\n")) is True

    assert _calls_prompt_id(ast.parse("build_generation_payload('setup.generate', {})\n"), "setup.generate") is True
    assert _calls_prompt_id(ast.parse("PromptAssembler().build(prompt_id='setup.generate')\n"), "setup.generate") is True

    assert _has_json_response_or_parser(ast.parse("ai_service.parse_json(result.content)\n")) is True
    assert _has_json_response_or_parser(
        ast.parse("await ai_service.complete([], response_format={'type': 'json_object'})\n")
    ) is True
    assert _production_json_prompt_call_contracts_from_tree(
        ast.parse(
            "def build_payload():\n"
            "    return build_generation_payload('setup.generate', {})\n\n"
            "async def endpoint():\n"
            "    payload = build_payload()\n"
            "    await ai_service.complete([], response_format={'type': 'json_object'})\n"
            "    return ai_service.parse_json('{}')\n"
        ),
        "setup.generate",
        "backend/app/api/demo.py",
    ) == {("backend/app/api/demo.py", "build_payload", "endpoint")}

    assert _production_json_prompt_call_contracts_from_tree(
        ast.parse(
            "def build_payload():\n"
            "    return build_generation_payload('setup.generate', {})\n\n"
            "async def unprotected():\n"
            "    payload = build_payload()\n"
            "    await ai_service.complete([])\n"
        ),
        "setup.generate",
        "backend/app/api/demo.py",
    ) == {("backend/app/api/demo.py", "build_payload", "<missing_json_consumer>")}


def _uses_prompt_manager(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "app.core":
            if any(alias.name == "prompt_manager" for alias in node.names):
                return True
        if isinstance(node, ast.ImportFrom) and node.module == "app.core.prompt_manager":
            if any(alias.name in {"PromptManager", "*"} for alias in node.names):
                return True
        if isinstance(node, ast.Import):
            if any(alias.name == "app.core.prompt_manager" for alias in node.names):
                return True
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "PromptManager":
                return True
            if isinstance(func, ast.Attribute) and func.attr == "PromptManager":
                return True
    return False


def _calls_prompt_id(tree: ast.AST, prompt_id: str) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if node.args and _string_constant_value(node.args[0]) == prompt_id:
            return True
        for keyword in node.keywords:
            if keyword.arg == "prompt_id" and _string_constant_value(keyword.value) == prompt_id:
                return True
    return False


def _has_json_response_or_parser(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _is_parse_json_call(node):
            return True
        for keyword in node.keywords:
            if keyword.arg == "response_format" and _is_json_object_response_format(keyword.value):
                return True
    return False


def _has_json_response_format(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg == "response_format" and _is_json_object_response_format(keyword.value):
                return True
    return False


def _has_parse_json_call(tree: ast.AST) -> bool:
    return any(
        isinstance(node, ast.Call) and _is_parse_json_call(node)
        for node in ast.walk(tree)
    )


def _is_parse_json_call(node: ast.Call) -> bool:
    return _call_name(node.func) == "parse_json"


def _call_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _is_json_object_response_format(value: ast.AST) -> bool:
    if not isinstance(value, ast.Dict):
        return False
    for key, item in zip(value.keys, value.values, strict=True):
        if _string_constant_value(key) == "type" and _string_constant_value(item) == "json_object":
            return True
    return False


def _string_constant_value(value: ast.AST | None) -> str | None:
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    return None


def _production_call_site_files(prompt_id: str) -> set[str]:
    files = set()
    for path in APP_ROOT.rglob("*.py"):
        relative_path = _relative_backend_path(path)
        if relative_path == "backend/app/prompting/registry.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if _calls_prompt_id(tree, prompt_id):
            files.add(relative_path)
    return files


def _production_json_prompt_call_contracts(prompt_id: str) -> set[tuple[str, str, str]]:
    contracts: set[tuple[str, str, str]] = set()
    for path in APP_ROOT.rglob("*.py"):
        relative_path = _relative_backend_path(path)
        if relative_path == "backend/app/prompting/registry.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        contracts.update(
            _production_json_prompt_call_contracts_from_tree(
                tree,
                prompt_id,
                relative_path,
            )
        )
    return contracts


def _production_json_prompt_call_contracts_from_tree(
    tree: ast.AST,
    prompt_id: str,
    relative_path: str,
) -> set[tuple[str, str, str]]:
    functions = _function_nodes_by_name(tree)
    builders = {
        name
        for name, node in functions.items()
        if _calls_prompt_id(node, prompt_id)
    }
    if not builders:
        return set()

    contracts = set()
    for builder_name in builders:
        json_consumers = {
            name
            for name, node in functions.items()
            if (name == builder_name or _calls_function(node, builder_name))
            and _has_json_response_format(node)
            and _has_parse_json_call(node)
        }
        consumer_name = sorted(json_consumers)[0] if json_consumers else "<missing_json_consumer>"
        contracts.add((relative_path, builder_name, consumer_name))
    return contracts


def _calls_function(tree: ast.AST, function_name: str) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == function_name:
            return True
        if isinstance(func, ast.Attribute) and func.attr == function_name:
            return True
    return False


def _function_node(path: Path, function_name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return _function_nodes_by_name(tree).get(function_name)


def _function_nodes_by_name(tree: ast.AST) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _scan_large_inline_prompt_constants(app_root: Path, backend_parent: Path) -> list[str]:
    suspicious = []

    for path in sorted(app_root.rglob("*.py")):
        relative_path = _relative_backend_path(path, backend_parent)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        docstring_node_ids = _docstring_constant_node_ids(tree)
        for value, lineno, node_id in _string_literals(tree):
            if node_id in docstring_node_ids:
                continue
            if _looks_like_inline_prompt(value):
                suspicious.append(f"{relative_path}:{lineno}")

    return suspicious


def _unresolved_placeholders(content: str) -> tuple[list[str], list[str]]:
    return (
        Template(content).get_identifiers(),
        re.findall(r"{{[^{}]+}}", content),
    )


def _backend_file(relative_path: str) -> Path:
    return BACKEND_ROOT.parent / relative_path


def _relative_backend_path(path: Path, backend_parent: Path = BACKEND_ROOT.parent) -> str:
    return path.relative_to(backend_parent).as_posix()


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

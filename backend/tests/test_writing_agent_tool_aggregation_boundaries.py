import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_tool_registry_remains_descriptor_aggregator_only():
    source = _source("app/services/writing_agent/tool_registry.py")

    assert "AgentToolDescriptor(" not in source
    assert "from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor" not in source
    assert "object_schema" not in source


def test_tool_executor_remains_adapter_aggregator_only():
    source = _source("app/services/writing_agent/tool_executor.py")

    assert "WritingAgentToolAdapter" not in source


def test_agent_tool_descriptor_imports_come_from_descriptor_types():
    offenders = []
    for path in (ROOT / "app/services/writing_agent").glob("*.py"):
        if path.name == "tool_registry.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if _imports_name_from(tree, "app.services.writing_agent.tool_registry", "AgentToolDescriptor"):
            offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == []


def test_tool_context_imports_come_from_adapter_types():
    offenders = []
    for path in (ROOT / "app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if _imports_name_from(tree, "app.services.writing_agent.tool_executor", "WritingAgentToolContext"):
            offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == []


def _imports_name_from(tree: ast.AST, module: str, name: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            if any(alias.name == name for alias in node.names):
                return True
    return False

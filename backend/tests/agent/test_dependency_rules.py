"""依赖方向规则（04-development-rules.md §3）作为测试钉死。

api → agent → tools → domain → models，禁止反向；
agent/ 是通用内核，不依赖任何小说领域模块（CADR-005）。
"""
from __future__ import annotations

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2] / "app"

# 包名 -> 禁止 import 的 app 子包
# agent 是通用内核库：不依赖任何领域模块。
# tools 可向下依赖 domain/models，也可依赖 agent 的类型与注册机制（内核库角色）。
FORBIDDEN = {
    "agent": {"app.api", "app.tools", "app.domain", "app.services", "app.core", "app.schemas", "app.prompting"},
    "tools": {"app.api", "app.services"},
    "domain": {"app.api", "app.agent", "app.tools", "app.services"},
}


def iter_imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module


def violations_for(package: str) -> list[str]:
    forbidden = FORBIDDEN[package]
    found: list[str] = []
    pkg_dir = APP_ROOT / package
    for py_file in pkg_dir.rglob("*.py"):
        for module in iter_imports(py_file):
            if any(module == bad or module.startswith(bad + ".") for bad in forbidden):
                found.append(f"{py_file.relative_to(APP_ROOT.parent)} imports {module}")
    return found


def test_agent_kernel_is_domain_free():
    assert violations_for("agent") == []


def test_tools_do_not_import_upward():
    assert violations_for("tools") == []


def test_domain_does_not_import_upward():
    assert violations_for("domain") == []

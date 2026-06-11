"""默认工具注册表：import 各工具模块触发自注册（CADR-003）。"""
from __future__ import annotations

from app.agent.tooling import ToolRegistry

registry = ToolRegistry()


def build_default_registry() -> ToolRegistry:
    """构建包含全部已实现工具的注册表。每次调用返回同一个模块级实例。"""
    # import 即注册；放在函数内避免循环 import
    from app.tools import chapters, project, retrieval, world  # noqa: F401

    return registry

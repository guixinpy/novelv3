"""M2 存根：tool_registry 原实现依赖 descriptor 层，已删除。"""
from __future__ import annotations

from typing import Any


def get_agent_tool_descriptor(tool_name: str) -> Any | None:
    return None


def list_agent_tool_descriptors() -> list[Any]:
    return []


def internal_tool_names() -> set[str]:
    return set()


def allowed_tool_names() -> set[str]:
    return set()


def non_blocking_report_tool_names() -> set[str]:
    return set()


def target_type_for_tool(tool_name: str) -> str | None:
    return None


def build_agent_tool_plan(*args: Any, **kwargs: Any) -> list[Any]:
    return []

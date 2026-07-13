"""M2 存根：移除了对整个 descriptor-adapter 层的依赖。
原始实现在 git history 中可查，不再需要。
"""
from __future__ import annotations

from typing import Any

from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.tool_adapter_types import WritingAgentToolExecutionResult


_STATIC_TOOL_ADAPTERS: dict[str, Any] = {}


async def execute_writing_agent_tool(
    context: Any,
    tool: WritingAgentToolRequest,
    *,
    preflight_writing: Any | None = None,
) -> WritingAgentToolExecutionResult:
    return WritingAgentToolExecutionResult(handled=False)


def static_writing_agent_tool_adapter_names() -> set[str]:
    return set()


def writing_agent_tool_adapter_metadata(tool_name: str) -> dict[str, Any] | None:
    return None


def writing_agent_tool_adapter_metadata_by_name() -> dict[str, dict[str, Any]]:
    return {}


def unhandled_internal_writing_agent_tool_names() -> set[str]:
    return set()

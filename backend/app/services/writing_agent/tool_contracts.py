"""M2 存根：tool_contracts 原实现依赖 descriptor-adapter 层，已删除。"""
from __future__ import annotations

from typing import Any


def agent_tool_execution_metadata(
    descriptor: Any | None = None,
    adapter_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {"contract_version": "v1", "status": "stub"}


def build_agent_tool_contract_snapshot(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {"contracts": {}, "status": "stub"}

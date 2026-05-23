from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.writing_agent import WritingAgentToolRequest


PreflightWriting = Callable[[str, dict[str, Any]], dict[str, Any]]
StaticToolAdapterOutput = dict[str, Any] | Awaitable[dict[str, Any]]
StaticToolAdapterHandler = Callable[["WritingAgentToolContext", WritingAgentToolRequest], StaticToolAdapterOutput]


@dataclass(frozen=True)
class WritingAgentToolContext:
    db: Session
    project_id: str
    run_id: str | None = None


@dataclass(frozen=True)
class WritingAgentToolExecutionResult:
    handled: bool
    output: dict[str, Any] | None = None


@dataclass(frozen=True)
class WritingAgentToolAdapter:
    tool_name: str
    handler: StaticToolAdapterHandler
    category: str
    mutability: str
    adapter_type: str = "static"

    def to_metadata(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "adapter_type": self.adapter_type,
            "category": self.category,
            "mutability": self.mutability,
            "handler_name": self.handler.__name__,
        }

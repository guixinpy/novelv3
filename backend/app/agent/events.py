"""循环事件：经 event sink 发出，供 SSE 流、会话日志、轨迹记录消费。"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.agent.providers.base import Usage


@dataclass(frozen=True)
class AssistantDelta:
    text: str


@dataclass(frozen=True)
class AssistantMessage:
    content: str
    tool_call_names: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ToolCallStarted:
    id: str
    name: str
    arguments: dict | None


@dataclass(frozen=True)
class ToolCallFinished:
    id: str
    name: str
    is_error: bool
    result_text: str


@dataclass(frozen=True)
class TurnEnded:
    stop_reason: str
    iterations: int
    usage: Usage


LoopEvent = AssistantDelta | AssistantMessage | ToolCallStarted | ToolCallFinished | TurnEnded

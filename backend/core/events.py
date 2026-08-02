"""事件模型：agent 回合的唯一事实流（openclaw 事件协议 / openhuman journal 思想）。

所有消费者（SSE 推送、持久化、观测、分析）消费同一事件流。
事件带稳定 id（{session_id}-evt-{offset}），支持事后重放。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EventKind(StrEnum):
    AGENT_START = "agent_start"
    TURN_START = "turn_start"
    ASSISTANT_DELTA = "assistant_delta"
    ASSISTANT_MESSAGE = "assistant_message"
    TOOL_STARTED = "tool_started"
    TOOL_FINISHED = "tool_finished"
    GUARD_TRIPPED = "guard_tripped"
    CONTEXT_WARNING = "context_warning"
    COMPACTION = "compaction"
    APPROVAL_PENDING = "approval_pending"
    TURN_ENDED = "turn_ended"
    AGENT_END = "agent_end"


@dataclass(frozen=True)
class LoopEvent:
    kind: EventKind

    def with_id(self, event_id: str) -> LoopEvent:
        object.__setattr__(self, "event_id", event_id)
        return self


@dataclass(frozen=True)
class AgentStart(LoopEvent):
    kind: EventKind = EventKind.AGENT_START
    session_id: str = ""


@dataclass(frozen=True)
class TurnStart(LoopEvent):
    kind: EventKind = EventKind.TURN_START
    turn_index: int = 0


@dataclass(frozen=True)
class AssistantDelta(LoopEvent):
    kind: EventKind = EventKind.ASSISTANT_DELTA
    text: str = ""


@dataclass(frozen=True)
class AssistantMessage(LoopEvent):
    kind: EventKind = EventKind.ASSISTANT_MESSAGE
    content: str = ""
    tool_call_names: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ToolStarted(LoopEvent):
    kind: EventKind = EventKind.TOOL_STARTED
    call_id: str = ""
    name: str = ""
    arguments: dict | None = None


@dataclass(frozen=True)
class ToolFinished(LoopEvent):
    kind: EventKind = EventKind.TOOL_FINISHED
    call_id: str = ""
    name: str = ""
    is_error: bool = False
    result_text: str = ""
    # 失败分类（ClassifiedFailure）——失败进事件，可观测与可恢复同源
    error_code: str = ""
    next_action: str = ""


@dataclass(frozen=True)
class GuardTripped(LoopEvent):
    kind: EventKind = EventKind.GUARD_TRIPPED
    level: str = ""
    reason: str = ""
    diagnosis: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ContextWarning(LoopEvent):
    kind: EventKind = EventKind.CONTEXT_WARNING
    usage_pct: float = 0.0
    total_tokens: int = 0
    max_tokens: int = 0


@dataclass(frozen=True)
class Compaction(LoopEvent):
    kind: EventKind = EventKind.COMPACTION
    before_count: int = 0
    after_count: int = 0
    summary: str = ""


@dataclass(frozen=True)
class ApprovalPending(LoopEvent):
    kind: EventKind = EventKind.APPROVAL_PENDING
    call_id: str = ""
    name: str = ""
    arguments: dict | None = None


@dataclass(frozen=True)
class TurnEnded(LoopEvent):
    kind: EventKind = EventKind.TURN_ENDED
    stop_reason: str = ""
    iterations: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    exit_detail: dict = field(default_factory=dict)


@dataclass(frozen=True)
class AgentEnd(LoopEvent):
    kind: EventKind = EventKind.AGENT_END
    turns: int = 0

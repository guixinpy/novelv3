from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TraceSourceOut(BaseModel):
    source_type: str
    source_id: str | None = None
    label: str | None = None
    chapter_index: int | None = None
    source_ref: str | None = None
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextBlockOut(BaseModel):
    key: str
    kind: str
    title: str = ""
    content: str
    sources: list[TraceSourceOut] = Field(default_factory=list)
    char_count: int
    token_estimate: int
    original_char_count: int | None = None
    truncated: bool = False


class ModelCallTraceListItem(BaseModel):
    id: str
    project_id: str
    trace_type: str
    status: str
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int | None = None
    error_message: str | None = None
    dialog_id: str | None = None
    request_message_id: str | None = None
    response_message_id: str | None = None
    chapter_id: str | None = None
    chapter_index: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ModelCallTraceDetail(ModelCallTraceListItem):
    temperature: float | None = None
    max_tokens: int | None = None
    messages: list[dict[str, Any]] = Field(default_factory=list)
    context_blocks: list[ContextBlockOut] = Field(default_factory=list)
    trace_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("messages", mode="before")
    @classmethod
    def normalize_nullable_lists(cls, value):
        return [] if value is None else value

    @field_validator("context_blocks", mode="before")
    @classmethod
    def normalize_context_blocks(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            return []

        normalized_blocks = []
        for index, block in enumerate(value):
            if not isinstance(block, dict):
                content = str(block or "")
                normalized_blocks.append(
                    {
                        "key": f"block-{index}",
                        "kind": "unknown",
                        "title": f"block-{index}",
                        "content": content,
                        "sources": [],
                        "char_count": len(content),
                        "token_estimate": 0,
                        "truncated": False,
                    }
                )
                continue

            normalized = dict(block)
            key = str(normalized.get("key") or f"block-{index}")
            content = str(normalized.get("content") or "")
            title = str(normalized.get("title") or key or "上下文块")
            sources = normalized.get("sources")
            if not isinstance(sources, list):
                sources = []

            normalized["key"] = key
            normalized["kind"] = str(normalized.get("kind") or "unknown")
            normalized["title"] = title
            normalized["content"] = content
            normalized["sources"] = [
                _normalize_trace_source(source)
                for source in sources
            ]
            normalized["char_count"] = len(content)
            normalized["token_estimate"] = normalized.get("token_estimate") or 0
            normalized["truncated"] = bool(normalized.get("truncated"))
            normalized_blocks.append(normalized)
        return normalized_blocks

    @field_validator("trace_metadata", mode="before")
    @classmethod
    def normalize_nullable_dict(cls, value):
        return {} if value is None else value


def _normalize_trace_source(source: Any) -> dict[str, Any]:
    if isinstance(source, dict):
        normalized = dict(source)
        normalized["source_type"] = str(normalized.get("source_type") or "Unknown")
        return normalized
    return {
        "source_type": "Unknown",
        "label": str(source),
    }


class PaginatedModelCallTraces(BaseModel):
    total: int
    items: list[ModelCallTraceListItem]

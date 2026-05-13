from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class PromptMetadataOut(BaseModel):
    prompt_id: str | None = None
    prompt_version: str | None = None
    template_name: str | None = None
    template_hash: str | None = None


class PromptBudgetOut(BaseModel):
    max_context_chars: int | None = None
    requested_context_chars: int = 0
    used_context_chars: int = 0
    remaining_context_chars: int = 0
    included_blocks: int = 0
    omitted_blocks: int = 0
    omitted_block_keys: list[str] = Field(default_factory=list)
    truncated_blocks: list[str] = Field(default_factory=list)
    has_omitted_blocks: bool = False
    has_truncated_blocks: bool = False

    @model_validator(mode="after")
    def derive_flags(self):
        self.has_omitted_blocks = (
            self.has_omitted_blocks
            or self.omitted_blocks > 0
            or bool(self.omitted_block_keys)
        )
        self.has_truncated_blocks = self.has_truncated_blocks or bool(self.truncated_blocks)
        return self


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
    prompt_metadata: PromptMetadataOut | None = None
    prompt_budget: PromptBudgetOut | None = None

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
        return value if isinstance(value, dict) else {}

    @model_validator(mode="after")
    def derive_prompt_fields(self):
        if self.prompt_metadata is None:
            self.prompt_metadata = _derive_prompt_metadata(self.trace_metadata)
        if self.prompt_budget is None:
            self.prompt_budget = _derive_prompt_budget(self.trace_metadata)
        return self


def _normalize_trace_source(source: Any) -> dict[str, Any]:
    if isinstance(source, dict):
        normalized = dict(source)
        normalized["source_type"] = str(normalized.get("source_type") or "Unknown")
        return normalized
    return {
        "source_type": "Unknown",
        "label": str(source),
    }


def _derive_prompt_metadata(trace_metadata: dict[str, Any]) -> PromptMetadataOut | None:
    fields = {
        "prompt_id": _string_or_none(trace_metadata.get("prompt_id")),
        "prompt_version": _string_or_none(trace_metadata.get("prompt_version")),
        "template_name": _string_or_none(trace_metadata.get("template_name")),
        "template_hash": _string_or_none(trace_metadata.get("template_hash")),
    }
    if not any(fields.values()):
        return None
    return PromptMetadataOut(**fields)


def _derive_prompt_budget(trace_metadata: dict[str, Any]) -> PromptBudgetOut | None:
    budget = trace_metadata.get("budget")
    if not isinstance(budget, dict):
        return None

    omitted_block_keys = _string_list(budget.get("omitted_block_keys"))
    truncated_blocks = _string_list(budget.get("truncated_blocks"))
    omitted_blocks = _int_or_zero(budget.get("omitted_blocks"))

    return PromptBudgetOut(
        max_context_chars=_int_or_none(budget.get("max_context_chars")),
        requested_context_chars=_int_or_zero(budget.get("requested_context_chars")),
        used_context_chars=_int_or_zero(budget.get("used_context_chars")),
        remaining_context_chars=_int_or_zero(budget.get("remaining_context_chars")),
        included_blocks=_int_or_zero(budget.get("included_blocks")),
        omitted_blocks=omitted_blocks,
        omitted_block_keys=omitted_block_keys,
        truncated_blocks=truncated_blocks,
        has_omitted_blocks=omitted_blocks > 0 or bool(omitted_block_keys),
        has_truncated_blocks=bool(truncated_blocks),
    )


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None and str(item)]


def _int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _int_or_zero(value: Any) -> int:
    return _int_or_none(value) or 0


class PaginatedModelCallTraces(BaseModel):
    total: int
    items: list[ModelCallTraceListItem]

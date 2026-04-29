from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PromptSpec:
    prompt_id: str
    version: str
    template_name: str
    output_type: str
    required_vars: tuple[str, ...] = ()
    model_defaults: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RenderedTemplate:
    template_name: str
    content: str
    template_hash: str


@dataclass(frozen=True)
class PromptModelParams:
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PromptBudgetReport:
    max_context_chars: int
    included_blocks: int
    omitted_blocks: int
    omitted_block_keys: list[str] = field(default_factory=list)
    truncated_blocks: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PromptBuildResult:
    prompt_id: str
    version: str
    template_name: str
    output_type: str
    required_vars: tuple[str, ...]
    model_defaults: dict[str, Any]
    content: str
    template_hash: str
    messages: list[dict[str, Any]]
    context_blocks: list[dict[str, Any]]
    budget_report: PromptBudgetReport | None = None

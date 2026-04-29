from copy import deepcopy
from collections.abc import Callable
from typing import Any

from app.prompting.budget import PromptBudgeter
from app.prompting.contracts import PromptBuildResult
from app.prompting.registry import PROMPT_REGISTRY
from app.prompting.renderer import PromptRenderer
from app.prompting.tracing import build_prompt_trace_metadata


class PromptAssembler:
    def __init__(
        self,
        renderer: PromptRenderer | None = None,
        budgeter: PromptBudgeter | None = None,
    ):
        self.renderer = renderer or PromptRenderer()
        self.budgeter = budgeter or PromptBudgeter()

    def build(
        self,
        prompt_id: str,
        variables: dict | None = None,
        context_blocks: list[dict[str, Any]] | None = None,
        max_context_chars: int | None = None,
        messages: list[dict[str, Any]] | None = None,
    ) -> PromptBuildResult:
        if prompt_id not in PROMPT_REGISTRY:
            raise KeyError(prompt_id)

        spec = PROMPT_REGISTRY[prompt_id]
        self._validate_required_vars(spec.required_vars, variables)
        rendered = self.renderer.render(spec.template_name, variables)
        budget_report = None
        kept_context_blocks = list(context_blocks or [])

        if context_blocks is not None and max_context_chars is not None:
            kept_context_blocks, budget_report = self.budgeter.apply(
                context_blocks,
                max_context_chars,
            )

        if messages is not None:
            prompt_messages = messages
        else:
            prompt_messages = [
                {
                    "role": "user",
                    "content": self._message_content_with_context(
                        rendered.content,
                        kept_context_blocks,
                    ),
                }
            ]

        return PromptBuildResult(
            prompt_id=spec.prompt_id,
            version=spec.version,
            template_name=spec.template_name,
            output_type=spec.output_type,
            required_vars=spec.required_vars,
            model_defaults=deepcopy(spec.model_defaults),
            content=rendered.content,
            template_hash=rendered.template_hash,
            messages=prompt_messages,
            context_blocks=kept_context_blocks,
            budget_report=budget_report,
        )

    def _validate_required_vars(
        self,
        required_vars: tuple[str, ...],
        variables: dict | None,
    ) -> None:
        provided = variables or {}
        missing = [name for name in required_vars if name not in provided]
        if missing:
            raise ValueError(f"Missing prompt variables: {', '.join(missing)}")

    def _message_content_with_context(
        self,
        content: str,
        context_blocks: list[dict[str, Any]],
    ) -> str:
        if not context_blocks:
            return content

        parts = [content, "【上下文】"]
        for block in context_blocks:
            title = block.get("title") or block.get("key") or "context"
            block_content = str(block.get("content", ""))
            parts.append(f"【{title}】\n{block_content}")
        return "\n\n".join(parts)


def build_generation_payload(
    prompt_id: str,
    variables: dict | None,
    *,
    trace_context_blocks: list[dict[str, Any]] | Callable[[str], list[dict[str, Any]]] | None = None,
    command_args: str | None = None,
    max_tokens: int = 4000,
) -> dict[str, Any]:
    build_result = PromptAssembler().build(prompt_id, variables)
    prompt = build_result.content
    if command_args and command_args.strip():
        prompt = f"{prompt}\n\n附加要求：{command_args.strip()}"
    if callable(trace_context_blocks):
        context_blocks = trace_context_blocks(build_result.content)
    else:
        context_blocks = list(trace_context_blocks or [])

    return {
        "messages": [{"role": "user", "content": prompt}],
        "context_blocks": context_blocks,
        "max_tokens": max_tokens,
        "trace_metadata": build_prompt_trace_metadata(build_result),
        "rendered_prompt": build_result.content,
    }

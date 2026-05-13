from copy import deepcopy
from typing import Any

from app.core.model_call_trace import estimate_tokens
from app.prompting.contracts import PromptBudgetReport


class PromptBudgeter:
    def apply(
        self,
        blocks: list[dict[str, Any]],
        max_chars: int,
    ) -> tuple[list[dict[str, Any]], PromptBudgetReport]:
        remaining = max(0, max_chars)
        requested_chars = sum(len(self._block_content(block)) for block in blocks)
        selected: dict[int, dict[str, Any]] = {}
        omitted_keys: list[str] = []
        truncated_keys: list[str] = []

        ordered = sorted(
            enumerate(blocks),
            key=lambda item: (item[1].get("priority", 100), item[0]),
        )

        for index, block in ordered:
            key = self._block_key(block, index)
            content = self._block_content(block)

            if len(content) <= remaining:
                if remaining == 0:
                    omitted_keys.append(key)
                    continue
                selected[index] = self._copy_block_with_content(block, content)
                remaining -= len(content)
                continue

            if remaining > 0:
                kept = self._copy_block_with_content(
                    block,
                    content[:remaining],
                    budget_truncated=True,
                    original_char_count=len(content),
                )
                selected[index] = kept
                truncated_keys.append(key)
                remaining = 0
                continue

            omitted_keys.append(key)

        kept_blocks = [selected[index] for index in sorted(selected)]
        used_chars = sum(len(self._block_content(block)) for block in kept_blocks)
        report = PromptBudgetReport(
            max_context_chars=max_chars,
            included_blocks=len(kept_blocks),
            omitted_blocks=len(omitted_keys),
            requested_context_chars=requested_chars,
            used_context_chars=used_chars,
            remaining_context_chars=remaining,
            omitted_block_keys=omitted_keys,
            truncated_blocks=truncated_keys,
        )
        return kept_blocks, report

    def _block_key(self, block: dict[str, Any], index: int) -> str:
        key = block.get("key", index)
        return str(key)

    def _block_content(self, block: dict[str, Any]) -> str:
        if "content" not in block:
            return ""
        return str(block["content"])

    def _copy_block_with_content(
        self,
        block: dict[str, Any],
        content: str,
        *,
        budget_truncated: bool = False,
        original_char_count: int | None = None,
    ) -> dict[str, Any]:
        copied = deepcopy(block)
        copied["content"] = content
        if budget_truncated:
            copied["char_count"] = len(content)
            copied["token_estimate"] = estimate_tokens(content)
            copied["original_char_count"] = max(
                self._safe_int(block.get("original_char_count")),
                original_char_count or len(content),
            )
            copied["truncated"] = True
        return copied

    def _safe_int(self, value: Any) -> int:
        if isinstance(value, bool):
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

# Phase 150 - Bound dialog compaction prompts

## Goal

Keep `/compact` usable after long writing sessions with large dialog histories.

## Why

Compaction may run after many regular chat turns. Sending every post-summary plain message verbatim to the model can create an oversized prompt, slow down the operation, or exceed model context limits. The command should still compact all selected messages, but the model input must be bounded.

## TDD

RED:

- Added a long-history compaction test with 180 verbose messages.
- The test asserts the prompt variable `dialog_lines` is capped at 12,000 characters, marks omitted older messages, preserves the latest message, and keeps `compacted_count` at 180.
- It failed because the old implementation generated about 75,000 characters.

GREEN:

- `_build_dialog_lines` now returns the original small-history text unchanged.
- Long histories are reduced to a bounded recent window with an omission notice.
- A single oversized latest line is truncated rather than exceeding the prompt cap.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_compaction_summary_bounds_dialog_lines_for_long_history -q` -> 1 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q` -> 46 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> 572 passed
- `.\backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup` -> passed, retrieval reindex 11,625 ms, elapsed 12,582 ms
- `git diff --check` -> passed
- Exact DeepSeek key scan -> no matches

# Phase 152 - Bound dialog history in model payloads

## Goal

Prevent long chat messages from overflowing Hermes/Athena model-call payloads.

## Why

The model call only includes the latest eight dialog messages, but any one message can contain a chapter-sized draft or long assistant reply. Without a per-message cap, recent history can still dominate the prompt and destabilize long sessions.

## TDD

RED:

- Added a payload test with two very long Athena dialog history messages.
- The test asserts model history messages after the system prompt are individually capped and include a truncation notice.
- It failed because the full long message content was passed through unchanged.

GREEN:

- `build_dialog_history_messages` now applies a 2,000-character cap per history item.
- `build_dialog_history_block` uses the same bounded content, keeping trace/context blocks aligned with model messages.
- Short dialog history remains unchanged.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_dialog.py::test_dialog_chat_payload_bounds_long_history_messages -q` -> 1 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_dialog.py backend\tests\test_prompting_dialog_migration.py -q` -> 26 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> 574 passed
- `.\backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup` -> passed, retrieval reindex 10,934 ms, elapsed 11,857 ms
- `git diff --check` -> passed
- Exact DeepSeek key scan -> no matches

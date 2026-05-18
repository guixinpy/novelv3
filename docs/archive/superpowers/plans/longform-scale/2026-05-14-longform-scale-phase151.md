# Phase 151 - Bound dialog message list payloads

## Goal

Keep Hermes and Athena chat history loading stable when recent messages contain long drafts or model responses.

## Why

The message list endpoints already page to the latest 80 messages, but each message body was returned in full. Long writing sessions can include chapter-sized messages, making chat reloads and workspace hydration heavier than needed. The dialog message service already supported bounded previews; the public message endpoints now use it by default.

## TDD

RED:

- Added a test that seeds both Hermes and Athena dialogs with a long assistant message.
- The test asserts both message endpoints return `content_truncated`, `original_content_length`, and a shorter preview by default.
- It failed because both endpoints returned the full content without truncation metadata.

GREEN:

- Hermes `/dialog/projects/{project_id}/messages` now defaults to `DEFAULT_MESSAGE_CONTENT_PREVIEW_CHARS`.
- Athena `/projects/{project_id}/athena/dialog/messages` uses the same default.
- Both endpoints expose `full_content=true` for explicit full-content reads and `max_content_chars` for bounded tuning.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_get_messages_defaults_to_bounded_content_preview -q` -> 1 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q` -> 47 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> 573 passed
- `.\backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup` -> passed, retrieval reindex 11,802 ms, elapsed 12,773 ms
- `git diff --check` -> passed
- Exact DeepSeek key scan -> no matches

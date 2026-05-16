# Phase 236: Deterministic Dialog History Window

## Goal

Make prompt dialog history selection deterministic when multiple messages share the same timestamp, so long-running Athena/Hermes chats consistently include the latest messages.

## RED

- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_athena_dialog.py::test_dialog_history_messages_use_id_tie_breaker_for_same_timestamp -q`
  - Failed because the history query sorted only by `created_at DESC`; same-timestamp rows returned the earliest inserted messages instead of the latest ids.

## GREEN

- Added `DialogMessage.id.desc()` as a tie-breaker in `_latest_dialog_history()`.
- The query still fetches a bounded window and still projects bounded content.

## Verification

- Targeted backend test passes after implementation.
- Full backend, frontend build, frontend unit tests, whitespace diff check, and key scan are required before commit.

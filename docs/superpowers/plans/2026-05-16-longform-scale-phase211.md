# Longform Scale Phase 211 - Bound Dialog Compaction Message Projection

## Goal

Keep `/compact` stable for long Hermes/Athena dialog histories.

## Problem

`select_compactable_plain_messages()` returned full `DialogMessage` ORM rows for every plain message after the latest summary. `build_compaction_summary()` later bounds the prompt to 12k characters, but the database query could still transfer and materialize very large message bodies first.

## Change

- Added `COMPACTION_MESSAGE_CONTENT_QUERY_CHARS = 2000`.
- `select_compactable_plain_messages()` now projects only the fields needed by compaction and deletion:
  - `id`
  - `role`
  - `message_type`
  - bounded `content`
  - `action_result`
- The query uses `substr(DialogMessage.content, 1, 2000)` so long message bodies are bounded before Python materialization.

## Regression Test

- `test_select_compactable_plain_messages_projects_bounded_content_preview` verifies:
  - selected compactable rows still expose `id`, `role`, `action_result`, and `content`;
  - returned content is bounded to 2000 characters;
  - SQL no longer selects `dialog_messages.content AS ...` as a full ORM column.

## Verification

Initial verification:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py::test_select_compactable_plain_messages_projects_bounded_content_preview -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py -q
```

Results:

- Regression test: `1 passed`
- Dialog tests: `48 passed`

Full verification is run before commit.

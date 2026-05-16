# Phase 222: Bound Dialog Prompt History Loading

## Goal

Avoid loading full `DialogMessage.content` values when building chat prompts from recent dialog history.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_athena_dialog.py::test_dialog_chat_payload_projects_bounded_history_content -q`
  - Failed because the history query selected full message content.
- GREEN: same targeted test passes after projecting `substr(DialogMessage.content, 1, 2001)`.

## Notes

- Existing prompt truncation markers are preserved.
- This reduces memory pressure for long Athena/Hermes conversations.

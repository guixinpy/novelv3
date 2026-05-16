# Phase 223: Lightweight Athena Chat Profile Lookup

## Goal

Avoid loading large `ProjectProfileVersion.profile_payload` values when building Athena chat prompts and context-boundary blocks.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_athena_dialog.py::test_athena_chat_payload_profile_lookup_skips_profile_payload -q`
  - Failed because the dialog provider selected `profile_payload`.
- GREEN: same targeted test passes after projecting only profile id and version.

## Notes

- Athena prompt variables only need the current profile version.
- Context-boundary filters only need profile id and version.

# Phase 221: Lightweight World Context Profile Lookup

## Goal

Avoid loading large `ProjectProfileVersion.profile_payload` values when assembling chapter world context.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_athena_dialog.py::test_chapter_context_profile_lookup_skips_profile_payload -q`
  - Failed because the current profile lookup selected `profile_payload`.
- GREEN: same targeted test passes after applying `load_only` to `WorldContextAssembler._current_profile()`.

## Notes

- Chapter context assembly only needs profile id, project id, version, and contract version.
- This reduces prompt-context overhead on projects with large world-model profile contracts.

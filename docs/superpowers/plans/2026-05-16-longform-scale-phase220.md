# Phase 220: Project Setup Characters for Manual Consistency Checks

## Goal

Remove full `Setup` JSON loading from the manual L1 consistency check endpoint when no world-model profile is active.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_consistency.py::test_consistency_check_uses_setup_character_projection_without_selecting_full_setup_json -q`
  - Failed because the endpoint did not use `json_each(setups.characters)`.
- GREEN: same targeted test passes after switching to the shared setup character projection.

## Notes

- Character state checks still detect dead-character appearances.
- This aligns manual checks with chapter generation and background checks.

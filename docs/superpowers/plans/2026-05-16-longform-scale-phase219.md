# Phase 219: Project Setup Characters for Background Checks

## Goal

Remove full `Setup` JSON loading from the background deep consistency checker so batch checks over long projects do not repeatedly materialize large setup payloads.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_background_analyzer.py::test_deep_check_uses_setup_character_projection_without_selecting_full_setup_json -q`
  - Failed because deep checks did not use `json_each(setups.characters)`.
- GREEN: same targeted test passes after switching to the shared setup character projection.

## Notes

- Existing checkers still receive character name/status/alias data.
- Full world-building and core-concept setup fields are not selected in this path.

# Phase 218: Project Setup Characters for Athena Analysis

## Goal

Avoid full `Setup` JSON loading when Athena chapter analysis falls back to setup characters because a world-model profile exists but no canonical characters have been imported yet.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_athena_longform.py::test_analyze_chapter_uses_bounded_setup_character_projection_when_world_model_has_no_characters -q`
  - Failed because the analyzer did not use `json_each(setups.characters)`.
- GREEN: same targeted test passes after adding a shared setup character projection helper.

## Notes

- The helper reads only character name, status, ref, aliases, and names.
- Chapter generation consistency checks now use the same projection helper.

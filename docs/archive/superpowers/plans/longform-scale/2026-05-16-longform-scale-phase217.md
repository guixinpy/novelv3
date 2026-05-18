# Phase 217: Bound Chapter Setup Loading

## Goal

Remove full `Setup` JSON row loading from chapter generation, including prompt setup context, world-model fallback context, and the legacy consistency check.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_chapters.py::test_generate_chapter_uses_bounded_setup_context_without_selecting_full_setup_json -q`
  - Failed because chapter generation did not use lightweight setup projections.
- GREEN: same targeted test passes after:
  - using bounded setup snippets for the chapter prompt,
  - using `json_each(setups.characters)` for consistency characters,
  - using bounded setup fallback context when no world-model profile exists.

## Notes

- The dead-character consistency check still catches the generated chapter fixture.
- The generated prompt keeps readable Chinese setup values while excluding oversized setup noise.

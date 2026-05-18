# Longform Scale Phase 275 - Direct Chapter Generation Target Guard

## Objective

Close the direct chapter generation bypass after Phase 274. Writing controls now stop at the project target, but `/chapters/{index}/generate` could still be called directly for chapter indexes beyond the configured project or outline target.

## Scope

- Added a shared `chapter_target` helper for resolving the effective chapter target from:
  - `Project.target_chapter_count`
  - latest outline `total_chapters` when the project target is empty
- Updated writing controls to use the shared helper instead of local duplicate target logic.
- Updated direct chapter generation to reject target overflow before setup lookup, prompt assembly, model calls, traces, chapter writes, and maintenance side effects.
- Rejection response:
  - HTTP `400`
  - `Chapter index exceeds project target chapter count`

## TDD Evidence

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py -q -k "target_overflow"`
  - Failed because direct generation returned `200` and created chapter 2 for a target of 1.
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py -q -k "target_overflow"`
  - `2 passed, 29 deselected`.
- Related regression: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py backend\tests\test_writing.py -q`
  - `45 passed`.

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `666 passed in 56.61s`.
- `npm run build` in `frontend`
  - `vue-tsc --noEmit && vite build` completed successfully.
- `npm run test:unit -- --run` in `frontend`
  - `64 passed`, `432 passed`.
- `git diff --check`
  - Passed with no output.
- DeepSeek key scan
  - `NO_MATCH`.

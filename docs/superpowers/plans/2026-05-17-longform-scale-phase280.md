# Longform Scale Phase 280 - Chapter Index Lower Bound

## Objective

Prevent invalid chapter indexes from entering long-form writing, retrieval, revision, consistency, and Athena context endpoints. A thousand-chapter project must not allow chapter `0` or negative chapter numbers to create tasks, mask validation as 404s, or trigger downstream side effects.

## Scope

- Added `Path(..., ge=1)` to chapter-index path parameters in core chapter, writing retry, Athena retrieval, longform context, evolution, consistency, outline patch, and revision endpoints.
- Added regression tests for direct generation, direct read, retry, and retrieval chapter indexing.
- Left existing upper-bound target checks unchanged.

## TDD Evidence

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py backend\tests\test_writing.py backend\tests\test_athena_retrieval.py -q -k "non_positive_chapter_index"`
  - Failed because invalid generation returned API-key error, reads and retrieval returned 404, and retry created a task.
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py backend\tests\test_writing.py backend\tests\test_athena_retrieval.py -q -k "non_positive_chapter_index"`
  - `4 passed, 92 deselected`.
- Related regression: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py backend\tests\test_writing.py backend\tests\test_athena_retrieval.py backend\tests\test_outlines.py backend\tests\test_chapter_revisions.py backend\tests\test_consistency.py backend\tests\test_athena_evolution_generation_windows.py backend\tests\test_longform_scale.py -q`
  - `177 passed`.

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `678 passed in 63.16s`.
- `npm run build` in `frontend`
  - Passed (`vue-tsc --noEmit && vite build`).
- `npm run test:unit -- --run` in `frontend`
  - `64 passed`; `432 passed`.
- `git diff --check`
  - Passed.
- DeepSeek key scan
  - `NO_MATCH`.

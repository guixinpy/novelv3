# Longform Scale Phase 278 - Retry Task Target Guard

## Objective

Keep manual chapter retry controls stable for long-running projects. After a target chapter count changes, retry must not enqueue work beyond the active target. Repeated retry clicks for the same chapter should reuse the active task instead of stacking duplicate background work.

## Scope

- Added target chapter guard to `POST /api/v1/projects/{project_id}/writing/chapters/{chapter_index}/retry`.
- Added active retry task reuse for the same project and chapter.
- Left valid in-target retry behavior unchanged.

## TDD Evidence

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q -k "retry"`
  - Failed because retry beyond project target returned `200`, and repeated retry created two active tasks.
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q -k "retry"`
  - `5 passed, 11 deselected`.
- Related regression: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py backend\tests\test_chapters.py backend\tests\test_projects.py -q`
  - `61 passed`.

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `672 passed in 86.27s`.
- `npm run build` in `frontend`
  - Passed (`vue-tsc --noEmit && vite build`).
- `npm run test:unit -- --run` in `frontend`
  - `64 passed`; `432 passed`.
- `git diff --check`
  - Passed.
- DeepSeek key scan
  - `NO_MATCH`.
